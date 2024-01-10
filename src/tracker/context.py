import os
import shutil
import uuid
from datetime import datetime
from typing import List, Any
from fastapi import UploadFile

from action.base import ResponseMessageType
from nlu.intent_with_entity import Entity, Intent
from collections import deque

from loguru import logger

from third_system.search_entity import SearchResponse


def prepare_response_content(answer):
    if not answer:
        return "Jump out"
    elif answer.messageType == ResponseMessageType.FORMAT_TEXT:
        return answer.content
    elif answer.messageType == ResponseMessageType.FORMAT_INTELLIGENT_EXEC:
        return (
            f"已为您完成 {answer.content.businessInfo['instruction']}"
            if answer.content.businessInfo["instruction"]
            else "ok"
        )
    else:
        return ""


class History:
    def __init__(self, rounds: List[dict[str, Any]], max_history: int = 6):
        self.max_history = max_history
        self.rounds = rounds[-self.max_history :]

    def add_history(self, role: str, message: str):
        if len(self.rounds) >= self.max_history:
            self.rounds.pop(0)
        self.rounds.append({"role": role, "content": message})

    def format_string(self):
        return "\n".join([f'{entry["role"]}: {entry["content"]}' for entry in self.rounds])

    def format_messages(self):
        return [{"role": entry["role"], "content": entry["content"]} for entry in self.rounds]


class ConversationFiles:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.file_dir = os.path.join(os.path.dirname(__file__), "../tmp", self.session_id)
        self.filenames = []

    def add_files(self, files: list[UploadFile]):
        if files and len(files) > 0:
            if not os.path.exists(self.file_dir):
                os.makedirs(self.file_dir)
            for f in files:
                file_path = f"{self.file_dir}/{f.filename}"
                self.filenames.append(f.filename)
                with open(file_path, "wb+") as fo:
                    shutil.copyfileobj(f.file, fo)

    def delete_files(self):
        if os.path.exists(self.file_dir):
            shutil.rmtree(self.file_dir)


class ConversationContext:
    def __init__(
        self,
        current_user_input: str,
        session_id: str,
        current_user_intent: Intent = None,
    ):
        self.current_user_input = current_user_input
        self.session_id = session_id if session_id else str(uuid.uuid4())
        self.current_intent = current_user_intent
        self.intent_queue = deque(maxlen=3)
        self.history = History([])
        # used for logging
        self.status = "start"
        # used for condition jughment
        self.state = ""
        self.entities = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        # counter for inquiry times
        self.inquiry_times = 0
        self.has_update = False
        self.current_round = 0
        self.files = ConversationFiles(self.session_id)
        self.uploaded_file_contents: list[SearchResponse] = []

    def get_history(self) -> History:
        return self.history

    def append_user_history(self, message: str):
        self.history.add_history("user", message)

    def append_assistant_history(self, answer):
        response_content = prepare_response_content(answer)
        self.history.add_history("assistant", response_content)

    def add_files(self, files: list[UploadFile]):
        self.files.add_files(files)

    def add_file_contents(self, contents: list[SearchResponse]):
        self.uploaded_file_contents.extend(contents)

    def delete_files(self):
        self.files.delete_files()

    def add_entity(self, entities: List[Entity]):
        entity_map = {entity.type: entity for entity in self.entities}

        # todo: set as True when updated entity belong to current intent
        if len(entities) > 0:
            self.inquiry_times = 0
            self.has_update = True

        for new_entity in entities:
            if new_entity.type in entity_map:
                existing_entity = entity_map[new_entity.type]
                existing_entity.__dict__.update(new_entity.__dict__)
                logger.info(f"Updated entity {new_entity.type} for session {self.session_id}")
            else:
                self.entities.append(new_entity)
                logger.info(f"Added entity {new_entity.type} for session {self.session_id}")

    def get_entities(self):
        return self.entities

    def get_simplified_entities(self):
        return {entity.type: entity.value for entity in self.entities}

    def flush_entities(self):
        self.entities = []

    def set_status(self, status: str):
        self.status = status
        logger.info(f"session {self.session_id}, conversation status: {status}")

    def set_state(self, state: str):
        self.state = state
        state_prefix = state.split(":")[0]
        keywords = ["intent_filling", "intent_confirm", "slot_filling"]
        if any(keyword in state_prefix for keyword in keywords):
            self.inquiry_times += 1

    def handle_intent(self, next_intent: Intent):
        # if slot_filling intent found, we will not change current intent to next intent
        if next_intent.name not in ["slot_filling", "negative", "positive"]:
            self.update_intent(next_intent)

        # if intent same as last round, keep the confidence high
        # if self.current_intent and next_intent.name == self.current_intent.name:
        #     self.current_intent.confidence = 1

        # if no obviously intent found before, throw out to fusion engine
        if self.current_intent is None and next_intent.name in [
            "slot_filling",
            "positive",
            "negative",
        ]:
            self.update_intent(None)

        # if last round set conversation state "intent_confirm" and user confirmed in current round
        if next_intent.name in ["positive"] and self.state in ["intent_confirm"]:
            self.current_intent.confidence = 1.0
            self.has_update = True
            self.inquiry_times = 0

        # if last round set conversation state "slot_confirm" and user confirmed in current round
        if next_intent.name in ["positive"] and self.state.split(":")[0] in ["slot_confirm"]:
            self.inquiry_times = 0
            slot_name = self.state.split(":")[1].strip()
            for entity in self.entities:
                if entity.type == slot_name:
                    entity.confidence = 1.0
                    entity.possible_slot.confidence = 1.0
                    break

        # if user deny intent in current round
        if next_intent.name in ["negative"] and self.state.split(":")[0] not in [
            "slot_confirm",
            "slot_filling",
        ]:
            self.update_intent(None)

        # if user deny slot in current round
        # todo: if slot found in negative utterance
        if next_intent.name in ["negative"] and self.state.split(":")[0] in [
            "slot_confirm",
            "slot_filling",
        ]:
            slot_name = self.state.split(":")[1].strip()
            self.entities = [entity for entity in self.entities if entity.type != slot_name]

    def update_intent(self, intent: Intent):
        if intent is not None:
            self.has_update = True
            self.intent_queue.append(intent)
            if intent != self.current_intent:
                self.inquiry_times = 0
        self.current_intent = intent

    def intent_restore(self):
        self.current_intent = self.intent_queue[0]

from typing import Tuple

from action_runner.action import Action, SlotFillingAction, SmartHomeOperatingAction, PrintStatementAction
from action_runner.rag_action import RAGAction
from conversation_tracker.context import ConversationContext
from gm_logger import get_logger
from nlu.forms import FormStore
from nlu.intent_with_entity import IntentWithEntity
from prompt_manager.base import PromptManager

logger = get_logger()

class Policy:

    def __init__(self, prompt_manager: PromptManager):
        self.prompt_manager = prompt_manager

    def handle(self, intent: IntentWithEntity, context: ConversationContext, model_type: str) -> Tuple[bool, Action]:
        pass

    @staticmethod
    def get_possible_slots(intent: IntentWithEntity):
        return {entity.possible_slot for entity in intent.entities if Policy.is_not_empty(entity)}

    @staticmethod
    def is_not_empty(entity):
        return entity.value is not None and entity.value != ''


class SlotCheckPolicy(Policy):
    def __init__(self, prompt_manager: PromptManager, form_store: FormStore):
        Policy.__init__(self, prompt_manager)
        self.form_store = form_store

    def handle(self, intent: IntentWithEntity, context: ConversationContext, model_type: str) -> Tuple[bool, Action]:
        possible_slots = self.get_possible_slots(intent=intent)
        logger.debug(f"最终识别的\n意图：{intent.intent.name}\n实体：{[f'{slot.name}: {slot.value}'for slot in possible_slots if slot]}")
        if form := self.form_store.get_form_from_intent(intent.intent):
            missed_slots = set(form.slots) - possible_slots
            missed_slots = list(filter(lambda slot: slot.optional is not True, missed_slots))
            logger.debug(f"需要填充的槽位： {[slot.name for slot in missed_slots if slot]}")
            if missed_slots:
                return True, SlotFillingAction(model_type, missed_slots, intent.intent, prompt_manager=self.prompt_manager)
            else:
                return False, None
        return False, None


class SmartHomeOperatingPolicy(Policy):

    def __init__(self, prompt_manager: PromptManager):
        Policy.__init__(self, prompt_manager)

    def handle(self, intent: IntentWithEntity, context: ConversationContext, model_type: str) -> Tuple[bool, Action]:
        if intent.intent.name == "控制智能家居":
            possible_slots = {entity.possible_slot.name: entity.possible_slot for entity in intent.entities if entity.possible_slot}
            if len(possible_slots) == 3:
                return True, SmartHomeOperatingAction(
                    f'已经帮你{possible_slots["操作"].value}{possible_slots["位置"].value}的{possible_slots["对象"].value}了')
            elif len(possible_slots) == 4:
                return True, SmartHomeOperatingAction(f'已经帮你{possible_slots["操作"].value}{possible_slots["位置"].value}的{possible_slots["对象"].value}到{possible_slots["操作值"].value}了')
            else:
                return False, None
        else:
            return False, None


class RAGPolicy(Policy):

    def __init__(self, prompt_manager: PromptManager):
        Policy.__init__(self, prompt_manager)

    def handle(self, intent: IntentWithEntity, context: ConversationContext, model_type: str) -> Tuple[bool, Action]:
        if intent.intent.name == "保险知识问答":
            possible_slots = self.get_possible_slots(intent)
            if len(possible_slots) > 0:
                return True, RAGAction(model_type, possible_slots)

        return False, None
    

class PrintStatementPolicy(Policy):

    def __init__(self, prompt_manager: PromptManager):
        Policy.__init__(self, prompt_manager)

    def handle(self, intent: IntentWithEntity, context: ConversationContext, model_type: str) -> Tuple[bool, Action]:
        if intent.intent.name == "查询打印回单":
            possible_slots = {entity.possible_slot.name: entity.possible_slot for entity in intent.entities if entity.possible_slot}
            if len(possible_slots) == 1:
                return True, PrintStatementAction(
                    f'已经帮你打印好时间范围为{possible_slots["时间范围"].value}的回单了')
            # elif len(possible_slots) == 3:
            #     return True, PrintStatementAction(f'已经帮你{possible_slots["操作"].value}{possible_slots["位置"].value}的{possible_slots["对象"].value}到{possible_slots["操作值"].value}了')
            # elif len(possible_slots) == 4:
            #     return True, PrintStatementAction(f'已经帮你{possible_slots["操作"].value}{possible_slots["位置"].value}的{possible_slots["对象"].value}到{possible_slots["操作值"].value}了')
            else:
                return False, None
        else:
            return False, None
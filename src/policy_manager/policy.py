from typing import Tuple

from action_runner.action import Action
from action_runner.actions.general import SlotFillingAction, IntentConfirmAction
from action_runner.actions.bnb import BankRelatedAction
from conversation_tracker.context import ConversationContext
from gm_logger import get_logger
from nlu.forms import FormStore
from nlu.intent_with_entity import IntentWithEntity
from prompt_manager.base import PromptManager

logger = get_logger()

class Policy:

    def __init__(self, prompt_manager: PromptManager):
        self.prompt_manager = prompt_manager

    def handle(self, intent: IntentWithEntity, context: ConversationContext) -> Tuple[bool, Action]:
        pass

    @staticmethod
    def get_possible_slots(intent: IntentWithEntity):
        return {entity.possible_slot for entity in intent.entities if Policy.is_not_empty(entity)}

    @staticmethod
    def is_not_empty(entity):
        return entity.value is not None and entity.value != ''


class IntentConfirmPolicy(Policy):
    def __init__(self, prompt_manager: PromptManager, form_store: FormStore):
        Policy.__init__(self, prompt_manager)
        self.form_store = form_store

    def handle(self, IE: IntentWithEntity, context: ConversationContext) -> Tuple[bool, Action]:
        significant_value = 0.9
        possible_slots = self.get_possible_slots(intent=IE)
        logger.debug(f"当前状态\n待明确的意图：{IE.intent.name}\n实体：{[f'{slot.name}: {slot.value}'for slot in possible_slots if slot]}")
        if IE.intent.confidence < significant_value:
            return True, IntentConfirmAction(IE.intent, prompt_manager=self.prompt_manager)
        else:
            return False, None
    
class SlotFillingPolicy(Policy):
    def __init__(self, prompt_manager: PromptManager, form_store: FormStore):
        Policy.__init__(self, prompt_manager)
        self.form_store = form_store

    def handle(self, IE: IntentWithEntity, context: ConversationContext) -> Tuple[bool, Action]:
        possible_slots = self.get_possible_slots(intent=IE)
        logger.debug(f"当前状态\n意图：{IE.intent.name}\n实体：{[f'{slot.name}: {slot.value}'for slot in possible_slots if slot]}")
        if form := self.form_store.get_form_from_intent(IE.intent):
            missed_slots = set(form.slots) - possible_slots
            missed_slots = list(filter(lambda slot: slot.optional is not True, missed_slots))
            logger.debug(f"需要填充的槽位： {[slot.name for slot in missed_slots if slot]}")
            if missed_slots:
                return True, SlotFillingAction(missed_slots, IE.intent, prompt_manager=self.prompt_manager)
            else:
                return False, None
        return False, None

class AssistantPolicy(Policy):
    def __init__(self, prompt_manager: PromptManager, form_store: FormStore):
        Policy.__init__(self, prompt_manager)
        self.form_store = form_store

    def handle(self, IE: IntentWithEntity, context: ConversationContext) -> Tuple[bool, Action]:
        possible_slots = self.get_possible_slots(intent=IE)
        logger.debug(f"最终识别的\n意图：{IE.intent.name}\n实体：{[f'{slot.name}: {slot.value}'for slot in possible_slots if slot]}")
        if form := self.form_store.get_form_from_intent(IE.intent):
            print(f'exec action {form.action}')
            return True, BankRelatedAction(form.action)
        return False, None
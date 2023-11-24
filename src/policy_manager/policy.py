from typing import Tuple

from action_runner.action import Action
from action_runner.actions.general import SlotFillingAction
from action_runner.actions.bank import PrintStatementAction
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


class SlotFillingPolicy(Policy):
    def __init__(self, prompt_manager: PromptManager, form_store: FormStore):
        Policy.__init__(self, prompt_manager)
        self.form_store = form_store

    def handle(self, intent: IntentWithEntity, context: ConversationContext) -> Tuple[bool, Action]:
        possible_slots = self.get_possible_slots(intent=intent)
        logger.debug(f"最终识别的\n意图：{intent.intent.name}\n实体：{[f'{slot.name}: {slot.value}'for slot in possible_slots if slot]}")
        if form := self.form_store.get_form_from_intent(intent.intent):
            missed_slots = set(form.slots) - possible_slots
            missed_slots = list(filter(lambda slot: slot.optional is not True, missed_slots))
            logger.debug(f"需要填充的槽位： {[slot.name for slot in missed_slots if slot]}")
            if missed_slots:
                return True, SlotFillingAction(missed_slots, intent.intent, prompt_manager=self.prompt_manager)
            else:
                return False, None
        return False, None

class RulePolicy(Policy):
    def __init__(self, prompt_manager: PromptManager, form_store: FormStore):
        Policy.__init__(self, prompt_manager)
        self.form_store = form_store

    def handle(self, intent: IntentWithEntity, context: ConversationContext) -> Tuple[bool, Action]:
        possible_slots = self.get_possible_slots(intent=intent)
        logger.debug(f"最终识别的\n意图：{intent.intent.name}\n实体：{[f'{slot.name}: {slot.value}'for slot in possible_slots if slot]}")
        if form := self.form_store.get_form_from_intent(intent.intent):
            print(f'exec action {form.action}')
            return True, PrintStatementAction('打印成功')
        return False, None
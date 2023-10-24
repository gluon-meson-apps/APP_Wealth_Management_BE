from typing import Tuple

from action_runner.action import Action, SlotFillingAction, SmartHomeOperatingAction
from conversation_tracker.context import ConversationContext
from gm_logger import get_logger
from nlu.forms import FormStore
from nlu.intent_with_entity import IntentWithEntity

logger = get_logger()

class Policy:
    def handle(self, intent: IntentWithEntity, context: ConversationContext, model_type: str) -> Tuple[bool, Action]:
        pass


class SlotCheckPolicy(Policy):
    def __init__(self, form_store: FormStore):
        self.form_store = form_store

    def handle(self, intent: IntentWithEntity, context: ConversationContext, model_type: str) -> Tuple[bool, Action]:
        possible_slots = {entity.possible_slot for entity in intent.entities if self.is_not_empty(entity)}
        logger.debug(f"最终识别的\n意图：{intent.intent.name}\n实体：{[f'{slot.name}: {slot.value}'for slot in possible_slots if slot]}")
        if form := self.form_store.get_form_from_intent(intent.intent):
            missed_slots = set(form.slots) - possible_slots
            missed_slots = list(filter(lambda slot: slot.optional is not True, missed_slots))
            logger.debug(f"需要填充的槽位： {[slot.name for slot in missed_slots if slot]}")
            if missed_slots:
                return True, SlotFillingAction(model_type, missed_slots, intent.intent)
            else:
                return False, None
        return False, None

    @staticmethod
    def is_not_empty(entity):
        return entity.value is not None and entity.value != ''


class SmartHomeOperatingPolicy(Policy):
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


from typing import Tuple, Optional

from loguru import logger

from action.actions.general import SlotFillingAction, SlotConfirmAction
from action.base import Action
from nlu.forms import FormStore
from nlu.intent_with_entity import IntentWithEntity
from policy.base import Policy
from policy.general import MAX_FOLLOW_UP_TIMES, SLOT_SIG_TRH
from prompt_manager.base import PromptManager
from tracker.context import ConversationContext


class SlotFillingPolicy(Policy):
    def __init__(self, prompt_manager: PromptManager, form_store: FormStore):
        Policy.__init__(self, prompt_manager)
        self.form_store = form_store

    def handle(self, IE: IntentWithEntity, context: ConversationContext) -> Tuple[bool, Optional[Action]]:
        possible_slots = self.get_possible_slots(intent=IE)
        logger.debug(
            f"current status\nintent：{IE.intent.name}\n"
            f"entities：{[f'{slot.name}: {slot.value}' for slot in possible_slots if slot]}"
        )
        if form := self.form_store.get_form_from_intent(IE.intent):
            missed_slots = set(form.slots) - possible_slots
            missed_slots = list(filter(lambda slot: slot.optional is not True, missed_slots))
            logger.debug(f"Slots to be filled： {[slot.name for slot in missed_slots if slot]}")

            # 追问槽位
            if missed_slots and context.inquiry_times < MAX_FOLLOW_UP_TIMES:
                context.set_state(f"slot_filling:{missed_slots}")
                return True, SlotFillingAction(missed_slots, IE.intent, prompt_manager=self.prompt_manager)

            # 确认槽位
            for slot in possible_slots:
                if slot in form.slots and slot.confidence < SLOT_SIG_TRH:
                    context.set_state(f"slot_confirm: {slot.name}")
                    return True, SlotConfirmAction(IE.intent, slot, prompt_manager=self.prompt_manager)

            # 如果所有的可选槽位都没有被填充且form.slot_required为True，则通过话术引导用户填充任意一个槽位
            if form.slot_required and context.inquiry_times < MAX_FOLLOW_UP_TIMES:
                optional_slots = [slot for slot in form.slots if slot.optional]
                if optional_slots and len(possible_slots) == 0:
                    to_filled_slot = optional_slots.pop()
                    context.set_state(f"slot_filling:{to_filled_slot.name}")
                    return True, SlotFillingAction(optional_slots, IE.intent, prompt_manager=self.prompt_manager)

        return False, None

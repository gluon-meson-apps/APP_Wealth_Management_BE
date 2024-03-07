from loguru import logger

from action.actions.general import SlotFillingAction, SlotConfirmAction
from nlu.forms import FormStore
from nlu.intent_with_entity import IntentWithEntity
from policy.base import Policy, PolicyResponse
from policy.general import MAX_FOLLOW_UP_TIMES, SLOT_SIG_TRH
from policy.slot_filling.slot_checker import SlotChecker
from prompt_manager.base import PromptManager
from tracker.context import ConversationContext


class SlotFillingPolicy(Policy):
    def __init__(self, prompt_manager: PromptManager, form_store: FormStore):
        Policy.__init__(self, prompt_manager)
        self.form_store = form_store

    def handle(self, IE: IntentWithEntity, context: ConversationContext) -> PolicyResponse:
        possible_slots = self.get_possible_slots(intent=IE)
        logger.debug(
            f"current status\nintent：{IE.intent.name}\n"
            f"entities：{[f'{slot.name}: {slot.value}' for slot in possible_slots if slot]}"
        )
        if form := self.form_store.get_form_from_intent(IE.intent):
            # ask for missing slots
            checker = SlotChecker(form, [slot.name for slot in possible_slots])
            if checker.slot_is_missing() and context.inquiry_times < MAX_FOLLOW_UP_TIMES:
                missed_slots = checker.get_missed_slots()
                context.set_state(f"slot_filling: {missed_slots}")
                logger.debug(f"Slots to be filled： {[slot.name for slot in missed_slots[0] if slot]}")
                return PolicyResponse(
                    True, SlotFillingAction(missed_slots, IE.intent, prompt_manager=self.prompt_manager)
                )

            # ask for slot confirmation
            for slot in possible_slots:
                if slot in form.slots and slot.confidence < SLOT_SIG_TRH:
                    context.set_state(f"slot_confirm: {slot.name}")
                    return PolicyResponse(True, SlotConfirmAction(IE.intent, slot, prompt_manager=self.prompt_manager))

        return PolicyResponse(False, None)

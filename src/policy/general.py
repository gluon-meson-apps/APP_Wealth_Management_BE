from typing import Tuple

from action.base import Action
from action.actions.general import EndDialogueAction, SlotFillingAction, IntentConfirmAction, IntentFillingAction, SlotConfirmAction
from action.actions.bnb import BankRelatedAction, JumpOut
from policy.base import Policy
from tracker.context import ConversationContext
from loguru import logger
from nlu.forms import FormStore
from nlu.intent_with_entity import IntentWithEntity
from prompt_manager.base import PromptManager


INTENT_SIG_TRH = 0.9
SLOT_SIG_TRH = 0.8

MAX_FOLLOW_UP_TIMES = 2

BUSINESS_INTENS = ["activate_function", "add_header", "enlarge_page", "reduce_page", "page_resize", "remove_header"]

class EndDialoguePolicy(Policy):
    def __init__(self, prompt_manager: PromptManager, form_store: FormStore):
        Policy.__init__(self, prompt_manager)

    def handle(self, IE: IntentWithEntity, context: ConversationContext) -> Tuple[bool, Action]:
        logger.info(f"Inquiry_times: {context.inquiry_times}")
        if context.inquiry_times >= MAX_FOLLOW_UP_TIMES:
            return True, EndDialogueAction()
        return False, None

class IntentFillingPolicy(Policy):
    def __init__(self, prompt_manager: PromptManager, form_store: FormStore):
        Policy.__init__(self, prompt_manager)
        self.form_store = form_store

    def handle(self, IE: IntentWithEntity, context: ConversationContext) -> Tuple[bool, Action]:
        possible_slots = self.get_possible_slots(intent=IE)
        logger.debug(f"当前状态\n待明确的意图：{IE.intent}\n实体：{[f'{slot.name}: {slot.value}'for slot in possible_slots if slot]}")
        if IE.intent is None:
            context.set_state("intent_filling")
            return True, IntentFillingAction(prompt_manager=self.prompt_manager)
        elif IE.intent.confidence < INTENT_SIG_TRH and IE.intent.name in BUSINESS_INTENS:
            context.set_state("intent_confirm")
            return True, IntentConfirmAction(IE.intent, prompt_manager=self.prompt_manager)        
        return False, None
    
class SlotFillingPolicy(Policy):
    def __init__(self, prompt_manager: PromptManager, form_store: FormStore):
        Policy.__init__(self, prompt_manager)
        self.form_store = form_store

    def handle(self, IE: IntentWithEntity, context: ConversationContext) -> Tuple[bool, Action]:
        possible_slots = self.get_possible_slots(intent=IE)
        print(possible_slots)
        logger.debug(f"当前状态\n意图：{IE.intent.name}\n实体：{[f'{slot.name}: {slot.value}'for slot in possible_slots if slot]}")
        if form := self.form_store.get_form_from_intent(IE.intent):
            missed_slots = set(form.slots) - possible_slots
            missed_slots = list(filter(lambda slot: slot.optional is not True, missed_slots))
            logger.debug(f"需要填充的槽位： {[slot.name for slot in missed_slots if slot]}")
            if missed_slots:
                context.set_state("slot_filling")
                return True, SlotFillingAction(missed_slots, IE.intent, prompt_manager=self.prompt_manager)

            #print(f"possible slots: {possible_slots}")
            for slot in possible_slots:
                # print(slot)
                if slot in form.slots and slot.confidence < SLOT_SIG_TRH:
                    context.set_state(f"slot_confirm: {slot.name}")
                    return True, SlotConfirmAction(IE.intent, slot, prompt_manager=self.prompt_manager)

        return False, None

class AssistantPolicy(Policy):
    def __init__(self, prompt_manager: PromptManager, form_store: FormStore):
        Policy.__init__(self, prompt_manager)
        self.form_store = form_store

    def handle(self, IE: IntentWithEntity, context: ConversationContext) -> Tuple[bool, Action]:
        possible_slots = self.get_possible_slots(intent=IE)
        logger.debug(f"最终识别的\n意图：{IE.intent.name}\n实体：{[f'{slot.name}: {slot.value}' for slot in possible_slots if slot]}")
        form = self.form_store.get_form_from_intent(IE.intent)

        if not form:
            return False, None
        
        # 处理业务相关的意图
        if IE.intent.name in BUSINESS_INTENS and context.has_update:
            context.has_update = False
            return True, BankRelatedAction(form.action, possible_slots, IE.intent)

        # 跳出对话
        elif IE.intent.name in ("skill_irrelevant", "other_skill"):
            return True, JumpOut()

        # 处理闲聊意图
        elif IE.intent.name == "chitchat":
            if len(context.intent_queue) < 2 or context.intent_queue[-2].name == "chitchat":
                return True, JumpOut()
            else:
                context.set_state("intent_filling")
                return True, IntentFillingAction(prompt_manager=self.prompt_manager)

        # 其他意图
        else:
            return True, IntentFillingAction(prompt_manager=self.prompt_manager)
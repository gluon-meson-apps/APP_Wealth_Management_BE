from typing import Tuple

from action.base import Action
from action.actions.general import EndDialogueAction, SlotFillingAction, IntentConfirmAction, IntentFillingAction, \
    SlotConfirmAction
from action.actions.bnb import BankRelatedAction, JumpOut
from action.repository.action_repository import ActionRepository, action_repository as default_action_repository
from policy.base import Policy
from tracker.context import ConversationContext
from loguru import logger
from nlu.forms import FormStore
from nlu.intent_with_entity import IntentWithEntity
from prompt_manager.base import PromptManager
from output_adapter.base import BaseOutputAdapter

INTENT_SIG_TRH = 0.8
SLOT_SIG_TRH = 0.8

MAX_FOLLOW_UP_TIMES = 2

IN_SCOPE_INTENTS = ["activate_function", "add_header", "enlarge_page", "reduce_page", "page_resize", "remove_header"]


def intent_in_scope(intent: str) -> bool:
    return True


class EndDialoguePolicy(Policy):
    def __init__(self, prompt_manager: PromptManager, form_store: FormStore):
        Policy.__init__(self, prompt_manager)

    def handle(self, IE: IntentWithEntity, context: ConversationContext) -> Tuple[bool, Action]:
        logger.info(f"Inquiry_times: {context.inquiry_times}")
        # 追问次数超过最大值
        if context.inquiry_times >= MAX_FOLLOW_UP_TIMES and context.current_intent is None:
            return True, EndDialogueAction()

        if context.current_intent is not None:
            if context.inquiry_times >= MAX_FOLLOW_UP_TIMES and not intent_in_scope(context.current_intent.name):
                return True, EndDialogueAction()
        return False, None


class JumpOutPolicy(Policy):
    def __init__(self, prompt_manager: PromptManager, form_store: FormStore):
        Policy.__init__(self, prompt_manager)

    def handle(self, IE: IntentWithEntity, context: ConversationContext) -> Tuple[bool, Action]:

        # 没有意图
        if not IE.intent:
            return False, None

        # 非Agent处理之意图
        if IE.intent.name in ("skill_irrelevant", "other_skills"):
            return True, JumpOut()

        # 处理闲聊意图
        return False, None


class IntentFillingPolicy(Policy):
    def __init__(self, prompt_manager: PromptManager, form_store: FormStore):
        Policy.__init__(self, prompt_manager)
        self.form_store = form_store

    def handle(self, IE: IntentWithEntity, context: ConversationContext) -> Tuple[bool, Action]:
        possible_slots = self.get_possible_slots(intent=IE)
        logger.debug(
            f"当前状态\n待明确的意图：{IE.intent}\n"
            f"实体：{[f'{slot.name}: {slot.value}' for slot in possible_slots if slot]}")

        # 没有非辅助外的意图
        if IE.intent is None:
            context.set_state("intent_filling")
            return True, IntentFillingAction(prompt_manager=self.prompt_manager, form_store=self.form_store)

        # 有非辅助外的意图但是置信度低
        if IE.intent.confidence < INTENT_SIG_TRH and intent_in_scope(
                IE.intent.name) and context.inquiry_times < MAX_FOLLOW_UP_TIMES:
            context.set_state("intent_confirm")
            return True, IntentConfirmAction(IE.intent, prompt_manager=self.prompt_manager)
        return False, None


class SlotFillingPolicy(Policy):
    def __init__(self, prompt_manager: PromptManager, form_store: FormStore):
        Policy.__init__(self, prompt_manager)
        self.form_store = form_store

    def handle(self, IE: IntentWithEntity, context: ConversationContext) -> Tuple[bool, Action]:
        possible_slots = self.get_possible_slots(intent=IE)
        logger.debug(
            f"当前状态\n意图：{IE.intent.name}\n"
            f"实体：{[f'{slot.name}: {slot.value}' for slot in possible_slots if slot]}")
        if form := self.form_store.get_form_from_intent(IE.intent):
            missed_slots = set(form.slots) - possible_slots
            missed_slots = list(filter(lambda slot: slot.optional is not True, missed_slots))
            logger.debug(f"需要填充的槽位： {[slot.name for slot in missed_slots if slot]}")

            # 追问槽位
            if missed_slots and context.inquiry_times < MAX_FOLLOW_UP_TIMES:
                to_filled_slot = missed_slots.pop()
                context.set_state(f"slot_filling:{to_filled_slot.name}")
                return True, SlotFillingAction(to_filled_slot, IE.intent, prompt_manager=self.prompt_manager)

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


class AssistantPolicy(Policy):
    def __init__(self, prompt_manager: PromptManager, form_store: FormStore,
                 action_repository: ActionRepository = default_action_repository):
        Policy.__init__(self, prompt_manager)
        self.form_store = form_store
        self.action_repository = action_repository

    def handle(self, IE: IntentWithEntity, context: ConversationContext) -> Tuple[bool, Action]:
        potential_slots = self.get_possible_slots(intent=IE)
        logger.debug(
            f"最终识别的\n意图：{IE.intent.name}\n"
            f"实体：{[f'{slot.name}: {slot.value}' for slot in potential_slots if slot]}")
        intent_form = self.form_store.get_form_from_intent(IE.intent)

        # 出现了预定义之外的意图
        if not intent_form:
            return True, JumpOut()

        action = self.action_repository.find_by_name(intent_form.action)
        # 范围内意图但多轮追问都不能获取到必要的槽位
        if intent_in_scope(
                IE.intent.name) and IE.intent.confidence > INTENT_SIG_TRH and\
                context.inquiry_times >= MAX_FOLLOW_UP_TIMES:
            if action is not None:
                return True, action
            return True, BankRelatedAction(intent_form.action, potential_slots, IE.intent, BaseOutputAdapter())

        # 范围内意图但多轮追问都不能获取到必要的槽位
        if intent_in_scope(IE.intent.name) and IE.intent.confidence <= INTENT_SIG_TRH and \
                context.inquiry_times >= MAX_FOLLOW_UP_TIMES:
            context.set_state("intent_confirm")
            return True, EndDialogueAction()

        # 范围内意图，且此轮槽位有更新或者是新的意图
        if intent_in_scope(IE.intent.name) and context.has_update:
            context.has_update = False
            if action is not None:
                return True, action
            return True, BankRelatedAction(intent_form.action, potential_slots, IE.intent, BaseOutputAdapter())

        # 范围内意图但无更新
        if intent_in_scope(IE.intent.name) and not context.has_update:
            context.set_state("intent_confirm")
            return True, IntentConfirmAction(IE.intent, prompt_manager=self.prompt_manager)

        context.set_state("intent_filling")
        return True, IntentFillingAction(prompt_manager=self.prompt_manager, form_store=self.form_store)

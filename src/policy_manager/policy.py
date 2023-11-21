from typing import Tuple

from action_runner.action import Action, SlotFillingAction, SmartHomeOperatingAction, PrintStatementAction, FontPageAdjustmentAction, AdjustTableColumnAction, ActivateFunctionAction, QAAction
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
                    f'已经帮你打印好账号信息为{possible_slots["账号"].value}的回单了')
            elif len(possible_slots) > 1:
                if "时间范围" not in possible_slots.keys():
                    possible_slots["时间范围"] = ''
                if "金额范围" not in possible_slots.keys():
                    possible_slots["金额范围"] = ''
                if "是否已经打印" not in possible_slots.keys():
                    possible_slots["是否已经打印"] = ''

#                 return True, PrintStatementAction(f"""已经帮你好账号信息为{possible_slots["账号"].value}的回单了
# 时间范围：{possible_slots["时间范围"].value}
# 金额范围：{possible_slots["金额范围"].value}
# 是否已经打印：{possible_slots["是否已经打印"].value}""")
                return True, PrintStatementAction(f"""已经帮你查询打印账号信息为{possible_slots["账号"].value}的回单了
""")
            # elif len(possible_slots) == 4:
            #     return True, PrintStatementAction(f'已经帮你{possible_slots["操作"].value}{possible_slots["位置"].value}的{possible_slots["对象"].value}到{possible_slots["操作值"].value}了')
            else:
                return False, None
        else:
            return False, None
        

class FontPageAdjustmentPolicy(Policy):

    def __init__(self, prompt_manager: PromptManager):
        Policy.__init__(self, prompt_manager)

    def handle(self, intent: IntentWithEntity, context: ConversationContext, model_type: str) -> Tuple[bool, Action]:
        if intent.intent.name == "页面字体缩放":
            possible_slots = {entity.possible_slot.name: entity.possible_slot for entity in intent.entities if entity.possible_slot}
            if len(possible_slots) == 1:
                return True, FontPageAdjustmentAction(
                    f'已经帮你进行了页面字体缩放：{possible_slots["调整方向"].value}')
            # elif len(possible_slots) == 3:
            #     return True, PrintStatementAction(f'已经帮你{possible_slots["操作"].value}{possible_slots["位置"].value}的{possible_slots["对象"].value}到{possible_slots["操作值"].value}了')
            # elif len(possible_slots) == 4:
            #     return True, PrintStatementAction(f'已经帮你{possible_slots["操作"].value}{possible_slots["位置"].value}的{possible_slots["对象"].value}到{possible_slots["操作值"].value}了')
            else:
                return False, None
        else:
            return False, None
        
class AdjustTableColumnPolicy(Policy):

    def __init__(self, prompt_manager: PromptManager):
        Policy.__init__(self, prompt_manager)

    def handle(self, intent: IntentWithEntity, context: ConversationContext, model_type: str) -> Tuple[bool, Action]:
        if intent.intent.name == "增减表头":
            possible_slots = {entity.possible_slot.name: entity.possible_slot for entity in intent.entities if entity.possible_slot}
            if len(possible_slots) == 1:
                return True, AdjustTableColumnAction(
                    f'已经确认了你想调整表头的方向：{possible_slots["调整方向"].value}')
            elif len(possible_slots) == 2:
                return True, AdjustTableColumnAction(f'了解了，你想按下列方式调整表头：{possible_slots["调整方向"].value}{possible_slots["字段要素"].value}')
            # elif len(possible_slots) == 4:
            #     return True, PrintStatementAction(f'已经帮你{possible_slots["操作"].value}{possible_slots["位置"].value}的{possible_slots["对象"].value}到{possible_slots["操作值"].value}了')
            else:
                return False, None
        else:
            return False, None
        

class ActivateFunctionPolicy(Policy):

    def __init__(self, prompt_manager: PromptManager):
        Policy.__init__(self, prompt_manager)

    def handle(self, intent: IntentWithEntity, context: ConversationContext, model_type: str) -> Tuple[bool, Action]:
        if intent.intent.name == "开通功能":
            possible_slots = {entity.possible_slot.name: entity.possible_slot for entity in intent.entities if entity.possible_slot}
            if len(possible_slots) == 1:
                return True, ActivateFunctionAction(
                    f'已经确认了你想开通：{possible_slots["功能名称"].value}')
            # elif len(possible_slots) == 2:
            #     return True, PrintStatementAction(f'了解了，你想按下列方式调整表头：{possible_slots["调整方向"].value}{possible_slots["字段要素"].value}')
            # elif len(possible_slots) == 4:
            #     return True, PrintStatementAction(f'已经帮你{possible_slots["操作"].value}{possible_slots["位置"].value}的{possible_slots["对象"].value}到{possible_slots["操作值"].value}了')
            else:
                return False, None
        else:
            return False, None
        
class QAPolicy(Policy):

    def __init__(self, prompt_manager: PromptManager):
        Policy.__init__(self, prompt_manager)

    def handle(self, intent: IntentWithEntity, context: ConversationContext, model_type: str) -> Tuple[bool, Action]:
        if intent.intent.name == "金融产品知识问答":
            possible_slots = {entity.possible_slot.name: entity.possible_slot for entity in intent.entities if entity.possible_slot}
            # if len(possible_slots) == 1:
            return True, QAAction(
                f'小照X将回答您的问题。。。')
            # elif len(possible_slots) == 2:
            #     return True, PrintStatementAction(f'了解了，你想按下列方式调整表头：{possible_slots["调整方向"].value}{possible_slots["字段要素"].value}')
            # elif len(possible_slots) == 4:
            #     return True, PrintStatementAction(f'已经帮你{possible_slots["操作"].value}{possible_slots["位置"].value}的{possible_slots["对象"].value}到{possible_slots["操作值"].value}了')
            # else:
                # return False, None
        else:
            return False, None
import configparser
from loguru import logger
from action.base import Action, ActionResponse, ActionToSlotCategoryDict, SlotTypeToSlotValueTypeDict, \
    ActionToValidSlotTypesDict, ActionResponseAnswerContent, ActionResponseAnswer, \
    JumpOutResponse, ResponseMessageType, SlotTypeToNormalizeTypeDict, SlotType, SlotTypeToOperateTypeDict
from output_adapter.base import OutputAdapter

config = configparser.ConfigParser()
config.read('config.ini')


class BankRelatedAction(Action):
    def __init__(self, action_name, possible_slots, intent, output_adapter: OutputAdapter):
        self.action_name = action_name
        self.possible_slots = possible_slots
        self.intent = intent
        self.output_adapter = output_adapter

    def run(self, context) -> ActionResponse:
        logger.info(f'exec action {self.action_name}')
        target_slots = [x for x in self.possible_slots if x.name in ActionToValidSlotTypesDict[self.action_name]]
        if len(target_slots) > 1:
            target_slots.sort(key=lambda x: x.priority, reverse=True)
        target_slot_value, target_slot_name = self._get_target_slot_values(target_slots)
        slot = self._prepare_slot(target_slot_value, target_slot_name)
        answer = self._prepare_answer(slot, target_slot_name)
        return ActionResponse(code=200, message="success", answer=answer, jump_out_flag=False)

    def _prepare_slot(self, target_slot_value, target_slot_name):
        if target_slot_name in [SlotType.functions, SlotType.font_target]:
            slot = {"value": target_slot_value}
        elif target_slot_name in [SlotType.font_change]:
            slot = {"category": ActionToSlotCategoryDict[self.action_name], "value": target_slot_value}
        elif target_slot_name in [SlotType.header_element, SlotType.header_position]:
            slot = {
                "category": ActionToSlotCategoryDict[self.action_name],
                "valueType": SlotTypeToSlotValueTypeDict[target_slot_name],
                "value": target_slot_value
            }
        else:
            slot = {}
        return slot

    def _get_target_slot_values(self, target_slots):
        target_slot_name = target_slots[0].name if target_slots else ActionToValidSlotTypesDict[self.action_name][0]
        target_slot_value = self.output_adapter.normalize_slot_value(
            target_slots[0].value if target_slots else config.get('defaultActionSlotValue', self.action_name),
            SlotTypeToNormalizeTypeDict[target_slot_name]
        )
        return target_slot_value, target_slot_name

    def _prepare_answer(self, slot, target_slot_name):
        return ActionResponseAnswer(
            messageType=ResponseMessageType.FORMAT_INTELLIGENT_EXEC,
            content=ActionResponseAnswerContent(
                businessId="N35010Operate",
                operateType=SlotTypeToOperateTypeDict[target_slot_name],
                operateSlots=slot,
                businessInfo={}
            )
        )


class JumpOut(Action):
    def __init__(self):
        pass

    def run(self, context) -> ActionResponse:
        logger.debug("非范围内意图")
        return JumpOutResponse(code=200, message="success", answer={}, jump_out_flag=True)

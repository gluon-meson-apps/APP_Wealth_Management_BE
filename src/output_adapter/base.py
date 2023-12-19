import chinese2digits as c2d
import numpy as np
import configparser

from action.base import SlotType, NormalizeType, ActionToSlotCategoryDict, SlotTypeToSlotValueTypeDict, \
    ActionResponseAnswer, ResponseMessageType, \
    ActionResponseAnswerContent, SlotTypeToOperateTypeDict, SlotTypeToNormalizeTypeDict, ActionName

config = configparser.ConfigParser()
config.read('config.ini')


def transform_slot_value_to_natural_language(slot_value: str, slot_type: SlotType) -> str:
    if slot_type == SlotType.font_change:
        return f"{slot_value}%"
    if slot_type == SlotType.font_target:
        return f"到{slot_value}%"
    if slot_type == SlotType.header_position:
        return f"第{slot_value}个"
    return slot_value


def prepare_instruction(intent_description: str, slot_value: str, slot_type: SlotType) -> str:
    return f"{intent_description}{transform_slot_value_to_natural_language(slot_value, slot_type)}"


class OutputAdapter:
    def process_output(self, output: object) -> object:
        raise NotImplementedError()

    def prepare_slot(self, action_name, target_slot_value, target_slot_name):
        raise NotImplementedError()

    def prepare_answer(self, slot, intent_description, target_slot_value, target_slot_name):
        raise NotImplementedError()

    def normalize_slot_value(self, target_slots: [], target_slot_name: SlotType, action_name: ActionName) -> str:
        raise NotImplementedError()


class BaseOutputAdapter(OutputAdapter):
    def process_output(self, output: object) -> object:
        return output

    def normalize_slot_value(self, target_slots: [], target_slot_name: SlotType, action_name: ActionName) -> str:
        normalize_type = SlotTypeToNormalizeTypeDict[target_slot_name]
        slot_value = target_slots[0].value if target_slots else config.get('defaultActionSlotValue', action_name)

        if normalize_type == NormalizeType.PERCENTAGE:
            result = c2d.takeNumberFromString(slot_value)
            result_value = result['digitsStringList'][0] if result['digitsStringList'] else config.get(
                'defaultActionSlotValue', action_name)
            rounded_value = np.ceil(float(result_value) * 10)
            result_str = str(int(rounded_value * 10))
            return result_str

        if normalize_type == NormalizeType.NUMBER:
            replaced_value = (slot_value
                              .replace("倒数", "负")
                              .replace("第", ""))
            result = c2d.takeNumberFromString(replaced_value)
            return result['digitsStringList'][0]
        return slot_value

    def prepare_slot(self, action_name, target_slot_value, target_slot_name):
        if target_slot_name in [SlotType.functions, SlotType.font_target]:
            slot = {"value": target_slot_value}
        elif target_slot_name in [SlotType.font_change]:
            slot = {"category": ActionToSlotCategoryDict[action_name], "value": target_slot_value}
        elif target_slot_name in [SlotType.header_element, SlotType.header_position]:
            slot = {
                "category": ActionToSlotCategoryDict[action_name],
                "valueType": SlotTypeToSlotValueTypeDict[target_slot_name],
                "value": target_slot_value
            }
        else:
            slot = {}
        return slot

    def prepare_answer(self, slot, intent_description, target_slot_value, target_slot_name, ):
        return ActionResponseAnswer(
            messageType=ResponseMessageType.FORMAT_INTELLIGENT_EXEC,
            content=ActionResponseAnswerContent(
                businessId="N35010Operate",
                operateType=SlotTypeToOperateTypeDict[target_slot_name],
                operateSlots=slot,
                businessInfo={
                    "instruction": prepare_instruction(intent_description, target_slot_value,
                                                       target_slot_name)
                }))

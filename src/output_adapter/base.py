import chinese2digits as c2d
import numpy as np
import configparser

from action.base import SlotType, NormalizeType, ActionToSlotCategoryDict, SlotTypeToSlotValueTypeDict, \
    ActionResponseAnswer, ResponseMessageType, \
    ActionResponseAnswerContent, ActionName, \
    actionsHaveDefaultValue, SlotTypeToNormalizeTypeDict, ActionToValidSlotTypesDict, ActionTypeToOperateTypeDict, \
    SlotTypeToOperateTypeDict

config = configparser.ConfigParser()
config.read('config.ini')


def transform_slot_value_to_natural_language(slot_value: str, slot_type: str) -> str:
    if slot_type == SlotType.font_change:
        return f"{slot_value}%"
    if slot_type == SlotType.font_target:
        return f"到{slot_value}%"
    if slot_type == SlotType.header_position:
        return f"第{slot_value}个"
    return slot_value


def prepare_instruction(intent_description: str, slot_value: str, slot_type: str) -> str:
    return f"{intent_description}{transform_slot_value_to_natural_language(slot_value, slot_type)}" if slot_type else ''


def get_parsed_slot_value(action_name, value):
    result = c2d.takeNumberFromString(value)
    if action_name in actionsHaveDefaultValue:
        result_value = result['digitsStringList'][0] if result['digitsStringList'] else config.get(
            'defaultActionSlotValue', action_name)
    else:
        result_value = result['digitsStringList'][0] if result['digitsStringList'] else ''
    return result_value


class OutputAdapter:
    def process_output(self, output: object) -> object:
        raise NotImplementedError()

    def get_slot_value(self, action_name, target_slots):
        raise NotImplementedError()

    def normalize_slot_value(self, slot_value: str, target_slot_name: str, action_name: ActionName) -> str:
        raise NotImplementedError()

    def get_slot_name(self, action_name, target_slots):
        raise NotImplementedError()

    def prepare_slot(self, action_name, target_slot_value, target_slot_name):
        raise NotImplementedError()

    def prepare_answer(self, slot, intent_description, target_slot_value, target_slot_name, action_name):
        raise NotImplementedError()


class BaseOutputAdapter(OutputAdapter):
    def process_output(self, output: object) -> object:
        return output

    def get_slot_name(self, action_name, target_slots):
        if action_name in actionsHaveDefaultValue:
            target_slot_name = target_slots[0].name if target_slots else ActionToValidSlotTypesDict[action_name][0]
        else:
            target_slot_name = target_slots[0].name if target_slots else ''
        return target_slot_name

    def get_slot_value(self, action_name, target_slots):
        if action_name in actionsHaveDefaultValue:
            slot_value = target_slots[0].value if target_slots else config.get('defaultActionSlotValue', action_name)
        else:
            slot_value = target_slots[0].value if target_slots else ''
        return slot_value

    def normalize_slot_value(self, slot_value: str, target_slot_name: str, action_name: ActionName) -> str:
        if not target_slot_name:
            return ''

        normalize_type = SlotTypeToNormalizeTypeDict[target_slot_name]
        if normalize_type == NormalizeType.PERCENTAGE:
            parsed_value = get_parsed_slot_value(action_name, slot_value)
            if not parsed_value:
                return ''
            rounded_value = np.ceil(float(parsed_value) * 10)
            result_str = str(int(rounded_value * 10))
            return result_str

        if normalize_type == NormalizeType.NUMBER:
            replaced_value = (slot_value
                              .replace("倒数", "负")
                              .replace("第", ""))
            return get_parsed_slot_value(action_name, replaced_value)
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
        elif not target_slot_name:
            if action_name in [ActionName.remove_header, ActionName.add_header]:
                slot = {
                    "category": ActionToSlotCategoryDict[action_name],
                    "valueType": '',
                    "value": ''
                }
            else:
                slot = {"value": ''}
        else:
            slot = {"value": target_slot_value}
        return slot

    def prepare_answer(self, slot, intent_description, target_slot_value, target_slot_name, action_name):
        return ActionResponseAnswer(
            messageType=ResponseMessageType.FORMAT_INTELLIGENT_EXEC,
            content=ActionResponseAnswerContent(
                businessId="N35010Operate",
                operateType=SlotTypeToOperateTypeDict[target_slot_name] if target_slot_name else
                ActionTypeToOperateTypeDict[action_name],
                operateSlots=slot,
                businessInfo={
                    "instruction": prepare_instruction(intent_description, target_slot_value,
                                                       target_slot_name)
                }))

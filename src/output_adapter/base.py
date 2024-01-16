from typing import List

import chinese2digits as c2d
import numpy as np
import configparser

from fastapi import Depends
from loguru import logger

from action.base import (
    SlotType,
    NormalizeType,
    ActionToSlotCategoryDict,
    SlotTypeToSlotValueTypeDict,
    ActionResponseAnswer,
    ResponseMessageType,
    ActionResponseAnswerContent,
    ActionName,
    SlotTypeToNormalizeTypeDict,
    ActionToValidSlotTypesDict,
    ActionTypeToOperateTypeDict,
    SlotTypeToOperateTypeDict,
    slotsHaveDefaultValue,
    actionsHaveDefaultValue,
    AttachmentResponse,
)
from third_system.search_entity import SearchItem
from third_system.unified_search import UnifiedSearch

config = configparser.ConfigParser()
config.read("config.ini")


def transform_slot_value_to_natural_language(slot_value: str, slot_type: str) -> str:
    if slot_type == SlotType.font_change:
        return f"{slot_value}%"
    if slot_type == SlotType.font_target:
        return f"到{slot_value}%"
    if slot_type == SlotType.header_position:
        return f"第{slot_value}个"
    return slot_value


def prepare_instruction(intent_description: str, slot_value: str, slot_type: str) -> str:
    return f"{intent_description}{transform_slot_value_to_natural_language(slot_value, slot_type)}" if slot_type else ""


def get_parsed_slot_value(target_slot_name: str, slot_value: str, force_filter: bool = False):
    if force_filter:
        if "倍" in slot_value or "/" in slot_value:
            return config.get("defaultSlotValue", target_slot_name) if target_slot_name in slotsHaveDefaultValue else ""

        check_slash = c2d.takeNumberFromString(slot_value, percentConvert=False)["digitsStringList"][0]
        if "/" in check_slash:
            return config.get("defaultSlotValue", target_slot_name) if target_slot_name in slotsHaveDefaultValue else ""

    result = c2d.takeNumberFromString(slot_value)
    if target_slot_name in slotsHaveDefaultValue:
        result_value = (
            result["digitsStringList"][0]
            if result["digitsStringList"]
            else config.get("defaultSlotValue", target_slot_name)
        )
    else:
        result_value = result["digitsStringList"][0] if result["digitsStringList"] else ""
    return result_value


class OutputAdapter:
    def process_output(self, output: object) -> object:
        raise NotImplementedError()

    def get_slot_name(self, action_name: str, target_slots: []):
        raise NotImplementedError()

    def get_slot_value(self, action_name: str, target_slots: []):
        raise NotImplementedError()

    def normalize_slot_value(self, slot_value: str, target_slot_name: str, action_name: ActionName) -> str:
        raise NotImplementedError()

    def prepare_slot(self, action_name: ActionName, target_slot_value: str, target_slot_name: str):
        raise NotImplementedError()

    def prepare_answer(
        self,
        slot: {},
        intent_description: str,
        target_slot_value: str,
        target_slot_name: str,
        action_name: ActionName,
    ):
        raise NotImplementedError()


def generate_table_html(item):
    headers = []
    cells = []
    for key, value in item.dict().items():
        if key not in ["meta__score", "meta__reference"]:
            headers.append(key)
            cells.append(str(value))
    table_header_html = "".join(f"<th>{header}</th>" for header in headers)
    table_cell_html = "".join(f"<td>{cell}</td>" for cell in cells)
    table_html = f"<table><tr>{table_header_html}</tr><tr>{table_cell_html}</tr></table>"
    return table_html


def process_references(references: List[SearchItem]):
    html = ""
    for item in references:
        summary = item.meta__reference.meta__source_name
        table_html = generate_table_html(item)
        details_html = f"<details><summary>{summary}</summary>{table_html}</details>"
        html += details_html
    logger.info(html)
    return html


class BaseOutputAdapter(OutputAdapter):
    def __init__(self, unified_search: UnifiedSearch = Depends()):
        self.unified_search = unified_search

    def process_output(self, output: object) -> object:
        if isinstance(output, AttachmentResponse):
            logger.info(f"process attachment: {output.attachment}")
            output.answer.content += f"\n\nAttachment\n------------------\n{output.attachment.url}"
            return output
        if output.answer.references and len(output.answer.references) > 0:
            output.answer.content += f"\n\nReferences\n------------------\n"
            output.answer.content += process_references(output.answer.references)
        return output

    def get_slot_name(self, action_name: str, target_slots: []):
        if action_name in actionsHaveDefaultValue:
            target_slot_name = target_slots[0].name if target_slots else ActionToValidSlotTypesDict[action_name][0]
        else:
            target_slot_name = target_slots[0].name if target_slots else ""
        return target_slot_name

    def get_slot_value(self, target_slot_name: str, target_slots: []):
        if target_slot_name in slotsHaveDefaultValue:
            slot_value = target_slots[0].value if target_slots else config.get("defaultSlotValue", target_slot_name)
        else:
            slot_value = target_slots[0].value if target_slots else ""
        return slot_value

    def normalize_slot_value(self, slot_value: str, target_slot_name: str, action_name: ActionName) -> str:
        if not target_slot_name:
            return ""

        normalize_type = SlotTypeToNormalizeTypeDict[target_slot_name]
        if normalize_type == NormalizeType.PERCENTAGE:
            parsed_value = get_parsed_slot_value(target_slot_name, slot_value, True)
            if not parsed_value:
                return ""
            rounded_value = np.ceil(float(parsed_value) * 10)
            result_str = str(int(rounded_value * 10))
            return result_str

        if normalize_type == NormalizeType.NUMBER:
            replaced_value = slot_value.replace("倒数", "负").replace("第", "")
            return get_parsed_slot_value(action_name, replaced_value)
        return slot_value

    def prepare_slot(self, action_name: ActionName, target_slot_value: str, target_slot_name: str):
        if target_slot_name in [SlotType.functions, SlotType.font_target]:
            slot = {"value": target_slot_value}
        elif target_slot_name in [SlotType.font_change]:
            slot = {
                "category": ActionToSlotCategoryDict[action_name],
                "value": target_slot_value,
            }
        elif target_slot_name in [SlotType.header_element, SlotType.header_position]:
            slot = {
                "category": ActionToSlotCategoryDict[action_name],
                "valueType": SlotTypeToSlotValueTypeDict[target_slot_name],
                "value": target_slot_value,
            }
        elif not target_slot_name:
            if action_name in [ActionName.remove_header, ActionName.add_header]:
                slot = {
                    "category": ActionToSlotCategoryDict[action_name],
                    "valueType": "",
                    "value": "",
                }
            else:
                slot = {"value": ""}
        else:
            slot = {"value": target_slot_value}
        return slot

    def prepare_answer(
        self,
        slot: {},
        intent_description: str,
        target_slot_value: str,
        target_slot_name: str,
        action_name: ActionName,
    ):
        return ActionResponseAnswer(
            messageType=ResponseMessageType.FORMAT_INTELLIGENT_EXEC,
            content=ActionResponseAnswerContent(
                businessId="twAgentExec",
                operateType=SlotTypeToOperateTypeDict[target_slot_name]
                if target_slot_name
                else ActionTypeToOperateTypeDict[action_name],
                operateSlots=slot,
                businessInfo={
                    "instruction": prepare_instruction(intent_description, target_slot_value, target_slot_name)
                },
            ),
        )

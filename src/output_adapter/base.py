import configparser
import json
from typing import List
import re

import chinese2digits as c2d
import numpy as np
from fastapi import Depends
from loguru import logger
from requests.utils import requote_uri

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
from tracker.context import ConversationContext

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
    async def process_output(self, output: object, conversation: ConversationContext) -> object:
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


def remove_extra_newline(string: str) -> str:
    return re.sub("\n+", "\n", string)


def generate_table_html(summary_details: list[SearchItem]) -> str:
    if not summary_details:
        return ""

    headers = [
        key for key in summary_details[0].model_dump().keys() if key not in ["meta__score", "meta__reference", "id"]
    ]

    score_row = f"<tr><th>score</th><td style='text-align: center;'>{summary_details[0].meta__score}</td></tr>"

    references_header_row = "<tr><th colspan='2' style='text-align: center;'>references</th></tr>"

    references_row = ""
    for item in summary_details:
        header_to_value = item.model_dump()
        row = [str(header_to_value[header]) for header in headers]
        row.append(str(header_to_value["meta__score"]))
        references = item.meta__reference.meta__source_content
        if references:
            for key, value in references.items():
                references_row += f"<tr><th>{key}</th><td>&nbsp;&nbsp;&nbsp;&nbsp;{value}</td></tr>"
        else:
            references_row = "<tr><td colspan='2'  style='text-align: center;'>No references available</td></tr>"

    table_html = f"<table>{score_row}{references_header_row}{references_row}</table>"

    return table_html

def process_references(references: List[SearchItem]):
    html = ""

    summary_detail_dict = {}
    for item in references:
        if item.meta__reference:
            summary = item.meta__reference.meta__source_name
            if item.meta__reference.meta__source_sub_name:
                summary += f"({item.meta__reference.meta__source_sub_name})"
            if item.meta__reference.meta__source_url:
                url = requote_uri(item.meta__reference.meta__source_url)
                summary += (
                    f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href={url}>Download for checking details</a>"
                )
            summary_detail_dict.setdefault(summary, []).append(item)

    for summary in summary_detail_dict.keys():
        table_html = generate_table_html(summary_detail_dict[summary])
        details_html = f"<details><summary>{summary}</summary>{table_html}</details>"
        html += details_html

    logger.info(html)
    return html


class BaseOutputAdapter(OutputAdapter):
    def __init__(self, unified_search: UnifiedSearch = Depends()):
        self.unified_search = unified_search

    async def process_output(self, output: object, conversation: ConversationContext) -> object:
        if isinstance(output, AttachmentResponse):
            urls = [f"<a href={requote_uri(a.url)}>{requote_uri(a.url)}</a>" for a in output.attachments]
            logger.info(f"process attachment: {urls}")
            output.answer.extra_info["Attachments"] = urls
        if output.answer.references and len(output.answer.references) > 0:
            output_html = process_references(output.answer.references)
            if output_html:
                output.answer.extra_info["References Info"] = output_html
        if conversation.current_intent:
            slot_expression = conversation.current_intent.slot_expression
            self._fill_intent_value(conversation, output)
            self._fill_filled_slots_value(conversation, output, slot_expression)
            self._fill_unfilled_slots_value(conversation, output, slot_expression)
            self._fill_slot_expression(output, slot_expression)
        return output

    def _fill_slot_expression(self, output, slot_expression):
        output.answer.extra_info["slot expression"] = slot_expression

    def _fill_unfilled_slots_value(self, conversation, output, slot_expression):
        unhidden_slots = filter(lambda slot: not slot.hidden, conversation.get_unfilled_slots())
        unfilled_slots = [
            f"{slot.name} (optional)"
            if slot.optional and not slot_expression
            else f"{slot.name} (mandatory)"
            if not slot_expression
            else f"{slot.name}"
            for slot in unhidden_slots
        ]
        output.answer.extra_info["unfilled key information"] = "\n".join(unfilled_slots)

    def _fill_filled_slots_value(self, conversation, output, slot_expression):
        unhidden_entities = filter(
            lambda entity: not entity.possible_slot.hidden, conversation.get_extracted_entities()
        )
        filled_slots = [
            f"{entity.type}: {entity.value} (optional)"
            if entity.possible_slot.optional and not slot_expression
            else f"{entity.type}: {entity.value} (mandatory)"
            if not slot_expression
            else f"{entity.type}: {entity.value}"
            for entity in unhidden_entities
        ]
        output.answer.extra_info["filled key information"] = "\n".join(filled_slots)

    def _fill_intent_value(self, conversation, output):
        output.answer.extra_info["intent"] = conversation.current_intent.display_name
        if conversation.current_intent.disabled:
            output.answer.extra_info["intent"] += "(suspended)"
        if conversation.current_intent.hints:
            output.answer.extra_info["hints"] = conversation.current_intent.hints
        if conversation.current_intent.display_examples:
            output.answer.extra_info["examples"] = ""
            for index, example in enumerate(conversation.current_intent.display_examples):
                if index > 0:
                    output.answer.extra_info["examples"] += "\n"
                output.answer.extra_info["examples"] += f"Example {index + 1}: {example}"

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

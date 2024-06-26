from enum import Enum
from typing import List, Optional, Union

from nlu.intent_config import IntentConfig
from util import HashableBaseModel
from utils.common import parse_str_to_bool


class SlotType(str, Enum):
    TEXT = "text"
    CATEGORICAL = "categorical"
    INTEGER = "integer"
    LIST = "list"
    FLOAT = "float"
    BOOLEAN = "boolean"
    NUMERIC_OR_TEXT = "numeric or text"
    DATE = "date"


class Intent(HashableBaseModel):
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    confidence: Optional[float] = 1
    business: Optional[bool] = False
    full_name_of_parent_intent: Optional[str] = None
    disabled: Optional[bool] = False
    slot_expression: Optional[str] = None
    ignore_previous_slots: Optional[bool] = False
    hints: Optional[str] = None
    examples: Optional[List[str]] = None
    display_examples: Optional[List[str]] = None

    def get_full_intent_name(self) -> str:
        return f"{self.full_name_of_parent_intent}.{self.name}" if self.full_name_of_parent_intent else self.name

    def minimal_info(self):
        return {
            "name": self.name,
            "description": self.description,
        }

    @staticmethod
    def from_intent_config(intent_name: str, confidence: float, intent_config: IntentConfig):
        return Intent(
            name=intent_name,
            confidence=confidence,
            description=intent_config.description,
            full_name_of_parent_intent=intent_config.full_name_of_parent_intent,
            disabled=intent_config.disabled,
            slot_expression=intent_config.slot_expression,
            ignore_previous_slots=intent_config.ignore_previous_slots,
            display_name=intent_config.display_name,
            hints=intent_config.hints,
            examples=intent_config.examples,
            display_examples=intent_config.display_examples,
        )


class Slot(HashableBaseModel):
    name: str
    description: str
    value: Optional[str] = None
    slot_type: Optional[SlotType] = None
    confidence: Optional[float] = None
    optional: bool = True
    priority: int = 0
    hidden: bool = False

    def __hash__(self):
        return hash((self.name,))

    def __eq__(self, other):
        return self.name == other.name

    def minimal_info(self):
        return {
            "name": self.name,
            "description": self.description,
        }

    @staticmethod
    def from_dict(slot_dict: dict):
        return Slot(
            name=slot_dict["name"],
            description=slot_dict["description"],
            value=slot_dict.get("default", None),
            optional=parse_str_to_bool(slot_dict.get("optional", True), True),
            slot_type=SlotType(slot_dict["slotType"]),
            hidden=slot_dict.get("hidden", False),
        )


class Entity(HashableBaseModel):
    type: str
    value: Union[str, int, float, bool, list]
    role: Optional[str] = None
    confidence: Optional[float] = None
    possible_slot: Optional[Slot] = None


class IntentWithEntity(HashableBaseModel):
    intent: Union[Intent, None]
    entities: List[Entity]
    action: str


class IntentWithSlot(HashableBaseModel):
    intent_label: str
    intent_confidence: float
    slot_label: str

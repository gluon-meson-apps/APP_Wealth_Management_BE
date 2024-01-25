from enum import Enum
from typing import List, Optional, Union

from util import HashableBaseModel


class SlotType(str, Enum):
    TEXT = "text"
    CATEGORICAL = "categorical"
    INTEGER = "integer"
    LIST = "list"
    FLOAT = "float"
    BOOLEAN = "boolean"
    NUMERIC_OR_TEXT = "numeric or text"


class Intent(HashableBaseModel):
    name: str
    description: Optional[str]
    confidence: Optional[float] = 1
    business: Optional[bool] = False

    def minimal_info(self):
        return {
            "name": self.name,
            "description": self.description,
        }


class Slot(HashableBaseModel):
    name: str
    description: str
    value: Optional[str] = None
    slot_type: Optional[SlotType] = None
    confidence: Optional[float] = None
    optional: bool = True
    priority: int = 0

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
            optional=bool(slot_dict.get("optional", True)),
            slot_type=SlotType(slot_dict["slotType"]),
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

from enum import Enum
from typing import List, Optional

from util import HashableBaseModel


class SlotType(str, Enum):
    TEXT = "text"
    CATEGORICAL = "categorical"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    NUMERIC_OR_TEXT = "numeric or text"


class Intent(HashableBaseModel):
    name: str
    confidence: Optional[float] = None


class Slot(HashableBaseModel):
    name: str
    description: str
    value: Optional[str] = None
    slot_type: Optional[SlotType] = None
    confidence: Optional[float] = None
    optional: bool = True

    def __hash__(self):
        return hash((self.name,))

    def __eq__(self, other):
        return self.name == other.name

    @staticmethod
    def from_dict(slot_dict: dict):
        return Slot(name=slot_dict['name'], description=slot_dict['description'],
                    value=slot_dict.get('default', None), optional=bool(slot_dict.get('optional', True)),
                    slot_type=SlotType(slot_dict['slotType']))


class Entity(HashableBaseModel):
    type: str
    value: str
    role: Optional[str] = None
    confidence: Optional[float] = None
    possible_slot: Optional[Slot] = None


class IntentWithEntity(HashableBaseModel):
    intent: Intent
    entities: List[Entity]

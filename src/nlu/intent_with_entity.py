from typing import List, Optional
from enum import Enum

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

    def __hash__(self):
        return hash((self.name,))
    def __eq__(self, other):
        return self.name == other.name


class Entity(HashableBaseModel):
    type: str
    value: str
    role: Optional[str] = None
    confidence: Optional[float] = None
    possible_slot: Optional[Slot] = None


class IntentWithEntity(HashableBaseModel):
    intent: Intent
    entities: List[Entity]

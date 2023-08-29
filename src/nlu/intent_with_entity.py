from typing import List, Optional
from enum import Enum

from pydantic import BaseModel


class SlotType(str, Enum):
    TEXT = "text"
    CATEGORICAL = "categorical"
    numeric = "numeric"
    boolean = "boolean"


class Intent(BaseModel):
    name: str
    confidence: float


class Slot(BaseModel):
    name: str
    description: str
    value: Optional[str] = None
    slot_type: Optional[SlotType] = None
    confidence: Optional[float] = None


class Entity(BaseModel):
    type: str
    value: str
    role: Optional[str] = None
    confidence: Optional[float] = None
    possible_slot: Optional[Slot] = None


class IntentWithEntity(BaseModel):
    intent: List[Intent]
    entities: List[Entity]

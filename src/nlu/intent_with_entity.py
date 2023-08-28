from typing import List

from pydantic import BaseModel


class Intent(BaseModel):
    name: str
    confidence: float


class SlotFilling(BaseModel):
    name: str
    confidence: float


class Entity(BaseModel):
    type: str
    role: str
    value: str
    confidence: float
    possible_slot: SlotFilling


class IntentWithEntity(BaseModel):
    intent: List[Intent]
    entities: List[Entity]

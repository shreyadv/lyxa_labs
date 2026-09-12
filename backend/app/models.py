from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ApplianceCreate(BaseModel):
    name: str = Field(..., min_length=1)
    wattage: int = Field(..., gt=0)
    priority: int = Field(..., ge=1)


class ApplianceOut(BaseModel):
    id: int
    name: str
    wattage: int
    priority: int
    state: Literal["running", "off", "shed"]


class StatusOut(BaseModel):
    appliances: List[ApplianceOut]
    current_load: int
    capacity: int
    remaining_capacity: int


class ActionResult(BaseModel):
    success: bool
    message: str
    shed: List[str] = []
    restored: List[str] = []
    appliances: List[ApplianceOut]
    current_load: int
    remaining_capacity: int


class EventOut(BaseModel):
    id: int
    timestamp: str
    appliance_id: Optional[int]
    appliance_name: str
    from_state: Optional[str]
    to_state: str
    cause: str
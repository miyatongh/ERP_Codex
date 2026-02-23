from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class CreateRequestInput(BaseModel):
    request_no: str
    requested_at: datetime
    destination: str
    item_code: str
    qty: int = Field(ge=1)


class RequestView(BaseModel):
    request_no: str
    state: str
    destination: str
    item_code: str
    qty: int
    shortage_qty: int


class AllocationLine(BaseModel):
    container_no: str
    item_code: str
    qty: int


class AllocationResult(BaseModel):
    request_no: str
    allocated_qty: int
    shortage_qty: int
    picks: list[AllocationLine]


class WorkOrderView(BaseModel):
    request_no: str
    destination: str
    picks: list[AllocationLine]
    empty_container_marks: list[str]

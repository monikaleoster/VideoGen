import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Generic, TypeVar


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    DONE = "done"


OutputT = TypeVar("OutputT")


@dataclass
class StepState(Generic[OutputT]):
    """Holds one step's in-flight status, approval gate, and output.

    Shared shape reused by every pipeline step (Phase 2 adds six more).
    """

    status: StepStatus = StepStatus.PENDING
    approval_event: asyncio.Event = field(default_factory=asyncio.Event)
    output: OutputT | None = None

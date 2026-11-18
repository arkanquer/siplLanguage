from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from .ast import SourceSpan


@dataclass(frozen=True)
class TraceEvent:
    kind: str
    step: int
    span: SourceSpan | None
    state: dict[str, int]
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

class ExecutionTrace:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def record(self, kind: str, step: int, span: SourceSpan | None,
               state: dict[str, int], **details: Any) -> None:
        self.events.append(TraceEvent(kind, step, span, dict(state), details))

    def to_json_data(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self.events]

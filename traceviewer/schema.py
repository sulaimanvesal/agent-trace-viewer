"""Trace event schema: validation + normalization for agent run traces."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

VALID_TYPES = {"thought", "tool_call", "observation", "error", "final_answer", "user"}


@dataclass
class Event:
    """One normalized trace event."""

    step: int
    type: str
    content: str = ""
    tool: str = ""
    args: dict = field(default_factory=dict)
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    timestamp: str = ""
    run_id: str = ""
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize(raw: dict, fallback_step: int) -> Event:
    """Normalize a raw event dict into an :class:`Event`.

    Tolerates missing/alternate keys so traces from different agent
    frameworks (ReAct loops, tool routers, custom loggers) load without
    a strict schema.
    """
    if not isinstance(raw, dict):
        raw = {"content": str(raw)}

    ev_type = str(raw.get("type") or raw.get("event") or "thought").lower()
    if ev_type not in VALID_TYPES:
        ev_type = "thought"

    tokens = raw.get("tokens") or {}
    if not isinstance(tokens, dict):
        tokens = {}

    tool = raw.get("tool") or raw.get("tool_name") or ""
    args = raw.get("args") or raw.get("arguments") or {}
    if not isinstance(args, dict):
        args = {"value": args}

    content = raw.get("content") or raw.get("text") or raw.get("message") or ""
    if not isinstance(content, str):
        content = str(content)

    return Event(
        step=_as_int(raw.get("step"), fallback_step),
        type=ev_type,
        content=content,
        tool=str(tool),
        args=args,
        latency_ms=_as_float(raw.get("latency_ms", raw.get("latency"))),
        input_tokens=_as_int(tokens.get("input", tokens.get("prompt"))),
        output_tokens=_as_int(tokens.get("output", tokens.get("completion"))),
        timestamp=str(raw.get("t") or raw.get("timestamp") or ""),
        run_id=str(raw.get("run_id") or ""),
        raw=raw,
    )


def parse_timestamp(value: str) -> datetime | None:
    """Best-effort ISO-8601 parse; returns None when unparsable."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

"""Aggregate statistics over a normalized trace."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .schema import Event, parse_timestamp


@dataclass
class Summary:
    n_events: int = 0
    n_steps: int = 0
    n_tool_calls: int = 0
    n_errors: int = 0
    n_thoughts: int = 0
    n_observations: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_latency_ms: float = 0.0
    wall_ms: float | None = None
    run_id: str = ""
    tool_counts: dict = field(default_factory=dict)
    slowest: list = field(default_factory=list)  # [(step, tool/type, latency_ms)]

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens


def summarize(events: list[Event]) -> Summary:
    """Compute aggregate stats for a trace."""
    s = Summary()
    s.n_events = len(events)
    if not events:
        return s

    steps = {e.step for e in events}
    s.n_steps = len(steps)
    s.run_id = next((e.run_id for e in events if e.run_id), "")

    tools: Counter[str] = Counter()
    for e in events:
        s.total_input_tokens += e.input_tokens
        s.total_output_tokens += e.output_tokens
        s.total_latency_ms += e.latency_ms
        if e.type == "tool_call":
            s.n_tool_calls += 1
            tools[e.tool or "(unnamed)"] += 1
        elif e.type == "error":
            s.n_errors += 1
        elif e.type == "thought":
            s.n_thoughts += 1
        elif e.type == "observation":
            s.n_observations += 1
    s.tool_counts = dict(tools.most_common())

    timed = sorted(events, key=lambda e: e.latency_ms, reverse=True)[:5]
    s.slowest = [(e.step, e.tool or e.type, e.latency_ms) for e in timed if e.latency_ms > 0]

    stamps = [parse_timestamp(e.timestamp) for e in events]
    stamps = [t for t in stamps if t is not None]
    if len(stamps) >= 2:
        s.wall_ms = (max(stamps) - min(stamps)).total_seconds() * 1000.0

    return s

"""Load traces from JSONL or JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from .schema import Event, normalize


def load_file(path: str | Path) -> list[Event]:
    """Load events from one file.

    Accepts JSONL (one event per line) or JSON (a single event object
    or an array of event objects). Blank lines are skipped.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    raw_events: list[dict] = []
    if path.suffix.lower() == ".jsonl" or text.splitlines()[0].lstrip().startswith("{") and "\n" in text:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}: invalid JSONL on line: {line[:80]!r}") from exc
            raw_events.append(obj)
    else:
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: invalid JSON: {exc}") from exc
        raw_events = obj if isinstance(obj, list) else [obj]

    return [normalize(raw, fallback_step=i + 1) for i, raw in enumerate(raw_events)]


def load_trace(paths: list[str | Path]) -> list[Event]:
    """Load and merge events from several trace files, ordered by step."""
    events: list[Event] = []
    for p in paths:
        events.extend(load_file(p))
    events.sort(key=lambda e: (e.step, e.timestamp))
    return events

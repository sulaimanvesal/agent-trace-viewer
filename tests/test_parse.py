"""Tests for trace loading / normalization."""

import json

import pytest

from traceviewer.parse import load_file, load_trace
from traceviewer.schema import normalize


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_load_jsonl(tmp_path):
    p = _write(
        tmp_path,
        "t.jsonl",
        '{"step": 1, "type": "thought", "content": "hmm"}\n'
        '{"step": 2, "type": "tool_call", "tool": "search", "args": {"q": "x"}, "latency_ms": 120}\n',
    )
    events = load_file(p)
    assert len(events) == 2
    assert events[0].type == "thought"
    assert events[0].content == "hmm"
    assert events[1].tool == "search"
    assert events[1].args == {"q": "x"}
    assert events[1].latency_ms == 120


def test_load_json_array(tmp_path):
    p = _write(tmp_path, "t.json", json.dumps([{"type": "error", "content": "boom"}]))
    events = load_file(p)
    assert len(events) == 1
    assert events[0].type == "error"
    assert events[0].step == 1  # fallback step


def test_blank_lines_skipped(tmp_path):
    p = _write(tmp_path, "t.jsonl", '\n{"type": "user", "content": "hi"}\n\n')
    assert len(load_file(p)) == 1


def test_invalid_jsonl_raises(tmp_path):
    p = _write(tmp_path, "t.jsonl", '{"type": "thought"}\nnot json\n')
    with pytest.raises(ValueError):
        load_file(p)


def test_normalize_unknown_type_defaults_to_thought():
    e = normalize({"type": "weird_thing", "content": "x"}, fallback_step=7)
    assert e.type == "thought"
    assert e.step == 7


def test_normalize_alternate_keys():
    e = normalize(
        {
            "event": "tool_call",
            "tool_name": "calc",
            "arguments": {"a": 1},
            "tokens": {"prompt": 50, "completion": 10},
        },
        fallback_step=1,
    )
    assert e.type == "tool_call"
    assert e.tool == "calc"
    assert e.args == {"a": 1}
    assert e.input_tokens == 50
    assert e.output_tokens == 10
    assert e.total_tokens == 60


def test_load_trace_merges_and_sorts(tmp_path):
    a = _write(tmp_path, "a.jsonl", '{"step": 2, "type": "observation", "content": "o"}\n')
    b = _write(tmp_path, "b.jsonl", '{"step": 1, "type": "thought", "content": "t"}\n')
    events = load_trace([a, b])
    assert [e.step for e in events] == [1, 2]

"""Tests for stats aggregation and HTML rendering."""

from traceviewer.render import render_html
from traceviewer.schema import normalize
from traceviewer.stats import summarize


def _events():
    raw = [
        {"step": 1, "type": "thought", "content": "need info"},
        {
            "step": 2,
            "type": "tool_call",
            "tool": "web_search",
            "args": {"q": "llm"},
            "latency_ms": 900,
            "tokens": {"input": 100, "output": 40},
            "t": "2026-09-24T17:00:01Z",
        },
        {"step": 3, "type": "observation", "tool": "web_search", "content": "results"},
        {"step": 4, "type": "error", "content": "timeout", "latency_ms": 100},
        {
            "step": 5,
            "type": "final_answer",
            "content": "done",
            "tokens": {"input": 200, "output": 60},
            "t": "2026-09-24T17:00:10Z",
        },
    ]
    return [normalize(r, i + 1) for i, r in enumerate(raw)]


def test_summarize_counts():
    s = summarize(_events())
    assert s.n_events == 5
    assert s.n_steps == 5
    assert s.n_tool_calls == 1
    assert s.n_errors == 1
    assert s.n_thoughts == 1
    assert s.n_observations == 1
    assert s.total_input_tokens == 300
    assert s.total_output_tokens == 100
    assert s.total_latency_ms == 1000
    assert s.tool_counts == {"web_search": 1}
    assert s.wall_ms == 9000


def test_summarize_empty():
    s = summarize([])
    assert s.n_events == 0
    assert s.total_tokens == 0
    assert s.wall_ms is None


def test_summarize_slowest():
    s = summarize(_events())
    assert s.slowest[0] == (2, "web_search", 900)


def test_render_html_contains_key_sections():
    events = _events()
    doc = render_html(events, summarize(events), title="Demo")
    assert "<title>Demo</title>" in doc
    assert "Latency waterfall" in doc
    assert "web_search" in doc
    assert "timeout" in doc  # error content present
    assert "<svg" in doc  # waterfall chart rendered
    assert "http" not in doc.split("<style>")[0]  # no external assets before CSS


def test_render_html_escapes_content():
    events = [normalize({"step": 1, "type": "thought", "content": "<script>alert(1)</script>"}, 1)]
    doc = render_html(events, summarize(events))
    assert "<script>alert(1)</script>" not in doc
    assert "&lt;script&gt;" in doc


def test_render_empty_trace():
    doc = render_html([], summarize([]))
    assert "0 events" in doc

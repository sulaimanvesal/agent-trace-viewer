"""Zero-API-key demo: generate a realistic sample agent trace, then render it.

Usage:
    python demo/make_demo.py            # writes demo/sample_trace.jsonl + demo/report.html
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

from traceviewer.cli import main as cli_main  # noqa: E402

rng = random.Random(42)
t0 = datetime(2026, 9, 24, 17, 0, 0, tzinfo=timezone.utc)


def _t(seconds: float) -> str:
    return (t0 + timedelta(seconds=seconds)).isoformat()


def build_trace() -> list[dict]:
    clock = 0.0
    events: list[dict] = []

    def add(ev: dict):
        nonlocal clock
        ev = dict(ev)
        ev["t"] = _t(clock)
        events.append(ev)

    plan = [
        ("user", "Compare vector DB options for a RAG prototype.", 0),
        ("thought", "I should search for current vector DB benchmarks and pricing.", 0),
        ("tool_call", "web_search", {"query": "vector database benchmark 2026 recall latency"}, 1840, 1250, 380),
        ("observation", "web_search", "Top hits: pgvector, Qdrant, Weaviate, Milvus. Benchmarks show ...", 0),
        ("thought", "Good overview. Now check pricing pages for the hosted options.", 0),
        ("tool_call", "web_search", {"query": "qdrant cloud pricing vs weaviate pricing 2026"}, 1210, 900, 260),
        ("observation", "web_search", "Qdrant Cloud from $25/mo; Weaviate Cloud from $25/mo; ...", 0),
        ("thought", "I have enough for a comparison table. Let me verify the pgvector HNSW claim.", 0),
        ("tool_call", "web_search", {"query": "pgvector HNSW recall benchmark"}, 960, 820, 240),
        ("observation", "web_search", "pgvector HNSW recall@10 ~0.97 on 1M vectors ...", 0),
        ("error", None, "calculator plugin unavailable, falling back to mental math", 0, 0, 0),
        ("thought", "Compiling the final comparison now.", 0),
        (
            "final_answer",
            None,
            "## Vector DB comparison\n\n| DB | Recall@10 | Latency p50 | Hosted from |\n"
            "|---|---|---|---|\n| pgvector (HNSW) | 0.97 | 8 ms | self-host |\n"
            "| Qdrant | 0.98 | 5 ms | $25/mo |\n| Weaviate | 0.97 | 6 ms | $25/mo |\n"
            "| Milvus | 0.98 | 4 ms | self-host |\n\nRecommendation: start with pgvector ...",
            0,
            2100,
            640,
        ),
    ]

    step = 0
    for kind, *rest in plan:
        step += 1
        if kind == "tool_call":
            tool, args, latency, tin, tout = rest
            clock += latency / 1000.0
            add(
                {
                    "step": step,
                    "type": "tool_call",
                    "tool": tool,
                    "args": args,
                    "latency_ms": latency,
                    "tokens": {"input": tin, "output": tout},
                }
            )
        elif kind == "observation":
            tool, content, *_ = rest
            clock += 0.05
            add({"step": step, "type": "observation", "tool": tool, "content": content})
        elif kind == "error":
            _, content, *_ = rest
            add({"step": step, "type": "error", "content": content})
        elif kind == "final_answer":
            _, content, _, tin, tout = rest
            clock += 2.4
            add(
                {
                    "step": step,
                    "type": "final_answer",
                    "content": content,
                    "latency_ms": 2400,
                    "tokens": {"input": tin, "output": tout},
                }
            )
        else:  # user / thought
            content = rest[0]
            clock += rng.uniform(0.2, 0.9)
            add({"step": step, "type": kind, "content": content})
    return events


def main() -> None:
    ROOT.mkdir(exist_ok=True)
    trace_path = ROOT / "sample_trace.jsonl"
    report_path = ROOT / "report.html"

    events = build_trace()
    trace_path.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {trace_path} ({len(events)} events)")

    rc = cli_main(
        [str(trace_path), "-o", str(report_path), "--title", "Demo: research agent trace"]
    )
    if rc != 0:
        raise SystemExit(rc)

    # Also exercise the --summary path.
    subprocess.run(
        [sys.executable, "-m", "traceviewer", str(trace_path), "--summary"],
        cwd=str(ROOT.parent),
        check=True,
    )


if __name__ == "__main__":
    main()

"""CLI: traceviewer trace.jsonl [more.jsonl ...] -o report.html"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .parse import load_trace
from .render import render_html
from .stats import summarize


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="traceviewer",
        description="Render agent run traces (JSONL/JSON) as a self-contained HTML report.",
    )
    p.add_argument("inputs", nargs="+", help="trace file(s): .jsonl or .json")
    p.add_argument("-o", "--output", default="trace-report.html", help="output HTML path")
    p.add_argument("--title", default="Agent trace report", help="report title")
    p.add_argument("--summary", action="store_true", help="print text summary and exit")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    for path in args.inputs:
        if not Path(path).is_file():
            print(f"error: not found: {path}", file=sys.stderr)
            return 2

    try:
        events = load_trace(args.inputs)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    summary = summarize(events)

    if args.summary:
        print(f"events:        {summary.n_events}")
        print(f"steps:         {summary.n_steps}")
        print(f"tool calls:    {summary.n_tool_calls}")
        print(f"errors:        {summary.n_errors}")
        print(f"tokens in/out: {summary.total_input_tokens} / {summary.total_output_tokens}")
        print(f"LLM latency:   {summary.total_latency_ms:.0f} ms")
        if summary.wall_ms is not None:
            print(f"wall time:     {summary.wall_ms:.0f} ms")
        for tool, count in summary.tool_counts.items():
            print(f"  tool {tool}: {count}")
        return 0

    html_doc = render_html(events, summary, title=args.title)
    out = Path(args.output)
    out.write_text(html_doc, encoding="utf-8")
    print(f"wrote {out} ({summary.n_events} events, {summary.n_steps} steps)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

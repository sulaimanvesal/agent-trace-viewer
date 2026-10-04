"""Render a self-contained HTML report from events + summary.

No external assets: inline CSS, inline SVG waterfall, <details> for
collapsible steps. The report opens offline in any browser.
"""

from __future__ import annotations

import html
import json
from datetime import datetime

from .schema import Event
from .stats import Summary

TYPE_COLORS = {
    "thought": "#7c6ff0",
    "tool_call": "#2f9e6e",
    "observation": "#c98a1b",
    "error": "#d64545",
    "final_answer": "#1f6feb",
    "user": "#6e7781",
}

CSS = """
:root { color-scheme: light dark; }
body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0;
       padding: 24px; max-width: 1100px; margin-inline: auto; line-height: 1.5; }
h1 { font-size: 1.6rem; margin-bottom: 0.2rem; }
.sub { color: #888; margin-bottom: 1.2rem; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
         gap: 12px; margin-bottom: 1.6rem; }
.card { border: 1px solid #ddd; border-radius: 10px; padding: 12px 14px; }
.card .k { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #888; }
.card .v { font-size: 1.35rem; font-weight: 650; }
section { margin-bottom: 1.8rem; }
table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
th, td { border: 1px solid #ddd; padding: 8px 10px; text-align: left; vertical-align: top; }
th { background: #f4f4f5; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 999px; color: #fff;
         font-size: 0.75rem; font-weight: 600; }
details { border: 1px solid #ddd; border-radius: 8px; margin-bottom: 8px; }
summary { padding: 10px 12px; cursor: pointer; font-size: 0.92rem; }
.stepbody { padding: 0 12px 12px 12px; font-size: 0.88rem; }
pre { background: #f6f8fa; padding: 10px; border-radius: 6px; overflow-x: auto;
      font-size: 0.82rem; white-space: pre-wrap; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }
"""


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _fmt_ms(ms: float) -> str:
    if ms >= 60_000:
        return f"{ms / 60_000:.1f} min"
    if ms >= 1_000:
        return f"{ms / 1_000:.2f} s"
    return f"{ms:.0f} ms"


def _waterfall(events: list[Event]) -> str:
    """Inline SVG bar chart of per-step latency."""
    timed = [e for e in events if e.latency_ms > 0]
    if not timed:
        return "<p>No per-step latency data in this trace.</p>"
    peak = max(e.latency_ms for e in timed)
    w, row_h, label_w, bar_max = 900, 26, 200, 640
    h = row_h * len(timed) + 10
    rows = []
    for i, e in enumerate(timed):
        y = 10 + i * row_h
        bar_w = max(3, e.latency_ms / peak * bar_max)
        color = TYPE_COLORS.get(e.type, "#888")
        label = _esc(f"step {e.step} · {e.tool or e.type}")
        rows.append(
            f'<text x="0" y="{y + 15}" font-size="12">{label}</text>'
            f'<rect x="{label_w}" y="{y + 4}" width="{bar_w:.1f}" height="14" rx="3" fill="{color}"/>'
            f'<text x="{label_w + bar_w + 6:.1f}" y="{y + 15}" font-size="12" fill="#888">'
            f"{_fmt_ms(e.latency_ms)}</text>"
        )
    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="per-step latency waterfall">{"".join(rows)}</svg>'
    )


def _event_block(e: Event) -> str:
    color = TYPE_COLORS.get(e.type, "#888")
    head = f'<span class="dot" style="background:{color}"></span><b>step {e.step}</b>'
    head += f' <span class="badge" style="background:{color}">{_esc(e.type)}</span>'
    if e.tool:
        head += f" <code>{_esc(e.tool)}</code>"
    if e.latency_ms:
        head += f" <span style='color:#888'>· {_fmt_ms(e.latency_ms)}</span>"
    if e.total_tokens:
        head += f" <span style='color:#888'>· {e.total_tokens} tok</span>"

    body_parts = []
    if e.content:
        body_parts.append(f"<pre>{_esc(e.content[:4000])}</pre>")
    if e.args:
        pretty = json.dumps(e.args, indent=2, ensure_ascii=False)[:4000]
        body_parts.append(f"<b>args</b><pre>{_esc(pretty)}</pre>")
    meta = []
    if e.timestamp:
        meta.append(f"at {_esc(e.timestamp)}")
    if e.input_tokens or e.output_tokens:
        meta.append(f"tokens in={e.input_tokens} out={e.output_tokens}")
    if meta:
        body_parts.append(f"<div style='color:#888'>{' · '.join(meta)}</div>")
    body = "".join(body_parts) or "<i>(empty)</i>"
    return f"<details><summary>{head}</summary><div class='stepbody'>{body}</div></details>"


def render_html(events: list[Event], summary: Summary, title: str = "Agent trace report") -> str:
    """Build the full HTML document."""
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    cards = [
        ("steps", summary.n_steps),
        ("events", summary.n_events),
        ("tool calls", summary.n_tool_calls),
        ("errors", summary.n_errors),
        ("tokens in / out", f"{summary.total_input_tokens:,} / {summary.total_output_tokens:,}"),
        ("LLM latency", _fmt_ms(summary.total_latency_ms)),
    ]
    if summary.wall_ms is not None:
        cards.append(("wall time", _fmt_ms(summary.wall_ms)))
    cards_html = "".join(
        f"<div class='card'><div class='k'>{_esc(k)}</div><div class='v'>{_esc(v)}</div></div>"
        for k, v in cards
    )

    if summary.tool_counts:
        tool_rows = "".join(
            f"<tr><td><code>{_esc(t)}</code></td><td>{c}</td></tr>"
            for t, c in summary.tool_counts.items()
        )
        tools_html = f"<table><tr><th>tool</th><th>calls</th></tr>{tool_rows}</table>"
    else:
        tools_html = "<p>No tool calls recorded.</p>"

    if summary.slowest:
        slow_rows = "".join(
            f"<tr><td>{s}</td><td><code>{_esc(t)}</code></td><td>{_fmt_ms(ms)}</td></tr>"
            for s, t, ms in summary.slowest
        )
        slow_html = f"<table><tr><th>step</th><th>tool / event</th><th>latency</th></tr>{slow_rows}</table>"
    else:
        slow_html = "<p>No latency data.</p>"

    timeline = "".join(_event_block(e) for e in events) or "<p>(empty trace)</p>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title>
<style>{CSS}</style>
</head>
<body>
<h1>{_esc(title)}</h1>
<div class="sub">generated {generated}{" · run " + _esc(summary.run_id) if summary.run_id else ""} · {summary.n_events} events</div>
<section><div class="cards">{cards_html}</div></section>
<section><h2>Latency waterfall</h2>{_waterfall(events)}</section>
<section><h2>Tool usage</h2>{tools_html}</section>
<section><h2>Slowest steps</h2>{slow_html}</section>
<section><h2>Step timeline</h2>{timeline}</section>
</body>
</html>
"""

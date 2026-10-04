"""agent-trace-viewer: turn agent run traces into readable HTML reports.

Ingest JSONL/JSON traces of LLM agent runs (thoughts, tool calls,
observations, errors, final answers) and render a single self-contained
HTML report with a latency waterfall, token summary, and step timeline.
"""

__version__ = "0.1.0"

from .parse import load_trace
from .stats import summarize
from .render import render_html

__all__ = ["load_trace", "summarize", "render_html", "__version__"]

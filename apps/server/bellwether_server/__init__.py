"""bellwether-server: the service behind the dashboard, the public API, the
MCP server (the Alexa+ surface) and the Bedrock-phrased weekly note.

It receives feature rows and never text. Every tier, trend and report is
derived from the stored rows on each read by the pure engine, never stored.
"""

from .app import build_app
from .bedrock import MODEL_LADDER, build_model_ladder, phrase_weekly_note, template_note
from .mcp import MCP_PROTOCOL_VERSION, build_report, profile_view
from .store import DynamoStore, MemoryStore, Store

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "MCP_PROTOCOL_VERSION",
    "MODEL_LADDER",
    "DynamoStore",
    "MemoryStore",
    "Store",
    "build_app",
    "build_model_ladder",
    "build_report",
    "phrase_weekly_note",
    "profile_view",
    "template_note",
]

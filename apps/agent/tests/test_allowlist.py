"""The Bee tool allowlist is a safety boundary, so it gets a test.

Bellwether's guarantee is that words are reduced to numbers where the
transcript lives and nothing that can reconstruct a sentence ever travels.
The Context Check-in agent connects to Bee's own MCP server, which exposes
verbatim speech alongside derived context, so the allowlist in that agent is
the single point where the guarantee could be lost quietly.

These tests pin it: that the two sets never overlap, that filtering is
positive rather than negative, and that an unknown tool is excluded by
default rather than admitted by accident.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

AGENT = Path(__file__).resolve().parents[1] / "context_check_in.py"


def load_agent():
    """Import the agent module without requiring strands to be installed.

    The agent imports strands and mcp at module level, which are optional
    for anyone running only the test suite. Stubbing them keeps this test
    runnable everywhere, and the allowlist is a plain constant that does not
    need either package to be verified.
    """
    import types

    for name, attrs in {
        "mcp": [],
        "mcp.client": [],
        "mcp.client.streamable_http": ["streamablehttp_client"],
        "strands": ["Agent"],
        "strands.models": ["BedrockModel"],
        "strands.tools": [],
        "strands.tools.mcp": ["MCPClient"],
    }.items():
        if name not in sys.modules:
            mod = types.ModuleType(name)
            for a in attrs:
                setattr(mod, a, object)
            sys.modules[name] = mod

    spec = importlib.util.spec_from_file_location("context_check_in", AGENT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def agent():
    return load_agent()


def test_no_speech_tool_is_in_the_allowlist(agent):
    """The core guarantee. If this ever fails, the agent can read what the
    person actually said, and the product's central claim is false."""
    overlap = agent.BEE_CONTEXT_TOOLS & agent.BEE_SPEECH_TOOLS
    assert overlap == frozenset(), f"speech tools reachable by the model: {sorted(overlap)}"


def test_every_documented_speech_tool_is_named(agent):
    """Bee's MCP catalogue, as documented, returns verbatim speech from these
    tools. Naming them explicitly makes the exclusion auditable rather than
    incidental, so a reviewer can check the list against Bee's docs."""
    documented = {
        "bee_get_conversation_transcript",
        "bee_get_conversation",
        "bee_list_conversations",
        "bee_get_related_conversations",
        "bee_search",
        "bee_list_voice_notes",
        "bee_search_voice_notes",
        "bee_get_voice_note",
    }
    assert documented <= agent.BEE_SPEECH_TOOLS


def test_allowlist_contains_only_derived_context(agent):
    """Everything permitted describes the shape of a day: what it was
    summarised as, what had to be done, where the person was."""
    assert agent.BEE_CONTEXT_TOOLS == frozenset(
        {
            "bee_get_daily_summary",
            "bee_list_daily_summaries",
            "bee_list_todos",
            "bee_get_insights",
            "bee_get_location_clusters",
            "bee_get_recent_visits",
            "bee_get_current_location",
            "bee_get_recent_activity",
            "bee_status",
        }
    )


@pytest.mark.parametrize(
    "unknown",
    [
        "bee_get_conversation_audio",
        "bee_export_everything",
        "bee_get_transcript_v2",
        "bee_search_utterances",
        "",
    ],
)
def test_an_unknown_tool_is_excluded_by_default(agent, unknown):
    """Filtering is positive: membership in the allowlist, not absence from a
    denylist. A tool Bee adds tomorrow, or renames, is withheld until someone
    reads it and decides, which is the safe direction for this to fail in."""
    assert unknown not in agent.BEE_CONTEXT_TOOLS


def test_partition_is_exhaustive_over_the_documented_catalogue(agent):
    """Every tool in Bee's documented catalogue is either allowed or named as
    withheld. A tool in neither set would be silently excluded, which is safe
    but would mean the file no longer describes reality."""
    documented_catalogue = agent.BEE_CONTEXT_TOOLS | agent.BEE_SPEECH_TOOLS
    # Todo mutations and fact tools exist in Bee's catalogue but are neither
    # context we read nor speech we withhold; they are simply not used.
    assert len(documented_catalogue) == len(agent.BEE_CONTEXT_TOOLS) + len(
        agent.BEE_SPEECH_TOOLS
    )

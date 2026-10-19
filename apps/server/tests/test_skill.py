"""The Agent Skill names every tool the MCP server has, and no other."""

import re
from pathlib import Path

from bellwether_server.mcp import TOOLS

SKILL = Path(__file__).resolve().parents[3] / "skills" / "bellwether" / "SKILL.md"


def test_the_skill_names_every_tool_on_the_server():
    text = SKILL.read_text(encoding="utf-8")
    for t in TOOLS:
        assert f"`{t['name']}`" in text, t["name"]


def test_the_skill_names_no_tool_the_server_lacks():
    text = SKILL.read_text(encoding="utf-8")
    listed = set(re.findall(r"^- \*\*`([a-z_]+)`\*\*", text, flags=re.M))
    assert listed <= {t["name"] for t in TOOLS}, listed - {t["name"] for t in TOOLS}

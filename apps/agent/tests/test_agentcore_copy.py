"""The agent hosted on AgentCore is the same code as the local one."""

from pathlib import Path

AGENT = Path(__file__).resolve().parents[1]


def test_the_hosted_second_opinion_is_byte_for_byte_the_local_one():
    local = (AGENT / "second_opinion.py").read_bytes()
    hosted = (AGENT.parent / "agentcore" / "app" / "secondopinion" / "second_opinion.py").read_bytes()
    assert hosted == local, "copy apps/agent/second_opinion.py into apps/agentcore/app/secondopinion/"

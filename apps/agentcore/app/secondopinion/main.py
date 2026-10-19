"""Bellwether's second opinion, hosted on Amazon Bedrock AgentCore Runtime.

Invoke with {"profile": "alex-drift"} (or any profile id). The runtime asks
Bellwether's MCP server, the same endpoint Alexa+ uses, for
weigh_the_change, then runs the three Strands agents from
second_opinion.py: an Advocate, a Sceptic and a Referee whose note passes
a gate (both sides cited, only the evidence's numbers, no condition named)
before it is returned.

second_opinion.py here is a copy of apps/agent/second_opinion.py; a test
in apps/agent/tests fails if the two ever differ, so the hosted agent and
the local one are always the same code.

The runtime has no database access and no privileged path: it reaches a
profile only through the MCP server's public tools, and there are no
transcripts for it to reach, because none exist.
"""

from __future__ import annotations

import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp

import second_opinion as so

app = BedrockAgentCoreApp()
log = app.logger

MCP_URL = os.environ.get("BELLWETHER_MCP_URL", so.DEFAULT_MCP_URL)
# The profile this account is verified to invoke from AWS (the Bedrock
# ladder in Bellwether's service starts here too).
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")


@app.entrypoint
def invoke(payload, context):
    profile = "alex-drift"
    if isinstance(payload, dict):
        profile = str(payload.get("profile") or payload.get("prompt") or profile).strip() or profile
    log.info("second opinion for %s", profile)
    w = so.fetch_evidence(MCP_URL, profile)
    if not w.get("change"):
        return {"profile_id": profile, "tier": w.get("tier"), "note": w.get("note"), "note_source": "nothing to weigh"}
    out = so.debate(w, so.strands_ask(MODEL_ID))
    out["model"] = MODEL_ID
    out["runtime"] = "Amazon Bedrock AgentCore Runtime"
    return out


if __name__ == "__main__":
    app.run()

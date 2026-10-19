# The second opinion, hosted on Amazon Bedrock AgentCore

The same three-agent second opinion that runs locally in [`apps/agent/second_opinion.py`](../agent/second_opinion.py), deployed to AgentCore Runtime as an invocable endpoint.

```
Runtime: bellwethersecond_secondopinion
Region:  us-east-1
Model:   us.anthropic.claude-sonnet-4-6
```

## What it does

Invoked with a profile id, it asks Bellwether's MCP server (spec 2025-11-25, Streamable HTTP, the endpoint Alexa+ uses) for `weigh_the_change`: numbered evidence that a flagged change is real (C1...) and that an ordinary week explains it (O1...), computed from the engine's numbers with no model. Three Strands agents then argue it. The Advocate makes the case for a real change, the Sceptic the case for an ordinary week, and the Referee writes the note. The note is returned only if it cites both sides, uses no number outside the evidence and names no condition; a refused note gets one retry with the reason, then falls back to a note built from the evidence alone.

The runtime has no database access and no privileged path. It reaches a profile only through the MCP server's public tools, and there are no transcripts for it to reach, because none exist.

## Why host it

Locally the second opinion is a script. On AgentCore Runtime it is an endpoint with an ARN, its own IAM role and CloudWatch traces, so Alexa+, a scheduled weekly job, or another agent can ask for a second opinion on any flagged change.

## Verified running, 2026-10-19

```
npx @aws/agentcore invoke --prompt "alex-drift"
```

The hosted run returned the Advocate's and the Sceptic's arguments, the full evidence, and a Referee note that passed the gate first time (`"note_source": "referee"`, `"gate": "ok"`, no rejected notes), on Claude Sonnet 4.6.

## Deploy it yourself

```
cd apps/agentcore
cp agentcore/aws-targets.example.json agentcore/aws-targets.json   # set your account id
(cd agentcore/cdk && npm install)
npx @aws/agentcore deploy --yes
npx @aws/agentcore invoke --prompt "alex-drift"
```

`aws-targets.json` holds your own account and region and is gitignored. `.cli/` and `.cache/` are local state.

## What is in here

| Path | What it is |
|---|---|
| `app/secondopinion/main.py` | The entrypoint: fetch the evidence over MCP, run the debate, return the gated result |
| `app/secondopinion/second_opinion.py` | A copy of `apps/agent/second_opinion.py`; `apps/agent/tests/test_agentcore_copy.py` fails if they differ |
| `agentcore/agentcore.json` | The project: one Python runtime, CodeZip build, public network, HTTP protocol |
| `agentcore/cdk/` | The CDK app the AgentCore CLI deploys with |

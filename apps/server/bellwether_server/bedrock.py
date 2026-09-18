"""The weekly note: the one paragraph a person reads about their own week.

Division of labour, stated because it is a design principle: the engine
decides WHAT happened (deterministic, tested, never a model). Claude on
Amazon Bedrock decides only HOW TO SAY IT, warmly and briefly, from facts
the engine computed. The model may not add, remove or alter a fact, may
not diagnose, and may not predict.

A model ladder, not a model. A single model id is a single point of
failure, and on Bedrock those failures are real: per-account allowlist
gates, regional capacity, throttling. Three Claude models are tried in
order; if every rung fails, the deterministic template ships. It is the
engine's own summary, so the note degrades in warmth and never in accuracy.
Every note reports which rung wrote it and what was tried.

Configuration cannot silently remove the ladder: BELLWETHER_MODEL_IDS is an
explicit complete ladder; BELLWETHER_MODEL_ID names a preference and is
prepended to the defaults rather than replacing them.
"""

from __future__ import annotations

import os
import re

DEFAULT_LADDER = [
    "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    "us.anthropic.claude-3-5-haiku-20241022-v1:0",
]


def build_model_ladder(env=None) -> list[str]:
    env = os.environ if env is None else env
    explicit = env.get("BELLWETHER_MODEL_IDS")
    if explicit:
        ladder = [m.strip() for m in explicit.split(",") if m.strip()]
        if ladder:
            return ladder
    preferred = (env.get("BELLWETHER_MODEL_ID") or "").strip()
    if preferred:
        return [preferred, *[m for m in DEFAULT_LADDER if m != preferred]]
    return list(DEFAULT_LADDER)


MODEL_LADDER = build_model_ladder()

SYSTEM = "\n".join(
    [
        "You phrase a short weekly note for one person about how their own speech has been, based on facts computed by a monitoring system that compares them only with their own past.",
        "Rules, all mandatory:",
        "1. Use only the facts given. Never add events, causes, numbers or reassurances that are not stated.",
        "2. Never alter a number, a date, a tier, or a feature name.",
        "3. Never diagnose, never name a condition, never predict what will happen, never give medical advice. You may suggest only what the person can do themselves: add a note about sleep, travel or illness, run the spoken check, or bring the report to their clinician.",
        "4. Three sentences maximum. Warm, calm, plain language, second person. No emojis. No dashes of any kind as punctuation.",
        "5. If the week was stable, say so plainly and briefly. A short note is a good week, not a failure to find something.",
        "Reply with the note only.",
    ]
)

_TIER_PLAIN = {
    "learning": "still learning your baseline",
    "stable": "within your normal range",
    "watch": "showing some change worth watching",
    "discuss": "showing a change worth raising with your clinician",
    "excluded": "too quiet to assess",
}


def facts_text(summary: dict, trend: list[dict]) -> str:
    """The facts the model is allowed to phrase, and nothing else."""
    lines = [
        f"Current tier: {summary.get('tier')} since {summary.get('since')}.",
        f"Eligible days: {summary.get('eligible_days')}. Excluded low-exposure days: {summary.get('excluded_days')}.",
    ]
    if summary.get("in_warmup"):
        lines.append(f"Warmup days remaining: {summary.get('warmup_days_remaining')}.")
    if summary.get("stable_streak_days"):
        lines.append(f"Stable streak: {summary['stable_streak_days']} days.")
    if summary.get("contributors"):
        lines.append("Features driving the change: " + ", ".join(summary["contributors"]) + ".")
    if trend:
        tiers = [t.get("tier") for t in trend]
        counts = {t: tiers.count(t) for t in ("stable", "watch", "discuss", "excluded", "learning") if tiers.count(t)}
        lines.append(f"Last {len(trend)} days by tier: " + ", ".join(f"{k} {v}" for k, v in counts.items()) + ".")
        noted = [t for t in trend if t.get("annotation")]
        if noted:
            lines.append("Notes on days: " + "; ".join(f"{t['date']}: {t['annotation']}" for t in noted[-3:]) + ".")
    return " ".join(lines)


def template_note(summary: dict) -> str:
    """The deterministic floor. Plain, and always exactly right."""
    tier = summary.get("tier", "learning")
    if tier == "learning":
        left = summary.get("warmup_days_remaining", 0)
        return (
            f"Bellwether is still learning your baseline. {left} more day(s) of speech are needed before it can say anything about change."
            if left
            else "Bellwether has learned your baseline. From now on each day is compared with it."
        )
    if tier == "stable":
        streak = summary.get("stable_streak_days", 0)
        return f"This week your speech stayed {_TIER_PLAIN['stable']}. That is {streak} day(s) in a row."
    who = ", ".join(summary.get("contributors") or []) or "several measures"
    return (
        f"Since {summary.get('since')}, your speech has been {_TIER_PLAIN[tier]}. The measures behind this are {who}. "
        "This is not a diagnosis. Adding a note about sleep, travel or illness helps read it in context, and the report can be shared with your clinician."
    )


def sanitise(text: str) -> str:
    """Enforce the house style instead of asking for it.

    The system prompt tells the model to use no dashes as punctuation and
    no emoji. The model agrees and then does it anyway, which is the
    normal outcome of putting a formatting rule in a prompt: it is a
    preference expressed to a sampler, not a constraint on the output.

    A dash is not a cosmetic issue here. This note is read by someone who
    has just been told something about their own speech, and an em dash
    sets up an aside in a sentence that should be plain. So the rule is
    applied deterministically after the fact, where it cannot be ignored.

    Em and en dashes become commas when they are doing the work of a
    parenthetical and disappear when they are not, which leaves a sentence
    that still reads naturally rather than one with a gap in it.
    """
    out = text
    # A dash between two digits is a range, not an aside. Turning it into a
    # comma would change "3 to 5 days" into "3, 5 days", which means
    # something else. Caught by a test rather than by reading the output.
    out = re.sub(r"(?<=\d)\s*[\u2013\u2014]\s*(?=\d)", " to ", out)
    for dash in ("\u2014", "\u2013"):
        # Spaced: a parenthetical or a break. A comma carries the same pause.
        out = out.replace(f" {dash} ", ", ")
        # Unspaced between words: the same aside, written tight.
        out = out.replace(dash, ", ")
    # A double comma is the tell that two dashes bracketed one aside.
    while ", ," in out:
        out = out.replace(", ,", ",")
    out = out.replace(" ,", ",").replace(",,", ",")
    return " ".join(out.split()).strip()


def _bedrock_create_text(system: str, user: str, model: str) -> str:
    from anthropic import AnthropicBedrock  # lazy: tests inject a fake

    client = AnthropicBedrock(aws_region=os.environ.get("AWS_REGION", "us-east-1"))
    response = client.messages.create(
        model=model, max_tokens=400, system=system, messages=[{"role": "user", "content": user}]
    )
    if getattr(response, "stop_reason", None) == "refusal":
        raise RuntimeError("model declined")
    text = " ".join(b.text for b in response.content if getattr(b, "type", "") == "text").strip()
    if not text:
        raise RuntimeError("empty response")
    return text


def phrase_weekly_note(summary: dict, trend: list[dict], deps: dict | None = None) -> dict:
    """Phrase the week. ``deps`` may carry ``create_text(system, user,
    model)``, ``models`` and ``enabled`` for tests and for local runs."""
    deps = deps or {}
    facts = facts_text(summary, trend)
    fallback = {"text": template_note(summary), "source": "template", "facts_text": facts, "model": None, "attempts": []}

    enabled = deps.get("enabled", os.environ.get("BELLWETHER_BEDROCK") == "1")
    create = deps.get("create_text")
    if not enabled and create is None:
        return fallback
    create = create or _bedrock_create_text
    models = deps.get("models") or MODEL_LADDER
    prompt = f"Facts:\n{facts}\n\nWrite the weekly note now."
    attempts: list[dict] = []

    for model in models:
        try:
            text = sanitise(create(SYSTEM, prompt, model))
            # A rambling answer is the cheapest sign the note lost the plot;
            # it fails this rung, not the ladder.
            if len(text) > 600:
                attempts.append({"model": model, "ok": False, "reason": "response too long"})
                continue
            attempts.append({"model": model, "ok": True})
            return {"text": text, "source": "bedrock", "facts_text": facts, "model": model, "attempts": attempts}
        except Exception as err:  # noqa: BLE001
            attempts.append({"model": model, "ok": False, "reason": str(err)[:200]})

    return {**fallback, "attempts": attempts}

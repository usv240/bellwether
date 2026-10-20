"""What one person costs to run for a month, at AWS list prices, from measured usage.

    python scripts/cost.py

Every input is either an AWS list price or something measured on the
deployed stack, and each says which. The usage pattern is stated, and it
is generous: a hosted check-in every day, the dashboard opened every day
with the whole site downloaded as if nothing were cached, a full year of
history read on every request, and the AWS free tier ignored. Writes
docs/cost.json, which the evidence and the Devpost quote.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# AWS Price List API (pricing:GetProducts), us-east-1, read 2026-10-20.
PRICE = {
    "dynamodb_write_unit": 0.625 / 1e6,       # on-demand, per write request unit
    "dynamodb_read_unit": 0.125 / 1e6,        # on-demand, per read request unit
    "lambda_request": 0.20 / 1e6,             # x86, per request
    "lambda_gb_second": 0.0000166667,         # x86, first tier
    "bedrock_input_token": 3.30 / 1e6,        # Claude Sonnet 4.6, us. cross-region profile
    "bedrock_output_token": 16.50 / 1e6,
    "polly_neural_character": 16.0 / 1e6,     # the Check-in Host's voice
    "cloudfront_gb": 0.085,                   # United States, first 10 TB
    "cloudfront_request": 0.01 / 1e4,         # HTTPS, United States
}

# Measured on the deployed stack, 2026-10-20.
MEASURED = {
    "lambda_memory_gb": 0.5,                  # the function's configuration
    "lambda_avg_seconds": 0.945,              # CloudWatch REPORT lines, 14 days, 1,660 invocations; includes cold starts and Bedrock waits
    "note_input_tokens": 287,                 # one real weekly note on the deployed model
    "note_output_tokens": 39,
    "check_in_polly_characters": 672,         # tonight's eight host lines (418) and the coaching note read back (254)
    "new_polly_characters": 293,              # what is new on a night once the host's audio is kept: the dated opener (39) and the note (254)
    "prompt_bank_characters": 935,            # twelve questions, synthesised once and kept on the wearer's machine
    "dashboard_api_requests": 14,             # headless browser, one load of the dashboard
    "dashboard_cdn_requests": 14,
    "dashboard_cdn_bytes": 1_048_371,
    "day_bytes": 279,                         # the largest stored day on the live check-in profile
}

# The pattern, per person, per 30-day month.
USAGE = {
    "check_ins": 30,
    "posts_per_check_in": 2,                  # `mine` posts the conversation profile and the check-in profile
    "mcp_requests_per_check_in": 6,           # the host: initialize, initialized, start_check_in, coaching_note, and two list calls
    "dashboard_views": 30,
    "notes_phrased": 30,                      # once per change in the facts: a new day
    "history_days_read": 365,                 # every request reads a full year
}


def month() -> dict:
    b = MEASURED["day_bytes"]
    read_history = math.ceil(USAGE["history_days_read"] * b / 1024 / 4) * 0.5 + 0.5
    posts = USAGE["check_ins"] * USAGE["posts_per_check_in"]
    mcp = USAGE["check_ins"] * USAGE["mcp_requests_per_check_in"]
    dash = USAGE["dashboard_views"] * MEASURED["dashboard_api_requests"]
    requests = posts + mcp + dash

    dynamodb = posts * math.ceil(b / 1024) * PRICE["dynamodb_write_unit"] + (mcp + dash) * read_history * PRICE["dynamodb_read_unit"]
    lam = requests * (PRICE["lambda_request"] + MEASURED["lambda_memory_gb"] * MEASURED["lambda_avg_seconds"] * PRICE["lambda_gb_second"])
    bedrock = USAGE["notes_phrased"] * (MEASURED["note_input_tokens"] * PRICE["bedrock_input_token"]
                                        + MEASURED["note_output_tokens"] * PRICE["bedrock_output_token"])
    # The host keeps each line's audio (check_in_host.PollySpeaker.audio_for),
    # so a month after the first pays only for what is new each night.
    polly = USAGE["check_ins"] * MEASURED["new_polly_characters"] * PRICE["polly_neural_character"]
    polly_uncached = USAGE["check_ins"] * MEASURED["check_in_polly_characters"] * PRICE["polly_neural_character"]
    cdn = USAGE["dashboard_views"] * (MEASURED["dashboard_cdn_bytes"] / 1e9 * PRICE["cloudfront_gb"]
                                      + MEASURED["dashboard_cdn_requests"] * PRICE["cloudfront_request"])
    parts = {"dynamodb": dynamodb, "lambda": lam, "bedrock": bedrock, "polly": polly, "cloudfront": cdn}
    total = sum(parts.values())
    return {
        "per_person_per_month_usd": round(total, 4),
        "cents": round(100 * total, 1),
        "people_per_dollar_month": int(1 / total),
        "parts_usd": {k: round(v, 5) for k, v in parts.items()},
        "without_the_hosted_check_in_cents": round(100 * (total - polly), 1),
        "polly_before_the_audio_cache_usd": round(polly_uncached, 5),
        "usage": USAGE,
        "measured": MEASURED,
        "prices": "AWS Price List API, us-east-1, 2026-10-20; free tier ignored",
        "not_counted": "the Bee (49.99 dollars once, the wearer's) and the wearer's own computer, where the words are read and discarded",
    }


if __name__ == "__main__":
    m = month()
    (REPO / "docs/cost.json").write_text(json.dumps(m, indent=1) + "\n", encoding="utf-8")
    print(f"{m['cents']} cents per person per month ({m['people_per_dollar_month']} people per dollar)")
    for k, v in m["parts_usd"].items():
        print(f"  {k:10} ${v:.5f}")

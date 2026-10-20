"""The published running cost is recomputed, not remembered.

scripts/cost.py multiplies AWS list prices by usage measured on the live
stack and writes docs/cost.json. This fails if the file is stale against
the script, or if the evidence and the site quote a different figure.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def _cost():
    spec = importlib.util.spec_from_file_location("cost", REPO / "scripts" / "cost.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.month()


def test_the_committed_cost_is_what_the_script_computes():
    assert json.loads((REPO / "docs" / "cost.json").read_text(encoding="utf-8")) == json.loads(json.dumps(_cost()))


def test_the_evidence_and_the_site_quote_the_computed_cost():
    m = _cost()
    with_host, without = round(m["cents"]), round(m["without_the_hosted_check_in_cents"])
    evidence = (REPO / "docs" / "EVIDENCE.md").read_text(encoding="utf-8")
    assert f"About {with_host} cents a person a month" in evidence and f"{without} cents without it" in evidence
    page = (REPO / "apps" / "web" / "src" / "app" / "page.tsx").read_text(encoding="utf-8")
    # The page writes the cent sign as a JavaScript escape.
    cent = "\\u00a2"
    assert f'value: "{with_host}{cent}"' in page and f"{without}{cent} without" in page

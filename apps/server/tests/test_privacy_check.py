"""The privacy proof has to be a proof, not a reassuring panel.

Bellwether's premise is that it never holds what a person said. The site
now lets a visitor press a button that sends a day with a transcript full
of names attached and shows what survived. These tests make sure that
button tells the truth in both directions: that nothing survives today,
and that the check would notice if something did.

The second direction matters more. A check that always reports "absent"
proves nothing, so one test deliberately weakens the intake to keep a
text field and asserts the check catches it.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from bellwether_server import app as app_module
from bellwether_server.privacy_check import SENSITIVE, run_privacy_check


def test_the_day_is_accepted_through_the_real_route():
    r = run_privacy_check()
    assert r["response"]["status"] == 200
    assert r["response"]["body"]["stored"] == 1


def test_every_text_field_sent_is_dropped():
    r = run_privacy_check()
    assert set(r["dropped"]) == {"transcript", "speaker_name", "notes"}


def test_the_only_string_left_is_the_date():
    # The page's claim, measured on the row just written.
    assert run_privacy_check()["strings_kept"] == ["date"]


def test_none_of_the_sensitive_words_survive():
    r = run_privacy_check()
    found = [f["looked_for"] for f in r["findings"] if f["found"]]
    assert found == []
    assert r["any_found"] is False
    # And it looked for every one, not a convenient subset.
    assert {f["looked_for"] for f in r["findings"]} == set(SENSITIVE.values())


def test_the_nine_numbers_do_survive():
    # A privacy check that passes because nothing was stored at all would
    # be a broken intake, not a private one.
    r = run_privacy_check()
    for k in ("mattr", "filler_rate", "idea_density", "vocab_size_day"):
        assert isinstance(r["stored"][k], (int, float))


def test_it_would_notice_if_a_word_got_through(monkeypatch):
    # Weaken the intake to keep the transcript, as a careless change might,
    # and the check must report it. Without this test the four above could
    # all pass against a check that never looks.
    real = app_module.validate_day

    def leaky(row):
        kept = real(row)
        kept["transcript"] = row.get("transcript", "")
        return kept

    monkeypatch.setattr(app_module, "validate_day", leaky)
    r = run_privacy_check()
    assert r["any_found"] is True
    assert "transcript" not in r["dropped"]
    assert {f["looked_for"] for f in r["findings"] if f["found"]} >= {"Margaret", "donepezil"}


def test_it_is_a_sandbox_and_says_so():
    # A visitor pressing a button must not be able to write rows into the
    # deployed table, and the response has to carry that fact so the page
    # cannot imply otherwise.
    r = run_privacy_check()
    assert r["sandbox"] is True


def test_the_route_serves_it():
    client = TestClient(app_module.build_app(seed=False))
    res = client.post("/v1/privacy-check")
    assert res.status_code == 200
    assert res.json()["any_found"] is False

"""The house style, enforced rather than requested.

The system prompt tells the model to use no dashes as punctuation. The
model agrees and then uses them anyway, which is the ordinary outcome of
putting a formatting rule in a prompt: it is a preference expressed to a
sampler, not a constraint on the output. This is the constraint.

Found on the deployed dashboard, where the weekly note read "nine
features, em dash, including filler rate, em dash, that differ", in a
product whose whole register is plain sentences for someone who has just
been told something about their own speech.
"""

from bellwether_server.bedrock import sanitise


def test_a_bracketing_pair_becomes_one_comma_pair():
    text = "The system found nine features\u2014including filler rate\u2014that differ."
    assert sanitise(text) == (
        "The system found nine features, including filler rate, that differ."
    )


def test_a_spaced_dash_becomes_a_comma():
    assert sanitise("Your speech has been steady \u2014 nothing changed.") == (
        "Your speech has been steady, nothing changed."
    )


def test_an_en_dash_is_handled_too():
    assert "\u2013" not in sanitise("Steady \u2013 and quiet.")


def test_a_range_between_numbers_keeps_its_meaning():
    # The failure this test exists for: a comma here would turn a range
    # into a list and change what the sentence says.
    assert sanitise("A range of 3\u20135 days.") == "A range of 3 to 5 days."
    assert sanitise("Between 10\u201320 percent.") == "Between 10 to 20 percent."


def test_clean_text_is_returned_unchanged():
    clean = "No dashes here at all."
    assert sanitise(clean) == clean


def test_whitespace_is_normalised_without_eating_words():
    assert sanitise("Two   spaces  collapse.") == "Two spaces collapse."


def test_no_double_comma_survives():
    assert ",," not in sanitise("A\u2014B\u2014C")
    assert ", ," not in sanitise("A\u2014B\u2014C")

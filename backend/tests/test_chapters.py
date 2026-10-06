"""Creator chapters parsed from video descriptions (docs/decisions.md §6)."""
import pytest

from app.services import ai
from app.services.youtube import parse_chapters


@pytest.mark.parametrize("description, expected", [
    ("Intro text\n00:00:00 Intro\n00:02:41 Protocols\n01:37:03 Ads\nfollow me",
     [(0, "Intro"), (161, "Protocols"), (5823, "Ads")]),
    ("(00:00) LIVE setup\n(01:30) What's new\n(37:24) Best", [(0, "LIVE setup"), (90, "What's new"), (2244, "Best")]),
    ("0:00 - Intro\n1:30 - Meeting the guys\n18:10 - Day in the life",
     [(0, "Intro"), (90, "Meeting the guys"), (1090, "Day in the life")]),
])
def test_parses_the_formats_seen_in_practice(description, expected):
    assert parse_chapters(description) == expected


@pytest.mark.parametrize("description", [
    "0:30 a\n1:00 b\n2:00 c",  # does not start at 0:00
    "0:00 a\n1:00 b",  # fewer than three
    "0:00 a\n5:00 b\n2:00 c",  # not ascending
    "no chapters here",
    None,
])
def test_follows_youtubes_rules_for_what_counts_as_chapters(description):
    assert parse_chapters(description) == []


def test_chapters_are_given_to_gemini_as_timestamp_anchors():
    prompt = ai._chapters_prompt([(0, "Intro"), (161, "Protocols"), (7679, "Metabolism")])
    assert "[0:00:00] Intro" in prompt and "[2:07:59] Metabolism" in prompt
    short = ai._chapters_prompt([(0, "Intro"), (90, "New"), (2244, "Best")])
    assert "[01:30] New" in short

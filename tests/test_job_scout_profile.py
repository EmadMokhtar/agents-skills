"""Tests for the job-scout profile reader: a small YAML subset, read with the standard library."""

from __future__ import annotations

import pytest

from job_scout import load

profile_yaml = load("profile_yaml")


def test_reads_nested_mappings_lists_and_scalars():
    text = """\
# A comment line
role:
  target_titles:
    - Staff Software Engineer
    - "Principal Engineer"
  report_threshold: 7
  ratio: 0.5
location:
  relocation: false
  home_base: 'Porto, Portugal'   # trailing comment
  time_zones:
  notes: Remote — Europe
"""
    assert profile_yaml.loads(text) == {
        "role": {
            "target_titles": ["Staff Software Engineer", "Principal Engineer"],
            "report_threshold": 7,
            "ratio": 0.5,
        },
        "location": {
            "relocation": False,
            "home_base": "Porto, Portugal",
            "time_zones": None,
            "notes": "Remote — Europe",
        },
    }


def test_empty_list_and_null_values():
    assert profile_yaml.loads("a: []\nb: null\nc: ~\nd: true\n") == {
        "a": [],
        "b": None,
        "c": None,
        "d": True,
    }


def test_hash_inside_quotes_is_kept():
    assert profile_yaml.loads('tag: "C# and F#"  # langs\n') == {"tag": "C# and F#"}


def test_list_item_with_colon_is_a_plain_string():
    assert profile_yaml.loads("x:\n  - 'Tech Lead: judge on the body'\n") == {
        "x": ["Tech Lead: judge on the body"]
    }


@pytest.mark.parametrize(
    "text",
    [
        "a: [x, y]\n",
        "a: {b: 1}\n",
        "a: |\n  text\n",
        "a: &anchor 1\n",
        "a:\n\t- x\n",
        "  a: 1\n",
        "a: 1\na: 2\n",
        "just text\n",
    ],
)
def test_unsupported_syntax_is_an_error_with_a_line_number(text):
    with pytest.raises(profile_yaml.ProfileError, match=r"line \d+"):
        profile_yaml.loads(text)


def test_get_follows_a_dotted_path():
    data = {"role": {"lower_title_exception": {"allowed_at": ["Globex"]}}}
    assert profile_yaml.get(data, "role.lower_title_exception.allowed_at") == ["Globex"]
    assert profile_yaml.get(data, "role.missing", default=[]) == []
    assert profile_yaml.get(data, "role.lower_title_exception.allowed_at.x", default=0) == 0

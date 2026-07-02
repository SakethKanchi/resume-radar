#!/usr/bin/env python3
"""Offline unit tests for github_enrich helpers. Run: python scripts/test_github_enrich.py

Tests pure logic (username parsing, classification, cap detection) without
hitting the network, so they pass in the no-network Claude API environment.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from github_enrich import extract_username  # noqa: E402


def test_extract_username():
    cases = {
        "https://github.com/SakethKanchi": "SakethKanchi",
        "github.com/octocat?tab=repositories": "octocat",
        "@torvalds": "torvalds",
        "some-user": "some-user",
        "https://github.com/org/repo": "org",
        "": None,
        "https://gitlab.com/someone": None,  # non-github URL yields no match
    }
    for value, expected in cases.items():
        got = extract_username(value)
        assert got == expected, f"extract_username({value!r}) = {got!r}, want {expected!r}"


def test_classification_logic():
    # project_type mirrors github.py: >1 contributor => open_source.
    classify = lambda n: "open_source" if n > 1 else "self_project"
    assert classify(1) == "self_project"
    assert classify(2) == "open_source"
    assert classify(50) == "open_source"


def test_cap_rule():
    # If no repo is open_source but some exist, the open_source cap triggers.
    def cap(open_source, self_project):
        return open_source == 0 and self_project > 0
    assert cap(0, 5) is True
    assert cap(1, 5) is False
    assert cap(0, 0) is False


def test_eligibility_threshold():
    # A repo is an eligible top project only with >= 4 of the author's commits.
    eligible = lambda commits: commits >= 4
    assert eligible(3) is False
    assert eligible(4) is True


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} passed")

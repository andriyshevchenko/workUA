"""Tests for utils helpers."""

from utils import separator_line


def test_separator_line_defaults():
    line = separator_line()
    assert line == "=" * 60


def test_separator_line_custom():
    line = separator_line(width=4, char="-")
    assert line == "----"

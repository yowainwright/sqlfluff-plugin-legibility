"""Test plugin integration."""

from sqlfluff.core import FluffConfig, Linter


def test_rule_can_be_reported_as_a_warning() -> None:
    core = {
        "dialect": "ansi",
        "rules": "Legibility_L001",
        "warnings": "Legibility_L001",
    }
    config = FluffConfig(configs={"core": core})
    linted = Linter(config=config).lint_string("-- Explain this query.\nSELECT 1;\n")

    assert len(linted.violations) == 1
    assert linted.violations[0].rule_code() == "Legibility_L001"
    assert linted.violations[0].warning is True
    assert linted.is_clean()


def test_stacked_comments_are_errors_by_default() -> None:
    core = {
        "dialect": "ansi",
        "rules": "Legibility_L002",
    }
    config = FluffConfig(configs={"core": core})
    sql = "-- First explanation.\n-- Second explanation.\nSELECT 1;\n"
    linted = Linter(config=config).lint_string(sql)

    assert len(linted.violations) == 1
    assert linted.violations[0].rule_code() == "Legibility_L002"
    assert linted.violations[0].warning is False
    assert not linted.is_clean()


def test_stacked_comments_can_be_warnings() -> None:
    core = {
        "dialect": "ansi",
        "rules": "Legibility_L002",
        "warnings": "Legibility_L002",
    }
    config = FluffConfig(configs={"core": core})
    sql = "-- First explanation.\n-- Second explanation.\nSELECT 1;\n"
    linted = Linter(config=config).lint_string(sql)

    assert len(linted.violations) == 1
    assert linted.violations[0].warning is True
    assert linted.is_clean()


def test_each_comment_after_the_first_reports() -> None:
    core = {
        "dialect": "ansi",
        "rules": "Legibility_L002",
    }
    config = FluffConfig(configs={"core": core})
    sql = "-- First.\n-- Second.\n-- Third.\nSELECT 1;\n"
    linted = Linter(config=config).lint_string(sql)

    assert len(linted.violations) == 2
    assert [violation.line_no for violation in linted.violations] == [2, 3]

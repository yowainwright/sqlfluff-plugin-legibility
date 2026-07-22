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

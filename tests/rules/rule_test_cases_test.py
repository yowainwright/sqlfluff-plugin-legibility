"""Run SQLFluff rule fixtures."""

from pathlib import Path

import pytest
from sqlfluff.utils.testing.rules import RuleTestCase, load_test_cases

TEST_CASES = Path(__file__).parent / "test_cases" / "*.yml"
IDS, CASES = load_test_cases(test_cases_path=str(TEST_CASES))


@pytest.mark.parametrize("test_case", CASES, ids=IDS)
def test_rule_case(test_case: RuleTestCase) -> None:
    test_case.evaluate()

from typing import TypedDict


class TestFailure(TypedDict):
    name: str
    message: str


class FailureExplanation(TypedDict):
    name: str
    explained: bool
    reason: str | None


def upload_failures(test_failures: list[TestFailure]):
    pass


def explain_failures(test_failures: list[TestFailure]) -> list[FailureExplanation]:
    explanations = []
    for test_failure in test_failures:
        explanations.append(
            {"name": test_failure["name"], "explained": False, "reason": None}
        )
    return explanations

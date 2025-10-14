from typing import TypedDict
import sqlite3
import logging


class TestFailure(TypedDict):
    name: str
    message: str


class FailureExplanation(TypedDict):
    name: str
    explained: bool
    reason: str | None


class FailureUpload(TypedDict):
    source_type: str
    base_commit_sha: str
    source_id: str
    failures: list[TestFailure]


def setup_db(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    tables = connection.execute("SELECT name from sqlite_master").fetchall()
    if "failures" not in tables:
        logging.info("Did not find failures table, creating.")
        connection.execute(
            "CREATE TABLE failures(source_type, base_commit_sha, source_id, test_file, failure_message)"
        )
        connection.commit()
    return connection


def upload_failures(failure_info: FailureUpload, db_connection: sqlite3.Connection):
    failures = []
    for failure in failure_info["failures"]:
        failures.append(
            (
                failure_info["source_type"],
                failure_info["base_commit_sha"],
                failure_info["source_id"],
                failure["name"],
                failure["message"],
            )
        )
    db_connection.executemany("INSERT INTO failures VALUES(?, ?, ?, ?, ?)", failures)
    db_connection.commit()


def explain_failures(test_failures: list[TestFailure]) -> list[FailureExplanation]:
    explanations = []
    for test_failure in test_failures:
        explanations.append(
            {"name": test_failure["name"], "explained": False, "reason": None}
        )
    return explanations

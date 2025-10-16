from typing import TypedDict
import time
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
    platform: str


_CREATE_TABLE_CMD = "CREATE TABLE failures(source_type, base_commit_sha, source_id, test_file, failure_message, platform)"


def _create_failures_table(connection: sqlite3.Connection):
    logging.info("Did not find failures table, creating.")
    connection.execute(_CREATE_TABLE_CMD)
    connection.commit()


def setup_db(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    tables = connection.execute("SELECT name from sqlite_master").fetchall()
    if ("failures",) not in tables:
        _create_failures_table(connection)
        return connection

    table_schema = connection.execute(
        "SELECT sql FROM sqlite_master WHERE name=?", ("failures",)
    ).fetchone()
    if table_schema == (_CREATE_TABLE_CMD,):
        return connection

    # The schema of the table does not match what we were expecting. Keep the
    # current table around just in case by renaming it and recreate the
    # failures table using the expected schema.
    new_table_name = f"failures_old_{int(time.time())}"
    connection.execute(f"ALTER TABLE failures RENAME TO {new_table_name}")
    connection.commit()

    _create_failures_table(connection)
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
                failure_info["platform"],
            )
        )
    db_connection.executemany("INSERT INTO failures VALUES(?, ?, ?, ?, ?, ?)", failures)
    db_connection.commit()


def explain_failures(test_failures: list[TestFailure]) -> list[FailureExplanation]:
    explanations = []
    for test_failure in test_failures:
        explanations.append(
            {"name": test_failure["name"], "explained": False, "reason": None}
        )
    return explanations

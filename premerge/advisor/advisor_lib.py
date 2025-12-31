from typing import TypedDict
import time
import sqlite3
import logging
import re

import git_utils


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


class TestExplanationRequest(TypedDict):
    base_commit_sha: str
    failures: list[TestFailure]
    platform: str


class FlakyTestInfo(TypedDict):
    test_name: str
    first_failed_index: str
    last_failed_index: str
    failure_range_commit_count: int
    fail_count: int


_TABLE_SCHEMAS = {
    "failures": "CREATE TABLE failures(source_type, base_commit_sha, commit_index, source_id, test_file, failure_message, platform)",
    "commits": "CREATE TABLE commits(commit_sha, commit_index)",
}

EXPLAINED_HEAD_MAX_COMMIT_INDEX_DIFFERENCE = 5
EXPLAINED_FLAKY_MIN_COMMIT_RANGE = 200


def _create_table(table_name: str, connection: sqlite3.Connection):
    logging.info("Did not find failures table, creating.")
    connection.execute(_TABLE_SCHEMAS[table_name])
    connection.commit()


def setup_db(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    for table_name in _TABLE_SCHEMAS:
        tables = connection.execute("SELECT name from sqlite_master").fetchall()
        if (table_name,) not in tables:
            _create_table(table_name, connection)
            continue

        table_schema = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name=?", (table_name,)
        ).fetchone()
        if table_schema == (_TABLE_SCHEMAS[table_name],):
            continue

        # The schema of the table does not match what we were expecting. Keep the
        # current table around just in case by renaming it and recreate the
        # failures table using the expected schema.
        new_table_name = f"{table_name}_old_{int(time.time())}"
        connection.execute(f"ALTER TABLE failures RENAME TO {new_table_name}")
        connection.commit()

        _create_table(table_name, connection)
    return connection


def _canonicalize_failures(failures: list[TestFailure]):
    for failure in failures:
        failure["message"] = re.sub(
            r"\/home\/.*\/llvm-project", "llvm-project", failure["message"]
        )


def upload_failures(
    failure_info: FailureUpload, db_connection: sqlite3.Connection, repository_path: str
):
    _canonicalize_failures(failure_info["failures"])
    failures = []
    for failure in failure_info["failures"]:
        failures.append(
            (
                failure_info["source_type"],
                failure_info["base_commit_sha"],
                git_utils.get_commit_index(
                    failure_info["base_commit_sha"], repository_path, db_connection
                ),
                failure_info["source_id"],
                failure["name"],
                failure["message"],
                failure_info["platform"],
            )
        )
    db_connection.executemany(
        "INSERT INTO failures VALUES(?, ?, ?, ?, ?, ?, ?)", failures
    )
    db_connection.commit()


def _try_explain_failing_at_head(
    db_connection: sqlite3.Connection,
    test_failure: TestFailure,
    base_commit_sha: str,
    base_commit_index: int | None,
    platform: str,
) -> FailureExplanation | None:
    query = (
        "SELECT failure_message FROM failures "
        "WHERE source_type='postcommit' AND platform=? AND test_file=?"
    )
    query_params = (
        platform,
        test_failure["name"],
    )
    if base_commit_index:
        min_commit_index = (
            base_commit_index - EXPLAINED_HEAD_MAX_COMMIT_INDEX_DIFFERENCE
        )
        query += (
            f" AND commit_index > {min_commit_index} "
            f"AND commit_index <= {base_commit_index}"
        )
    else:
        query += "AND base_commit_sha=?"
        query_params += (base_commit_sha,)
    test_name_matches = db_connection.execute(
        query,
        query_params,
    ).fetchall()
    for test_name_match in test_name_matches:
        failure_message = test_name_match[0]
        if failure_message == test_failure["message"]:
            return {
                "name": test_failure["name"],
                "explained": True,
                "reason": "This test is already failing at the base commit.",
            }
    return None


def _try_explain_flaky_failure(
    db_connection: sqlite3.Connection,
    test_failure: TestFailure,
    platform: str,
) -> FailureExplanation | None:
    """See if a failure is flaky at head.

    This function looks at a test failure and tries to see if the failure is
    a known flake at head. It does this heuristically, by seeing if there have
    been at least two failures across more than 200 commits. This has the
    advantage of being a simple heuristic and performant. We do not
    explicitly handle the case where a test has been failing continiously
    for this amount of time as this is an OOM more range than any non-flaky
    tests have stayed in tree.

    Args:
      db_connection: The database connection.
      test_failure: The test failure to try and explain.
      platform: The platform the test failed on.

    Returns:
      Either None, if the test could not be explained as flaky, or a
      FailureExplanation object explaining the test failure.
    """
    test_name_matches = db_connection.execute(
        "SELECT failure_message, commit_index FROM failures WHERE source_type='postcommit' AND platform=? AND test_file=?",
        (
            platform,
            test_failure["name"],
        ),
    ).fetchall()
    commit_indices = []
    for failure_message, commit_index in test_name_matches:
        if failure_message == test_failure["message"]:
            commit_indices.append(commit_index)
    if len(commit_indices) == 0:
        return None
    commit_range = max(commit_indices) - min(commit_indices)
    if commit_range > EXPLAINED_FLAKY_MIN_COMMIT_RANGE:
        return {
            "name": test_failure["name"],
            "explained": True,
            "reason": "This test is flaky in main.",
        }
    return None


def explain_failures(
    explanation_request: TestExplanationRequest,
    repository_path: str,
    db_connection: sqlite3.Connection,
) -> list[FailureExplanation]:
    _canonicalize_failures(explanation_request["failures"])
    explanations = []
    for test_failure in explanation_request["failures"]:
        commit_index = git_utils.get_commit_index(
            explanation_request["base_commit_sha"], repository_path, db_connection
        )
        # We want to try and explain flaky failures first. Otherwise we might
        # explain a flaky failure as a failure at head if there is a recent
        # failure in the last couple of commits.
        explained_as_flaky = _try_explain_flaky_failure(
            db_connection,
            test_failure,
            explanation_request["platform"],
        )
        if explained_as_flaky:
            explanations.append(explained_as_flaky)
            continue
        explained_at_head = _try_explain_failing_at_head(
            db_connection,
            test_failure,
            explanation_request["base_commit_sha"],
            commit_index,
            explanation_request["platform"],
        )
        if explained_at_head:
            explanations.append(explained_at_head)
            continue
        explanations.append(
            {"name": test_failure["name"], "explained": False, "reason": None}
        )
    return explanations


def get_flaky_tests(
    db_connection: sqlite3.Connection,
) -> list[FlakyTestInfo]:
    possibly_flaky_tests = db_connection.execute(
        "SELECT test_file, commit_index FROM failures where test_file "
        "IN (SELECT test_file FROM failures GROUP BY test_file "
        "HAVING COUNT(test_file) > 10)"
    ).fetchall()
    flaky_test_info: dict[str, FlakyTestInfo] = {}
    for test_name, commit_index in possibly_flaky_tests:
        if test_name not in flaky_test_info:
            flaky_test_info[test_name] = {
                "test_name": test_name,
                "first_failed_index": commit_index,
                "last_failed_index": commit_index,
                "failure_range_commit_count": 0,
                "fail_count": 1,
            }
            continue

        flaky_test_info[test_name]["first_failed_index"] = min(
            flaky_test_info[test_name]["first_failed_index"], commit_index
        )
        flaky_test_info[test_name]["last_failed_index"] = max(
            flaky_test_info[test_name]["last_failed_index"], commit_index
        )
        flaky_test_info[test_name]["failure_range_commit_count"] = (
            flaky_test_info[test_name]["last_failed_index"]
            - flaky_test_info[test_name]["first_failed_index"]
        )
        flaky_test_info[test_name]["fail_count"] += 1

    output_list: list[FlakyTestInfo] = []
    for test_name in flaky_test_info:
        if (
            flaky_test_info[test_name]["failure_range_commit_count"]
            == flaky_test_info[test_name]["fail_count"] - 1
        ):
            continue

        output_list.append(flaky_test_info[test_name])

    return output_list

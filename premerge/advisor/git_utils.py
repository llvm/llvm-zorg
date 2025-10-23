import sqlite3
import os
import subprocess
import logging

REPOSITORY_URL = "https://github.com/llvm/llvm-project"
FIRST_COMMIT_SHA = "f8f7f1b67c8ee5d81847955dc36fab86a6d129ad"


def _clone_repository_if_not_present(
    repository_path: str, repository_url=REPOSITORY_URL
):
    if not os.path.exists(os.path.join(repository_path, ".git")):
        logging.info("Cloning git repository.")
        subprocess.run(
            ["git", "clone", repository_url, os.path.basename(repository_path)],
            cwd=os.path.dirname(repository_path),
            check=True,
        )
        logging.info("Finished cloning git repository.")


def _get_and_add_commit_index(
    commit_sha: str,
    repository_path: str,
    db_connection: sqlite3.Connection,
    first_commit_sha,
) -> int:
    # Ensure the repository is up to date.
    subprocess.run(["git", "fetch"], cwd=repository_path, check=True)
    # Get the highest indexed commit so we can ensure we only add new
    # commits.
    latest_commit_info = db_connection.execute(
        "SELECT * FROM commits ORDER BY commit_index DESC"
    ).fetchone()
    commits_to_add = []
    if latest_commit_info:
        latest_sha, latest_index = latest_commit_info
    else:
        latest_sha = first_commit_sha
        latest_index = 1
    log_output = subprocess.run(
        ["git", "log", "--oneline", "--no-abbrev", f"{latest_sha}..{commit_sha}"],
        cwd=repository_path,
        stdout=subprocess.PIPE,
        check=True,
    )
    log_lines = log_output.stdout.decode("utf-8").split("\n")[:-1]
    if len(log_lines) == 0:
        raise ValueError(
            "Did not find any commits. The commit likely happened before the commit with index 1."
        )
    commit_index = latest_index + len(log_lines) + 1
    for log_line in log_lines:
        line_commit_sha = log_line.split(" ")[0]
        commit_index -= 1
        commits_to_add.append((line_commit_sha, commit_index))
    db_connection.executemany("INSERT INTO commits VALUES(?, ?)", commits_to_add)
    if not latest_commit_info:
        commits_to_add.append((first_commit_sha, 1))
    return commits_to_add[0][1]


def get_commit_index(
    commit_sha: str,
    repository_path: str,
    db_connection: sqlite3.Connection,
    first_commit_sha=FIRST_COMMIT_SHA,
) -> int:
    _clone_repository_if_not_present(repository_path)
    # Check to see if we already have the commit in the DB.
    commit_matches = db_connection.execute(
        "SELECT * FROM commits WHERE commit_sha=?", (commit_sha,)
    ).fetchall()
    if len(commit_matches) > 1:
        raise ValueError("Expected only one entry per commit SHA")
    elif len(commit_matches) == 1:
        return commit_matches[0][1]
    # We have not seen this commit before. Count the index and then add it to
    # the DB.
    return _get_and_add_commit_index(
        commit_sha, repository_path, db_connection, first_commit_sha
    )

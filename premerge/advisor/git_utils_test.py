import unittest
import tempfile
import sqlite3
import subprocess
import os

import advisor_lib
import git_utils


class GitUtilsTest(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile()
        self.db_connection = advisor_lib.setup_db(self.db_file.name)
        self.repository_path = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.db_file.close()
        self.repository_path.cleanup()

    def setup_repository(self, commit_count: int) -> list[str]:
        subprocess.run(["git", "init"], cwd=self.repository_path.name, check=True)
        for commit_index in range(commit_count):
            with open(
                os.path.join(self.repository_path.name, str(commit_index)), "w"
            ) as commit_file:
                commit_file.write("test")
            subprocess.run(
                ["git", "add", "--all"], cwd=self.repository_path.name, check=True
            )
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name='test'",
                    "-c",
                    "user.email='test@example.com",
                    "commit",
                    "-m",
                    "message",
                ],
                cwd=self.repository_path.name,
                check=True,
            )
        log_process = subprocess.run(
            ["git", "log", "--oneline", "--no-abbrev"],
            cwd=self.repository_path.name,
            stdout=subprocess.PIPE,
            check=True,
        )
        commit_shas = []
        for log_line in log_process.stdout.decode("utf-8").split("\n")[:-1]:
            commit_shas.append(log_line.split(" ")[0])
        commit_shas.reverse()
        return commit_shas

    def test_clone_repository(self):
        self.setup_repository(5)
        utils_repo_folder = tempfile.TemporaryDirectory()
        utils_repo_path = os.path.join(utils_repo_folder.name, "repo")
        git_utils.clone_repository_if_not_present(
            utils_repo_path, self.repository_path.name
        )
        log_process = subprocess.run(
            ["git", "log", "--oneline", "--no-abbrev", "--max-count=5"],
            cwd=utils_repo_path,
            stdout=subprocess.PIPE,
            check=True,
        )
        self.assertEqual(len(log_process.stdout.decode("utf-8").split("\n")) - 1, 5)

    def test_get_index_from_db(self):
        self.setup_repository(1)
        self.db_connection.execute(
            "INSERT INTO commits VALUES(?, ?)",
            ("f3939dc5093826c05f2a78ce1b0af769cd48fdab", 5),
        )
        self.assertEqual(
            git_utils.get_commit_index(
                "f3939dc5093826c05f2a78ce1b0af769cd48fdab",
                self.repository_path.name,
                self.db_connection,
            ),
            5,
        )

    def test_get_first_commit_from_git(self):
        commit_shas = self.setup_repository(2)
        self.assertEqual(
            git_utils.get_commit_index(
                commit_shas[1],
                self.repository_path.name,
                self.db_connection,
                commit_shas[0],
            ),
            2,
        )

    def test_get_index_from_git(self):
        commit_shas = self.setup_repository(3)
        self.db_connection.execute(
            "INSERT INTO commits VALUES(?, ?)", (commit_shas[1], 3)
        )
        self.assertEqual(
            git_utils.get_commit_index(
                commit_shas[2], self.repository_path.name, self.db_connection
            ),
            4,
        )

    def test_get_index_from_git_multiple_commits(self):
        commit_shas = self.setup_repository(4)
        self.db_connection.execute(
            "INSERT INTO commits VALUES(?, ?)", (commit_shas[1], 3)
        )
        self.assertEqual(
            git_utils.get_commit_index(
                commit_shas[3], self.repository_path.name, self.db_connection
            ),
            5,
        )
        self.assertEqual(
            git_utils.get_commit_index(
                commit_shas[2], self.repository_path.name, self.db_connection
            ),
            4,
        )

    def test_get_index_error_invalid_sha(self):
        commit_shas = self.setup_repository(3)
        self.assertIsNone(
            git_utils.get_commit_index(
                commit_shas[0],
                self.repository_path.name,
                self.db_connection,
                commit_shas[1],
            )
        )

    def test_get_index_error_before_first_commit(self):
        commit_shas = self.setup_repository(3)
        self.assertIsNone(
            git_utils.get_commit_index(
                "bad_sha", self.repository_path.name, self.db_connection, commit_shas[0]
            )
        )

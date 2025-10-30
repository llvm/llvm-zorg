import unittest
import tempfile
import sqlite3
import os

import advisor_lib


class AdvisorLibDbSetupTest(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile()

    def tearDown(self):
        self.db_file.close()

    def test_create_tables(self):
        db_connection = advisor_lib.setup_db(self.db_file.name)
        db_connection.close()
        connection = sqlite3.connect(self.db_file.name)
        tables = connection.execute("SELECT name from sqlite_master").fetchall()
        self.assertListEqual(tables, [("failures",), ("commits",)])
        table_schema = connection.execute("SELECT sql FROM sqlite_master").fetchall()
        self.assertListEqual(
            table_schema,
            [
                (advisor_lib._TABLE_SCHEMAS["failures"],),
                (advisor_lib._TABLE_SCHEMAS["commits"],),
            ],
        )
        connection.close()

    def test_create_one_table(self):
        connection_setup = sqlite3.connect(self.db_file.name)
        connection_setup.execute(advisor_lib._TABLE_SCHEMAS["failures"])
        connection_setup.close()

        connection = advisor_lib.setup_db(self.db_file.name)
        tables = connection.execute("SELECT name from sqlite_master").fetchall()
        self.assertListEqual(tables, [("failures",), ("commits",)])
        table_schema = connection.execute("SELECT sql FROM sqlite_master").fetchall()
        self.assertListEqual(
            table_schema,
            [
                (advisor_lib._TABLE_SCHEMAS["failures"],),
                (advisor_lib._TABLE_SCHEMAS["commits"],),
            ],
        )
        connection.close()

    def test_update_schema(self):
        connection_setup = sqlite3.connect(self.db_file.name)
        connection_setup.execute("CREATE TABLE failures(dummy_field)")
        connection_setup.close()

        db_connection = advisor_lib.setup_db(self.db_file.name)
        db_connection.close()

        connection = sqlite3.connect(self.db_file.name)
        tables = connection.execute("SELECT name from sqlite_master").fetchall()
        found_failures_table = False
        found_old_failures_table = False
        for table_name in [table_tuple[0] for table_tuple in tables]:
            if table_name == "failures":
                found_failures_table = True
                continue
            elif table_name.startswith("failures_old_"):
                found_old_failures_table = True
                continue
        self.assertTrue(found_failures_table)
        self.assertTrue(found_old_failures_table)
        table_schema = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name=?", ("failures",)
        ).fetchone()
        self.assertEqual(table_schema, (advisor_lib._TABLE_SCHEMAS["failures"],))
        connection.close()


class AdvisorLibTest(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile()
        self.db_connection = advisor_lib.setup_db(self.db_file.name)
        # Create the commit indices for the commits that we will use so that
        # we can avoid cloning a git repository to attempt to compute them.
        self.db_connection.executemany(
            "INSERT INTO commits VALUES(?, ?)",
            [
                ("8d29a3bb6f3d92d65bf5811b53bf42bf63685359", 1),
                ("6b7064686b706f7064656d6f6e68756e74657273", 2),
            ],
        )
        self.repository_path_dir = tempfile.TemporaryDirectory()
        self.repository_path = self.repository_path_dir.name
        os.mkdir(os.path.join(self.repository_path_dir.name, ".git"))

    def tearDown(self):
        self.db_connection.close()
        self.db_file.close()
        self.repository_path_dir.cleanup()

    def test_upload_failures(self):
        failure_info = {
            "source_type": "postcommit",
            "base_commit_sha": "8d29a3bb6f3d92d65bf5811b53bf42bf63685359",
            "source_id": "10000",
            "failures": [
                {"name": "a.ll", "message": "failed in way 1"},
                {"name": "b.ll", "message": "failed in way 2"},
            ],
            "platform": "linux-x86_64",
        }
        advisor_lib.upload_failures(
            failure_info, self.db_connection, self.repository_path
        )
        failures = self.db_connection.execute("SELECT * from failures").fetchall()
        self.assertListEqual(
            failures,
            [
                (
                    "postcommit",
                    "8d29a3bb6f3d92d65bf5811b53bf42bf63685359",
                    1,
                    "10000",
                    "a.ll",
                    "failed in way 1",
                    "linux-x86_64",
                ),
                (
                    "postcommit",
                    "8d29a3bb6f3d92d65bf5811b53bf42bf63685359",
                    1,
                    "10000",
                    "b.ll",
                    "failed in way 2",
                    "linux-x86_64",
                ),
            ],
        )

    def test_explain_failures(self):
        explanation_request = {
            "failures": [{"name": "a.ll", "message": "failed"}],
            "base_commit_sha": "8d29a3bb6f3d92d65bf5811b53bf42bf63685359",
            "platform": "linux-x86_64",
        }
        self.assertListEqual(
            advisor_lib.explain_failures(
                explanation_request,
                self.db_connection,
            ),
            [{"name": "a.ll", "explained": False, "reason": None}],
        )

    def _get_explained_failures(
        self,
        failure_name="a.ll",
        failure_message="failed in way 1",
        base_commit_sha="8d29a3bb6f3d92d65bf5811b53bf42bf63685359",
        platform="linux-x86_64",
        prev_failure_source_type="postcommit",
        prev_failure_base_commit_sha="8d29a3bb6f3d92d65bf5811b53bf42bf63685359",
        prev_failure_failure_name="a.ll",
        prev_failure_failure_message="failed in way 1",
        prev_failure_platform="linux-x86_64",
    ) -> list[advisor_lib.FailureExplanation]:
        """Constructs explanations.

        By default, an explanation will be given as all the information will
        match. Different parameters can be passed to construct negative tests.
        """
        failure_info = {
            "source_type": prev_failure_source_type,
            "base_commit_sha": prev_failure_base_commit_sha,
            "source_id": "10000",
            "failures": [
                {
                    "name": prev_failure_failure_name,
                    "message": prev_failure_failure_message,
                },
            ],
            "platform": prev_failure_platform,
        }
        advisor_lib.upload_failures(
            failure_info, self.db_connection, self.repository_path
        )
        explanation_request = {
            "failures": [{"name": failure_name, "message": failure_message}],
            "base_commit_sha": base_commit_sha,
            "platform": platform,
        }
        return advisor_lib.explain_failures(explanation_request, self.db_connection)

    # Test that we can explain away a failure at head, assuming all of the
    # appropriate fields match.
    def test_explain_failures_at_head(self):
        self.assertListEqual(
            self._get_explained_failures(),
            [
                {
                    "name": "a.ll",
                    "explained": True,
                    "reason": "This test is already failing at the base commit.",
                }
            ],
        )

    # Test that we do not explain away a failure at head if the base commit
    # SHA is different.
    def test_no_explain_different_base_commit(self):
        self.assertListEqual(
            self._get_explained_failures(
                prev_failure_base_commit_sha="6b7064686b706f7064656d6f6e68756e74657273"
            ),
            [
                {
                    "name": "a.ll",
                    "explained": False,
                    "reason": None,
                }
            ],
        )

    # Test that we do not explain away a failure at head if the only matching
    # failure information comes from a PR.
    def test_no_explain_different_source_type(self):
        self.assertListEqual(
            self._get_explained_failures(prev_failure_source_type="pull_request"),
            [
                {
                    "name": "a.ll",
                    "explained": False,
                    "reason": None,
                }
            ],
        )

    # Test that we do not explain away a failure at head if the only matching
    # failure information comes from a different platform.
    def test_no_explain_different_platform(self):
        self.assertListEqual(
            self._get_explained_failures(prev_failure_platform="linux-arm64"),
            [
                {
                    "name": "a.ll",
                    "explained": False,
                    "reason": None,
                }
            ],
        )

    # Test that we do not explain away a failure at head if the failure
    # message for the only matching failure information differs.
    def test_no_explain_different_message(self):
        self.assertListEqual(
            self._get_explained_failures(failure_message="failed in way 2"),
            [
                {
                    "name": "a.ll",
                    "explained": False,
                    "reason": None,
                }
            ],
        )

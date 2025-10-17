import unittest
import tempfile
import sqlite3

import advisor_lib


class AdvisorLibDbSetupTest(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile()

    def tearDown(self):
        self.db_file.close()

    def test_create_table(self):
        db_connection = advisor_lib.setup_db(self.db_file.name)
        db_connection.close()
        connection = sqlite3.connect(self.db_file.name)
        tables = connection.execute("SELECT name from sqlite_master").fetchall()
        self.assertListEqual(tables, [("failures",)])
        table_schema = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name=?", ("failures",)
        ).fetchone()
        self.assertEqual(table_schema, (advisor_lib._CREATE_TABLE_CMD,))
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
        self.assertEqual(table_schema, (advisor_lib._CREATE_TABLE_CMD,))
        connection.close()


class AdvisorLibTest(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile()
        self.db_connection = advisor_lib.setup_db(self.db_file.name)

    def tearDown(self):
        self.db_connection.close()
        self.db_file.close()

    def test_upload_failures(self):
        failure_info = {
            "source_type": "buildbot",
            "base_commit_sha": "8d29a3bb6f3d92d65bf5811b53bf42bf63685359",
            "source_id": "10000",
            "failures": [
                {"name": "a.ll", "message": "failed in way 1"},
                {"name": "b.ll", "message": "failed in way 2"},
            ],
            "platform": "linux-x86_64",
        }
        advisor_lib.upload_failures(failure_info, self.db_connection)
        failures = self.db_connection.execute("SELECT * from failures").fetchall()
        self.assertListEqual(
            failures,
            [
                (
                    "buildbot",
                    "8d29a3bb6f3d92d65bf5811b53bf42bf63685359",
                    "10000",
                    "a.ll",
                    "failed in way 1",
                    "linux-x86_64",
                ),
                (
                    "buildbot",
                    "8d29a3bb6f3d92d65bf5811b53bf42bf63685359",
                    "10000",
                    "b.ll",
                    "failed in way 2",
                    "linux-x86_64",
                ),
            ],
        )

    def test_explain_failures(self):
        failures = [{"name": "a.ll", "message": "failed"}]
        self.assertListEqual(
            advisor_lib.explain_failures(failures),
            [{"name": "a.ll", "explained": False, "reason": None}],
        )

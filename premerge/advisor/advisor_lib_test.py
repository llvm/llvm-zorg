import unittest
import tempfile

import advisor_lib


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
                ),
                (
                    "buildbot",
                    "8d29a3bb6f3d92d65bf5811b53bf42bf63685359",
                    "10000",
                    "b.ll",
                    "failed in way 2",
                ),
            ],
        )

    def test_explain_failures(self):
        failures = [{"name": "a.ll", "message": "failed"}]
        self.assertListEqual(
            advisor_lib.explain_failures(failures),
            [{"name": "a.ll", "explained": False, "reason": None}],
        )

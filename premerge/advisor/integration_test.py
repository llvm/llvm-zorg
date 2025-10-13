import unittest
import tempfile

import advisor


class AdvisorIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile()
        self.app = advisor.create_app(self.db_file.name)
        self.client = self.app.test_client()

    def tearDown(self):
        self.db_file.close()

    def test_upload_failures(self):
        failure_info = {
            "source_type": "buildbot",
            "base_commit_sha": "8d29a3bb6f3d92d65bf5811b53bf42bf63685359",
            "source_id": "10000",
            "failures": [
                {"name": "a.ll", "message": "failed in way 1"},
            ],
        }
        result = self.client.post("/upload", json=failure_info)
        self.assertEqual(result.status_code, 204)

    def test_explain_failures(self):
        failures = [{"name": "a.ll", "message": "failed"}]
        result = self.client.get("/explain", json=failures)
        self.assertEqual(result.status_code, 200)
        self.assertListEqual(
            result.json, [{"name": "a.ll", "explained": False, "reason": None}]
        )

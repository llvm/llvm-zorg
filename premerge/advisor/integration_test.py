import unittest
import tempfile
import os

import git_utils
import advisor


class AdvisorIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile()
        self.repository_path_dir = tempfile.TemporaryDirectory()
        self.repository_path = os.path.join(self.repository_path_dir.name, "actions")
        git_utils.clone_repository_if_not_present(
            self.repository_path, "https://github.com/llvm/actions"
        )
        self.app = advisor.create_app(self.db_file.name, self.repository_path)
        self.client = self.app.test_client()

    def tearDown(self):
        self.db_file.close()
        self.repository_path_dir.cleanup()

    def test_upload_failures(self):
        failure_info = {
            "source_type": "buildbot",
            "base_commit_sha": "e375fbb0917869e940c189ee0c178155b104b28a",
            "source_id": "10000",
            "failures": [
                {"name": "a.ll", "message": "failed in way 1"},
            ],
            "platform": "linux-x86_64",
        }
        result = self.client.post("/upload", json=failure_info)
        self.assertEqual(result.status_code, 204)

    def test_explain_failures(self):
        explanation_request = {
            "failures": [{"name": "a.ll", "message": "failed"}],
            "base_commit_sha": "e375fbb0917869e940c189ee0c178155b104b28a",
            "platform": "x86_64-linux",
        }
        result = self.client.get("/explain", json=explanation_request)
        self.assertEqual(result.status_code, 200)
        self.assertListEqual(
            result.json, [{"name": "a.ll", "explained": False, "reason": None}]
        )

    def test_flaky_tests(self):
        result = self.client.get("/flaky_tests")
        self.assertEqual(result.status_code, 200)
        self.assertListEqual(result.json, [])

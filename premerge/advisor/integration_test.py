import unittest

import advisor


class AdvisorIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.app = advisor.create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        pass

    def test_upload_failures(self):
        failures = [{"name": "a.ll", "message": "failed"}]
        result = self.client.post("/upload", json=failures)
        self.assertEqual(result.status_code, 204)

    def test_explain_failures(self):
        failures = [{"name": "a.ll", "message": "failed"}]
        result = self.client.get("/explain", json=failures)
        self.assertListEqual(
            result.json, [{"name": "a.ll", "explained": False, "reason": None}]
        )

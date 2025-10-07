import unittest

import advisor_lib


class AdvisorLibTest(unittest.TestCase):
    def test_upload_failures(self):
        failures = [{"name": "a.ll", "message": "failed"}]
        advisor_lib.upload_failures(failures)

    def test_explain_failures(self):
        failures = [{"name": "a.ll", "message": "failed"}]
        self.assertListEqual(
            advisor_lib.explain_failures(failures),
            [{"name": "a.ll", "explained": False, "reason": None}],
        )

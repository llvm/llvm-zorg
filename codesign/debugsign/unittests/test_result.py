#!/usr/bin/env python -tt

"""
unittests.test_result
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import mock
import StringIO

import dbsign.result as R


class TestResult(unittest.TestCase):
    def setUp(self):
        self.msg = "The quick brown fox."

    def test_result_failure(self):
        value = self.msg
        failure = R.Failure(value)

        self.assertFalse(failure.checked)
        self.assertEqual(value, failure.value)
        self.assertFalse(failure)
        self.assertTrue(failure.checked)
        self.assertRegexpMatches(repr(failure), value)

    def test_result_success(self):
        value = self.msg
        success = R.Success(value)

        self.assertFalse(success.checked)
        self.assertEqual(success.value, value)
        self.assertTrue(success)
        self.assertTrue(success.checked)
        self.assertRegexpMatches(repr(success), value)

    def test_abstract(self):
        text = self.msg
        error_text = "does not support boolean evaluation"
        res = R.Result(text)

        self.assertEqual(text, res.value)
        with self.assertRaisesRegexp(NotImplementedError, error_text):
            bool(res)

    def test_renew(self):
        msg = self.msg

        def fn(res_type):
            # create instance
            res = res_type(msg)
            self.assertFalse(res.checked)
            # invoke __nonzero__()
            bool(res)
            self.assertTrue(res.checked)
            # return "renewed" object
            return res.renew()

        for res_type in (R.Success, R.Failure):
            with self.subTest(resultType=res_type.__name__):
                res = fn(res_type)
                self.assertEqual(res_type, res.__class__)
                self.assertFalse(res.checked)
                bool(res)
                self.assertTrue(res.checked)

    @mock.patch('sys.stderr', new_callable=StringIO.StringIO)
    def test_unchecked_asserts(self, mock_stderr):
        for res_type in (R.Result, R.Success, R.Failure):
            with self.subTest(resultType=res_type.__name__):
                with self.assertRaises(AssertionError):
                    # generate an instance of the passed class
                    res = res_type(res_type.__name__)
                    # call destructor to simulate program termination
                    res.__del__()

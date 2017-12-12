#!/usr/bin/env python -tt

"""
unittests.test_ansi
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import mock
import re
import StringIO
import sys

import dbsign.ansi as A


class TestAnsi(unittest.TestCase):
    def setUp(self):
        self.test_text = "The quick brown fox, etc."
        self.codes = A._ANSI_CODES
        re_ansi = r"\033\[.*?m"
        ansi_msg_pattern = r'(?P<begin>{0})(?P<middle>.*?)(?P<end>{0})'
        self.re_ansi_msg = re.compile(ansi_msg_pattern.format(re_ansi))

    @unittest.skipUnless(sys.stdout.isatty(), A.WARN("requires tty"))
    def test_ansi_tty(self):
        msg = self.test_text

        for color in self.codes:
            with self.subTest(color):
                ansi_msg = A.ANSI(color, msg)
                self.assertTrue(ansi_msg.startswith(self.codes[color]))
                self.assertTrue(ansi_msg.endswith(self.codes['clear']))

    @unittest.skipUnless(sys.stdout.isatty(), A.WARN("requires tty"))
    def test_ansi_convenience_tty(self):
        msg = self.test_text
        funcs = [A.OK, A.INFO, A.WARN, A.ERROR]

        for func in funcs:
            with self.subTest(func=func.func_name):
                ansi_msg = func(msg)
                m = self.re_ansi_msg.match(ansi_msg)
                self.assertTrue(m)
                self.assertIn(m.group('begin'), self.codes.values())
                self.assertEqual(m.group('middle'), msg)
                self.assertEqual(m.group('end'), self.codes['clear'])

    @mock.patch('sys.stdout', new_callable=StringIO.StringIO)
    def test_ansi_notty(self, mock_stdout):
        msg = self.test_text

        for color in self.codes:
            with self.subTest(color):
                ansi_msg = A.ANSI(color, msg)
                self.assertEqual(msg, ansi_msg)

    @mock.patch('sys.stdout', new_callable=StringIO.StringIO)
    def test_ansi_convenience_notty(self, mock_stdout):
        msg = self.test_text
        funcs = [A.OK, A.INFO, A.WARN, A.ERROR]

        for func in funcs:
            with self.subTest(func=func.func_name):
                self.assertEqual(msg, func(msg))

#!/usr/bin/env python -tt

"""
unittests.test_logger
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import logging

import dbsign.logger as L


class TestLogger(unittest.TestCase):
    def test_logger(self):  # type: () -> ()
        # This test assumes the initial, intended semantics of the various
        # loggers returned. If semantics change, so must the tests.
        init_level = L._root.level
        test_level = 7
        log_name = "TestLoggerLogger"
        log = L.get_logger(log_name)

        with self.subTest(method=L.get_logger):
            self.assertEqual(log.__class__, logging.Logger)
            self.assertEqual(log_name, log.name)
            # Returned loggers should default to 0 (inherit parent level)
            self.assertEqual(0, log.level)

        with self.subTest(method=L.set_level):
            # Assert set_level() sets root level, not sublogger level
            L.set_level(test_level)
            self.assertEqual(test_level, L._root.level)
            self.assertEqual(0, log.level)

            # Restore and verify
            L.set_level(init_level)
            self.assertEqual(init_level, L._root.level)
            self.assertEqual(0, log.level)

    def test_normalize(self):  # type: () -> ()
        self.assertEqual(logging.WARN, L.normalize(logging.WARN))
        self.assertEqual(logging.DEBUG, L.normalize(logging.DEBUG - 1))
        self.assertEqual(logging.CRITICAL, L.normalize(logging.CRITICAL + 1))

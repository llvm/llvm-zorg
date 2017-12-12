#!/usr/bin/env python -tt

"""
unittests.test_shell
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import os
import sys

import dbsign.shell as sh
import dbsign.logger as logger

log = logger.get_logger(__name__)


class TestShellCommand(unittest.TestCase):
    def setUp(self):
        """Create some dummy ShellCommand objects"""
        self.params = [
            (["good", "command"], 0, 'OUT', 'ERR'),
            (["bad", "command"], 1, 'OUT', 'ERR'),
        ]

    def test_attrs(self):
        """
        - assert data equivalence of each attribute for all commands
        """
        self.assertTrue(self.params, "Empty test set?")
        for params in self.params:
            with self.subTest(params=params):
                cmd = sh.ShellCommand(*params)
                with self.assertRaises(AttributeError):
                    cmd.dummy_attribute
                self.assertEqual(params[0], cmd.args)
                self.assertEqual(params[1], cmd.code)
                self.assertEqual(params[2], cmd.stdout)
                self.assertEqual(params[3], cmd.stderr)

    def test_repr(self):
        self.assertTrue(self.params, "Empty test set?")
        for params in self.params:
            with self.subTest(params=params):
                cmd = sh.ShellCommand(*params)
                stringified = repr(cmd)
                args = params[0]
                self.assertGreaterEqual(len(args), 1)
                for arg in args:
                    self.assertIn(arg, stringified, )

    def test_equal(self):
        """
        - assert objects with different data are not equal
        - create duplicate ShellCommand objects
        - assert object data is equal
        - assert objects are equal
        """
        self.assertTrue(self.params, "Empty test set?")
        cmd_params = self.params
        cmd_a = sh.ShellCommand(*cmd_params[0])
        cmd_b = sh.ShellCommand(*cmd_params[-1])
        self.assertNotEqual(cmd_a, cmd_b)
        for params in cmd_params:
            with self.subTest(params=params):
                cmd_a = sh.ShellCommand(*params)
                cmd_b = sh.ShellCommand(*params)
                self.assertEqual(cmd_a, cmd_b, params)
                self.assertDictEqual(cmd_a.data, cmd_b.data, params)

    def test_nonzero(self):
        """
        - assert ShellCommand objects are "True" if code == 0
        - assert ShellCommand objects are "False" if code != 0
        """
        for params in self.params:
            with self.subTest(params=params):
                (args, code, stdout, stderr) = params
                cmd = sh.ShellCommand(*params)
                bool_value = bool(cmd)
                self.assertEqual(code == 0, bool_value, params)


class TestRun(unittest.TestCase):
    def test_run_simple(self):
        """
        - ensure true returns 0
        - ensure false returns non-zero
        """
        cmd_true = sh.run(['/usr/bin/true'])
        log.debug(cmd_true)
        self.assertTrue(cmd_true)
        self.assertEqual(0, cmd_true.code)

        cmd_false = sh.run(['/usr/bin/false'])
        log.debug(cmd_false)
        self.assertFalse(cmd_false)
        self.assertNotEqual(0, cmd_false.code)

    def test_sudo_run_simple(self):
        """
        - ensure true returns 0
        - ensure false returns non-zero
        """
        cmd_true = sh.sudo_run(['/usr/bin/true'])
        log.debug(cmd_true)
        self.assertTrue(cmd_true)
        self.assertEqual(0, cmd_true.code)

        cmd_false = sh.sudo_run(['/usr/bin/false'])
        log.debug(cmd_false)
        self.assertFalse(cmd_false)
        self.assertNotEqual(0, cmd_false.code)

    def test_run_invalid_executable(self):
        """
        - run() should raise OSError if execution is impossible
        """
        with self.assertRaises(OSError):
            sh.run(['/'])

    def test_run_compound(self):
        """
        - describe expected output (stdout, stderr, return code)
        - construct python program to emit expected output
        - run python code (using the current python interpreter)
        - ensure program executed successfully
        - ensure expected output was received
        """
        sub_stdout = r"Some out text."
        sub_stderr = r"Some err text."
        sub_code = 7

        sub_string = ('import sys;'
                      ' sys.stdout.write("{0}");'
                      ' sys.stderr.write("{1}");'
                      ' sys.exit({2})').format(
            sub_stdout, sub_stderr, sub_code)

        # run above python code in current executable
        sub_cmd = sh.run([sys.executable, '-c', sub_string])
        log.debug(sub_cmd)

        self.assertEqual(sub_code, sub_cmd.code)
        self.assertEqual(sub_stderr, sub_cmd.stderr)
        self.assertEqual(sub_stdout, sub_cmd.stdout)
        if sub_code == 0:
            self.assertTrue(sub_cmd)
        else:
            self.assertFalse(sub_cmd)

    def test_run_with_sudo(self):
        """
        - run should raise if asked to perform su/sudo operations
        - attempt to execute several illegal commands
        - assert that each raises a RuntimeError
        """
        illegal_cmds = [
            ['sudo', 'ls'],
            ['su', os.getenv('USER'), '-c', 'ls'],
        ]
        for cmd in illegal_cmds:
            with self.subTest(cmd=cmd):
                with self.assertRaisesRegexp(RuntimeError, 'Unauthorized'):
                    sh.run(cmd)

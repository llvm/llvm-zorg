#!/usr/bin/env python -tt

"""
unittests.test_commands
"""

from __future__ import print_function

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import mock
import os
import StringIO

import dbsign.commands as C
import dbsign.logger as L
from dbsign.result import Failure, Success
import dbsign.shell as sh


log = L.get_logger(__name__)


def dummy_sudo_run(params, *args):
    if sh.UNSAFE_FLAG in os.environ:
        return dummy_run(params, *args)
    else:
        raise RuntimeError()


def dummy_run(params, *args):
    return sh.ShellCommand(params, 0, 'dummy_stdout', 'dummy_stderr')


class TestCommands(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @mock.patch('dbsign.shell.sudo_run')
    @mock.patch('__builtin__.print')
    def test_auth_sudo(self, _print, _sudo_run):
        _sudo_run.side_effect = [
            Success('good1'),                   # run 1
            Failure('bad2'), Success('good2'),  # run 2
            Failure('bad3'), Failure('bad3'),   # run 3
        ]
        self.assertTrue(C._auth_sudo())
        self.assertTrue(C._auth_sudo())
        self.assertFalse(C._auth_sudo())

    @mock.patch('dbsign.shell.run')
    @mock.patch('sys.stdout', new_callable=StringIO.StringIO)
    def test_run_linter(self, mock_stdout, new_run):
        new_run.side_effect = dummy_run
        C._run_linter()
        new_run.assert_called()
        self.assertIn('flake8', new_run.call_args[0][0])

    @mock.patch('__builtin__.print')
    def test_cmd_help(self, _print):
        parser = mock.MagicMock()
        code = C.cmd_help(parser)
        self.assertTrue(_print.called)
        self.assertTrue(parser.format_help.called)
        self.assertEqual(0, code)

    @mock.patch('dbsign.security.unlock_keychain')
    @mock.patch('__builtin__.print')
    def test_cmd_prep(self, _print, _unlock):
        _unlock.side_effect = (Success('good'), Failure('bad'))
        self.assertEqual(0, C.cmd_prep())
        self.assertEqual(1, C.cmd_prep())

    @mock.patch('dbsign.commands._run_unittests')
    @mock.patch('dbsign.commands._auth_sudo')
    @mock.patch('__builtin__.print')
    def test_cmd_test(self, _print, _auth_sudo, _run_unit):
        _run_unit.side_effect = [(), (1, 2, 3)]
        self.assertEqual(0, C.cmd_test())
        self.assertEqual(1, _print.call_count)

        _print.reset_mock()
        self.assertEqual(3, C.cmd_test())
        self.assertEqual(2, _print.call_count)

    @mock.patch('unittest.TextTestRunner().run()')
    @mock.patch('unittest.TestLoader().discover()')
    @unittest.skip('TODO')
    def test_run_unittests(self, _test_discover, _test_run):
        _test_discover.return_value = ('test1', 'test2', 'test3')
        _test_run.return_value = mock.MagicMock()

        problems = C._run_unittests()
        self.assertEqual(0, len(problems))

        problems = C._run_unittests()
        self.assertEqual(0, len(problems))

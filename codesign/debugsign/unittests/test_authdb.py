#!/usr/bin/env python -tt

"""
unittests.test_authdb
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import logging
import mock
import os
import sys

import dbsign.logger as L
from dbsign.result import Failure, Success
import dbsign.shell as sh
import dbsign.security as S

log = L.get_logger(__name__)


@unittest.skipUnless(sys.platform == 'darwin',
                     "The authorizationdb is used only by macOS systems.")
class TestAuthDB(unittest.TestCase):
    def setUp(self):
        # Use system.privilege.taskport.debug since it can
        # be restored using the DevToolsSecurity tool
        self.invalid_priv = "foo.bar.baz"
        self.test_priv = "system.privilege.taskport.debug"

        # stash for later
        self.orig_unsafe_flag = os.getenv(S.UNSAFE_FLAG, None)

    def tearDown(self):
        if self.orig_unsafe_flag:
            os.environ[S.UNSAFE_FLAG] = self.orig_unsafe_flag

    def test_privilege_read(self):
        # assert read of valid privilege succeeds and matches
        priv = self.test_priv

        res_read = S.authdb_privilege_read(priv)
        self.assertTrue(res_read)
        rules = S.rules_from(res_read.value)

        cmd_read = sh.run(['security', 'authorizationdb', 'read', priv])
        self.assertTrue(cmd_read)

        for rule in rules:
            self.assertIn(rule, cmd_read.stdout)

    @unittest.skipUnless(os.getenv(S.UNSAFE_FLAG), "Requires --unsafe")
    def test_privilege_read_negative(self):
        """
        - assert read of invalid privilege fails

        Consecutive unsuccessful read operations can
        result in delayed or denied authdb calls.
        Require --unsafe to prevent inadvertent lockouts.
        """
        priv = self.invalid_priv
        log_level = L._root.level

        L.set_level(logging.CRITICAL)
        res_read = S.authdb_privilege_read(priv)
        L.set_level(log_level)
        self.assertFalse(res_read)

    def test_privilege_write_safe(self):
        # make sure we have a value backed up, then delete it
        if S.UNSAFE_FLAG in os.environ:
            del os.environ[S.UNSAFE_FLAG]

        res_write = S.authdb_privilege_write(self.test_priv, '42')
        self.assertFalse(res_write)
        self.assertIn('--unsafe', res_write.value)

    @unittest.skipUnless(os.getenv(S.UNSAFE_FLAG), "Requires --unsafe")
    def test_privilege_write(self):
        """
        - read current privilege value
        - write and verify new value
        - restore and verify original value
        - in case of failure, re-run DevToolsSecurity to ensure safe value
        """
        priv = self.test_priv
        test_rule = "is-admin"

        # read current value
        res_read = S.authdb_privilege_read(priv)
        self.assertTrue(res_read)
        # stash for later
        orig_value = res_read.value

        # write new value
        res_write = S.authdb_privilege_write(priv, "is-admin")
        self.assertTrue(res_write)

        # read new value
        res_verify = S.authdb_privilege_read(priv)
        self.assertTrue(res_verify)
        new_rules = S.rules_from(res_verify.value)
        self.assertEqual([test_rule], new_rules)

        # restore original value
        cmdline = ['security', 'authorizationdb', 'write', priv]
        res_restore = sh.sudo_run(cmdline, stdin=orig_value)
        self.assertTrue(res_restore)

        # verify restored value
        res_verify2 = S.authdb_privilege_read(priv)
        self.assertTrue(res_verify2)
        orig_rules = S.rules_from(orig_value)
        restored_rules = S.rules_from(res_verify2.value)
        restored_check = orig_rules == restored_rules
        self.assertEqual(orig_rules, restored_rules,
                         "There was an error restoring "+priv+". Falling back"
                         " to system defaults. You may need to re-run"
                         " DevToolsSecurity or re-init debugsign.")

        if not restored_check:
            cmd_dts = sh.sudo_run(['/usr/sbin/DevToolsSecurity', '-disable'])
            self.assertTrue(cmd_dts, "Failed to re-run DevToolsSecurity")

    @unittest.skipUnless(os.getenv(S.UNSAFE_FLAG), "Requires --unsafe")
    def test_privilege_write_negative(self):
        """
        - assert write of invalid privilege fails

        Consecutive unsuccessful write operations can
        result in delayed or denied authdb calls.
        Require --unsafe to prevent inadvertent lockouts.
        """
        priv = self.invalid_priv
        log_level = L._root.level

        L.set_level(logging.CRITICAL)
        res_write = S.authdb_privilege_write(priv, priv)
        L.set_level(log_level)
        self.assertFalse(res_write)

    def test_rules_from(self):
        for test_name in test_xml:
            with self.subTest(name=test_name):
                expected_rules, xml = test_xml[test_name]
                rules = S.rules_from(xml)
                self.assertEqual(expected_rules, rules)

    @mock.patch('plistlib.readPlistFromString')
    @mock.patch('dbsign.security.authdb_privilege_read')
    def test_verify_privilege(self, mock_auth_priv_read, mock_plist_read):
        mock_auth_priv_read.return_value = Failure('error1')
        res1 = S.verify_privilege('test1')
        self.assertFalse(res1)
        self.assertEqual('error1', res1.value)

        mock_auth_priv_read.return_value = Success('succ1')
        mock_plist_read.return_value = {'rule': ['allow']}
        res2 = S.verify_privilege('test2')
        self.assertTrue(res2)
        self.assertEqual('test2', res2.value)

    @mock.patch('dbsign.security.verify_privilege')
    def test_verify_privileges(self, mock_verify_priv):
        mock_verify_priv.side_effect = [
                Failure('1'),
                Success('2'), Failure('3'),
                Success('4'), Success('5')]

        res1 = S.verify_privileges('one')
        self.assertFalse(res1)
        self.assertEqual('1', res1.value)

        res2 = S.verify_privileges(['two', 'three'])
        self.assertFalse(res2)
        self.assertEqual('3', res2.value)

        privs = ['four', 'five']
        res3 = S.verify_privileges(list(privs))
        self.assertTrue(res3)
        self.assertEqual(privs, res3.value)


test_xml = {
    # Default value of system.privilege.taskport circa 10.13
    'sample1': ([],
        """<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd"><plist version="1.0"><dict><key>allow-root</key><false/><key>authenticate-user</key><true/><key>class</key><string>user</string><key>comment</key><string>Used by task_for_pid(...).  Task_for_pid is called by programs requesting full control over another program for things like debugging or performance analysis. This authorization only applies if the requesting and target programs are run by the same user; it will never authorize access to the program of another user.  WARNING: administrators are advised not to modify this right.</string><key>created</key><real>529441603.70259798</real><key>group</key><string>_developer</string><key>modified</key><real>529441603.70259798</real><key>session-owner</key><false/><key>shared</key><true/><key>timeout</key><integer>36000</integer><key>tries</key><integer>10000</integer><key>version</key><integer>0</integer></dict></plist>"""),  # noqa: E501
    # Default value of system.privilege.taskport.debug
    'sample2': (['is-admin', 'is-developer', 'authenticate-developer'],
                """<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd"><plist version="1.0"><dict><key>class</key><string>rule</string><key>created</key><real>505914196.93768197</real><key>k-of-n</key><integer>1</integer><key>modified</key><real>531881084.83930701</real><key>rule</key><array><string>is-admin</string><string>is-developer</string><string>authenticate-developer</string></array><key>version</key><integer>0</integer></dict></plist>"""),  # noqa: E501
    # Example of plist after running debugsign
    'sample3': (['allow'],
                """<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd"><plist version="1.0"><dict><key>class</key><string>rule</string><key>created</key><real>505914196.93768197</real><key>modified</key><real>531785828.17900801</real><key>rule</key><array><string>allow</string></array><key>version</key><integer>0</integer></dict></plist>"""),  # noqa: E501
}

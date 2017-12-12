#!/usr/bin/env python -tt

"""
unittests.test_security
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import logging
import os
# import sys

import dbsign.logger as L
import dbsign.security as S
import dbsign.shell as sh

log = L.get_logger(__name__)


@unittest.skip("need to mock identity/p12 file")
class TestIdentity(unittest.TestCase):
    def setUp(self):
        self.keyfile = S.keychain_to_file("debugsign_test")
        self.password = "12345"
        self.identity = 'debug_codesign'

        # store and override loglevel
        self.init_loglevel = L._root.level
        L.set_level(logging.CRITICAL)

        # create test keychain
        self.assertTrue(S.create_keychain(self.keyfile, self.password))

    def tearDown(self):
        # restore loglevel
        L.set_level(self.init_loglevel)

        # force remove test keychain
        if os.path.exists(self.keyfile):
            os.remove(self.keyfile)

    @unittest.skip("need to mock p12 file")
    def test_import_exists(self):  # type: () -> ()
        keydb = self.keyfile
        passwd = self.password
        ident = self.identity
        id_file = None

        self.assertFalse(S.find_identity(keydb, ident))
        self.assertTrue(S.import_identity(keydb, ident, id_file, passwd))
        self.assertTrue(S.find_identity(keydb, ident))

    @unittest.skip("need to mock p12 file")
    @unittest.skipUnless(os.getenv(S.UNSAFE_FLAG), "Requires --unsafe")
    def test_trust(self):  # type: () -> ()
        keydb = self.keyfile
        passwd = self.password
        ident = self.identity
        id_file = None

        self.assertTrue(S.import_identity(keydb, ident, id_file, passwd))
        self.assertTrue(S.find_identity(keydb, ident))
        self.assertTrue(S.trust_identity(keydb, ident))

    @unittest.skip("need to mock a trusted identity")
    def test_verify(self):  # type: () -> ()
        self.fail()

    @unittest.skip("need to mock a trusted identity")
    def test_verify_filename(self):  # type: () -> ()
        self.fail()

    @unittest.skip("need to mock p12 file")
    def test_delete(self):  # type: () -> ()
        self.fail()


class TestKeychain(unittest.TestCase):
    def setUp(self):
        self.keyfile = S.keychain_to_file("debugsign_test")
        self.password = "12345"
        self.init_loglevel = L._root.level
        L.set_level(logging.CRITICAL)

    def tearDown(self):
        L.set_level(self.init_loglevel)
        if os.path.exists(self.keyfile):
            os.remove(self.keyfile)

    def test_keychain_to_file(self):
        ext = S._KEYCHAIN_EXT
        login_path = os.path.expanduser(
            os.path.join("~/Library/Keychains", "login." + ext))
        self.assertTrue(login_path, S.keychain_to_file('login'))

    def test_derive_keychain_extension(self):
        """
        Because the tested method is itself guesswork,
        the test is rather simplistic:
        - generate expected location of user's login keychain
        - verify that "$HOME/Library/Keychains/login.${keychain_extension}"
          exists and is valid
        """
        login_keychain = os.path.expanduser(
            "~/Library/Keychains/login.{}".format(
                S.derive_keychain_extension()))
        self.assertTrue(os.path.exists(login_keychain))
        self.assertTrue(os.access(login_keychain, os.R_OK))

    def test_keychain_exists(self):
        """
        - assert existing keychain => True
        - assert non-existent keychain => False
        """
        valid_keychain = S.keychain_to_file("login")
        with self.subTest(keychain=valid_keychain):
            self.assertTrue(S.keychain_exists(valid_keychain))

        invalid_keychain = S.keychain_to_file("invalid")
        with self.subTest(keychain=invalid_keychain):
            self.assertFalse(S.keychain_exists(invalid_keychain))

    def test_keychain_operations(self):
        """
        - assert keychain does not exist
        - create keychain and assert exists
        - lock keychain
        - unlock keychain and assert exists
        """
        keyfile = self.keyfile
        password = self.password

        # some assorted negatives
        self.assertFalse(S.create_keychain('/tmp', password))

        # assert keychain does not exist
        self.assertFalse(S.keychain_exists(keyfile))

        # create and assert success
        res_create = S.create_keychain(keyfile, password)
        self.assertTrue(res_create)
        self.assertTrue(S.keychain_exists(keyfile))

        # assert second creation succeeds
        self.assertTrue(S.create_keychain(keyfile, password))

        # keychain is unlocked at creation; lock it to test unlocking
        cmd_lock = sh.run(['security', 'lock-keychain', keyfile])
        self.assertTrue(cmd_lock)
        self.assertFalse(S.unlock_keychain(keyfile, ''))
        self.assertTrue(S.unlock_keychain(keyfile, password))

        # ensure keychain settings were set correctly
        cmd_info = sh.run(['security', 'show-keychain-info', keyfile])
        self.assertTrue(cmd_info)
        self.assertRegexpMatches(cmd_info.stderr, r"\bno-timeout\b", cmd_info)

        # delete with backup
        res_delete = S.delete_keychain(keyfile, backup=True)
        self.assertTrue(res_delete)
        backup_file = res_delete.value
        # assert backup was made
        self.assertTrue(os.path.exists(backup_file))
        # assert keychain is gone
        self.assertFalse(S.keychain_exists(keyfile))
        self.assertFalse(os.path.exists(keyfile))
        # cleanup backup file
        os.unlink(backup_file)

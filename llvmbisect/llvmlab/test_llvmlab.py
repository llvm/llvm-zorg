# RUN: pythong test_llvmlab.py
import unittest

import os
import shutil
import tempfile
from . import ci

class TestLLVMLabCI(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        print self.workdir
        os.chdir(self.workdir)

    def tearDown(self):
        shutil.rmtree(self.workdir)

    def test_bisect(self):
        ci.action_bisect("llvmlab", ["--min-rev", "219719",
                              "--max-rev", "219899",
                              "bash", "-c",
                              "%(path)s/bin/clang -v | grep b700"])

    def test_ls(self):
        """Check that you can """
        builds = ci.action_ls("llvmlab", [])
        self.assertIn("clang-stage1-configure-RA_build", builds)
        compilers = ci.action_ls("llvmlab", 
                                 ["clang-stage1-configure-RA_build"])
        compiler_revs = [x.revision for x in compilers]
        self.assertIn(219899, compiler_revs)

    def test_fetch_noargs(self):
        """ """
        path = ci.action_fetch("llvmlab", ["clang-stage1-configure-RA_build"])
        self.assertTrue(os.path.isdir(path), "Fetch did not get a compiler?")

    def test_fetch_arg(self):
        """ """
        path = ci.action_fetch("llvmlab",
                               ["--update-link", "clang_link",
                                "clang-stage1-configure-RA_build",
                                "clang-r219899-t2014-10-15_20-42-53-b808"])
        self.assertTrue(os.path.isdir(path), "Fetch did not get a compiler?")


def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLLVMLabCI)
    unittest.TextTestRunner(verbosity=2).run(suite)

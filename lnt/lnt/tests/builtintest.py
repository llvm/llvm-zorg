"""
Base class for builtin-in tests.
"""

class BuiltinTest(object):
    def __init__(self):
        pass

    def describe(self):
        """"describe() -> str

        Return a short description of the test.
        """

    def run_test(self, name, args):
        """run_test(name, args) -> lnt.testing.Report

        Execute the test (accessed via name, for use in the usage message) with
        the given command line args.
        """
        abstract

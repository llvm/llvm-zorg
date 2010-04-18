import builtintest

class NTTest(builtintest.BuiltinTest):
    def describe(self):
        return 'LLVM test-suite compile and execution tests'

    def run_test(self, name, args):
        raise NotImplementedError

def create_instance():
    return NTTest()

__all__ = ['create_instance']

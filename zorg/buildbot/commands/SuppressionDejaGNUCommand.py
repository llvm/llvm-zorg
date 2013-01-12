import re
import StandardizedTest

class SuppressionDejaGNUCommand(StandardizedTest.StandardizedTest):
    kRunningRE = re.compile(r'Running (.*) ...')
    kRunningRE = re.compile(r'Running (.*) ...')
    kTestStateLineRE = re.compile(r'(FAIL|PASS|XFAIL|XPASS|UNRESOLVED): (.*)')

    testLogName = 'dg.sum'

    def parseLog(self, lines):
        results = []

        test_suite = None
        for ln in lines:
            m = self.kRunningRE.match(ln)
            if m is not None:
                test_suite, = m.groups()
                continue

            m = self.kTestStateLineRE.match(ln)
            if m is not None:
                code,name = m.groups()
                results.append((code, name, None))
                continue

        return results

if __name__ == '__main__':
    import sys
    t = SuppressionDejaGNUCommand()
    for res in t.parseLog(open(sys.argv[1]).readlines()):
        print res

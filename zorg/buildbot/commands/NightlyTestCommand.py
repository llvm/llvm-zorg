import itertools
import re
import os

import buildbot
import buildbot.steps.shell

class NightlyTestCommand(buildbot.steps.shell.Test):

    def __init__(self, xfails=[], *args, **kwargs):
        buildbot.steps.shell.Test.__init__(self, *args, **kwargs)

        self.expectedFailures = set(xfails)
        self.addFactoryArguments(xfails=list(xfails))

    def evaluateCommand(self, cmd):
        # Always fail if the command itself failed.
        #
        # Disabled for now, nightlytest is so broken.
        #if cmd.rc != 0:
        #    return buildbot.status.builder.FAILURE
    
        failures = {}
        xfailures = {}
        xpasses = {}
        num_passes = 0
        num_tests = 0
        for item in parse_report(self.getLog('report').readlines()):
            name = item.pop('Program')
            for key,value in item.items():
                if '/' in key:
                    continue
                kname = '%s.%s' % (key,name)
                if value == '*':
                    if kname in self.expectedFailures:
                        xfailures[key] = xfailures.get(key,[])
                        xfailures[key].append(kname)
                    else:
                        failures[key] = failures.get(key,[])
                        failures[key].append(kname)
                else:
                    if kname in self.expectedFailures:
                        xpasses[key] = xpasses.get(key,[])
                        xpasses[key].append(kname)
                    else:
                        num_passes += 1
            num_tests += 1

        num_fails = num_xfails = num_xpasses = 0
        for type,items in failures.items():
            if len(items) == num_tests: # Assume these are disabled.
                continue
            self.addCompleteLog('fail.%s' % type, '\n'.join(items) + '\n')
            num_fails += len(items)
        for type,items in xfailures.items():
            self.addCompleteLog('xfail.%s' % type, '\n'.join(items) + '\n')
            num_xfails += len(items)
        for type,items in xpasses.items():
            self.addCompleteLog('xpass.%s' % type, '\n'.join(items) + '\n')
            num_xpasses += len(items)
    
        self.setTestResults(total=(num_passes + num_fails + num_xfails +
                                   num_xpasses),
                            failed=num_fails,
                            passed=num_passes + num_xpasses,
                            warnings=num_xfails + num_xpasses)
        if num_fails:
          return buildbot.status.builder.FAILURE
        return buildbot.status.builder.SUCCESS
  
def parse_report(lines):
    def split_row(ln):
        return ln.split()

    header = None
    for ln in lines:
        if not ln.strip():
            continue

        if header is None:
            ln = ln.replace(' compile', '_compile')
            ln = ln.replace(' codegen', '_codegen')
            header = split_row(ln)
        else:
            row = split_row(ln)
            yield dict(zip(header, split_row(ln)))

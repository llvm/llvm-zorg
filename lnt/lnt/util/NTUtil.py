from lnt.server.ui import util
from lnt.db.perfdb import Run, Sample, Test

kPrefix = 'nightlytest'

# FIXME: We shouldn't need this.
kSentinelKeyName = 'bc.compile.success'

kComparisonKinds = [('File Size',None),
                    ('CBE','cbe.exec.time'),
                    ('LLC','llc.exec.time'),
                    ('JIT','jit.exec.time'),
                    ('GCCAS','gcc.compile.time'),
                    ('Bitcode','bc.compile.size'),
                    ('LLC compile','llc.compile.time'),
                    ('LLC-BETA compile','llc-beta.compile.time'),
                    ('JIT codegen','jit.compile.time'),
                    ('LLC-BETA','llc-beta.exec.time')]

kTSKeys = { 'gcc.compile' : 'GCCAS',
            'bc.compile' : 'Bitcode',
            'llc.compile' : 'LLC compile',
            'llc-beta.compile' : 'LLC_BETA compile',
            'jit.compile' : 'JIT codegen',
            'cbe.exec' : 'CBE',
            'llc.exec' : 'LLC',
            'llc-beta.exec' : 'LLC-BETA',
            'jit.exec' : 'JIT' }

# This isn't very fast, compute a summary if querying the same run
# repeatedly.
def getTestValueInRun(db, r, t, default=None, coerce=None):
    for value, in db.session.query(Sample.value).\
            filter(Sample.test == t).\
            filter(Sample.run == r):
        if coerce is not None:
            return coerce(value)
        return value
    return default

def getTestNameValueInRun(db, r, testname, default=None, coerce=None):
    for value, in db.session.query(Sample.value).join(Test).\
            filter(Test.name == testname).\
            filter(Sample.run == r):
        if coerce is not None:
            return coerce(value)
        return value
    return default

class RunSummary:
    def __init__(self):
        # The union of test names seen.
        self.testNames = set()
        # Map of test ids to test instances.
        self.testIds = {}
        # Map of test names to test instances
        self.testMap = {}
        # Map of run to multimap of test ID to sample list.
        self.runSamples = {}

        # FIXME: Should we worry about the info parameters on a
        # nightlytest test?

    def testMatchesPredicates(self, db, t, testPredicate, infoPredicates):
        if testPredicate:
            if not testPredicate(t):
                return False
        if infoPredicates:
            info = dict((i.key,i.value) for i in t.info.values())
            for key,predicate in infoPredicates:
                value = info.get(key)
                if not predicate(t, key, value):
                    return False
        return True

    def addRun(self, db, run, testPredicate=None, infoPredicates=None):
        sampleMap = self.runSamples.get(run.id)
        if sampleMap is None:
            sampleMap = self.runSamples[run.id] = util.multidict()

        q = db.session.query(Sample.value,Test).join(Test)
        q = q.filter(Sample.run == run)
        for s_value,t in q:
            if not self.testMatchesPredicates(db, t, testPredicate, infoPredicates):
                continue

            sampleMap[t.id] = s_value
            self.testMap[t.name] = t
            self.testIds[t.id] = t

            # Filter out summary things in name lists by only looking
            # for things which have a .success entry.
            if t.name.endswith('.success'):
                self.testNames.add(t.name.split('.', 3)[1])

    def getRunSamples(self, run):
        if run is None:
            return {}
        return self.runSamples.get(run.id, {})

    def getTestValueByName(self, run, testName, default, coerce=None):
        t = self.testMap.get(testName)
        if t is None:
            return default
        sampleMap = self.runSamples.get(run.id, {})
        samples = sampleMap.get(t.id)
        if sampleMap is None or samples is None:
            return default
        # FIXME: Multiple samples?
        if coerce:
            return coerce(samples[0].value)
        else:
            return samples[0].value

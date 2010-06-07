"""
Classes for caching metadata about a PerfDB instance.
"""

from lnt.viewer.PerfDB import RunInfo, Test

class SuiteSummary:
    def __init__(self, name, path):
        self.name = name
        self.path = path

class PerfDBSummary:
    @staticmethod
    def fromdb(db):
        revision = db.get_revision_number("Run")

        # Look for all the run tags and use them to identify the available
        # suites.
        q = db.session.query(RunInfo.value.distinct())
        q = q.filter(RunInfo.key == "tag")

        suites = [SuiteSummary("Nightlytest", ("nightlytest",))]
        for tag, in q:
            if tag == 'nightlytest':
                continue
            suites.append(SuiteSummary(tag, ("simple",tag)))

        suites.sort(key=lambda s: s.name)
        return PerfDBSummary(revision, suites)

    def __init__(self, revision, suites):
        self.revision = revision
        self.suites = suites

    def is_up_to_date(self, db):
        return self.revision == db.get_revision_number("Run")

class SimpleSuiteSummary:
    @staticmethod
    def fromdb(db, tag):
        revision = db.get_revision_number("Test")

        # Find all test names.
        q = db.session.query(Test)
        q = q.filter(Test.name.startswith(tag))
        tests = list(q)

        # Collect all the test data.
        test_names = set()
        parameter_sets = set()
        test_map = {}
        for t in tests:
            name = t.name.split(str('.'),1)[1]
            test_names.add(name)

            items = [(k,v.value) for k,v in t.info.items()]
            items.sort()
            key = tuple(items)

            parameter_sets.add(key)
            test_map[(name, key)] = t

        # Order the test names.
        test_names = list(test_names)
        test_names.sort()

        # Collect the set of all parameter keys.
        parameter_keys = list(set([k for pset in parameter_sets
                                   for k,v in pset]))
        parameter_keys.sort()

        # Order the parameter sets and convert to dictionaries.
        parameter_sets = list(parameter_sets)
        parameter_sets.sort()

        return SimpleSuiteSummary(revision, tag, test_names, test_map,
                                  parameter_keys, parameter_sets)

    def __init__(self, revision, tag, test_names, test_map,
                 parameter_keys, parameter_sets):
        self.revision = revision
        self.tag = tag
        self.test_names = test_names
        self.test_map = test_map
        self.parameter_keys = parameter_keys
        self.parameter_sets = parameter_sets

    def is_up_to_date(self, db):
        return self.revision == db.get_revision_number("Test")

_cache = {}
def get_simple_suite_summary(db, tag):
    key = (db.path, tag)
    entry = _cache.get(key)
    if entry is None or not entry.is_up_to_date(db):
        _cache[key] = entry = SimpleSuiteSummary.fromdb(db, tag)
    return entry

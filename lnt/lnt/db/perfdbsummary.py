"""
Classes for caching metadata about a PerfDB instance.
"""

from lnt.db.perfdb import Run, RunInfo, Sample, Test

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
        return (not db.modified_run and
                self.revision == db.get_revision_number("Run"))

class SimpleSuiteSummary(object):
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
        test_id_map = {}
        for t in tests:
            name = t.name.split('.', 1)[1]

            key = t.get_parameter_set()

            parameter_sets.add(key)
            test_id_map[(name, key)] = t.id

            if name.endswith('.success'):
                test_name = name.rsplit('.', 1)[0]
            elif name.endswith('.status'):
                test_name = name.rsplit('.', 1)[0]
            else:
                test_name = name

            test_names.add(test_name)

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

        return SimpleSuiteSummary(revision, tag, test_names,
                                  test_id_map, parameter_keys, parameter_sets)

    def __init__(self, revision, tag, test_names,
                 test_id_map, parameter_keys, parameter_sets):
        self.revision = revision
        self.tag = tag
        self.test_names = test_names
        self.test_id_map = test_id_map
        self.parameter_keys = parameter_keys
        self.parameter_sets = parameter_sets
        self.parameter_maps = map(dict, parameter_sets)
        self.test_info_map = dict([(v,k) for k,v in test_id_map.items()])

    def is_up_to_date(self, db):
        return (not db.modified_test and
                self.revision == db.get_revision_number("Test"))

    def get_test_names_in_runs(self, db, runs):
        # Load the distinct test ids for these runs.
        test_ids = db.session.query(Sample.test_id)\
            .filter(Sample.run_id.in_(runs)).distinct()

        # Get the test names for the test ids.
        test_names = [self.test_info_map[id][0]
                      for id, in test_ids]

        # Limit to the tests we actually report.
        test_names = list(set(test_names) & set(self.test_names))
        test_names.sort()

        return test_names

_cache = {}
def get_simple_suite_summary(db, tag):
    key = (db.path, tag)
    entry = _cache.get(key)
    if entry is None or not entry.is_up_to_date(db):
        _cache[key] = entry = SimpleSuiteSummary.fromdb(db, tag)
    return entry

class SimpleSuiteRunSummary(object):
    _cache = {}
    @staticmethod
    def get_summary(db, tag):
        key = (db.path, tag)
        entry = SimpleSuiteRunSummary._cache.get(key)
        if entry is None or not entry.is_up_to_date(db):
            entry = SimpleSuiteRunSummary.fromdb(db, tag)
            SimpleSuiteRunSummary._cache[key] = entry
        return entry

    @staticmethod
    def fromdb(db, tag):
        revision = db.get_revision_number("RunInfo")

        # Find all run_orders for runs with this tag, ordered by run time so
        # that runs are ordered by both (run_order, time) in the final ordering.
        all_run_orders = db.session.query(RunInfo.value, RunInfo.run_id,
                                          Run.machine_id).\
            join(Run).\
            order_by(Run.start_time.desc()).\
            filter(RunInfo.key == "run_order").\
            filter(RunInfo.run_id.in_(
                db.session.query(RunInfo.run_id).\
                    filter(RunInfo.key == "tag").\
                    filter(RunInfo.value == tag).subquery()))
        all_run_orders = list(all_run_orders)

        order_by_run = dict((run_id,order)
                            for order,run_id,machine_id in all_run_orders)
        machine_id_by_run = dict((run_id,machine_id)
                                 for order,run_id,machine_id in all_run_orders)

        # Create a mapping from run_order to the available runs with that order.
        runs_by_order = {}
        for order,run_id,_ in all_run_orders:
            runs = runs_by_order.get(order)
            if runs is None:
                runs = runs_by_order[order] = []
            runs.append(run_id)

        # Get all available run_orders, in order.
        def order_key(run_order):
            return run_order
        run_orders = runs_by_order.keys()
        run_orders.sort(key = order_key)
        run_orders.reverse()

        # Construct the total order of runs.
        runs_in_order = []
        for order in run_orders:
            runs_in_order.extend(runs_by_order[order])

        return SimpleSuiteRunSummary(
            revision, tag, run_orders, runs_by_order, runs_in_order,
            order_by_run, machine_id_by_run)

    def __init__(self, revision, tag, run_orders, runs_by_order, runs_in_order,
                 order_by_run, machine_id_by_run):
        self.revision = revision
        self.tag = tag
        self.run_orders = run_orders
        self.runs_by_order = runs_by_order
        self.runs_in_order = runs_in_order
        self.order_by_run = order_by_run
        self.machine_id_by_run = machine_id_by_run
        self.run_status_kinds = {}

    def is_up_to_date(self, db):
        return (not db.modified_run and
                self.revision == db.get_revision_number("RunInfo"))

    def contains_run(self, run_id):
        return run_id in self.machine_id_by_run

    def get_run_order(self, run_id):
        return self.order_by_run.get(run_id)

    def get_runs_on_machine(self, machine_id):
        return [k for k,v in self.machine_id_by_run.items()
                if v == machine_id]

    def get_run_ordered_index(self, run_id):
        try:
            return self.runs_in_order.index(run_id)
        except:
            print run_id
            print self.runs_in_order
            raise

    def get_previous_run_on_machine(self, run_id):
        machine_id = self.machine_id_by_run[run_id]
        index = self.get_run_ordered_index(run_id)
        for i in range(index + 1, len(self.runs_in_order)):
            id = self.runs_in_order[i]
            if machine_id == self.machine_id_by_run[id]:
                return id

    def get_next_run_on_machine(self, run_id):
        machine_id = self.machine_id_by_run[run_id]
        index = self.get_run_ordered_index(run_id)
        for i in range(0, index)[::-1]:
            id = self.runs_in_order[i]
            if machine_id == self.machine_id_by_run[id]:
                return id

    def get_run_status_kind(self, db, run_id):
        kind = self.run_status_kinds.get(run_id)
        if kind is None:
            # Compute the status kind by for .success tests in this run.
            if db.session.query(Test.name).join(Sample)\
                    .filter(Sample.run_id == run_id)\
                    .filter(Test.name.endswith(".success")).first() is not None:
                kind = False
            else:
                kind = True
        self.run_status_kinds[run_id] = kind
        return kind

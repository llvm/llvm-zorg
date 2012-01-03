"""
Utilities for helping with the analysis of data, for reporting purposes.
"""

from lnt.util import stats
from lnt.server.ui import util
from lnt.db.runinfo import ComparisonResult
from lnt.testing import PASS, FAIL, XFAIL

class RunInfo(object):
    def __init__(self, testsuite):
        self.testsuite = testsuite

        self.sample_map = util.multidict()
        self.loaded_run_ids = set()

    def get_run_comparison_result(self, run, compare_to, test_id, field,
                                  comparison_window=[]):
        field_index = self.testsuite.sample_fields.index(field)

        # Get the field which indicates the requested field's status.
        status_field = field.status_field
        if status_field:
            status_field_index = self.testsuite.sample_fields.index(
                status_field)

        # Load the sample data for the current and previous runs and the
        # comparison window.
        if compare_to is None:
            compare_id = None
        else:
            compare_id = compare_to.id
        runs_to_load = set([r.id for r in comparison_window])
        runs_to_load.add(run.id)
        if compare_id is not None:
            runs_to_load.add(compare_id)
        self._load_samples_for_runs(runs_to_load)

        # Lookup the current and previous samples.
        run_samples = self.sample_map.get((run.id, test_id), ())
        prev_samples = self.sample_map.get((compare_id, test_id), ())

        # Determine whether this (test,pset) passed or failed in the current and
        # previous runs.
        #
        # FIXME: Support XFAILs and non-determinism (mixed fail and pass)
        # better.
        run_failed = prev_failed = False
        if status_field:
            for sample in run_samples:
                run_failed |= sample[status_field_index] == FAIL
            for sample in prev_samples:
                prev_failed |= sample[status_field_index] == FAIL

        # Get the current and previous values.
        run_values = [s[field_index] for s in run_samples]
        prev_values = [s[field_index] for s in prev_samples]
        if run_values:
            run_value = min(run_values)
        else:
            run_value = None
        if prev_values:
            prev_value = min(prev_values)
        else:
            prev_value = None

        # If we have multiple values for this run, use that to estimate the
        # distribution.
        if run_values and len(run_values) > 1:
            stddev = stats.standard_deviation(run_values)
            MAD = stats.median_absolute_deviation(run_values)
            stddev_mean = stats.mean(run_values)
            stddev_is_estimated = False
        else:
            stddev = None
            MAD = None
            stddev_mean = None
            stddev_is_estimated = False

        # If we are missing current or comparison values we are done.
        if run_value is None or prev_value is None:
            return ComparisonResult(
                run_value, prev_value, delta=None,
                pct_delta = None, stddev = stddev, MAD = MAD,
                cur_failed = run_failed, prev_failed = prev_failed,
                samples = run_values)

        # Compute the comparison status for the test value.
        delta = run_value - prev_value
        if prev_value != 0:
            pct_delta = delta / prev_value
        else:
            pct_delta = 0.0

        # If we don't have an estimate for the distribution, attempt to "guess"
        # it using the comparison window.
        #
        # FIXME: We can substantially improve the algorithm for guessing the
        # noise level from a list of values. Probably better to just find a way
        # to kill this code though.
        if stddev is None:
            # Get all previous values in the comparison window, for passing
            # runs.
            #
            # FIXME: This is using the wrong status kind. :/
            prev_samples = [s for run in comparison_window
                            for s in self.sample_map.get((run.id, test_id), ())]
            # Filter out failing samples.
            if status_field:
                prev_samples = [s for s in prev_samples
                                if s[status_field_index] == PASS]
            if prev_samples:
                prev_values = [s[field_index]
                               for s in prev_samples]
                stddev = stats.standard_deviation(prev_values)
                MAD = stats.median_absolute_deviation(prev_values)
                stddev_mean = stats.mean(prev_values)
                stddev_is_estimated = True

        return ComparisonResult(run_value, prev_value, delta,
                                pct_delta, stddev, MAD,
                                run_failed, prev_failed, run_values,
                                stddev_mean, stddev_is_estimated)

    def _load_samples_for_runs(self, run_ids):
        # Find the set of new runs to load.
        to_load = set(run_ids) - self.loaded_run_ids
        if not to_load:
            return

        # Batch load all of the samples for the needed runs.
        #
        # We speed things up considerably by loading the column data directly
        # here instead of requiring SA to materialize Sample objects.
        columns = [self.testsuite.Sample.run_id,
                  self.testsuite.Sample.test_id]
        columns.extend(f.column for f in self.testsuite.sample_fields)
        q = self.testsuite.query(*columns)
        q = q.filter(self.testsuite.Sample.run_id.in_(to_load))
        for data in q:
            run_id = data[0]
            test_id = data[1]
            sample_values = data[2:]
            self.sample_map[(run_id, test_id)] = sample_values

        self.loaded_run_ids |= to_load


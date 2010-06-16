from lnt.util import stats
from lnt.viewer import Util
from lnt.viewer.PerfDB import Sample

REGRESSED = 'REGRESSED'
IMPROVED = 'IMPROVED'
UNCHANGED_PASS = 'UNCHANGED_PASS'
UNCHANGED_FAIL = 'UNCHANGED_FAIL'

class ComparisonResult:
    def __init__(self, cur_value, prev_value, delta, pct_delta, stddev, MAD,
                 cur_failed, prev_failed):
        self.current = cur_value
        self.previous = prev_value
        self.delta = delta
        self.pct_delta = pct_delta
        self.stddev = stddev
        self.MAD = MAD
        self.failed = cur_failed
        self.prev_failed = prev_failed

    def get_test_status(self):
        # Compute the comparison status for the test success.
        if self.failed:
            if self.prev_failed:
                return UNCHANGED_FAIL
            else:
                return REGRESSED
        else:
            if self.prev_failed:
                return IMPROVED
            else:
                return UNCHANGED_PASS

    def get_value_status(self, confidence_interval=2.576, value_precision=0.01):
        if self.current is None or self.previous is None:
            return None

        # Don't report value errors for tests which fail, or which just started
        # passing.
        #
        # FIXME: One bug here is that we risk losing performance data on tests
        # which flop to failure then back. What would be nice to do here is to
        # find the last value in a passing run, or to move to using proper keyed
        # reference runs.
        if self.failed:
            return UNCHANGED_FAIL
        elif self.prev_failed:
            return UNCHANGED_PASS

        # Ignore tests whose delt is too small relative to the precision we can
        # sample at; otherwise quantization means that we can't measure the
        # standard deviation with enough accuracy.
        if abs(self.delta) <= 2 * value_precision * confidence_interval:
            if self.failed:
                return UNCHANGED_FAIL
            else:
                return UNCHANGED_PASS

        # If we have a comparison window, then measure using a symmetic
        # confidence interval.
        if self.stddev is not None:
            if abs(self.delta) > self.stddev * confidence_interval:
                if self.delta < 0:
                    return IMPROVED
                else:
                    return REGRESSED
            else:
                if self.failed:
                    return UNCHANGED_FAIL
                else:
                    return UNCHANGED_PASS

        # Otherwise, use the old "significant change" metric of > 5%.
        if abs(self.pct_delta) >= .05:
            if self.pct_delta < 0:
                return IMPROVED
            else:
                return REGRESSED
        else:
            if self.failed:
                return UNCHANGED_FAIL
            else:
                return UNCHANGED_PASS

class SimpleRunInfo:
    def __init__(self, db, test_suite_summary):
        self.db = db
        self.test_suite_summary = test_suite_summary

        self.sample_map = Util.multidict()
        self.loaded_samples = set()

    def get_run_comparison_result(self, run, compare_to, test_name, pset,
                                  comparison_window=[]):
        # Get the test.
        test = self.test_suite_summary.test_map.get((test_name, pset))
        if test is None:
            return ComparisonResult(run_value=None, prev_value=None, delta=None,
                                    pct_delta=None, stddev=None, MAD=None,
                                    cur_failed=None, prev_failed=None)

        # Get the test status info.
        status_info = self.test_suite_summary.test_status_map.get(test_name)
        if status_info is not None:
            status_name,status_kind = status_info
            status_test = self.test_suite_summary.test_map.get(
                (status_name, pset))
        else:
            status_test = status_kind = None

        # Load the sample data for the current and previous runs and the
        # comparison window.
        if compare_to is None:
            compare_id = None
        else:
            compare_id = compare_to.id
        runs_to_load = set(comparison_window)
        runs_to_load.add(run.id)
        if compare_id is not None:
            runs_to_load.add(compare_id)
        self._load_samples_for_runs(runs_to_load)

        # Lookup the current and previous values.
        run_values = self.sample_map.get((run.id, test.id))
        prev_values = self.sample_map.get((compare_id, test.id))

        # Determine whether this (test,pset) passed or failed in the current and
        # previous runs.
        run_failed = prev_failed = False
        if not status_test:
            run_failed = not run_values
            prev_failed = not prev_values
        else:
            run_status = self.sample_map.get((run.id,status_test.id))
            prev_status = self.sample_map.get((compare_id,status_test.id))

            # FIXME: Support XFAILs.
            #
            # FIXME: What to do about the multiple entries here. We could start
            # by just treating non-matching samples as errors.
            if status_kind == False: # .success style
                run_failed = not run_status or not run_status[0]
                prev_failed = not prev_status or not prev_status[0]
            else:
                run_failed = run_status and run_status[0] != 0
                prev_failed = prev_status and prev_status[0] != 0

        # Get the current and previous values.
        if run_values:
            run_value = min(run_values)
        else:
            run_value = None
        if prev_values:
            prev_value = min(prev_values)
        else:
            prev_value = None

        # If we are missing current or comparison values we are done.
        if run_value is None or prev_value is None:
            return ComparisonResult(
                run_value, prev_value, delta=None,
                pct_delta=None, stddev=None, MAD=None,
                cur_failed=run_failed, prev_failed=prev_failed)

        # Compute the comparison status for the test value.
        delta = run_value - prev_value
        if prev_value != 0:
            pct_delta = delta / prev_value
        else:
            pct_delta = 0.0

        # Get all previous values in the comparison window.
        prev_values = [v for run_id in comparison_window
                       for v in self.sample_map.get((run_id, test.id), ())]
        if prev_values:
            stddev = stats.standard_deviation(prev_values)
            MAD = stats.median_absolute_deviation(prev_values)
        else:
            stddev = None
            MAD = None

        return ComparisonResult(run_value, prev_value, delta,
                                pct_delta, stddev, MAD,
                                run_failed, prev_failed)

    def _load_samples_for_runs(self, runs):
        # Find the set of new runs to load.
        to_load = set(runs) - self.loaded_samples
        if not to_load:
            return

        q = self.db.session.query(Sample.value, Sample.run_id, Sample.test_id)
        q = q.filter(Sample.run_id.in_(to_load))
        for value,run_id,test_id in q:
            self.sample_map[(run_id,test_id)] = value

        self.loaded_samples |= to_load


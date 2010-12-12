"""
Helper functions for graphing test results.
"""

import Util

from lnt.util import stats
from lnt.external.stats import stats as ext_stats

from PerfDB import Machine, Run, RunInfo, Sample, Test

def get_test_plots(db, machine, test_ids, run_summary, ts_summary,
                   show_mad_error = False, show_points = False,
                   show_all_points = False, show_stddev = False,
                   show_linear_regression = False):
    # Load all the samples for these tests and this machine.
    q = db.session.query(Sample.run_id,Sample.test_id,
                         Sample.value).join(Run)
    q = q.filter(Run.machine_id == machine.id)
    q = q.filter(Sample.test_id.in_(test_ids))
    samples = list(q)

    # Aggregate by test id and then run key.
    #
    # FIXME: Pretty expensive.
    samples_by_test_id = {}
    for run_id,test_id,value in samples:
        d = samples_by_test_id.get(test_id)
        if d is None:
            d = samples_by_test_id[test_id] = Util.multidict()
        run_key = run_summary.get_run_order(run_id)
        if run_key is None:
            continue

        # FIXME: What to do on failure?
        run_key = int(run_key)
        d[run_key] = value

    # Build the graph data
    pset_id_map = dict([(pset,i)
                        for i,pset in enumerate(ts_summary.parameter_sets)])
    num_plots = len(test_ids)
    for index,test_id in enumerate(test_ids):
        test = db.getTest(test_id)
        pset = test.get_parameter_set()
        name = test.name

        # Get the plot for this test.
        #
        # FIXME: Support order by something other than time.
        errorbar_data = []
        points_data = []
        data = []
        points = []
        for x,values in samples_by_test_id.get(test_id,{}).items():
            min_value = min(values)
            data.append((x, min_value))
            if show_points:
                if show_all_points:
                    for v in values:
                        points_data.append((x, v))
                else:
                    points_data.append((x, min_value))
            if show_stddev:
                mean = stats.mean(values)
                sigma = stats.standard_deviation(values)
                errorbar_data.append((x, mean - sigma, mean + sigma))
            if show_mad_error:
                med = stats.median(values)
                mad = stats.median_absolute_deviation(values, med)
                errorbar_data.append((x, med - mad, med + mad))
                points.append((x, min_value, mad, med))
        data.sort()
        points.sort()

        plot_js = ""

        # Determine the base plot color.
        col = list(Util.makeDarkColor(float(index) / num_plots))

        # Add regression line, if requested.
        if show_linear_regression:
            xs = [t for t,v in data]
            ys = [v for t,v in data]

            # We compute the regression line in terms of a normalized X scale.
            x_min, x_max = min(xs), max(xs)
            norm_xs = [(x - x_min) / (x_max - x_min)
                       for x in xs]
            slope, intercept,_,_,_ = ext_stats.linregress(norm_xs, ys)

            reglin_col = [c*.5 for c in col]
            pts = ','.join('[%.4f,%.4f]' % pt
                           for pt in [(x_min, 0.0 * slope + intercept),
                                      (x_max, 1.0 * slope + intercept)])
            style = "new Graph2D_LinePlotStyle(4, %r)" % ([.7, .7, .7],)
            plot_js += "    graph.addPlot([%s], %s);\n" % (pts,style)
            style = "new Graph2D_LinePlotStyle(2, %r)" % (reglin_col,)
            plot_js += "    graph.addPlot([%s], %s);\n" % (pts,style)

        pts = ','.join(['[%.4f,%.4f]' % (t,v)
                        for t,v in data])
        style = "new Graph2D_LinePlotStyle(1, %r)" % col
        plot_js += "    graph.addPlot([%s], %s);\n" % (pts,style)

        if points_data:
            pts_col = (0,0,0)
            pts = ','.join(['[%.4f,%.4f]' % (t,v)
                            for t,v in points_data])
            style = "new Graph2D_PointPlotStyle(1, %r)" % (pts_col,)
            plot_js += "    graph.addPlot([%s], %s);\n" % (pts,style)

        if errorbar_data:
            bar_col = [c*.7 for c in col]
            pts = ','.join(['[%.4f,%.4f,%.4f]' % (x,y_min,y_max)
                            for x,y_min,y_max in errorbar_data])
            style = "new Graph2D_ErrorBarPlotStyle(1, %r)" % (bar_col,)
            plot_js += "    graph.addPlot([%s], %s);\n" % (pts,style)

        yield (test_id, plot_js, col, data, points)

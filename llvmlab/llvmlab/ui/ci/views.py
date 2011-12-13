import flask
from flask import abort
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask import current_app
ci = flask.Module(__name__, url_prefix='/ci', name='ci')

from llvmlab import util

@ci.route('/')
def dashboard():
    return render_template("dashboard.html",
                           ci_config=current_app.config.summary.config)

@ci.route('/phase/<int:index>/<source_stamp>')
def phase_popup(index, source_stamp):
    cfg = current_app.config.summary.config

    # Validate the phase.
    if index >= len(cfg.phases):
        abort(404)

    # Get the phase.
    phase = cfg.phases[index]

    # Lookup the latest builds associated with this revision.
    phased_builds = dict(
        (builder, [b for b in current_app.config.status.builders.get(builder,[])
                   if b.source_stamp == source_stamp])
        for builder in phase.builder_names)
    return render_template("phase_popup.html",
                           ci_config=current_app.config.summary.config,
                           phase = phase, source_stamp = source_stamp,
                           phased_builds = phased_builds)

@ci.route('/latest_release')
def latest_release():
    return render_template("latest_release.html",
                           ci_config=current_app.config.summary.config)

@ci.route('/monitor')
def buildbot_monitor():
    return render_template("buildbot_monitor.html",
                           bb_status=current_app.config.status)

@ci.route('/build_chart')
def build_chart():
    import time

    # Determine the render constants.
    k_days_data = int(request.args.get('days', 1))
    k_pixels_per_minute = float(request.args.get('pixels_per_minute', .5))

    # Aggregate builds by slave, for completed builds within the desired time
    # frame.
    current_time = time.time()
    builders = current_app.config.status.builders
    slave_builders = util.multidict(
        (build.slave, build)
        for builds in builders.values()
        for build in builds
        if build.end_time is not None
        if current_time - build.start_time < 60 * 60 * 24 * k_days_data)

    # Compute the build chart.
    class ChartItem(object):
        def __init__(self, build, color, left, width):
            self.build = build
            self.color = color
            self.left = left
            self.width = width
    builder_colors = dict((name, util.make_dark_color(float(i) / len(builders)))
                          for i,name in enumerate(builders))
    build_chart_data = {}
    max_x = 0
    min_time = min(build.start_time
                   for builds in slave_builders.values()
                   for build in builds)
    for slave, builders in slave_builders.items():
        # Order the builders by time.
        builders.sort(key = lambda b: b.start_time)
        
        # Aggregate builds by builder type.
        builds_by_type = util.multidict(
            (build.name, build)
            for build in builders)

        # Create the char items.
        rows = []
        for name,builds in util.sorted(builds_by_type.items()):
            color = builder_colors[name]
            hex_color = '%02x%02x%02x' % tuple(int(x*255)
                                           for x in color)
            rows.append([])
            for build in builds:
                elapsed = build.end_time - build.start_time
                width = max(1, int(k_pixels_per_minute * elapsed / 60))
                left = int(k_pixels_per_minute *
                           (build.start_time - min_time) / 60)
                max_x = max(max_x, left + width)
                rows[-1].append(ChartItem(build, hex_color, left, width))
        build_chart_data[slave] = rows

    build_chart = { 'data' : build_chart_data,
                    'max_x' : max_x }
    return render_template("build_chart.html",
                           bb_status = current_app.config.status,
                           build_chart = build_chart)

@ci.route('/phase_description/<int:index>')
def phase_description(index):
    cfg = current_app.config.summary.config

    # Validate the phase.
    if index >= len(cfg.phases):
        abort(404)

    # Get the phase.
    phase = cfg.phases[index]
    return render_template("phase_description.html", phase=phase)

@ci.route('/times')
@ci.route('/times/<int:index>')
def phase_timing(index=None):
    cfg = current_app.config.summary.config

    # Determine what we are timing.
    if index is not None:
        # Validate the phase.
        if index >= len(cfg.phases):
            abort(404)

        # Get the phase.
        phase = cfg.phases[index]
    else:
        phase = None

    # Get the list of builders to time.
    builder_to_time = []
    if phase is None:
        builders_to_time = [p.phase_builder
                            for p in cfg.phases]
    else:
        builders_to_time = phase.builder_names

    # Get the builds to report timing information for.
    status = current_app.config.status
    builders = dict((name, [b for b in status.builders.get(name, [])
                            if b.end_time is not None])
                    for name in builders_to_time)

    # Return the timing data as a json object.
    data = []
    for i,(name,builds) in enumerate(util.sorted(builders.items())):
        color = list(util.make_dark_color(float(i) / len(builders)))
        hex_color = '%02x%02x%02x' % tuple(int(x*255)
                                           for x in color)
        points = [(float(i) / len(builds), b.end_time - b.start_time)
                  for i,b in enumerate(builds)]
        data.append((name, points, color, hex_color))
    return flask.jsonify(data = data)

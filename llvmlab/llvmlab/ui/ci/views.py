import flask
from flask import abort
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask import current_app
ci = flask.Module(__name__, url_prefix='/ci')

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

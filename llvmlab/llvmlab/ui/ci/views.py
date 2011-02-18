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
from llvmlab.ci import config

# Hard-coded current configuration.
#
# FIXME: Figure out how to get as much of this as possible dynamically. One
# problem is how do we deal with changes to the CI infrastructure? Should we
# load a config object per-revision, and try to be smart about caching it unless
# things change? Can we report results across changing configs?
phases = [
    config.Phase("Sanity", 1, "phase1 - sanity",
                 ["clang-x86_64-osx10-gcc42-RA"]),
    config.Phase("Living On", 2, "phase2 - living",
                 ["clang-x86_64-osx10-DA",
                  "clang-x86_64-osx10-RA",
                  "nightly_clang-x86_64-osx10-gcc42-RA"]),
    config.Phase("Tree Health", 3, "phase3 - tree health",
                 ["nightly_clang-x86_64-osx10-DA",
                  "nightly_clang-x86_64-osx10-RA",
                  "nightly_clang-x86_64-osx10-RA-O0",
                  "nightly_clang-x86_64-osx10-RA-Os",
                  "nightly_clang-x86_64-osx10-RA-O3",
                  "nightly_clang-x86_64-osx10-RA-flto",
                  "nightly_clang-x86_64-osx10-RA-g"]),
    config.Phase("Validation", 4, "phase4 - validation",
                 ["nightly_clang-i386-osx10-RA",
                  "gccTestSuite-clang-x86_64-osx10-RA",
                  "boost-trunk-clang-x86_64-osx10-RA"])]
builders = [
    config.Builder("Validated Build"),
    config.Builder("phase1 - sanity"),
    config.Builder("phase2 - living"),
    config.Builder("phase3 - tree health"),
    config.Builder("phase4 - validation"),
    config.Builder("clang-x86_64-osx10-gcc42-RA"),
    config.Builder("clang-x86_64-osx10-DA"),
    config.Builder("clang-x86_64-osx10-RA"),
    config.Builder("nightly_clang-x86_64-osx10-gcc42-RA"),
    config.Builder("nightly_clang-x86_64-osx10-DA"),
    config.Builder("nightly_clang-x86_64-osx10-RA"),
    config.Builder("nightly_clang-x86_64-osx10-RA-O0"),
    config.Builder("nightly_clang-x86_64-osx10-RA-Os"),
    config.Builder("nightly_clang-x86_64-osx10-RA-O3"),
    config.Builder("nightly_clang-x86_64-osx10-RA-flto"),
    config.Builder("nightly_clang-x86_64-osx10-RA-g"),
    config.Builder("gccTestSuite-clang-x86_64-osx10-RA"),
    config.Builder("boost-trunk-clang-x86_64-osx10-RA")]
published_builds = [
    config.PublishedBuild("LLVM", "Linux", "i386", "llvm-linux-i386.tgz"),
    config.PublishedBuild("LLVM", "Mac OS X (SnowLeopard)", "x86_64",
                          "llvm-darwin10-x86_64.tgz"),

    config.PublishedBuild("Clang", "Linux", "i386", "clang-linux-i386.tgz"),
    config.PublishedBuild("Clang", "Linux", "x86_64", "clang-linux-x86_64.tgz"),
    config.PublishedBuild("Clang", "Mac OS X (SnowLeopard)", "x86_64",
                          "clang-darwin10-x86_64.tgz"),
    config.PublishedBuild("Clang", "Windows", "i386", "clang-windows-i386.tgz"),

    config.PublishedBuild("llvm-gcc-4.2", "Linux", "i386",
                          "llvm-gcc-4.2-linux-i386.tgz"),
    config.PublishedBuild("llvm-gcc-4.2", "Linux", "x86_64",
                          "llvm-gcc-4.2-linux-x86_64.tgz")]
g_config = config.Config(phases, builders, published_builds,
                         'Validated Build')

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

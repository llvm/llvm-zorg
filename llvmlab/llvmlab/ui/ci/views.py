import flask
from flask import abort
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask import current_app
ci = flask.Module(__name__, url_prefix='/ci')

from llvmlab.ci import config

# Hard-coded current configuration.
#
# FIXME: Figure out how to get as much of this as possible dynamically. One
# problem is how do we deal with changes to the CI infrastructure? Should we
# load a config object per-revision, and try to be smart about caching it unless
# things change? Can we report results across changing configs?
phases = [
    config.Phase("Sanity", 1, []),
    config.Phase("Living On", 2, []),
    config.Phase("Tree Health", 3, []),
    config.Phase("Validation", 4, [])]
builders = []
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
                          "llvm-gcc-4.2-linux-x86_64.tgz"),
    ]
g_config = config.Config(phases, builders, published_builds)

@ci.route('/')
def dashboard():
    return render_template("dashboard.html", ci_config=g_config)


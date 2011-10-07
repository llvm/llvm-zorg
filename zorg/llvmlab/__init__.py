"""
lab.llvm.org site specific customizations for the LLVM Lab web app.
"""

import os
import sys

# Allow direct import of the master configuration files.
g_master_dir = os.path.join(os.path.dirname(__file__),
                            "..", "..", "buildbot", "llvmlab", "master")
if g_master_dir not in sys.path:
    sys.path.append(g_master_dir)
try:
    from config import phase_config
except:
    # FIXME: Remove this once actual phase_config object is in place.
    class DummyConfig:
        phases = []
    phase_config = DummyConfig()

import llvmlab.ci.config
import llvmlab.ci.summary

def construct_config():
    phases = []
    builders = []
    published_builds = []

    # Add hard coded builders.
    builders.append(llvmlab.ci.config.Builder("Validated Build"))

    for phase in phase_config.phases:
        # Add the phase object.
        phase_builder = "phase%d - %s" % (phase['number'], phase['name'])
        phases.append(llvmlab.ci.config.Phase(
                phase['title'], phase['number'], phase_builder,
                [b['name'] for b in phase['builders']],
                phase['description']))

        # Add the builder objects.
        builders.append(llvmlab.ci.config.Builder(phase_builder))
        for b in phase['builders']:
            builders.append(llvmlab.ci.config.Builder(b['name']))

    return llvmlab.ci.config.Config(phases, builders, published_builds,
                                    "Validated Build")

def register(app):
    # Construct the LLVM Lab dashboard configuration object directly from the
    # buildbot phase_config module.
    config = construct_config()
    app.config.summary = llvmlab.ci.summary.Summary(
        config, app.config.status)

    print >>sys.stderr, "note: loaded lab.llvm.org extensions"

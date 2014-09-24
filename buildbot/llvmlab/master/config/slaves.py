import buildbot
import buildbot.buildslave
import os
import config

from zorg.buildbot.util.phasedbuilderutils import set_config_option

def create_slave(name, jobs, max_builds = None):
    if max_builds is None:
        max_builds = jobs // 2
    return buildbot.buildslave.BuildSlave(
        name, password = 'password',
        notify_on_missing = set_config_option('Master Options',
                                               'default_email',
                                               'david_dean@apple.com'),
        properties = { 'jobs' : jobs },
        max_builds = max_builds)

def get_build_slaves():
    # Phase runnner.
    yield create_slave('macpro1', jobs = 1, max_builds = 8)

    # Builders.
    yield create_slave('xserve3', jobs = 2, max_builds = 1)
    yield create_slave('xserve4', jobs = 4, max_builds = 1)
    yield create_slave('xserve5', jobs = 4, max_builds = 1)

    is_production = config.options.has_option('Master Options', 'is_production')
    if not is_production:
        # Test slave which can do anything.
        yield create_slave('localhost', 8)

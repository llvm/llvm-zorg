import buildbot
import buildbot.buildslave
import os

def create_slave(name, *args, **kwargs):
    return buildbot.buildslave.BuildSlave(name, password='password',
                                          *args, **kwargs)

def get_build_slaves():
    yield create_slave("llvmlab.local",
                       notify_on_missing="david_dean@apple.com",
                       properties = { 'jobs' : 16 },
                       max_builds = 16)
    yield create_slave("lab-mini-01.local",
                       notify_on_missing="david_dean@apple.com",
                       properties = { 'jobs' : 2 },
                       max_builds = 2)
    yield create_slave("lab-mini-02.local",
                       notify_on_missing="david_dean@apple.com",
                       properties = { 'jobs' : 2 },
                       max_builds = 2)
    yield create_slave("lab-mini-03.local",
                       notify_on_missing="david_dean@apple.com",
                       properties = { 'jobs' : 2 },
                       max_builds = 2)
    yield create_slave("lab-mini-04.local",
                       notify_on_missing="david_dean@apple.com",
                       properties = { 'jobs' : 2 },
                       max_builds = 2)

# -*- Python -*-

from twisted.application import service
from buildbot.slave.bot import BuildSlave
import os, sys

basedir = os.path.dirname(os.path.abspath(__file__))

# Allow finding klee module.
sys.path.append(os.path.join(basedir, "../.."))

# Import klee to get configuration info.
import klee

buildmaster_host = klee.Config.getBuildmasterHost()
port = klee.Config.getBuildmasterPort()
slavename = klee.Config.getBuildslaveName()
passwd = klee.Config.getBuildslavePassword()
keepalive = 600
usepty = 1
umask = None

application = service.Application('buildslave')
s = BuildSlave(buildmaster_host, port, slavename, passwd, basedir,
               keepalive, usepty, umask=umask)
s.setServiceParent(application)

# -*- Python -*-

from twisted.application import service
from buildbot.slave.bot import BuildSlave
import os, sys

basedir = os.path.dirname(os.path.abspath(__file__))

# Allow finding smooshlab module.
sys.path.append(os.path.join(basedir,
                             "../.."))

# Import smooshlab to get configuration info.
import smooshlab

buildmaster_host = smooshlab.Config.getBuildmasterHost()
port = smooshlab.Config.getBuildmasterPort()
slavename = smooshlab.Config.getBuildslaveName()
passwd = smooshlab.Config.getBuildslavePassword()
keepalive = 600
usepty = 1
umask = None

application = service.Application('buildslave')
s = BuildSlave(buildmaster_host, port, slavename, passwd, basedir,
               keepalive, usepty, umask=umask)
s.setServiceParent(application)

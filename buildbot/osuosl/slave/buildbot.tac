# -*- Python -*-

from twisted.application import service
from buildbot.slave.bot import BuildSlave
import os, sys

basedir = os.path.dirname(os.path.abspath(__file__))

# Allow finding osuosl module.
sys.path.append(os.path.join(basedir,
                             "../.."))

# Import osuosl to get configuration info.
import osuosl

buildmaster_host = osuosl.Config.getBuildmasterHost()
port = osuosl.Config.getBuildmasterPort()
slavename = osuosl.Config.getBuildslaveName()
passwd = osuosl.Config.getBuildslavePassword()
keepalive = 600
usepty = 1
umask = None

application = service.Application('buildslave')
s = BuildSlave(buildmaster_host, port, slavename, passwd, basedir,
               keepalive, usepty, umask=umask)
s.setServiceParent(application)

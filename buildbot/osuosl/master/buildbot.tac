from twisted.application import service
from buildbot.master import BuildMaster
import os

basedir = os.path.dirname(os.path.abspath(__file__))
rotateLength = 10000000 # 10 MiB
maxRotatedFiles = 20
configfile = r'master.cfg'

application = service.Application('buildmaster')

try:
  from twisted.python.logfile import LogFile
  from twisted.python.log import ILogObserver, FileLogObserver
  logfile = LogFile.fromFullPath(os.path.join(basedir, "twistd.log"),
                                 rotateLength=rotateLength, maxRotatedFiles=maxRotatedFiles)
  application.setComponent(ILogObserver, FileLogObserver(logfile).emit)
except ImportError:
  # probably not yet twisted 8.2.0 and beyond, can't set log yet
  pass

m = BuildMaster(basedir, configfile)
m.setServiceParent(application)
m.log_rotation.rotateLength = rotateLength
m.log_rotation.maxRotatedFiles = maxRotatedFiles

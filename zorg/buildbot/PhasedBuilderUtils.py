import buildbot
from buildbot.steps.shell import WithProperties
from buildbot.steps.trigger import Trigger
import config
import StringIO

class NamedTrigger(Trigger):
    """Trigger subclass which allows overriding the trigger name, and also
    allows attaching a log to link to the triggered builds."""
    def __init__(self, name, triggeredBuilders = [], **kwargs):
        Trigger.__init__(self, **kwargs)
        self.name = name
        self.triggeredBuilders = triggeredBuilders
        self.addFactoryArguments(name = name,
                                 triggeredBuilders = triggeredBuilders)
    def start(self):
        # Add a log linking to the triggered builders, if supplied.
        if self.triggeredBuilders:
            logText = StringIO.StringIO()
            for builder in self.triggeredBuilders:
                print >>logText, ('<b><a href="../../../../../../%s">%s'
                                  '</a></b><br>' % (builder, builder))
            self.addHTMLLog('triggered builds', str(logText.getvalue()))
        # Dispatch to the super class.
        Trigger.start(self)

def setProperty(f, new_property, new_value):
    f.addStep(buildbot.steps.shell.SetProperty(name = 'set.' + new_property,
                                               command=['echo', new_value],
                                               property=new_property,
                                               description=['set property',
                                                            new_property],
                                               workdir='.'))
    return f

def getBuildDir(f):
    f.addStep(buildbot.steps.shell.SetProperty(name='get.build.dir',
                                               command=['pwd'],
                                               property='builddir',
                                               description='set build dir',
                                               workdir='.'))
    return f

def getUserDir(f):
    f.addStep(buildbot.steps.shell.SetProperty(command=['sh', '-c', 'cd ~;pwd'],
                                               haltOnFailure=True,
                                               property='user_dir',
                                               description=['set property',
                                                            'user_dir']))

def GetLatestValidated(f):
    master_name = config.options.get('Master Options', 'master_name')
    download_url = 'http://%s/artifacts' % master_name
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='rm.host-compiler',
            command=['rm', '-rfv', 'host-compiler', 'host-compiler.tar.gz'],
            haltOnFailure=False, description=['rm', 'host-compiler'],
            workdir=WithProperties('%(builddir)s')))
    latest_url = download_url
    latest_url += '/latest_validated/apple-clang-x86_64-darwin10-R.tar.gz'
    f.addStep(buildbot.steps.shell.ShellCommand(
              name='download.artifacts',
              command=['curl', '-svo', 'host-compiler.tar.gz', latest_url],
              haltOnFailure=True, description=['download build artifacts'],
              workdir=WithProperties('%(builddir)s')))
    f.addStep(buildbot.steps.shell.ShellCommand(
              name='unzip', command=['tar', '-zxvf','../host-compiler.tar.gz'],
              haltOnFailure=True, description=['extract', 'host-compiler'],
              workdir='host-compiler'))
    return f

def find_cc(status, stdin, stdout):
    lines = filter(bool, stdin.split('\n'))
    for line in lines:
        if 'bin/clang' in line:
            cc_path = line
            return { 'cc_path' : cc_path }
    return {}

def find_cxx(status, stdin, stdout):
    lines = filter(bool, stdin.split('\n'))
    for line in lines:
        if 'bin/clang++' in line:
            cxx_path = line
            return { 'cxx_path' : cxx_path }
    return {}


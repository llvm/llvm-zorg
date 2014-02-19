import buildbot
import json
import os 
import StringIO

from buildbot.steps.master import MasterShellCommand
from buildbot.steps.shell import SetProperty
from buildbot.steps.shell import WithProperties
from buildbot.steps.trigger import Trigger
from datetime import datetime, date, time

import zorg

import config

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

def _project_from_name(buildname):
    name = buildname.replace('llvm-gcc', 'llvm$gcc')\
                    .replace('apple-clang', 'apple$clang')
    params = name.split('-')
    project = params[0].replace('$', '-')
    return project

def _determine_remote_file(props):
    return os.path.join(os.getcwd(),props['scheduler'] + '_changes.txt')

def _load_changelist(props):
    changelist = []
    try:
        for line in open(_determine_remote_file(props)).readlines():
            change = json.loads(line)
            change['category'] = props['next_phase']
            if not change in changelist:
                changelist.append(change)
    except IOError:
        pass
    return json.dumps(changelist)

def _extract_changelist(status, stdin, stdout):
    newProps = {}
    changelist = []
    if status:
        return {'changes' : changelist, 'status' : status}
    buildprops = json.loads(stdin)
    props = buildprops['properties']
    ss = buildprops['sourcestamp']
    changes = ss['changes']
    changelist = json.loads(_load_changelist(props))
    for change in changes:
        newchange={}
        newchange['revision'] = change['revision']
        if change.has_key('who'):
            newchange['author'] = change['who']
        else:
            newchange['author'] = change['author']
        changefiles = change['files']
        files = []
        for file in changefiles:
             files.append(file['name'])
        newchange['files'] = files
        newchange['comments'] = change['comments']
        # FIXME: not correct
        # newchange['url'] = change['repository']
        newchange['branch'] = change['branch']
        newchange['link'] = change['revlink']
        newchange['timestamp'] = change['when']
        newchange['properties'] = {'phase_id' : props['phase_id']}
        with open(_determine_remote_file(props), 'a+') as myfile:
            myfile.write(json.dumps(newchange)+'\n')
        if not newchange in changelist:
            changelist.append(newchange)
    changelist = sorted(changelist, key=lambda k: k['timestamp'])
    newProps['changes'] = changelist
    newProps['old_changes'] = changes
    return newProps

def setProperty(f, new_property, new_value):
    f.addStep(SetProperty(name = 'set.' + new_property,
                          command=['echo', new_value],
                          property=new_property,
                          description=['set property', new_property],
                          workdir='.'))
    return f

def getBuildDir(f):
    f.addStep(SetProperty(name='get.build.dir',
                          command=['pwd'],
                          property='builddir',
                          description='set build dir',
                          workdir='.'))
    return f

def getUserDir(f):
    f.addStep(SetProperty(command=['sh', '-c', 'cd ~;pwd'],
                          haltOnFailure=True,
                          property='user_dir',
                          description=['set property', 'user_dir'],
                          workdir='.'))
    return f

def GetLatestValidated(f):
    import zorg.buildbot.util.artifacts as artifacts

    f.addStep(buildbot.steps.shell.ShellCommand(
            name='rm.host-compiler',
            command=['rm', '-rfv', 'host-compiler', 'host-compiler.tar.gz'],
            haltOnFailure=False, description=['rm', 'host-compiler'],
            workdir=WithProperties('%(builddir)s')))
    latest_url = artifacts.base_download_url
    latest_url += '/validated_builds/clang-x86_64-darwin11-R.tar.gz'
    f.addStep(buildbot.steps.shell.ShellCommand(
              name='download.artifacts',
              command=['curl', '-fvLo', 'host-compiler.tar.gz', latest_url],
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

def find_liblto(status, stdin, stdout):
    lines = filter(bool, stdin.split('\n'))
    for line in lines:
        if 'lib/libLTO.dylib' in line:
            liblto_path = os.path.dirname(line)
            return { 'liblto_path' : liblto_path }
    return {}

def determine_phase_id(props):
    # phase_id should be generated by the first phase to run and copied as a
    # propery to downstream builds
    if props.has_key('phase_id'):
        return props['phase_id']
    else:
        timestamp = datetime.now()
        timestamp = timestamp.strftime('%Y%m%d_%H%M%S')
        phase_id = 'r' + str(props['revision'])
        phase_id += '-t' + timestamp
        phase_id += '-b' + str(props['buildnumber'])
        return phase_id

def getPhaseBuilderFactory(config, phase, next_phase, stages):
    from buildbot.steps.transfer import JSONPropertiesDownload
    # Create the build factory.
    f = buildbot.process.factory.BuildFactory()
    f.addStep(buildbot.steps.shell.ShellCommand(
              command=['echo', WithProperties('%(phase_id:-)s')]))
    # constuct a new phase_id if phase_id is not already set
    phaseid = WithProperties('%(get_phase_id)s',
                             get_phase_id = determine_phase_id)
    setProperty(f, 'phase_id', phaseid)
    setProperty(f, 'next_phase', next_phase)
    f.addStep(JSONPropertiesDownload(slavedest='build-properties.json'))
    f.addStep(buildbot.steps.shell.SetProperty(
                name = 'get.build.properties',
                command = ['cat', 'build-properties.json'],
                extract_fn = _extract_changelist))
    # Buildbot uses got_revision instead of revision to identify builds.
    # We set it below so that the revision shows up in the html status pages.
    setProperty(f, 'got_revision', WithProperties('%(revision)s'))
    # this generates URLs we can use to link back to the builder which
    # triggered downstream builds
    master_url = set_config_option('Master Options', 'master_url',
                                   'http://localhost')
    this_str = '/'.join([master_url, 'builders', '%(buildername)s', 'builds',
                        '%(buildnumber)s'])
    setProperty(f, 'trigger', WithProperties(this_str))
    # Properties we always copy...
    copy_properties = [ 'phase_id', 'revision', 'got_revision', 'trigger' ]
    # Add the trigger for the next phase.
    changes = WithProperties('%(forward_changes)s',
                             forward_changes = _load_changelist)
    # Add the triggers for each stage...
    for i, (normal, experimental) in enumerate(stages):
        # Add the experimental trigger, if used, but don't wait or fail for it.
        if experimental:
            scheduler = 'phase%d-stage%d-experimental' % (phase['number'], i)
            f.addStep(Trigger(name = 'trigger.%s' % scheduler,
                                   schedulerNames = [scheduler],
                                   waitForFinish = False,
                                   updateSourceStamp = False,
                                   set_properties = {
                                      'triggeredBuilders' : [b['name']
                                                             for b in normal],
                                   },
                                   copy_properties = copy_properties))
        # Add the normal build trigger, if used.
        if normal:
            scheduler = 'phase%d-stage%d' % (phase['number'], i)
            f.addStep(Trigger(name = 'trigger.%s' % scheduler,
                                   schedulerNames = [scheduler],
                                   waitForFinish = True, haltOnFailure = True,
                                   updateSourceStamp = False,
                                   set_properties = {
                                      'triggeredBuilders' : [b['name']
                                                             for b in normal],
                                   },
                                   copy_properties = copy_properties))
    f.addStep(MasterShellCommand(
        name='trigger.next_phase', haltOnFailure = True,
        command = ['./process_changelist.py', next_phase,
                   WithProperties('%(scheduler)s_changes.txt')],
        description = ['Trigger', next_phase],
        descriptionDone = ['Trigger', next_phase]))
    # We have successfully sent the changes to the next phase, so it is  now
    # safe to erase the file and 'forget' the changes passed to this phase to
    # date.
    f.addStep(MasterShellCommand(
        name='clear.changelist', haltOnFailure = True,
        command = ['rm', '-fv', WithProperties('%(scheduler)s_changes.txt')],
        description = ['Clear changelist'],
        descriptionDone = ['Clear changelist']))
    return f

def set_config_option(section, option, default=False):
    import warnings
    if config.options.has_option(section, option):
        return config.options.get(section, option)
    else:
        warn_str = 'Please add the "%s" option to the ' % option
        warn_str += '"%s" section of your local.cfg file' % section
        warnings.warn(warn_str) 
        return default

def PublishGoodBuild(f=None, validated_build_dir='validated_builds',
                     publish_only_latest=False):
    import config.phase_config
    reload(config.phase_config)
    
    artifacts_dir = set_config_option('Master Options', 'artifacts_path',
                                      os.path.expanduser('~/artifacts/'))

    # TODO: Add steps to prepare a release and announce a good build.
    
    if f is None:
        f = buildbot.process.factory.BuildFactory()
        # Buildbot uses got_revision instead of revision to identify builds.
        # We set it below so that the revision shows up in the html status pages.
        setProperty(f, 'got_revision', WithProperties('%(revision)s'))

    f.addStep(MasterShellCommand(
            name='create.dir.validated_build_dir',
            command = ['mkdir', '-p',
                       os.path.join(artifacts_dir, validated_build_dir)],
            haltOnFailure = True,
            description = ['create', validated_build_dir, 'dir']))


    for phase in config.phase_config.phases:
        for build in phase['builders']:
            buildname = build['name']
            project = _project_from_name(buildname)
            if project in ('clang', 'llvm-gcc', 'apple-clang'):
                file_str = project + '-%(get_phase_id)s.tar.gz'
                link_str = os.path.join(artifacts_dir, buildname,
                                        file_str)
                build_artifacts_dir = os.path.join(artifacts_dir, validated_build_dir,
                                                   buildname)

                f.addStep(MasterShellCommand(
                    name='Publish.Latest.' + buildname,
                    haltOnFailure=True,
                    command=['cp', '-v',
                             WithProperties(link_str,
                                            get_phase_id=determine_phase_id),
                             os.path.join(artifacts_dir, validated_build_dir,
                                          "%s.tar.gz" % buildname)],
                    description=['publish', buildname, 'as latest']))

                if not publish_only_latest:
                    f.addStep(MasterShellCommand(
                            name='create.dir.%s' % buildname,
                            command = ['mkdir', '-p',
                                       build_artifacts_dir],
                            haltOnFailure = True,
                            description = ['create', 'validated', 'dir', 'for',
                                           buildname]))

                    artifacts_str = os.path.join(artifacts_dir, validated_build_dir,
                                                 buildname, file_str)                

                    f.addStep(MasterShellCommand(
                        name='Publish.'+ buildname, haltOnFailure = True,
                        command = ['cp', '-v',
                                   WithProperties(link_str,
                                                  get_phase_id=determine_phase_id),
                                   WithProperties(artifacts_str,
                                                  get_phase_id=determine_phase_id)],
                        description = ['publish', buildname]))
    return f


def SVNCleanupStep(f, name):
  f.addStep(buildbot.steps.shell.ShellCommand(
      name='svn.cleanup.%s' % name,
      command=['svn', 'cleanup'],
      haltOnFailure=False, flunkOnFailure=False,
      description='svn cleanup %s just in case' % name,
      workdir=name))
  return f


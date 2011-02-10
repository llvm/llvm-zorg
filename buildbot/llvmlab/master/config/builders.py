import buildbot
import buildbot.process.factory
from buildbot.steps.shell import WithProperties
from buildbot.steps.trigger import Trigger
from buildbot.schedulers import basic, timed, triggerable
from buildbot.steps import source

def setProperty(f, new_property, new_value):
    f.addStep(buildbot.steps.shell.SetProperty(command=['echo', new_value],
                                               property=new_property,
                                               description=['set property', new_property]))
    return f

# This serves as a generic method to pull different repositories.
def pullsrc(f, repo_name, URL, dir, pull_mode='clobber', def_branch='trunk', UseLatest=False):
    f.addStep(source.SVN(name='pull.' + repo_name,
                         mode=pull_mode,
                         baseURL=URL,
                         defaultBranch=def_branch, workdir=dir, always_purge=True,
                         alwaysUseLatest=UseLatest))
    return f

def pullClang(f):
   pullsrc(f, 'clang', 'http://llvm.org/svn/llvm-project/cfe/', 'llvm/tools/clang')
   return f

def pullllvm(f):
   pullsrc(f, 'llvm', 'http://llvm.org/svn/llvm-project/llvm/', 'llvm')
   return f

def pulltest_suite(f):
   pullsrc(f, 'llvm tests', 'http://llvm.org/svn/llvm-project/test-suite/', 'test-suite', 
           'clobber', 'trunk', 'True')
   return f

def pullclang_tests(f):
   pullsrc(f, 'clang tests', 'http://llvm.org/svn/llvm-project/clang-tests/', 'test-suite')
   return f

def pullboostrunner(f):
    pullsrc(f, 'boost.runner', 'http://svn.boost.org/svn/boost/%%BRANCH%%/tools/regression/src/', 
            'boost_runner', 'clobber', 'trunk', 'True')
    return f

def getBuildDir(f):
    f.addStep(buildbot.steps.shell.SetProperty(name='get.build.dir',
                                               command=['pwd'],
                                               property='builddir',
                                               description='set build dir',
                                               workdir='.'))
    return f

def GetCompilerArtifacts(f):
    # The 'revision' property is always defined, so it is safer to use.
    # That being said, it has not yet been set to a valid number for phase 1 builds.
    # You must use 'got_build' to determine which revision was actually pulled.
    if WithProperties('%(revision)s')=='None':
         src_file = WithProperties('buildmaster@llvmlab.local:~/artifacts/%(use_builder)s/' +
                                    'clang-r%(got_revision)s-*.tar.gz')
    else:
         src_file = WithProperties('buildmaster@llvmlab.local:~/artifacts/%(use_builder)s/' +
                                    'clang-r%(revision)s-*.tar.gz')
    slavedest=WithProperties('%(builddir)s/clang-host.tar.gz')
    f.addStep(buildbot.steps.shell.ShellCommand(
              name='download.artifacts',
              command=['rsync', '-ave', 'ssh', src_file, slavedest],
              haltOnFailure=True,
              description=['download build artifacts'],
              workdir=WithProperties('%(builddir)s')))
    f.addStep(buildbot.steps.shell.ShellCommand(
              name='unzip',
              command=['tar', '-zxvf','../clang-host.tar.gz'],
              haltOnFailure=True,
              description=['extract', 'clang-host'],
              workdir='clang-host'))
    return f

def cleanCompilerDir(f):
    f.addStep(buildbot.steps.shell.ShellCommand(
            command=['rm', '-rfv', 'clang-install'],
            haltOnFailure=False,
            description=['rm dir', 'clang-install'],
            workdir=WithProperties('%(builddir)s')))
    f.addStep(buildbot.steps.shell.ShellCommand(
            command=['rm', '-rfv', 'clang-host'],
            haltOnFailure=False,
            description=['rm dir', 'clang-host'],
            workdir=WithProperties('%(builddir)s')))
    f.addStep(buildbot.steps.shell.ShellCommand(
            command=['sh', '-c', 'rm -rfv clang*.tar.gz'],
            haltOnFailure=False,
            description=['rm archives'],
            workdir=WithProperties('%(builddir)s')))
    f.addStep(buildbot.steps.shell.ShellCommand(
            command=['rm', '-rfv', WithProperties('%(compiler_built:-)s')],
            haltOnFailure=False,
            description=['rm dir', WithProperties('%(compiler_built:-)s')],
            workdir=WithProperties('%(builddir)s')))
    return f

def uploadArtifacts(f):
    f.addStep(buildbot.steps.shell.ShellCommand(
              name='tar.and.zip',
              command=['tar', 'czvf', 
                       WithProperties('../clang-r%(got_revision)s-b%(buildnumber)s.tar.gz'),
                       './'],
              haltOnFailure=True,
              description=['tar', '&', 'zip'],
              workdir='clang-install'))
    archive_src = WithProperties('%(builddir)s/clang-r%(got_revision)s-b%(buildnumber)s.tar.gz')
    archive_dest = WithProperties('buildmaster@llvmlab.local:~/artifacts/%(buildername)s')
    f.addStep(buildbot.steps.shell.ShellCommand(
              name='upload.artifacts',
              command=['rsync', '-ave', 'ssh', archive_src, archive_dest],
              haltOnFailure=True,
              description=['upload build artifacts'],
              workdir=WithProperties('%(builddir)s')))
    artifactsURL = WithProperties('http://smooshlab.apple.com/artifacts/%(buildername)s' +
                                  '/clang-r%(got_revision)s-b%(buildnumber)s.tar.gz')
    setProperty(f, 'artifactsURL', artifactsURL)
    return f

def regressionTests(f):
    f.addStep(buildbot.steps.shell.ShellCommand(
        name='run.llvm.tests',
        command=['make', '-j', WithProperties('%(jobs)s')],
         haltOnFailure=True,
         description=['llvm', 'tests'],
         env={'PATH': 
              WithProperties('%(builddir)s/%(compiler_built)s/%(compiler_type)s/bin:${PATH}')},
         workdir=WithProperties('%(compiler_built)s/test')))
    f.addStep(buildbot.steps.shell.ShellCommand(
        name='run.clang.tests',
        command=['make', '-j', WithProperties('%(jobs)s')],
         haltOnFailure=True,
         description=['clang', 'tests'],
         env={'PATH': 
              WithProperties('%(builddir)s/%(compiler_built)s/%(compiler_type)s/bin:${PATH}')},
         workdir=WithProperties('%(compiler_built)s/tools/clang/test')))
    return f


def createPhase1():
    # Create an instance of the Builder.
    f = buildbot.process.factory.BuildFactory()
    f = clangStage1(f)
    # Save artifacts of thids build for use by other builders.
    f = uploadArtifacts(f)
    f = regressionTests(f)
    return f
    

def clangStage1(f, config_options=''):
    # Determine the build directory.
    f = getBuildDir(f)
    # Clean out the directories/archives used to ensure a clean build.
    f = cleanCompilerDir(f)
    # Pull sources.
    f = pullllvm(f)
    f = pullClang(f)
    # Configure to use built-in compiler.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='configure',
            command=[
                     '../llvm/configure', '--enable-optimized', '--disable-bindings',
                     '--with-llvmcc=clang', '--without-llvmgcc', '--without-llvmgxx',
                     WithProperties('--prefix=/')],
            haltOnFailure=True,
            description=['configure'],
            workdir=WithProperties('%(compiler_built)s')))
    # Build clang.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='make',
            command=['make', '-j', WithProperties('%(jobs)s')],
            haltOnFailure=True,
            description=['make'],
            workdir=WithProperties('%(compiler_built)s')))
    # Use make inatall-clang to produce minimal archive for use by downstream builders.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='make.install-clang',
            command=['make', 'install-clang', '-j', WithProperties('%(jobs)s'),
                     WithProperties('DESTDIR=%(builddir)s/clang-install')],
            haltOnFailure=True,
            description=['make install'],
            workdir=WithProperties('%(compiler_built)s')))
    return f

def clangHost(config_options):
    # Create an instance of the Builder.
    f = buildbot.process.factory.BuildFactory()
    # Determine the build directory.
    f = getBuildDir(f)
    f = setProperty(f, 'use_path', WithProperties('%(builddir)s/clang-host/bin'))
    # Clean out the directories/archives used to ensure a clean build.
    f = cleanCompilerDir(f)
    # Pull sources.
    f = pullllvm(f)
    f = pullClang(f)
    # Download artifacts from phase 1 compiler build.
    f = GetCompilerArtifacts(f)
    if config_options == ():
       config_options = []
    else:
       config_options = list(config_options)
    # Configure to use artifacts from upstream builder.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='configure.with.host',
            command=[
                     '../llvm/configure'] + config_options + ['--disable-bindings',
                     '--with-llvmcc=clang', '--without-llvmgcc', '--without-llvmgxx',
                     WithProperties('CC=%(use_path)s/clang'),
                     WithProperties('CXX=%(use_path)s/clang++'),
                     WithProperties('--prefix=/')],
            haltOnFailure=True,
            description=['configure'],
            env={'PATH': WithProperties('%(use_path)s:${PATH}')},
            workdir=WithProperties('%(compiler_built)s')))
    # Build clang using clang.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='stage.2.make',
            command=['make', '-j', WithProperties('%(jobs)s')],
            haltOnFailure=True,
            description=['make'],
            env={'PATH': WithProperties('%(use_path)s:${PATH}')},
            workdir=WithProperties('%(compiler_built)s')))
    # Use make inatall-clang to produce minimal archive for use by downstream builders.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='make.install-clang',
            command=['make', 'install-clang', '-j', WithProperties('%(jobs)s'),
                     WithProperties('DESTDIR=%(builddir)s/clang-install')],
            env={'PATH': WithProperties('%(use_path)s:${PATH}')},
            haltOnFailure=True,
            description=['make install'],
            workdir=WithProperties('%(compiler_built)s')))
    # Save artifacts of thids build for use by other builders.
    f = uploadArtifacts(f)
    f = regressionTests(f)
    return f

def getGatedFactory(buildphase, next):
    f = buildbot.process.factory.BuildFactory()
    f.addStep(Trigger(schedulerNames=[buildphase],
                       waitForFinish=True,
                       haltOnFailure=True,
                       updateSourceStamp=True,
                       set_properties={'revision': WithProperties('%(revision)s'), 
                                       'got_revision': WithProperties('%(revision)s')}))
    f.addStep(Trigger(schedulerNames=[next],
                       waitForFinish=False,
                       updateSourceStamp=True,
                       set_properties={'revision': WithProperties('%(revision)s'), 
                                       'got_revision': WithProperties('%(revision)s')}))
    return f

def PublishGoodBuild():
    f = buildbot.process.factory.BuildFactory()
    # TODO: Add steps to prepare a release and announce a good build.
    return f

def Placeholder():
    f = buildbot.process.factory.BuildFactory()
    return f

def makePhaseBuilder(bldname, trigger1, trigger2, bldslaves):
    return { 'name' : bldname,
             'factory' : getGatedFactory(trigger1, trigger2),
             'slavenames' : bldslaves ,
             'category' : 'status'}

def HostedClang(myname, compiler_type, use_compiler, slaves, *config_options):
    return { 'name' : myname,
             'builddir' : 'build.'+myname,
             'factory' : clangHost(config_options),
             'slavenames' : slaves,
             'category' : 'clang',
             'properties' : {'compiler_type': compiler_type, 
                             'use_builder': use_compiler,
                             'compiler_built': 'clang-build'}}

def CreateNightly(options):
    f = buildbot.process.factory.BuildFactory()
    NightlyFactory(f, options)
    return f

from zorg.buildbot.commands.NightlyTestCommand import NightlyTestCommand
def NightlyFactory(f, options, clean=True, test=True, xfails=set()):
    # Determine the build directory.
    f = getBuildDir(f)
    f = setProperty(f, 'use_path', WithProperties('%(builddir)s/clang-host/bin'))
    # Clean out the directories/archives used to ensure a clean build.
    f = cleanCompilerDir(f) 
    # Download compiler artifacts to be used for this build.
    f = GetCompilerArtifacts(f)
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='sanity.test',
            command=[WithProperties('%(use_path)s/clang'),
                     '--version'],
             haltOnFailure=True,
             description=['sanity test'],
             env={'PATH': WithProperties('%(use_path)s:${PATH}')}))
    # Pull source code.
    f = pulltest_suite(f)
    # Clean up.
    if clean:
        f.addStep(buildbot.steps.shell.ShellCommand(
                               name="rm.test-suite",
                               command=["rm", "-rfv", "test-suite-build"],
                               haltOnFailure=True,
                               description="rm test-suite build dir",
                               workdir=WithProperties('%(builddir)s')))
    # Configure tests to use clang from upstream build.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='configure.tests',
            command=['../test-suite/configure',
                     WithProperties('CC=%(use_path)s/clang'),
                     WithProperties('CXX=%(use_path)s/clang++'),
                     'CFLAGS='+options,
                     'CXXFLAGS='+options,
                     '--without-llvmsrc', '--without-llvmobj'],
            haltOnFailure=True,
            description=['configure tests'],
            env={'PATH': WithProperties('%(use_path)s:${PATH}')},
            workdir='test-suite-build'))
    # You need to make the tools target.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='make.tools',
            command=['make', 'tools', WithProperties('-j%(jobs)s')],
            env={'PATH': WithProperties('%(use_path)s:${PATH}')},
            haltOnFailure=True,
            description=['Make', 'tools'],
            workdir='test-suite-build'))
    # Build and test.
    f.addStep(NightlyTestCommand(
            name='run.fast.nightly.tests',
            command=['make', WithProperties('-j%(jobs)s'), 'ENABLE_PARALLEL_REPORT=1',
                     'DISABLE_CBE=1', 'DISABLE_JIT=1', 'TEST=simple', 'report'],
            env={'PATH': WithProperties('%(use_path)s:${PATH}')},
            haltOnFailure=True,
            description=['run', 'test-suite'],
            workdir='test-suite-build',
            logfiles={ 'report' : 'report.nightly.txt'},
            xfails=xfails))
    return f

def Nightly(compiler, slaves, options=''):
    return { 'name' : 'nightly_'+ compiler + options,
             'builddir' : 'build.nightly.'+ compiler + options,
             'factory' : CreateNightly(options),
             'slavenames' : slaves,
             'category' : 'tests',
             'properties' : {'use_builder': compiler}}

def stage1Clang(compiler, compiler_type, slave):
    return { 'name' : compiler,
             'builddir' : 'build.'+ compiler,
             'factory' : createPhase1(),
             'slavename' : slave,
             'category' : 'clang',
             'properties' : {'compiler_type': compiler_type,
                             'compiler_built': 'clang-build'}}

def HostStage3Clang(config_options):
    # Create instance of Builder.
    f = buildbot.process.factory.BuildFactory()
    # Determine the build directory.
    f = getBuildDir(f)
    f = setProperty(f, 'use_path', WithProperties('%(builddir)s/clang-host/bin'))
    # Clean out the directories/archives used to ensure a clean build.
    f = cleanCompilerDir(f)
    # Pull sources.
    f = pullllvm(f)
    f = pullClang(f)
    # Download artifacts from upstream builder.
    f = GetCompilerArtifacts(f)
    # Configure to use compiler from upstream builder.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='configure.with.host',
            command=[
                     '../llvm/configure', '--enable-optimized', '--disable-bindings',
                     '--with-llvmcc=clang', '--without-llvmgcc', '--without-llvmgxx',
                     config_options,
                     WithProperties('CC=%(use_path)s/clang'),
                     WithProperties('CXX=%(use_path)s/clang++'),
                     WithProperties('--prefix=/')],
            haltOnFailure=True,
            description=['configure'],
            env={'PATH': WithProperties('%(use_path)s:${PATH}')},
            workdir=WithProperties('%(compiler_built)s')))
    # Build clang using clang.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='stage.3.make',
            command=['make', '-j', WithProperties('%(jobs)s')],
            haltOnFailure=True,
            description=['make'],
            env={'PATH': WithProperties('%(use_path)s:${PATH}')},
            workdir=WithProperties('%(compiler_built)s')))
    # Use make inatall-clang to produce minimal archive for use by downstream builders.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='make.install-clang',
            command=['make', 'install-clang', '-j', WithProperties('%(jobs)s'),
                     WithProperties('DESTDIR=%(builddir)s/clang-install')],
            env={'PATH': WithProperties('%(use_path)s:${PATH}')},
            haltOnFailure=True,
            description=['make install'],
            workdir=WithProperties('%(compiler_built)s')))
    # Save artifacts of thids build for use by downstream builders.
    f = uploadArtifacts(f)
    f = regressionTests(f)
    NightlyFactory(f, '')
    return f

def stage3Clang(use_compiler, slaves, config_options=''):
    return { 'name' : use_compiler + '-stage3',
             'builddir' : 'build.'+ use_compiler + '-stage3',
             'factory' : HostStage3Clang(config_options),
             'slavenames' : slaves,
             'category' : 'clang',
             'properties' : {'use_builder': use_compiler,
                             'compiler_type': 'Release+Asserts',
                             'compiler_built': 'clang-build'}}

def gccTestSuite(use_compiler, slaves, config_options=''):
    return { 'name' : 'gccTestSuite-'+ use_compiler,
             'builddir' : 'build.'+ 'gccTestSuite-'+ use_compiler,
             'factory' : gccRunSuite(config_options),
             'slavenames' : slaves,
             'category' : 'clang',
             'properties' : { 'use_builder': use_compiler}}

def boost(tag, use_compiler, slaves, config_options=''):
    return { 'name' : 'boost-' + tag + '-' + use_compiler,
             'builddir' : 'build.'+ 'boost-' + tag + '-' + use_compiler,
             'factory' : runboost(config_options),
             'slavenames' : slaves,
             'category' : 'clang',
             'properties' : {'use_builder': use_compiler,
                             'boost_tag': tag}}

def gccRunSuite(config_options):
    f = buildbot.process.factory.BuildFactory()
    # Determine the build directory.
    getBuildDir(f)
    setProperty(f, 'use_path', WithProperties('%(builddir)s/clang-host/bin'))
    cleanCompilerDir(f)
    # Pull test-suite.
    pullclang_tests(f)
    # Download compiler from upstream builder.
    GetCompilerArtifacts(f)
    # Run gcc test suite.
    # TODO: This step returns as a failure because it does not handle expected failures.
#     f.addStep(buildbot.steps.shell.ShellCommand(
#             name='make.check',
#             command=['make', 'check', 
#             WithProperties('CC_UNDER_TEST=%(use_path)s/clang'),
#             WithProperties('CXX_UNDER_TEST=%(use_path)s/clang++')],
#             haltOnFailure=True,
#             description=['make check'],
#             env={'PATH': WithProperties('/usr/local/bin/:%(use_path)s:${PATH}')},
#             workdir='test-suite/gcc-4_2-testsuite'))
    return f

def runboost(config_options):
    f = buildbot.process.factory.BuildFactory()
    # Determine the build directory.
    getBuildDir(f)
    f = setProperty(f, 'use_path', WithProperties('%(builddir)s/clang-host/bin'))
    cleanCompilerDir(f)
    # Pull Boost's test-suite.
    pullboostrunner(f)
    # Download compiler artifacts to be used for this build.
    GetCompilerArtifacts(f)
    # Run boost test suite.
    f.addStep(buildbot.steps.shell.ShellCommand(
              name='user-config.jam',
              command=['echo', 'using', 'clang', ':', 'darwin-4.2.1', ':', 
                       WithProperties('%(use_path)s/clang'), ':', config_options, 
                       ';', '>', 'user-config.jam'],
              haltOnFailure=True,
              description=['create user-config.jam'],
              workdir=WithProperties('%(builddir)s')))
    f.addStep(buildbot.steps.shell.ShellCommand(
              name='run.py',
              command=['python', 'boost_runner/run.py', WithProperties('--tag=%(boost_tag)s'), 
                       '--runner=llvmlab', '--bjam-options=--toolset=clang-darwin', 
                       WithProperties('--bjam-options=--user-config=%(builddir)s/userconfig.jam'),
                       '--ftp=ftp://boost:4peiV8Xwxfv9@ftp.siliconman.net',
                       WithProperties('--bjam-options=-j%(jobs)s'),'--user=""'],
              haltOnFailure=True,
              description=['boost regression harness'],
              workdir=WithProperties('%(builddir)s'),
              timeout=14400))
    return f

def get_builders(all_slaves):
    phase1 = 'clang-x86_64-osx10-gcc42-RA'
    final_reference = 'clang-x86_64-osx10-RA'
    typeDA = 'Debug+Asserts'
    typeR  = 'Release'
    typeRA = 'Release+Asserts'
    phase1_slave = 'llvmlab.local'
    phaseRunners = [phase1_slave]
    phase3_slaves = ['lab-mini-04.local']
    return [
            # This builder should announce good builds and prepare potential release candidates.
            { 'name' : 'Validated Build',
              'factory' : PublishGoodBuild(),
              'slavenames' : phaseRunners,
              'category' : 'status'},

            # These builds coordinate and gate each phase as part of the staged design.
            makePhaseBuilder('phase1 - sanity', 'doPhase1','phase2', phaseRunners),
            makePhaseBuilder('phase2 - living', 'doPhase2','phase3', phaseRunners),
            makePhaseBuilder('phase3 - tree health', 'doPhase3','phase4', phaseRunners),
            makePhaseBuilder('phase4 - validation', 'doPhase4','GoodBuild', phaseRunners),

            # These are phase 1 build(s).
            stage1Clang(phase1, typeRA, phase1_slave),

            # These are phase 2 builds.
            HostedClang ('clang-x86_64-osx10-DA', typeDA, phase1, ['lab-mini-01.local']),
            HostedClang (final_reference, typeRA, phase1, ['lab-mini-02.local'], 
                         '--enable-optimized'),
            Nightly(phase1, ['lab-mini-03.local']),

            # These are phase 3 builds.
            HostedClang ('clang-i386-osx10-RA', typeRA, phase1, phase3_slaves, 
                         '--enable-optimized', '--target=i386'),
            Nightly('clang-x86_64-osx10-DA', phase3_slaves),
            Nightly(final_reference, phase3_slaves),
            Nightly(final_reference, phase3_slaves, '-O0'),
            Nightly(final_reference, phase3_slaves, '-Os'),
            Nightly(final_reference, phase3_slaves, '-O3'),
            Nightly(final_reference, phase3_slaves, '-flto'),
            Nightly(final_reference, phase3_slaves, '-g'),
           
            # These are phase 4 builds.
            Nightly('clang-i386-osx10-RA', phase3_slaves),
            stage3Clang(final_reference, phase3_slaves),
            gccTestSuite(final_reference, phase3_slaves),
            boost('trunk', final_reference, phase3_slaves)]

def prioritizeBuilders(buildmaster, builders):
    builderPriorities = {
            'phase1 - sanity':0,
            'clang-x86_64-osx10-gcc42-RA':0,
            'phase2 - living':1,
            'nightly_clang-x86_64-osx10-gcc42-RA':1,
            'clang-x86_64-osx10-RA':1,
            'clang-x86_64-osx10-DA':1,
            'phase3 - tree health':2,
            'clang-i386-osx10-RA':2,
            'nightly_clang-x86_64-osx10-DA':3,
            'nightly_clang-x86_64-osx10-RA':3,
            'nightly_clang-x86_64-osx10-RA-O0':3,
            'nightly_clang-x86_64-osx10-RA-Os':3,
            'nightly_clang-x86_64-osx10-RA-O3':3,
            'nightly_clang-x86_64-osx10-RA-flto':3,
            'nightly_clang-x86_64-osx10-RA-g':3,
            'phase4 - validation':4,
            'nightly_clang-i386-osx10-RA':5,
            'clang-x86_64-osx10-RA-stage3':4,
            'gccTestSuite-clang-x86_64-osx10-RA':4,
            'nightly_clang-x86_64-osx10-RA-stage3-g':5,
            'boost-trunk-clang-x86_64-osx10-RA':6,
            'Validated Build':7}
    builders.sort(key=lambda b: builderPriorities.get(b.name, 0))
    return builders


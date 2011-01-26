import buildbot
import buildbot.process.factory
from buildbot.steps.shell import WithProperties
from buildbot.steps.trigger import Trigger
from buildbot.schedulers import basic, timed, triggerable
from buildbot.steps import source
from buildbot.steps.transfer import FileUpload, FileDownload

def setProperty(f, new_property, new_value):
    f.addStep(buildbot.steps.shell.SetProperty(
                                               command=['echo', new_value],
                                               property=new_property,
                                               description=['set property', new_property],
                                               workdir='.'))
    return f

def pullsrc(f, repo_name, URL, dir, pull_mode='clobber', def_branch='trunk'):
    f.addStep(source.SVN(name='pull ' + repo_name,
                         mode=pull_mode,
                         baseURL=URL,
                         defaultBranch=def_branch, workdir=dir, always_purge='True'
                        ))
    return f


def pullClang(f):
	pullsrc(f, 'clang', 'http://llvm.org/svn/llvm-project/cfe/', 'llvm/tools/clang', 'update')
	return f

def pullllvm(f):
	pullsrc(f, 'llvm', 'http://llvm.org/svn/llvm-project/llvm/', 'llvm', 'update')
	return f

def pulltest_suite(f):
	pullsrc(f, 'llvm tests', 'http://llvm.org/svn/llvm-project/test-suite/', 'test-suite', 'update')
	return f

def pullclang_tests(f):
	pullsrc(f, 'clang tests', 'http://llvm.org/svn/llvm-project/clang-tests/', 'test-suite', 'update')
	return f

def pulllibcxx(f):
	pullsrc(f, 'libc++', 'http://llvm.org/svn/llvm-project/libcxx/', 'libcxx')
	return f

def pullboostrunner(f):
#alwaysUseLatest
#pullsrc(f, 'boost runner', 'http://svn.boost.org/svn/boost/%%BRANCH%%/tools/regression/src/', 'boost_runner')
    f.addStep(source.SVN(name='pull boost runner',
                         mode='clobber',
                         baseURL='http://svn.boost.org/svn/boost/%%BRANCH%%/tools/regression/src/',
                         defaultBranch='trunk', workdir='boost_runner', alwaysUseLatest='True',
                        ))
    return f

def getBuildDir(f):
    f.addStep(buildbot.steps.shell.SetProperty(name='get_builddir',
                                               command=['pwd'],
                                               property='builddir',
                                               description='set build dir',
                                               workdir='.'))
    return f

def GetCompilerArtifacts(f):
    if WithProperties('%(revision)s')=='None':
        src_file = WithProperties('~/artifacts/%(use_builder)s/%(got_revision)s/%(use_compiler)s.tar.gz')
    else:
        src_file = WithProperties('~/artifacts/%(use_builder)s/%(revision)s/%(use_compiler)s.tar.gz')
    f.addStep(FileDownload(mastersrc=src_file,
                           slavedest=WithProperties('%(builddir)s/%(use_compiler)s.tar.gz')
                           ))
    #extract compiler artifacts used for this build
    f.addStep(buildbot.steps.shell.ShellCommand(
              name='unzip',
              command=['tar', '-zxvf', WithProperties('%(use_compiler)s.tar.gz'),],
              haltOnFailure=True,
              description=['extract', WithProperties('%(use_compiler)s')],
              workdir='.',
              ))
    return f

def cleanCompilerDir(f):
    f.addStep(buildbot.steps.shell.ShellCommand(
            command=['rm', '-rf', WithProperties('%(use_compiler:-)s')],
            haltOnFailure=False,
            description=['rm dir', WithProperties('%(use_compiler:-)s')],
            workdir='.',))
    f.addStep(buildbot.steps.shell.ShellCommand(
            command=['rm', '-rf', WithProperties('%(use_compiler:-)s.tar.gz')],
            haltOnFailure=False,
            description=['rm archive', WithProperties('%(use_compiler:-)s')],
            workdir='.',))
    f.addStep(buildbot.steps.shell.ShellCommand(
            command=['rm', '-rf', WithProperties('%(compiler_built:-)s')],
            haltOnFailure=False,
            description=['rm dir', WithProperties('%(compiler_built:-)s')],
            workdir='.',))
    f.addStep(buildbot.steps.shell.ShellCommand(
            command=['rm', '-rf', WithProperties('%(compiler_built:-)s.tar.gz')],
            haltOnFailure=False,
            description=['rm archive', WithProperties('%(compiler_built:-)s')],
            workdir='.',))
    return f

def uploadArtifacts(f):
    f.addStep(buildbot.steps.shell.ShellCommand(
              name='tar_and_zip',
              command=['tar', 'czvf', WithProperties('%(compiler_built)s.tar.gz'),
                       WithProperties('./%(compiler_built)s/')],
              haltOnFailure=True,
              description=['tar', '&', 'zip'],
              workdir='.',
              ))
    archive_src = WithProperties('%(builddir)s/%(compiler_built)s.tar.gz')
    archive_dest = WithProperties('~/artifacts/%(buildername)s/%(got_revision)s/%(compiler_built)s.tar.gz')
    f.addStep(FileUpload(slavesrc=archive_src, masterdest=archive_dest))
    return f

def regressionTests(f):
    f.addStep(buildbot.steps.shell.ShellCommand(
        name='run_llvm_tests',
        command=['make', '-j', WithProperties('%(jobs)s'),
                ],
         haltOnFailure=True,
         description=['llvm', 'tests'],
         env={'PATH': WithProperties('%(builddir)s/%(compiler_built)s/%(compiler_type)s/bin:${PATH}')},
         workdir=WithProperties('%(compiler_built)s/test')))
    f.addStep(buildbot.steps.shell.ShellCommand(
        name='run_clang_tests',
        command=['make', '-j', WithProperties('%(jobs)s'),
                ],
         haltOnFailure=True,
         description=['clang', 'tests'],
         env={'PATH': WithProperties('%(builddir)s/%(compiler_built)s/%(compiler_type)s/bin:${PATH}')},
         workdir=WithProperties('%(compiler_built)s/tools/clang/test')))
    return f


def createPhase1():
    # create the factory
    f = buildbot.process.factory.BuildFactory()
    f = clangStage1(f)
    f = uploadArtifacts(f)
    f = regressionTests(f)
    return f
    

def clangStage1(f,config_options=''):
    # Determine the build directory.
    f = getBuildDir(f)
    f = setProperty(f, 'compiler_built', 'stage1')
    # clean out the directory used for the stage 1 compiler
    #f = cleanCompilerDir(f)
    # pull sources
    f = pullllvm(f)
    f = pullClang(f)
    # do config/make
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='configure',
            command=[
                     '../llvm/configure', '--enable-optimized', '--disable-bindings',
                     '--with-llvmcc=clang', '--without-llvmgcc', '--without-llvmgxx',
                    ],
            haltOnFailure=True,
            description=['configure'],
            workdir=WithProperties('%(compiler_built)s')))
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='make',
            command=['make', '-j', WithProperties('%(jobs)s'),],
            haltOnFailure=True,
            description=['make'],
            workdir=WithProperties('%(compiler_built)s')))
    return f

def clangHost(config_options):
    # create the factory
    f = buildbot.process.factory.BuildFactory()
    # Determine the build directory.
    f = getBuildDir(f)
    f = setProperty(f, 'compiler_built', 'stage2')
    f = setProperty(f, 'use_path', WithProperties('%(builddir)s/%(use_compiler)s/%(use_type)s'))
    # clean out the directory/archives used for the stage 1 compiler
    # clean out the directory used to build compiler
    f = cleanCompilerDir(f)
    # pull sources
    f = pullllvm(f)
    f = pullClang(f)
    #Download artifacts from phase 1 compiler build
    f = GetCompilerArtifacts(f)
    # configure to use stage1 compiler (artifacts from phase 1 build)
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='configure_with_host',
            command=[
                     '../llvm/configure', '--disable-bindings',
                     '--with-llvmcc=clang', '--without-llvmgcc', '--without-llvmgxx',
                     WithProperties('CC=%(use_path)s/bin/clang'),
                     WithProperties('CXX=%(use_path)s/bin/clang++'),
                     config_options],
            haltOnFailure=True,
            description=['configure'],
            env={'PATH': WithProperties('%(use_path)s/bin:${PATH}')},
            workdir=WithProperties('%(compiler_built)s')))
    # build stage 2 compiler
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='stage_2_make',
            command=['make', '-j', WithProperties('%(jobs)s')],
            haltOnFailure=True,
            description=['make'],
            env={'PATH': WithProperties('%(use_path)s/bin:${PATH}')},
            workdir=WithProperties('%(compiler_built)s')))
    # save artifacts of thids build for use by other builders
    f = uploadArtifacts(f)
    f = regressionTests(f)
    return f

def getGatedFactory(buildphase, next):
    f = buildbot.process.factory.BuildFactory()
    f.addStep(Trigger(schedulerNames=[buildphase],
                       waitForFinish=True,
                       haltOnFailure=True,
                       updateSourceStamp=True,
                       set_properties={'revision': WithProperties('%(revision)s'), 'got_revision': WithProperties('%(revision)s')}
#                        set_properties={'use_compiler': WithProperties('%(use_compiler:-stage1)s'),
#                                        'use_builder': WithProperties('%(use_builder:-phase1)s')},
                       ))
    f.addStep(Trigger(schedulerNames=[next],
                       waitForFinish=False,
                       updateSourceStamp=True,
                       set_properties={'revision': WithProperties('%(revision)s'), 'got_revision': WithProperties('%(revision)s')}
                       ))
    return f

def PublishGoodBuild():
    f = buildbot.process.factory.BuildFactory()
    #add steps to prepare a release and announce a good build
    return f

def Placeholder():
    f = buildbot.process.factory.BuildFactory()
    return f

def makePhaseBuilder(bldname, trigger1, trigger2, bldslaves):
    return { 'name' : bldname,
             'factory' : getGatedFactory(trigger1, trigger2),
             'slavenames' : bldslaves ,
             'category' : 'status',
           }

def HostedClang(myname, compiler_type, use_compiler, use_type, slaves, config_options=''):
    return { 'name' : myname,
             'builddir' : 'build.'+myname,
             'factory' : clangHost(config_options),
             'slavenames' : slaves,
             'category' : 'clang',
             'properties' : {'compiler_type': compiler_type, 'use_builder': use_compiler,
                             'use_type': use_type, 'use_compiler': 'stage1'
                            }}

def NightlyFactory(compiler, compiler_dir, options):
    f = buildbot.process.factory.BuildFactory()
    # Determine the build directory.
    f = getBuildDir(f)
    f = setProperty(f, 'use_builder', compiler)
    f = setProperty(f, 'use_compiler', compiler_dir)
    f = setProperty(f, 'use_path', WithProperties('%(builddir)s/%(use_compiler)s/%(use_type)s'))
    #clean out the directory/archives prior to extracting compiler
    f = cleanCompilerDir(f) 
    # pull test-suite
    f = pulltest_suite(f)
    #Download compiler artifacts to be used for this build
    f = GetCompilerArtifacts(f)
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='sanity_test',
            command=[WithProperties('%(use_path)s/bin/clang'),
                     '--version'],
             haltOnFailure=True,
             description=['sanity test'],
            env={'PATH': WithProperties('%(use_path)s/bin:${PATH}')},
             workdir='.'))
    # run tests
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='configure_tests',
            command=['./configure',
                     WithProperties('CC=%(use_path)s/bin/clang'),
                     WithProperties('CXX=%(use_path)s/bin/clang++'),
                     'CFLAGS='+options,
                     'CXXFLAGS='+options,
    #                  WithProperties('--with-llvmsrc=%(builddir)s/llvm'),
    #                  WithProperties('--with-llvmobj=%(builddir)s/'+compiler_dir),
                     #options
                     ],
            haltOnFailure=True,
            description=['configure tests'],
            env={'PATH': WithProperties('%(use_path)s/bin:${PATH}')},
            workdir='test-suite'))
#     f.addStep(buildbot.steps.shell.ShellCommand(
#             name='run_nightly_tests',
#             command=['make', WithProperties('-j%(jobs)s'), 'ENABLE_PARALLEL_REPORT=1',
#                      'DISABLE_CBE=1', 'DISABLE_JIT=1', 'TEST=nightly', 'report'
#                  ],
#             haltOnFailure=True,
#             env={'PATH': WithProperties('%(use_path)s/bin:${PATH}')},
#             description=['run tests'],
#             workdir='test-suite'))
    return f

def Nightly(compiler, compiler_type, compiler_dir, slaves, options=''):
    return { 'name' : 'nightly_'+ compiler + options,
             'builddir' : 'build.nightly.'+ compiler + options,
             'factory' : NightlyFactory(compiler, compiler_dir, options),
             'slavenames' : slaves,
             'category' : 'tests',
             'properties' : {'use_builder': compiler, 'use_type': compiler_type,
                             'use_compiler': compiler_dir
                            }}

def stage1Clang(compiler, compiler_type, slave):
    return { 'name' : compiler,
             'builddir' : 'build.'+ compiler,
             'factory' : createPhase1(),
             'slavename' : slave,
             'category' : 'clang',
             'properties' : {'compiler_type': compiler_type 
                            }}

def HostStage3Clang(config_options):
    # create the factory
    f = buildbot.process.factory.BuildFactory()
    # Determine the build directory.
    f = getBuildDir(f)
    f = setProperty(f, 'compiler_built', 'stage3')
    f = setProperty(f, 'use_path', WithProperties('%(builddir)s/%(use_compiler)s/%(use_type)s'))
    # clean out the directory/archives used for the stage 2 compiler
    # clean out the directory used to build compiler
    f = cleanCompilerDir(f)
    # pull sources
    f = pullllvm(f)
    f = pullClang(f)
    #Download artifacts from phase 1 compiler build
    f = GetCompilerArtifacts(f)
    # configure to use stage1 compiler (artifacts from phase 1 build)
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='configure_with_host',
            command=[
                     '../llvm/configure', '--enable-optimized', '--disable-bindings',
                     '--with-llvmcc=clang', '--without-llvmgcc', '--without-llvmgxx',
                     WithProperties('CC=%(use_path)s/bin/clang'),
                     WithProperties('CXX=%(use_path)s/bin/clang++'),
                     config_options],
            haltOnFailure=True,
            description=['configure'],
            env={'PATH': WithProperties('%(use_path)s/bin:${PATH}')},
            workdir=WithProperties('%(compiler_built)s')))
    # build stage 2 compiler
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='stage_3_make',
            command=['make', '-j', WithProperties('%(jobs)s')],
            haltOnFailure=True,
            description=['make'],
            env={'PATH': WithProperties('%(use_path)s/bin:${PATH}')},
            workdir=WithProperties('%(compiler_built)s')))
    # save artifacts of thids build for use by other builders
    f = uploadArtifacts(f)
    f = regressionTests(f)
    f.addStep(Trigger(schedulerNames=['stage3Nightly'],
                       waitForFinish=True,
                       updateSourceStamp=True,
                       set_properties={'revision': WithProperties('%(revision)s'), 'got_revision': WithProperties('%(revision)s')}
                       ))
    return f

def stage3Clang(use_compiler, use_type, slaves, config_options=''):
    return { 'name' : use_compiler + '-stage3',
             'builddir' : 'build.'+ use_compiler + '-stage3',
             'factory' : HostStage3Clang(config_options),
             'slavenames' : slaves,
             'category' : 'clang',
             'properties' : {'compiler_type': use_type, 'use_builder': use_compiler,
                             'use_type': use_type, 'use_compiler': 'stage2'
                            }}

def gccTestSuite(use_compiler, use_type, slaves, config_options=''):
    return { 'name' : 'gccTestSuite-'+ use_compiler,
             'builddir' : 'build.'+ 'gccTestSuite-'+ use_compiler,
             'factory' : gccRunSuite(config_options),
             'slavenames' : slaves,
             'category' : 'clang',
             'properties' : {'compiler_type': use_type, 'use_builder': use_compiler,
                             'use_type': use_type, 'use_compiler': 'stage2'
                            }}

def libcxx(use_compiler, use_type, slaves, config_options=''):
    return { 'name' : 'libcxx-'+ use_compiler,
             'builddir' : 'build.'+ 'libcxx-'+ use_compiler,
             'factory' : runlibcxx(config_options),
             'slavenames' : slaves,
             'category' : 'clang',
             'properties' : {'compiler_type': use_type, 'use_builder': use_compiler,
                             'use_type': use_type, 'use_compiler': 'stage2'
                            }}

def boost(tag, use_compiler, use_type, slaves, config_options=''):
    return { 'name' : 'boost-' + tag + '-' + use_compiler,
             'builddir' : 'build.'+ 'boost-' + tag + '-' + use_compiler,
             'factory' : runboost(config_options),
             'slavenames' : slaves,
             'category' : 'clang',
             'properties' : {'compiler_type': use_type, 'use_builder': use_compiler,
                             'use_type': use_type, 'use_compiler': 'stage2',
                             'boost_tag': tag
                            }}

def gccRunSuite(config_options):
    f = buildbot.process.factory.BuildFactory()
    # Determine the build directory.
    getBuildDir(f)
    setProperty(f, 'use_path', WithProperties('%(builddir)s/%(use_compiler)s/%(use_type)s'))
    cleanCompilerDir(f)
    # pull test-suite
    pullclang_tests(f)
    #Download compiler artifacts to be used for this build
    GetCompilerArtifacts(f)
    # run tests
#     f.addStep(buildbot.steps.shell.ShellCommand(
#             name='make_check',
#             command=['make', 'check', 
#             WithProperties('CC_UNDER_TEST=%(use_path)s/bin/clang'),
#             WithProperties('CXX_UNDER_TEST=%(use_path)s/bin/clang++'),],
#             haltOnFailure=True,
#             description=['make check'],
#             env={'PATH': WithProperties('/usr/local/bin/:%(use_path)s/bin:${PATH}')},
#             workdir='test-suite/gcc-4_2-testsuite'))
    return f

def runlibcxx(config_options):
    f = buildbot.process.factory.BuildFactory()
    # Determine the build directory.
    getBuildDir(f)
    setProperty(f, 'use_path', WithProperties('%(builddir)s/%(use_compiler)s/%(use_type)s'))
    cleanCompilerDir(f)
    # pull test-suite
    pulllibcxx(f)
    #Download compiler artifacts to be used for this build
    GetCompilerArtifacts(f)
    # run tests
#     f.addStep(buildbot.steps.shell.ShellCommand(
#             name='buildit',
#             command=['./buildit',],
#             haltOnFailure=True,
#             description=['build libc++'],
#             env={'PATH': WithProperties('%(use_path)s/bin:${PATH}')},
#             workdir='libcxx/lib'))
#     f.addStep(buildbot.steps.shell.ShellCommand(
#             name='testit',
#             command=['testit',],
#             haltOnFailure=True,
#             description=['test libc++'],
#             env={'PATH': WithProperties('%(use_path)s/bin:${PATH}')},
#             workdir='libcxx/test'))
    return f

def runboost(config_options):
    f = buildbot.process.factory.BuildFactory()
    # Determine the build directory.
    getBuildDir(f)
    setProperty(f, 'use_path', WithProperties('%(builddir)s/%(use_compiler)s/%(use_type)s'))
    cleanCompilerDir(f)
    # pull test-suite
    pullboostrunner(f)
    #Download compiler artifacts to be used for this build
    GetCompilerArtifacts(f)
    # run tests
    # runner=llvmlab
    # BOOST_ROOT=builddir/boost
    # echo using borland : "integration" : %CD:\=/%/integration/bin/bcc32 : ; > %MYJAMFILE%
    f.addStep(buildbot.steps.shell.ShellCommand(
              name='user-config.jam',
              command=['echo', 'using', 'clang', ':', 'darwin-4.2.1', ':', 
                       WithProperties('%(use_path)s/bin/clang'), ':', config_options, 
                       ';', '>', 'user-config.jam'],
              haltOnFailure=True,
              description=['create user-config.jam'],
              workdir='.',
              ))
    #--bjam-options=target-os=windows --bjam-options=-l300 --bjam-options=--debug-level=3 --bjam-options=--user-config=%MYJAMFILE% --have-source --skip-script-download --ftp=ftp://boost:4peiV8Xwxfv9@ftp.siliconman.net >runner.log
    f.addStep(buildbot.steps.shell.ShellCommand(
              name='run.py',
              command=['python', 'boost_runner/run.py', WithProperties('--tag=%(boost_tag)s'), 
                       '--runner=llvmlab', '--bjam-options=--toolset=clang-darwin', 
                       WithProperties('--bjam-options=--user-config=%(builddir)s/userconfig.jam'),
                       '--ftp=ftp://boost:4peiV8Xwxfv9@ftp.siliconman.net',
                       WithProperties('--bjam-options=-j%(jobs)s'),'--user=""',],
              haltOnFailure=True,
              description=['boost regression harness'],
              workdir='.',
              timeout=14400
              ))
    return f

def get_builders(all_slaves):
    phase1 = 'clang-x86_64-osx10-gcc42-RA'
    final_reference = 'clang-x86_64-osx10-RA'
    typeDA = 'Debug+Asserts'
    typeR  = 'Release'
    typeRA = 'Release+Asserts'
    phase1_slave = 'llvmlab.local'
    #phase2_slaves = [ 'leone.apple.com', 'dtqa09.apple.com' ]
    #phaseRunners = [ 'leone.apple.com', 'dtqa09.apple.com' ]
    snow_leopard_slaves = all_slaves
    barolo_slaves = []
    phase2_slaves = filter(lambda x:x not in [phase1_slave], snow_leopard_slaves)
    phaseRunners = filter(lambda x:x not in [phase1_slave], snow_leopard_slaves)
    return [
            #Build to announce good build and prepare potential release candidate
            { 'name' : 'Validated Build',
              'factory' : PublishGoodBuild(),
              'slavenames' : phaseRunners,
              'category' : 'status',
            },
            #parent builds for each phase
            makePhaseBuilder('phase1 - sanity', 'doPhase1','phase2', phaseRunners),
            makePhaseBuilder('phase2 - living', 'doPhase2','phase3', phaseRunners),
            makePhaseBuilder('phase3 - tree health', 'doPhase3','phase4', phaseRunners),
            makePhaseBuilder('phase4 - validation', 'doPhase4','GoodBuild', phaseRunners),
            # phase 1 build
            stage1Clang(phase1, typeRA, phase1_slave),
            #phase 2 Builds
            HostedClang ('clang-x86_64-osx10-DA', typeDA, phase1, typeRA, [phase1_slave]),
            HostedClang (final_reference, typeRA, phase1, typeRA, phase2_slaves, '--enable-optimized'),
            Nightly(phase1, typeRA, 'stage1', phase2_slaves),
            #phase3 builds
            Nightly('clang-x86_64-osx10-DA', typeDA, 'stage2', phase2_slaves),
            Nightly(final_reference, typeRA, 'stage2', phase2_slaves),
            Nightly(final_reference, typeRA, 'stage2', phase2_slaves, '-O0'),
            Nightly(final_reference, typeRA, 'stage2', phase2_slaves, '-Os'),
            Nightly(final_reference, typeRA, 'stage2', phase2_slaves, '-O3'),
            Nightly(final_reference, typeRA, 'stage2', phase2_slaves, '-flto'),
            Nightly(final_reference, typeRA, 'stage2', phase2_slaves, '-g'),
           
            #phase4 builds
            stage3Clang(final_reference, typeRA, phase2_slaves),
            gccTestSuite(final_reference, typeRA, phase2_slaves),
            Nightly(final_reference+ '-stage3', typeRA, 'stage3', all_slaves, '-g'),
            libcxx(final_reference, typeRA, phase2_slaves),
            boost('trunk', final_reference, typeRA, phase2_slaves),
            #A Placeholder builder is required for triggers which haven't had builders
            #configured yet, otherwise build will hang
#             { 'name' : 'Placeholder',
#               'factory' : Placeholder(),
#               'slavenames' : phaseRunners,
#               'category' : 'clang',
#             },
           ]

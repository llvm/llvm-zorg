from buildbot.steps.shell import ShellCommand
from buildbot.process.properties import WithProperties
from buildbot.plugins import steps

from zorg.buildbot.commands.LitTestCommand import LitTestCommand
from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.commands.NinjaCommand import NinjaCommand
from zorg.buildbot.builders import UnifiedTreeBuilder
from zorg.buildbot.process.factory import LLVMBuildFactory

def getOpenMPCMakeBuildFactory(
        jobs                = '%(jobs)s',   # Number of concurrent jobs.
        clean               = True,         # "clean" step is requested if true
        env                 = None,         # Environmental variables for all steps.
        ompt                = False,        # Whether to enable the OpenMP Tools Interface.
        test                = True,         # Test the built libraries.
        depends_on_projects = None,
        enable_runtimes     = None,
        extraCmakeArgs      = [],
        install             = False,
        testsuite           = False,
        testsuite_sollvevv  = False,
        extraTestsuiteCmakeArgs = [],
        add_lit_checks      = None,
        **kwargs):

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        'TERM' : 'dumb' # Make sure Clang doesn't use color escape sequences.
                 }
    # Overwrite pre-set items with the given ones, so user can set anything.
    if env is not None:
        merged_env.update(env)

    llvm_srcdir = 'llvm.src'
    llvm_builddir = 'llvm.build'
    llvm_instdir = 'llvm.inst'
    testsuite_srcdir = "test-suite.src"
    testsuite_builddir = "test-suite.build"
    sollvevv_srcdir = "sollvevv.src"

    # If true, clean everything, including source dirs
    def cleanBuildRequested(step):
        return step.build.getProperty("clean")
    # If true, clean build products; implied if cleanBuildRequested is true
    def cleanObjRequested(step):
        return cleanBuildRequested(step) or clean or step.build.getProperty("clean_obj")

    if depends_on_projects is None:
        # Monorepo configuration requires llvm and clang to get cmake work.
        depends_on_projects = ['llvm', 'clang', 'openmp']

    f = UnifiedTreeBuilder.getLLVMBuildFactoryAndSourcecodeSteps(
            depends_on_projects=depends_on_projects,
            enable_runtimes=enable_runtimes,
            llvm_srcdir=llvm_srcdir,
            obj_dir=llvm_builddir,
            cleanBuildRequested=cleanBuildRequested,
            env=merged_env,
            **kwargs) # Pass through all the extra arguments.

    f.addStep(steps.RemoveDirectory(name='clean',
                           dir=f.obj_dir,
                           warnOnFailure=True,
                           doStepIf=cleanObjRequested))

    # Configure LLVM and OpenMP (and Clang, if requested).
    cmake_args = ['-DCMAKE_BUILD_TYPE=Release', '-DLLVM_ENABLE_ASSERTIONS=ON']
    if ompt:
        cmake_args += ['-DLIBOMP_OMPT_SUPPORT=ON']
    if test:
        lit_args = '-vv --show-unsupported --show-xfail -j %s' % jobs
        cmake_args += [WithProperties('-DLLVM_LIT_ARGS=%s' % lit_args)]
    if install:
        cmake_args += [WithProperties('-DCMAKE_INSTALL_PREFIX=%(builddir)s/' + llvm_instdir)]
    cmake_args += extraCmakeArgs

    if f.enable_projects:
        CmakeCommand.applyDefaultOptions(cmake_args, [
            ('-DLLVM_ENABLE_PROJECTS=', ";".join(f.enable_projects)),
            ])

    if f.enable_runtimes:
        CmakeCommand.applyDefaultOptions(cmake_args, [
            ('-DLLVM_ENABLE_RUNTIMES=', ";".join(f.enable_runtimes)),
            ])

    # Add llvm-lit and clang (if built) to PATH
    merged_env.update({
        'PATH': WithProperties('%(builddir)s/' + llvm_builddir + '/bin:${PATH}')})

    src_dir = LLVMBuildFactory.pathRelativeTo(f.llvm_srcdir, f.obj_dir)

    f.addStep(CmakeCommand(name='configure-openmp',
                           description=['configure','openmp'],
                           generator='Ninja',
                           options=cmake_args,
                           path=src_dir,
                           env=merged_env,
                           workdir=f.obj_dir,
                           haltOnFailure=True,
                           **kwargs # Pass through all the extra arguments.
                           ))

    # Build OpenMP runtime libraries.
    f.addStep(
        NinjaCommand(
            name        = 'compile-openmp',
            description = 'compile openmp',
            workdir     = f.obj_dir,
            env         = merged_env,
            haltOnFailure=True))

    # Test OpenMP runtime libraries, if requested.
    if test:
        # Add llvm-lit and clang (if built) to PATH
        merged_env.update({
            'PATH': WithProperties('%(builddir)s/' + llvm_builddir + '/bin:${PATH}')})

        ninja_test_args = ['ninja', WithProperties('-j %s' % jobs)]
        f.addStep(
            LitTestCommand(
                name        = 'test-openmp',
                command     = ninja_test_args + ['check-openmp'],
                description = 'test openmp',
                workdir     = f.obj_dir,
                env         = merged_env,
                haltOnFailure=False,
                flunkOnFailure=True))
    # When requested run additional lit tests
    if add_lit_checks != None:
        for add_check in add_lit_checks:
            f.addStep(LitTestComamnd(
                name = 'Add check ' + add_check,
                command = ['ninja', add_check],
                description = ["Additional check in OpenMP for", add_check,],
                env = merged_env,
                workdir = f.obj_dir,
                haltOnFailure = False,
                flunkOnFailure=True))

    clangexe = "%(builddir)s/" + llvm_builddir + "/bin/clang"
    clangxxexe = "%(builddir)s/" + llvm_builddir + "/bin/clang++"
    litexe = "%(builddir)s/" + llvm_builddir + "/bin/llvm-lit"
    libdir = "%(builddir)s/" + llvm_builddir + "/lib"
    if install:
        f.addStep(steps.RemoveDirectory(name="LLVM: Clean Install Dir",
                               dir=llvm_instdir,
                               haltOnFailure=False))

        f.addStep(NinjaCommand(name="LLVM: Install",
                               description="installing",
                               descriptionDone="install",
                               descriptionSuffix="LLVM",
                               workdir=f.obj_dir,
                               targets=['install'],
                               env=merged_env,
                               haltOnFailure=True))
        # If installing, use the installed version of clang.
        clangexe = "%(builddir)s/" + llvm_instdir + "/bin/clang"
        clangxxexe = "%(builddir)s/" + llvm_instdir + "/bin/clang++"
        libdir = "%(builddir)s/" + llvm_instdir + "/lib"


    if testsuite:
        f.addStep(steps.RemoveDirectory(name="Test-Suite: Clean Source",
                           dir=testsuite_srcdir,
                           haltOnFailure=False,
                           warnOnFailure=True,
                           doStepIf=cleanBuildRequested))

        f.addGetSourcecodeForProject(name="Test-Suite: Checkout",
            description="fetching",
            descriptionDone="fetch",
            descriptionSuffix="Test-Suite",
            project='test-suite',
            src_dir=testsuite_srcdir,
            alwaysUseLatest=True)

        if testsuite_sollvevv:
            f.addStep(steps.RemoveDirectory(name="SOLLVE V&V: Clean Source",
                           dir=sollvevv_srcdir,
                           haltOnFailure=False,
                           warnOnFailure=True,
                           doStepIf=cleanBuildRequested))

            f.addStep(steps.Git(name="SOLLVE V&V: Checkout",
                    description="fetching",
                    descriptionDone="fetch",
                    descriptionSuffix="SOLLVE V&V",
                    repourl='https://github.com/SOLLVE/sollve_vv.git',
                    workdir=sollvevv_srcdir,
                    alwaysUseLatest=True))

        f.addStep(steps.RemoveDirectory(name="Test-Suite: Clean Build",
                           dir=testsuite_builddir,
                           haltOnFailure=False,
                           warnOnFailure=True))

        testsuite_options = [
            "-DCMAKE_BUILD_TYPE=Release",
            "-DTEST_SUITE_LIT_FLAGS=-vv;-s;-j6;-o;report.json",
            "-DTEST_SUITE_EXTRA_C_FLAGS=-gline-tables-only",
            "-DTEST_SUITE_EXTRA_CXX_FLAGS=-gline-tables-only",
            WithProperties("-DCMAKE_C_COMPILER=" + clangexe),
            WithProperties("-DCMAKE_CXX_COMPILER=" + clangxxexe),
            WithProperties("-DTEST_SUITE_LIT=" + litexe),
        ]
        if testsuite_sollvevv:
            testsuite_options += [
                "-DTEST_SUITE_SUBDIRS=External/sollve_vv",
                "-DTEST_SUITE_SOLLVEVV_ROOT=../" + sollvevv_srcdir,
            ]
        testsuite_options += extraTestsuiteCmakeArgs
        f.addStep(CmakeCommand(name="Test-Suite: Configure",
                            description="configuring",
                            descriptionDone="configure",
                            descriptionSuffix="Test-Suite",
                            generator='Ninja',
                            path='../' + testsuite_srcdir,
                            workdir=testsuite_builddir,
                            options=testsuite_options,
                            haltOnFailure=True,
                            logfiles={
                                'CMakeCache.txt'   : 'CMakeCache.txt',
                            }))

        f.addStep(NinjaCommand(name="Test-Suite: Compile",
                            description="compiling",
                            descriptionDone="compile",
                            descriptionSuffix="Test-Suite",
                            options=['-k0'],      # Continue building; programs that don't compile will fail with NOEXE.
                            haltOnFailure=False,
                            flunkOnFailure=False, # SOLLVE V&V contains tests that clang have not been implemented yet.
                            warnOnFailure=True,
                            workdir=testsuite_builddir))

        merged_env.update({
            'LD_LIBRARY_PATH': WithProperties(libdir + ':${LD_LIBRARY_PATH}')
            })
        f.addStep(LitTestCommand(name="Test-Suite: Run",
                            description="running",
                            descriptionDone="run",
                            descriptionSuffix="Test-Suite",
                            command=[WithProperties(litexe), '-vv', '-s',  '-j6', '-o','report.json', '.'],
                            haltOnFailure=False,
                            flunkOnFailure=False, # SOLLVE V&V contains tests that clang have not been implemented yet.
                            warnOnFailure=True,
                            workdir=testsuite_builddir,
                            env=merged_env,
                            logfiles={
                                'test.log'   : 'test.log',
                                'report.json': 'report.json'
                            }))

    return f

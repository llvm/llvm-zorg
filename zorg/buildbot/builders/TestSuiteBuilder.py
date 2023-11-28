from zorg.buildbot.builders.UnifiedTreeBuilder import getCmakeWithNinjaBuildFactory

from buildbot.plugins import util

from buildbot.steps.shell import ShellCommand

from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.commands.NinjaCommand import NinjaCommand
from zorg.buildbot.commands.LitTestCommand import LitTestCommand

# This builder is uses UnifiedTreeBuilders and adds running
# llvm-test-suite with cmake and ninja step.

def addTestSuiteStep(
            f,
            compiler_dir = None,
            env = None,
            cleanBuildRequested=True,
            lit_args = [],
            **kwargs):

    cc = util.Interpolate('-DCMAKE_C_COMPILER=' + '%(prop:builddir)s/'+compiler_dir+'/bin/clang')
    cxx = util.Interpolate('-DCMAKE_CXX_COMPILER=' + '%(prop:builddir)s/'+compiler_dir+'/bin/clang++')
    lit = util.Interpolate('%(prop:builddir)s/' + compiler_dir + '/bin/llvm-lit')
    test_suite_base_dir = util.Interpolate('%(prop:builddir)s/' + 'test')
    test_suite_src_dir = util.Interpolate('%(prop:builddir)s/' + 'test/test-suite')
    test_suite_workdir = util.Interpolate('%(prop:builddir)s/' + 'test/build-test-suite')
    cmake_lit_arg = util.Interpolate('-DTEST_SUITE_LIT:FILEPATH=' + '%(prop:builddir)s/' + compiler_dir + '/bin/llvm-lit')
    # used for cmake building test-suite step
    options = [cc, cxx, cmake_lit_arg]

    # The default value of cleanBuildRequested is TRUE as we should always
    # clobber the build directory to test each freshly built compiler.
    f.addStep(steps.RemoveDirectory(
                name='Clean Test Suite Build dir' % test_suite_workdir,
                dir=test_suite_workdir,
                haltOnFailure=False,
                flunkOnFailure=False,
                doStepIf=cleanBuildRequested,
                ))


    f.addGetSourcecodeForProject(
        project='test-suite',
        src_dir=test_suite_src_dir,
        alwaysUseLatest=True)

    f.addStep(CmakeCommand(name='cmake Test Suite',
                           haltOnFailure=True,
                           description='Running cmake on Test Suite dir',
                           workdir=test_suite_workdir,
                           options=options,
                           path=test_suite_src_dir,
                           generator='Ninja'))

    f.addStep(NinjaCommand(name='ninja Test Suite',
                           description='Running Ninja on Test Suite dir',
                           haltOnFailure=True,
                           workdir=test_suite_workdir))

    f.addStep(LitTestCommand(name='Run Test Suite with lit',
                             haltOnFailure=True,
                             description='Running test suite tests',
                             workdir=test_suite_workdir,
                             command=[lit] + lit_args + ['.'],
                             env=env,
                             **kwargs))

    return f

def getTestSuiteBuildFactory(
           depends_on_projects = None,
           enable_runtimes = "auto",
           targets = None,
           llvm_srcdir = None,
           obj_dir = None,
           checks = None,
           install_dir = None,
           clean = False,
           extra_configure_args = None,
           env = None,
           **kwargs):

    # handle the -DCMAKE args for lit
    lit_args = list()
    if any("DLLVM_LIT_ARGS" in arg for arg in extra_configure_args):
        arg = [arg for arg in extra_configure_args
                if "DLLVM_LIT_ARGS" in arg][0]
        lit_args = arg.split("=")[1]
        lit_args = lit_args.split(" ")

    f = getCmakeWithNinjaBuildFactory(
            depends_on_projects = depends_on_projects,
            enable_runtimes = enable_runtimes,
            targets = targets,
            llvm_srcdir = llvm_srcdir,
            obj_dir = obj_dir,
            checks = checks,
            install_dir = install_dir,
            clean = clean,
            extra_configure_args = extra_configure_args,
            env = env,
            **kwargs)


    addTestSuiteStep(f,
           compiler_dir=f.obj_dir,
           env=env,
           lit_args=lit_args,
           **kwargs)

    return f

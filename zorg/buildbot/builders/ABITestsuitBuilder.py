from buildbot.process.properties import WithProperties
from buildbot.steps.source       import SVN

from zorg.buildbot.builders                import UnifiedTreeBuilder
from zorg.buildbot.commands.CmakeCommand   import CmakeCommand
from zorg.buildbot.commands.NinjaCommand   import NinjaCommand
from zorg.buildbot.commands.LitTestCommand import LitTestCommand

def getABITestsuitBuildFactory(
            clean = True,
            depends_on_projects  = None,
            extra_configure_args = None, # Extra CMake args for all stages.
            jobs = None,                 # Restrict a degree of parallelism if needed.
            env  = None,                 # Environmental variables for all steps.
            **kwargs):

    # Prepare environmental variables. Set here all env we want for all steps.
    merged_env = {
        'TERM' : 'dumb' # Make sure Clang doesn't use color escape sequences.
        }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    if depends_on_projects:
        depends_on_projects = list(depends_on_projects)
    else:
        depends_on_projects = ['llvm', 'clang', 'clang-tools-extra', 'compiler-rt', 'lld']

    if extra_configure_args is None:
        cmake_args = list()
    else:
        cmake_args = list(extra_configure_args)

    # Some options are required for this build no matter what.
    CmakeCommand.applyRequiredOptions(cmake_args, [
        ('-G',                      'Ninja'),
        ])

    f = UnifiedTreeBuilder.getCmakeBuildFactory(
            depends_on_projects=depends_on_projects,
            llvm_srcdir="llvm",
            obj_dir="build",
            clean=clean,
            extra_configure_args=cmake_args,
            env=merged_env,
            **kwargs) # Pass through all the extra arguments.


    f.addStep(NinjaCommand(name="build-unified-tree",
                           haltOnFailure=True,
                           description=["Build", "unified", "tree"],
                           env=merged_env,
                           workdir=f.obj_dir,
                           **kwargs # Pass through all the extra arguments.
                           ))

    # Checkout the test-suite.
    f.addStep(SVN(name='svn-test-suite',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/test-suite/',
                  defaultBranch='trunk',
                  workdir='test-suite'))

    # Run the ABI test.
    abi_test_env = {
        'PYTHONPATH' : WithProperties("%(workdir)s/" + f.llvm_srcdir + "/utils/lit:${PYTHONPATH}"),
        'PATH'       : WithProperties("%(workdir)s/" + f.obj_dir + "/bin:${PATH}"),
        }
    merged_env.update(abi_test_env)

    abi_test_cmd = ["python", "linux-x86.py", "clang", "test", "-v"]
    if jobs:
        abi_test_cmd.append("-j" + str(jobs))

    f.addStep(LitTestCommand(name='abi-test-suite',
                             command=abi_test_cmd,
                             description=["running", "ABI", "test-suite"],
                             descriptionDone=["ABI", "test-suite", "completed"],
                             workdir='test-suite/ABI-Testsuite',
                             env=merged_env))

    return f

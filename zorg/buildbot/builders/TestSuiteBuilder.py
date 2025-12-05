from zorg.buildbot.builders.UnifiedTreeBuilder import getCmakeWithNinjaBuildFactory

from buildbot.plugins import steps, util

from buildbot.steps.shell import ShellCommand

from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.commands.NinjaCommand import NinjaCommand
from zorg.buildbot.commands.LitTestCommand import LitTestCommand

from zorg.buildbot.process.factory import LLVMBuildFactory


# Note: The 'compiler_dir' parameter or CMAKE_{C|CXX}_COMPILER and TEST_SUITE_LIT must be specified inside of 'cmake_definitions' parameters;
# otherwise the function will get failed by assert. Also, some of CMAKE_{C|CXX}_COMPILER and TEST_SUITE_LIT can be specified in case the 'compiler_dir'
# parameter is also specified. It is necessary to get a full set of those variables for the LLVM test suite configuration step.
# Note: The 'compiler_dir' must be a fully specified path, no relative pathes, no ~/ pathes. The same is also true for CMAKE_{C|CXX}_COMPILER and TEST_SUITE_LIT.

def getLlvmTestSuiteSteps(
        cmake_definitions = None,
        cmake_options = None,
        allow_cmake_defaults = True,    # Add default CMake definitions to build LLVM project (if not specified).
        targets = ".",
        checks = "check",
        generator = "Ninja",            # CMake generator.
        repo_profiles = "default",      # The source code repository profiles.
        extra_git_args = None,          # Extra parameters for steps.Git step (such as 'config', 'workdir', etc.)

        jobs = None,                    # Restrict a degree of parallelism.
        env  = None,                    # Common environmental variables.
        hint = "test-suite",

        compiler_dir = None,            # A path a root of built Clang toolchain tree. This path will be used
                                        # to specify CMAKE_{C|CXX}_COMPILER and TEST_SUITE_LIT if they are missing inside of
                                        # CMake definitions.
        compiler_flags = None,          # Common flags for C and C++ compilers.
        linker_flags = None,            # Common linker flags for all exe/module/shared configurations.

        src_dir = None,
        obj_dir = None,

        f = None
    ):
    """ Create and configure a builder factory with a set of the build steps to retrieve, build and run the LLVM Test Suite project
        (see https://github.com/llvm/llvm-test-suite.git).

        The factory can fill up existing factory object with these steps if this factory has been passed via the fucntion arguments.

        This is one-stage CMake configurable build that uses Ninja generator by default. Using the other CMake generators
        also possible.

        The factory supports the remote test runs on the dev boards. Specifying TEST_SUITE_REMOTE_HOST in the CMake definitions dict
        will add the rsync target step.

        Property Parameters
        -------------------

        clean : boolean
            Clean up the source and the build folders.

        clean_obj : boolean
            Clean up the build folders.


        Parameters
        ----------

        cmake_definitions : dict, optional
            A dictionary of the CMake definitions (default is None).

        cmake_options : list, optional
            A list of the CMake options (default is None).

        allow_cmake_defaults : boolean
            Add default CMake definitions to the build configuration step (default True).

            A default value will be used only if a definition is not explicitly specified in 'cmake_definitions'
            argument and allow_cmake_defaults evaluates to True.

        targets : list, optional
            A list of targets to build (default is ["."]).
            Each target gets built in a separate step, skipped if None.

            Pass string '.' in a list to build the default target.

        checks : list, optional
            A list of the check targets (default is ["check-all"]).

            Each check target gets executed in a separate step. The check step uses LitTestCommand
            to parse and display the test result logs.

            No check steps will be generated for the build if 'None' was provided with this argument.

        generator : str, required
            CMake generator (default is 'Ninja').

            See CMake documentation for more details.

        repo_profiles : string, optional
            A name of the source code profile to get from the remote repository. Currently is supported only "default"
            profile and None. Default is "default".

            If None is passed, no the repository checkout steps will be added to the factory workflow. This is useful
            for the nested factories when the single repo is shared between them.

        extra_git_args : dict, optional
            Provide extra arguments for the Git step (default is None).

            Sometimes it is necessary to pass some additional parameters to the git step, such as
            'config', 'workdir', etc.


        jobs : int, optional
            Restrict a degree of parallelism (default is None).

        env : dict, optional
            Common environmental variables for all build steps (default is None).

        hint : string, optional
            Use this hint to apply suffixes to the step names when factory is used as a nested factory for another one.
            The suffix will be added to the step name separated by dash symbol.

            As example, passing of 'stageX' with 'hint' will force generating of the following step names:
                cmake-cofigure => cmake-configure-stageX
                build => build-stageX
                install => install-stageX
                & etc.

            Note: cannot be a renderable object.

        compiler_dir : string, optional
            A fully specified path to the Clang toolchain root.

            This argument must be specified if any of CMAKE_{C|CXX}_COMPILER and TEST_SUITE_LIT weren't specified
            in the CMake definitions dict.

        compiler_flags : string, optional
            Common flags for C and C++ compilers.

            This argument will add CMAKE_{C|CXX}_FLAGS CMake definitions if they were not specified; otherwise the existing
            definitions will be extended with these compiler flags.

        linker_flags : string, optional
            Common linker flags for all exe/module/shared configurations.

            This argument will add CMAKE_{EXE|MODULE|SHARED}_LINKER_FLAGS CMake definitions if they were not specified; 
            otherwise the existing definitions will be extended with these linker flags.

        src_dir : str, optional
            A custom llvm-test-suite source directory within %(prop:builddir)s of the builder (default is "llvm-test-suite").

        obj_dir : str, optional
            The build folder (default is "build/llvm-test-suite").

        f : LLVMBuildFactory, optional
            A factory object to fill up with the build steps. An empty stub will be created if this argument wasn't specified.

        Returns
        -------

        Returns the factory object with the prepared build steps.

        Properties
        ----------

        ts_srcdir : str
            A full path to the LLVM test-suite source code directory.

        ts_objdir : str
            A full path to the build directory.

    """
    assert generator, "CMake generator must be specified."
    assert not hint or isinstance(hint, str),    "The 'hint' argument must be a str object."

    def norm_target_list_arg(lst):
        if type(lst) == str:
            lst = list(filter(None, lst.split(";")))
        # In case we got IRenderable, just wrap it into the list.
        if not isinstance(lst, list):
            lst = [ lst ]
        return lst

    # Normalize all arguments with a list of the targets.
    # We need to convert them into the regular lists of str/IRenderable objects or empty list.
    targets = norm_target_list_arg(targets or [])
    checks = norm_target_list_arg(checks or [])

    env = env or {}
    # Do not everride TERM just in case.
    if not "TERM" in env:
        # Be cautious and disable color output from all tools.
        env.update({ 'TERM' : 'dumb' })

    if not "NINJA_STATUS" in env and generator.upper() == "NINJA":
        env.update({ 'NINJA_STATUS' : "%e [%u/%r/%f] " })

    # Initial directories
    test_suite_src_dir = util.Interpolate("%(prop:builddir)s/%(kw:path_suffix)s",
                                          path_suffix = src_dir or "llvm-test-suite")
    test_suite_obj_dir = util.Interpolate("%(prop:builddir)s/%(kw:path_suffix)s",
                                          path_suffix = obj_dir or util.Interpolate("%(prop:objdir:-build)s/llvm-test-suite"))

    # Create and return the default factory stub to store the build steps.
    # This factory can be used with the composite builder factories.
    if f is None:
        f = LLVMBuildFactory(
                hint                = hint,
                obj_dir             = "build/llvm-test-suite",  # stub, shouldn't be used
            )

    f.addSteps([
        # Set up some properties, which could be used to configure the builders.
        steps.SetProperties(
            name            = f.makeStepName('set-props'),
            properties      = {
                "ts_srcdir"             : test_suite_src_dir,
                "ts_objdir"             : test_suite_obj_dir,
            }
        ),
    ])

    # Add the Git step.
    if repo_profiles == "default":
        f.addSteps([
            # Remove the source code for a clean checkout if requested by property.
            steps.RemoveDirectory(
                name            = f.makeStepName('clean-src-dir'),
                dir             = test_suite_src_dir,
                description     = ["Remove", test_suite_src_dir, "directory"],
                haltOnFailure   = False,
                flunkOnFailure  = False,
                doStepIf        = util.Property("clean", False) == True,
            ),
        ])

        extra_git_args = extra_git_args or {}

        f.addGetSourcecodeForProject(
            project             = 'test-suite',
            src_dir             = test_suite_src_dir,
            alwaysUseLatest     = True,
            **extra_git_args
        )

    # Build the CMake command definitions.
    cmake_definitions = cmake_definitions or dict()
    assert isinstance(cmake_definitions, dict), "The CMake definitions argument must be a dictionary."
    cmake_options = cmake_options or list()
    assert isinstance(cmake_options, list), "The CMake options argument must be a list."

    # Set proper defaults.
    if allow_cmake_defaults:
        if not "CMAKE_BUILD_TYPE" in cmake_definitions:
            cmake_definitions.update({ "CMAKE_BUILD_TYPE" : "Release" })
        if not "TEST_SUITE_LIT_FLAGS" in cmake_definitions and checks:
            cmake_definitions.update({ "TEST_SUITE_LIT_FLAGS" : "-v;--time-tests" })

    # Normalize TEST_SUITE_LIT_FLAGS option. We need to convert it to CMake formatted list.
    if "TEST_SUITE_LIT_FLAGS" in cmake_definitions:
        cmake_definitions.update({ "TEST_SUITE_LIT_FLAGS" : cmake_definitions["TEST_SUITE_LIT_FLAGS"].replace(" ", ";") })

    # Check if we need to sync the test data on the remote host.
    remote_rsync = ("TEST_SUITE_REMOTE_HOST" in cmake_definitions)

    if compiler_dir:
        #TODO: support for the executable extensions on the build host.
        if not "CMAKE_C_COMPILER" in cmake_definitions:
            cmake_definitions.update({ "CMAKE_C_COMPILER" : util.Interpolate("%(kw:compiler_dir)s/bin/clang", compiler_dir = compiler_dir) })
        if not "CMAKE_CXX_COMPILER" in cmake_definitions:
            cmake_definitions.update({ "CMAKE_CXX_COMPILER" : util.Interpolate("%(kw:compiler_dir)s/bin/clang++", compiler_dir = compiler_dir) })
        if not ("TEST_SUITE_LIT" in cmake_definitions or "TEST_SUITE_LIT:FILEPATH" in cmake_definitions):
            cmake_definitions.update({ "TEST_SUITE_LIT:FILEPATH" : util.Interpolate("%(kw:compiler_dir)s/bin/llvm-lit", compiler_dir = compiler_dir) })
    else:
        assert "CMAKE_C_COMPILER" in cmake_definitions, "CMAKE_C_COMPILER must be specified in the CMake definitions."
        assert "CMAKE_CXX_COMPILER" in cmake_definitions, "CMAKE_CXX_COMPILER must be specified in the CMake definitions."
        assert ("TEST_SUITE_LIT" in cmake_definitions or "TEST_SUITE_LIT:FILEPATH" in cmake_definitions), "TEST_SUITE_LIT must be specified in the CMake definitions."

    #Note: we can get those flags as the renderables. Properly handle them by using %(kw:) interpolation.
    if compiler_flags:
        c_flags = compiler_flags
        cxx_flags = compiler_flags
        if "CMAKE_C_FLAGS" in cmake_definitions:
            c_flags = util.Interpolate("%(kw:c_flags)s %(kw:flags)s",
                            c_flags = c_flags, flags = cmake_definitions["CMAKE_C_FLAGS"])
        cmake_definitions.update({ "CMAKE_C_FLAGS" : c_flags })
        if "CMAKE_CXX_FLAGS" in cmake_definitions:
            cxx_flags = util.Interpolate("%(kw:cxx_flags)s %(kw:flags)s",
                            cxx_flags = cxx_flags, flags = cmake_definitions["CMAKE_CXX_FLAGS"])
        cmake_definitions.update({ "CMAKE_CXX_FLAGS" : cxx_flags })

    if linker_flags:
        exe_flags = linker_flags
        module_flags = linker_flags
        shared_flags = linker_flags
        if "CMAKE_EXE_LINKER_FLAGS" in cmake_definitions:
            exe_flags = util.Interpolate("%(kw:exe_flags)s %(kw:flags)s",
                            exe_flags = exe_flags, flags = cmake_definitions["CMAKE_EXE_LINKER_FLAGS"])
        cmake_definitions.update({ "CMAKE_EXE_LINKER_FLAGS" : exe_flags })
        if "CMAKE_MODULE_LINKER_FLAGS" in cmake_definitions:
            module_flags = util.Interpolate("%(kw:module_flags)s %(kw:flags)s",
                            module_flags = module_flags, flags = cmake_definitions["CMAKE_MODULE_LINKER_FLAGS"])
        cmake_definitions.update({ "CMAKE_MODULE_LINKER_FLAGS" : module_flags })
        if "CMAKE_SHARED_LINKER_FLAGS" in cmake_definitions:
            shared_flags = util.Interpolate("%(kw:shared_flags)s %(kw:flags)s",
                            shared_flags = shared_flags, flags = cmake_definitions["CMAKE_SHARED_LINKER_FLAGS"])
        cmake_definitions.update({ "CMAKE_SHARED_LINKER_FLAGS" : shared_flags })

    f.addStep(
        steps.CMake(
            name            = f.makeStepName("cmake-configure"),
            path            = test_suite_src_dir,
            generator       = generator,
            definitions     = cmake_definitions,
            options         = cmake_options,
            description     = ["CMake configure"],
            haltOnFailure   = True,
            env             = env,
            workdir         = test_suite_obj_dir
        ))

    hint_suffix = f"-{hint}" if hint else ""
    # Build Commands.
    #NOTE: please note that the default target (.) cannot be specified by the IRenderable object.
    for target in targets:
        cmake_build_options = ["--build", "."]
        if target != ".":
            cmake_build_options.extend(["--target", target])
        if jobs:
            cmake_build_options.extend(["--", "-j", jobs])

        target_title = "default" if target == "." else target

        f.addStep(
            steps.CMake(
                name            = util.Interpolate("build-%(kw:title)s%(kw:hint)s",
                                                   title = target_title, hint = hint_suffix),
                options         = cmake_build_options,
                description     = ["Build target", target_title],
                haltOnFailure   = True,
                env             = env,
                workdir         = test_suite_obj_dir
            ))

        # Add a rsync step for each build target if the remote host has been specified
        # for the LLVM test suite.
        if remote_rsync:
            f.addStep(
                steps.CMake(
                    name            = util.Interpolate("rsync-%(kw:title)s%(kw:hint)s",
                                                       title = target_title, hint = hint_suffix),
                    options         = ["--build", ".", "--target", "rsync"],
                    description     = ["Rsync to target", target_title],
                    haltOnFailure   = True,
                    env             = env,
                    workdir         = test_suite_obj_dir
                ))

    # Check Commands.
    for target in checks:
        f.addStep(
            LitTestCommand(
                name            = util.Interpolate("test-%(kw:title)s%(kw:hint)s",
                                                   title = target, hint = hint_suffix),
                command         = [steps.CMake.DEFAULT_CMAKE, "--build", ".", "--target", target],
                description     = ["Running test:", target],
                descriptionDone = ["Running test:", target, "completed"],
                haltOnFailure   = False, # We want to test as much as we could.
                env             = env,
                workdir         = test_suite_obj_dir
            ))

    return f

# The DebugifyBuilder needs to know the test-suite build directory, so we share the build directory via this variable.
test_suite_build_path = 'test/build-test-suite'

# This builder is uses UnifiedTreeBuilders and adds running
# llvm-test-suite with cmake and ninja step.

def addTestSuiteStep(
            f,
            compiler_dir = '.',
            env = None,
            lit_args = None,
            extra_configure_args = None,
            **kwargs):

    # Set defaults
    if env is None:
        env = {}
    if lit_args is None:
        lit_args = []

    cc = util.Interpolate('-DCMAKE_C_COMPILER=%(prop:builddir)s/'+compiler_dir+'/bin/clang')
    cxx = util.Interpolate('-DCMAKE_CXX_COMPILER=%(prop:builddir)s/'+compiler_dir+'/bin/clang++')
    lit = util.Interpolate('%(prop:builddir)s/' + compiler_dir + '/bin/llvm-lit')
    test_suite_base_dir = util.Interpolate('%(prop:builddir)s/' + 'test')
    test_suite_src_dir = util.Interpolate('%(prop:builddir)s/' + 'test/test-suite')
    test_suite_workdir = util.Interpolate('%(prop:builddir)s/' + test_suite_build_path)
    cmake_lit_arg = util.Interpolate('-DTEST_SUITE_LIT:FILEPATH=%(prop:builddir)s/' + compiler_dir + '/bin/llvm-lit')
    # used for cmake building test-suite step
    if extra_configure_args is not None:
        cmake_args = extra_configure_args[:]
    else:
        cmake_args = list()
    cmake_args.extend([cc, cxx, cmake_lit_arg])

    # always clobber the build directory to test each new compiler
    f.addStep(ShellCommand(name='Clean Test Suite Build dir',
                           command=['rm', '-rf', test_suite_workdir],
                           haltOnFailure=True,
                           description='Removing the Test Suite build directory',
                           workdir=test_suite_base_dir,
                           env=env))

    f.addGetSourcecodeForProject(
        project='test-suite',
        src_dir=test_suite_src_dir,
        alwaysUseLatest=True)

    f.addStep(CmakeCommand(name='cmake Test Suite',
                           haltOnFailure=True,
                           description='Running cmake on Test Suite dir',
                           workdir=test_suite_workdir,
                           options=cmake_args,
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
           extra_test_suite_configure_args = None,
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
           extra_configure_args=extra_test_suite_configure_args,
           **kwargs)

    return f

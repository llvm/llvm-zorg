from buildbot.plugins import steps, util
from buildbot.steps.shell import SetPropertyFromCommand
from buildbot.process.properties import WithProperties

from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.commands.NinjaCommand import NinjaCommand
from zorg.buildbot.commands.LitTestCommand import LitTestCommand

from zorg.buildbot.conditions.FileConditions import FileDoesNotExist
from zorg.buildbot.process.factory import LLVMBuildFactory

import zorg.buildbot.builders.Util as builders_util

def getLLVMBuildFactoryAndPrepareForSourcecodeSteps(
           depends_on_projects = None,
           llvm_srcdir = None,
           obj_dir = None,
           install_dir = None,
           cleanBuildRequested = None,
           env = None,
           **kwargs):

    def cleanBuildRequestedByProperty(step):
        return step.build.getProperty("clean")

    if cleanBuildRequested is None:
        # We want a clean checkout only if requested by the property.
        cleanBuildRequested = cleanBuildRequestedByProperty

    f = LLVMBuildFactory(
            depends_on_projects=depends_on_projects,
            llvm_srcdir=llvm_srcdir,
            obj_dir=obj_dir,
            install_dir=install_dir,
            cleanBuildRequested=cleanBuildRequested,
            **kwargs) # Pass through all the extra arguments.

    # Remove the source code for a clean checkout if requested by property.
    # TODO: Some Windows workers do not handle RemoveDirectory command well.
    # So, consider running "rmdir /S /Q <dir>" if the build runs on Windows.
    f.addStep(steps.RemoveDirectory(name='clean-src-dir',
              dir=f.monorepo_dir,
              haltOnFailure=False,
              flunkOnFailure=False,
              doStepIf=cleanBuildRequestedByProperty,
              ))

    return f

def getLLVMBuildFactoryAndSourcecodeSteps(
           depends_on_projects = None,
           llvm_srcdir = None,
           obj_dir = None,
           install_dir = None,
           cleanBuildRequested = None,
           **kwargs):

    f = getLLVMBuildFactoryAndPrepareForSourcecodeSteps(
            depends_on_projects=depends_on_projects,
            llvm_srcdir=llvm_srcdir,
            obj_dir=obj_dir,
            install_dir=install_dir,
            cleanBuildRequested=cleanBuildRequested,
            **kwargs) # Pass through all the extra arguments.

    # Get the source code.
    f.addGetSourcecodeSteps(**kwargs)

    return f

def addCmakeSteps(
           f,
           cleanBuildRequested,
           obj_dir,
           generator=None,
           install_dir = None,
           extra_configure_args = None,
           env = None,
           stage_name = None,
           **kwargs):

    # Make a local copy of the configure args, as we are going to modify that.
    if extra_configure_args:
        cmake_args = extra_configure_args[:]
    else:
        cmake_args = list()

    if obj_dir is None:
        obj_dir = f.obj_dir

    # This is an incremental build, unless otherwise has been requested.
    # Remove obj and install dirs for a clean build.
    # TODO: Some Windows workers do not handle RemoveDirectory command well.
    # So, consider running "rmdir /S /Q <dir>" if the build runs on Windows.
    f.addStep(steps.RemoveDirectory(name='clean-%s-dir' % obj_dir,
              dir=obj_dir,
              haltOnFailure=False,
              flunkOnFailure=False,
              doStepIf=cleanBuildRequested,
              ))

    CmakeCommand.applyDefaultOptions(cmake_args, [
        ('-DLLVM_ENABLE_PROJECTS=', ";".join(f.depends_on_projects)),
        ])

    if install_dir:
        install_dir_rel = LLVMBuildFactory.pathRelativeTo(
                              install_dir,
                              obj_dir)
        CmakeCommand.applyRequiredOptions(cmake_args, [
            ('-DCMAKE_INSTALL_PREFIX=', install_dir_rel),
            ])

        f.addStep(steps.RemoveDirectory(name='clean-%s-dir' % install_dir,
              dir=install_dir,
              haltOnFailure=False,
              flunkOnFailure=False,
              doStepIf=cleanBuildRequested,
              ))

    # Reconcile the cmake options for this build.

    # Set proper defaults.
    CmakeCommand.applyDefaultOptions(cmake_args, [
        ('-DCMAKE_BUILD_TYPE=',        'Release'),
        ('-DLLVM_ENABLE_ASSERTIONS=',  'ON'),
        ('-DLLVM_LIT_ARGS=',           '-v -vv'),
        ])

    # Create configuration files with cmake, unless this has been already done
    # for an incremental build.
    if stage_name:
        step_name = "cmake-configure-%s" % stage_name
    else:
        stage_name = ""
        step_name = "cmake-configure"

    src_dir = LLVMBuildFactory.pathRelativeTo(f.llvm_srcdir, obj_dir)

    # Make a local copy of the configure args, as we are going to modify that.
    definitions = dict()
    options = list()
    for d in  cmake_args:
        if isinstance(d, str) and d.startswith("-D"):
            k,v = d[2:].split('=', 1)
            definitions[k] = v
        else:
            options.append(d)

    f.addStep(CmakeCommand(name=step_name,
                          haltOnFailure=True,
                          description=["Cmake", "configure", stage_name],
                          generator=generator,
                          definitions=definitions,
                          options=options,
                          path=src_dir,
                          env=env or {},
                          workdir=obj_dir,
                          **kwargs # Pass through all the extra arguments.
                          ))

def addNinjaSteps(
           f,
           obj_dir = None,
           targets = None,
           checks = None,
           install_dir = None,
           env = None,
           stage_name = None,
           **kwargs):

    if obj_dir is None:
        obj_dir = f.obj_dir

    if stage_name:
        step_name = "{}-".format(stage_name)
        step_description=["Build", stage_name]
    else:
        stage_name = ""
        step_name = ""
        step_description=["Build"]

    if targets:
        step_name = "build-{}{}".format(step_name, "-".join(targets))
        step_description.extend(targets)
    else:
        step_name = "build-{}unified-tree".format(step_name)
        step_description.extend(["unified", "tree"])

    # Build the unified tree.
    f.addStep(NinjaCommand(name=step_name,
                           haltOnFailure=True,
                           targets=targets,
                           description=step_description,
                           env=env or {},
                           workdir=obj_dir,
                           **kwargs # Pass through all the extra arguments.
                           ))

    # Test just built components if requested.
    # Note: At this point env could be None, a dictionary, or a Property object.
    if isinstance(env, dict):
        check_env = env.copy() if env else dict()
        check_env['NINJA_STATUS'] = check_env.get('NINJA_STATUS', "%e [%u/%r/%f] ")
    else:
        check_env = env or {}

    for check in checks:
        f.addStep(LitTestCommand(name="test-%s%s" % (step_name, check),
                                 command=['ninja', check],
                                 description=[
                                   "Test", "just", "built", "components", "for",
                                   check,
                                 ],
                                 env=check_env,
                                 workdir=obj_dir,
                                 **kwargs # Pass through all the extra arguments.
                                 ))

    # Install just built components
    if install_dir:
        # TODO: Run this step only if none of the prevous failed.
        f.addStep(NinjaCommand(name="install-%sall" % step_name,
                               targets=["install"],
                               description=["Install", "just", "built", "components"],
                               env=env or {},
                               workdir=obj_dir,
                               **kwargs # Pass through all the extra arguments.
                               ))

def getCmakeBuildFactory(
           depends_on_projects = None,
           llvm_srcdir = None,
           obj_dir = None,
           install_dir = None,
           clean = False,
           extra_configure_args = None,
           env = None,
           **kwargs):

    f = getLLVMBuildFactoryAndSourcecodeSteps(
            depends_on_projects=depends_on_projects,
            llvm_srcdir=llvm_srcdir,
            obj_dir=obj_dir,
            install_dir=install_dir,
            **kwargs) # Pass through all the extra arguments.

    cleanBuildRequested = lambda step: step.build.getProperty("clean", default=step.build.getProperty("clean_obj")) or clean
    addCmakeSteps(
        f,
        cleanBuildRequested=cleanBuildRequested,
        obj_dir=f.obj_dir,
        install_dir=f.install_dir,
        extra_configure_args=extra_configure_args,
        env=env,
        **kwargs)

    return f


def getCmakeWithNinjaBuildFactory(
           depends_on_projects = None,
           targets = None,
           llvm_srcdir = None,
           obj_dir = None,
           checks = None,
           install_dir = None,
           clean = False,
           extra_configure_args = None,
           env = None,
           **kwargs):

    # Make a local copy of the configure args, as we are going to modify that.
    if extra_configure_args:
        cmake_args = extra_configure_args[:]
    else:
        cmake_args = list()

    if checks is None:
        checks = ['check-all']

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        'TERM' : 'dumb' # Be cautious and disable color output from all tools.
    }
    if env:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    # Some options are required for this build no matter what.
    CmakeCommand.applyRequiredOptions(cmake_args, [
        ('-G',                      'Ninja'),
        ])

    f = getCmakeBuildFactory(
            depends_on_projects=depends_on_projects,
            llvm_srcdir=llvm_srcdir,
            obj_dir=obj_dir,
            install_dir=install_dir,
            clean=clean,
            extra_configure_args=cmake_args,
            env=merged_env,
            **kwargs) # Pass through all the extra arguments.

    addNinjaSteps(
           f,
           obj_dir=f.obj_dir,
           targets=targets,
           checks=checks,
           install_dir=f.install_dir,
           env=merged_env,
           **kwargs)

    return f

def getCmakeWithNinjaWithMSVCBuildFactory(
           depends_on_projects = None,
           targets = None,
           llvm_srcdir = None,
           obj_dir = None,
           checks = None,
           install_dir = None,
           clean = False,
           extra_configure_args = None,
           # VS tools environment variable if using MSVC. For example,
           # %VS140COMNTOOLS% selects the 2015 toolchain.
           vs=None,
           target_arch=None,
           env = None,
           **kwargs):

    assert not env, "Can't have custom builder env vars with MSVC build"

    # Make a local copy of the configure args, as we are going to modify that.
    if extra_configure_args:
        cmake_args = extra_configure_args[:]
    else:
        cmake_args = list()

    if checks is None:
        checks = ['check-all']

    f = getLLVMBuildFactoryAndSourcecodeSteps(
            depends_on_projects=depends_on_projects,
            llvm_srcdir=llvm_srcdir,
            obj_dir=obj_dir,
            install_dir=install_dir,
            **kwargs) # Pass through all the extra arguments.

    f.addStep(SetPropertyFromCommand(
        command=builders_util.getVisualStudioEnvironment(vs, target_arch),
        extract_fn=builders_util.extractVSEnvironment))
    env = util.Property('vs_env')

    cleanBuildRequested = lambda step: step.build.getProperty("clean", default=step.build.getProperty("clean_obj")) or clean

    addCmakeSteps(
        f,
        generator='Ninja',
        cleanBuildRequested=cleanBuildRequested,
        obj_dir=f.obj_dir,
        install_dir=f.install_dir,
        extra_configure_args=cmake_args,
        env=env,
        **kwargs)

    addNinjaSteps(
           f,
           targets=targets,
           obj_dir=obj_dir,
           checks=checks,
           install_dir=f.install_dir,
           env=env,
           **kwargs)

    return f

def getCmakeWithNinjaMultistageBuildFactory(
           depends_on_projects = None,
           llvm_srcdir = None,
           obj_dir = None,
           checks = None,
           install_dir = None,
           clean = False,
           extra_configure_args = None,
           env = None,
           stages=2,
           stage_names=None,
           **kwargs):

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        'TERM' : 'dumb' # Be cautious and disable color output from all tools.
    }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    # Make a local copy of the configure args, as we are going to modify that.
    if extra_configure_args:
        cmake_args = extra_configure_args[:]
    else:
        cmake_args = list()

    assert stages > 1, "It should be at least 2 stages in a multistage build."
    if stage_names is None:
        stage_names = list()
        for i in range(1, stages + 1):
            stage_names.append("stage%s" % i)
    else:
        assert len(stage_names) == stages, "Please specify names for none or all of the requested stages."

    if obj_dir is None:
        obj_dir = "build"
    if install_dir is None:
        install_dir = "install"

    if checks is None:
        checks = ['check-all']

    stage_objdirs = list()
    stage_installdirs = list()
    for s in stage_names:
        stage_objdirs.append("%s/%s" % (obj_dir, s))
        stage_installdirs.append("%s/%s" % (install_dir, s))

    f = getLLVMBuildFactoryAndPrepareForSourcecodeSteps(
            depends_on_projects=depends_on_projects,
            llvm_srcdir=llvm_srcdir,
            obj_dir=obj_dir,
            install_dir=install_dir,
            env=merged_env,
            stage_objdirs=stage_objdirs,
            stage_installdirs=stage_installdirs,
            stage_names=stage_names,
            **kwargs) # Pass through all the extra arguments.

    # Get the source code.
    # We have consumed kwargs specific to this factory, so
    # it is safe to pass all the remaining kwargs down.
    f.addGetSourcecodeSteps(**kwargs)

    # Set proper defaults.
    CmakeCommand.applyDefaultOptions(cmake_args, [
        ('-DCMAKE_BUILD_TYPE=',        'Release'),
        ('-DLLVM_BUILD_TESTS=',        'ON'),
        ('-DLLVM_ENABLE_ASSERTIONS=',  'OFF'),
        ('-DLLVM_OPTIMIZED_TABLEGEN=', 'ON'),
        ])

    if 'clang' in depends_on_projects:
        CmakeCommand.applyDefaultOptions(cmake_args, [
            ('-DCLANG_BUILD_EXAMPLES=',    'OFF'),
            ])

    # The stage 1 is special, though. We use the system compiler and
    # do incremental build, unless a clean one has been requested.
    cmake_args_stage1 = cmake_args[:]
    CmakeCommand.applyDefaultOptions(cmake_args_stage1, [
        # Do not expect warning free build by the system toolchain.
        ('-DLLVM_ENABLE_WERROR=',      'OFF'),
        ])

    cleanBuildRequested = lambda step: step.build.getProperty("clean", default=step.build.getProperty("clean_obj")) or clean

    addCmakeSteps(
           f,
           generator='Ninja',
           cleanBuildRequested=cleanBuildRequested,
           obj_dir=stage_objdirs[0],
           install_dir=stage_installdirs[0],
           extra_configure_args=cmake_args_stage1,
           env=merged_env,
           stage_name=stage_names[0],
           **kwargs)

    addNinjaSteps(
           f,
           obj_dir=stage_objdirs[0],
           checks=checks,
           install_dir=stage_installdirs[0],
           env=merged_env,
           stage_name=stage_names[0],
           **kwargs)

    # Build the rest stage by stage, using just built compiler to compile
    # the next stage.
    CmakeCommand.applyDefaultOptions(cmake_args, [
            # We should be warnings free when use just built compiler.
            ('-DLLVM_ENABLE_WERROR=', 'ON'),
            ])
    # If we build LLD, we would link with LLD.
    # Otherwise we link with a system linker.
    if 'lld' in f.depends_on_projects:
        CmakeCommand.applyDefaultOptions(cmake_args, [
            ('-DLLVM_ENABLE_LLD=', 'ON'),
            ])

    for stage_idx in range(1, stages):

        # Directories to use in this stage.
        obj_dir = f.stage_objdirs[stage_idx]
        src_dir = LLVMBuildFactory.pathRelativeTo(f.llvm_srcdir, obj_dir)
        install_dir = LLVMBuildFactory.pathRelativeTo(f.stage_installdirs[stage_idx], obj_dir)
        staged_install = f.stage_installdirs[stage_idx - 1]

        # Configure the compiler to use in this stage.
        cmake_args_stageN = cmake_args[:]
        CmakeCommand.applyRequiredOptions(cmake_args_stageN, [
            ('-DCMAKE_INSTALL_PREFIX=', install_dir),
            ])
        cmake_args_stageN.append(
            util.WithProperties(
                "-DCMAKE_CXX_COMPILER=%(builddir)s/" + staged_install + "/bin/clang++"
            ))
        cmake_args_stageN.append(
            util.WithProperties(
                "-DCMAKE_C_COMPILER=%(builddir)s/" + staged_install + "/bin/clang"
            ))

        addCmakeSteps(
           f,
           generator='Ninja',
           cleanBuildRequested=True, # We always do a clean build for the staged builds.
           obj_dir=stage_objdirs[stage_idx],
           install_dir=stage_installdirs[stage_idx],
           extra_configure_args=cmake_args_stageN,
           env=merged_env,
           stage_name=stage_names[stage_idx],
           **kwargs)

        addNinjaSteps(
           f,
           obj_dir=stage_objdirs[stage_idx],
           checks=checks,
           install_dir=stage_installdirs[stage_idx],
           env=merged_env,
           stage_name=stage_names[stage_idx],
           **kwargs)

    return f

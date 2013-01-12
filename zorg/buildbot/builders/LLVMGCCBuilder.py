import buildbot
from buildbot.steps.source import SVN
from buildbot.steps.shell import Configure, WarningCountingShellCommand
from buildbot.steps.shell import ShellCommand, SetProperty
from buildbot.process.properties import WithProperties

from zorg.buildbot.commands.LitTestCommand import LitTestCommand

from Util import getConfigArgs

def getLLVMGCCBuildFactory(jobs='%(jobs)s', update=True, clean=True,
                           gxxincludedir=None,
                           triple=None, build=None, host=None, target=None,
                           useTwoStage=True, stage1_config='Release+Asserts',
                           stage2_config='Release+Asserts', make='make',
                           extra_configure_args=[], extra_languages=None,
                           verbose=False, env = {}, defaultBranch='trunk',
                           timeout=20, package_dst=None):
  if build or host or target:
    if not build or not host or not target:
      raise ValueError,"Must specify all of 'build', 'host', 'target' if used."
    if triple:
      raise ValueError,"Cannot specify 'triple' and 'build', 'host', 'target' options."
  elif triple:
    build = host = target = triple

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
                   'TERM' : 'dumb'     # Make sure Clang doesn't use color escape sequences.
                 }
    if env is not None:
        merged_env.update(env)  # Overwrite pre-set items with the given ones, so user can set anything.

  f = buildbot.process.factory.BuildFactory()

  # Determine the build directory.
  f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                             command=["pwd"],
                                             property    = "builddir",
                                             description = "set build dir",
                                             workdir     = ".",
                                             env         = merged_env))

  # Get the sources.
  if update:
    f.addStep(SVN(name='svn-llvm',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch = defaultBranch,
                  workdir       = "llvm.src"))

    f.addStep(SVN(name='svn-llvm-gcc',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm-gcc-4.2/',
                  defaultBranch = defaultBranch,
                  workdir       = "llvm-gcc.src"))

  # Clean up llvm (stage 1).
  if clean:
    f.addStep(ShellCommand(name="rm-llvm.obj.stage1",
                           command=["rm", "-rf", "llvm.obj"],
                           haltOnFailure = True,
                           description   = ["rm build dir",
                                            "llvm",
                                            "(stage 1)"],
                           workdir       = ".",
                           env           = merged_env))

  # Configure llvm (stage 1).
  base_llvm_configure_args = [WithProperties("%(builddir)s/llvm.src/configure")]
  if build:
    base_llvm_configure_args.append('--build=' + build)
    base_llvm_configure_args.append('--host=' + host)
    base_llvm_configure_args.append('--target=' + target)
  stage_configure_args = getConfigArgs(stage1_config)
  f.addStep(Configure(name='configure.llvm.stage1',
                      command=base_llvm_configure_args +
                              stage_configure_args +
                              ["--without-llvmgcc",
                               "--without-llvmgxx"],
                      description = [ "configure",
                                      "llvm",
                                      "(stage 1)",
                                      stage1_config ],
                      workdir     = "llvm.obj",
                      env         = merged_env))

  # Build llvm (stage 1).
  base_llvm_make_args = ['nice', '-n', '10',
                         make, WithProperties("-j%s" % jobs)]
  if verbose:
    base_llvm_make_args.append('VERBOSE=1')
  f.addStep(WarningCountingShellCommand(name = "compile.llvm.stage1",
                                        command       = base_llvm_make_args,
                                        haltOnFailure = True,
                                        description   = ["compile",
                                                         "llvm",
                                                         "(stage 1)",
                                                         stage1_config],
                                        workdir       = "llvm.obj",
                                        env           = merged_env,
                                        timeout       = timeout * 60))

  # Run LLVM tests (stage 1).
  f.addStep(LitTestCommand(name = 'test.llvm.stage1',
                             command = [make, "check-lit", "VERBOSE=1"],
                             description     = ["testing", "llvm"],
                             descriptionDone = ["test",    "llvm"],
                             workdir         = 'llvm.obj',
                             env             = merged_env))

  # Clean up llvm-gcc.
  if clean:
    f.addStep(ShellCommand(name="rm-llvm-gcc.obj.stage1",
                           command=["rm", "-rf", "llvm-gcc.obj"],
                           haltOnFailure = True,
                           description   = ["rm build dir",
                                            "llvm-gcc"],
                           workdir       = ".",
                           env           = merged_env))

  # Configure llvm-gcc.
  base_llvmgcc_configure_args = ["../llvm-gcc.src/configure"]
  llvmgcc_languages = "--enable-languages=c,c++"
  if extra_languages:
    llvmgcc_languages = llvmgcc_languages + "," + extra_languages
  base_llvmgcc_configure_args.append(llvmgcc_languages)
  if gxxincludedir:
    base_llvmgcc_configure_args.append('--with-gxx-include-dir=' + gxxincludedir)
  base_llvmgcc_configure_args.extend(extra_configure_args)
  if build:
    base_llvmgcc_configure_args.append('--build=' + build)
    base_llvmgcc_configure_args.append('--host=' + host)
    base_llvmgcc_configure_args.append('--target=' + target)
  f.addStep(Configure(name='configure.llvm-gcc.stage1',
                      command=(base_llvmgcc_configure_args +
                               ["--program-prefix=llvm-",
                                WithProperties("--prefix=%(builddir)s/llvm-gcc.install"),                      
                                WithProperties("--enable-llvm=%(builddir)s/llvm.obj")]),
                      haltOnFailure = True,
                      description   = ["configure",
                                       "llvm-gcc",
                                       "(stage 1)"],
                      workdir       = "llvm-gcc.obj",
                      env           = merged_env))

  # Build llvm-gcc.
  f.addStep(WarningCountingShellCommand(name="compile.llvm-gcc.stage1",
                                        command=['nice', '-n', '10',
                                                 make, WithProperties("-j%s" % jobs)],
                                        haltOnFailure = True,
                                        description   = ["compile",
                                                         "llvm-gcc"],
                                        workdir       = "llvm-gcc.obj",
                                        env           = merged_env,
                                        timeout       = timeout * 60))

  # Clean up llvm-gcc install.
  if clean:
    f.addStep(ShellCommand(name="rm-llvm-gcc.install.stage1",
                           command=["rm", "-rf", "llvm-gcc.install"],
                           haltOnFailure = True,
                           description   = ["rm install dir",
                                            "llvm-gcc"],
                           workdir       = ".",
                           env           = merged_env))

  # Install llvm-gcc.
  f.addStep(WarningCountingShellCommand(name="install.llvm-gcc.stage1",
                                        command=['nice', '-n', '10',
                                                 make, 'install'],
                                        haltOnFailure = True,
                                        description   = ["install",
                                                         "llvm-gcc"],
                                        workdir       = "llvm-gcc.obj",
                                        env           = merged_env))

  # We are done if not doing a two-stage build.
  if not useTwoStage:
    return f

  # Clean up llvm (stage 2).
  if clean:
    f.addStep(ShellCommand(name="rm-llvm.obj.stage2",
                           command=["rm", "-rf", "llvm.obj.2"],
                           haltOnFailure = True,
                           description   = ["rm build dir",
                                            "llvm",
                                            "(stage 2)"],
                           workdir       = ".",
                           env           = merged_env))

  # Configure llvm (stage 2).
  stage_configure_args = getConfigArgs(stage2_config)
  local_env = dict(merged_env)
  local_env['CC'] = WithProperties("%(builddir)s/llvm-gcc.install/bin/llvm-gcc")
  local_env['CXX'] = WithProperties("%(builddir)s/llvm-gcc.install/bin/llvm-g++")
  f.addStep(Configure(name="configure.llvm.stage2",
                      command=base_llvm_configure_args + 
                              stage_configure_args +
                              [WithProperties("--with-llvmgcc=%(builddir)s/llvm-gcc.install/bin/llvm-gcc"),
                               WithProperties("--with-llvmgxx=%(builddir)s/llvm-gcc.install/bin/llvm-g++")],
                      haltOnFailure = True,
                      description   = ["configure",
                                       "llvm",
                                       "(stage 2)",
                                       stage2_config],
                      workdir      = "llvm.obj.2",
                      env          = local_env))

  # Build LLVM (stage 2).
  f.addStep(WarningCountingShellCommand(name = "compile.llvm.stage2",
                                        command = base_llvm_make_args,
                                        haltOnFailure = True,
                                        description   = ["compile",
                                                         "llvm",
                                                         "(stage 2)",
                                                         stage2_config],
                                        workdir       = "llvm.obj.2",
                                        env           = merged_env,
                                        timeout       = timeout * 60))

  # Run LLVM tests (stage 2).
  f.addStep(LitTestCommand(name = 'test.llvm.stage2',
                             command = [make, "check-lit", "VERBOSE=1"],
                             description     = ["testing", "llvm", "(stage 2)"],
                             descriptionDone = ["test",    "llvm", "(stage 2)"],
                             workdir         = 'llvm.obj.2',
                             env             = merged_env))

  # Clean up llvm-gcc (stage 2).
  if clean:
    f.addStep(ShellCommand(name="rm-llvm-gcc.obj.stage2",
                           command=["rm", "-rf", "llvm-gcc.obj.2"],
                           haltOnFailure = True,
                           description   = ["rm build dir",
                                            "llvm-gcc",
                                            "(stage 2)"],
                           workdir       = ".",
                           env           = merged_env))

  # Configure llvm-gcc (stage 2).
  local_env = dict(merged_env)
  local_env['CC'] = WithProperties("%(builddir)s/llvm-gcc.install/bin/llvm-gcc")
  local_env['CXX'] = WithProperties("%(builddir)s/llvm-gcc.install/bin/llvm-g++")
  f.addStep(Configure(name = 'configure.llvm-gcc.stage2',
                      command=base_llvmgcc_configure_args + [
                               "--program-prefix=llvm.2-",
                               WithProperties("--prefix=%(builddir)s/llvm-gcc.install.2"),
                               WithProperties("--enable-llvm=%(builddir)s/llvm.obj.2")],
                      haltOnFailure = True,
                      description   = ["configure",
                                       "llvm-gcc",
                                       "(stage 2)"],
                      workdir       = "llvm-gcc.obj.2",
                      env           = local_env))

  # Build llvm-gcc (stage 2).
  f.addStep(WarningCountingShellCommand(name="compile.llvm-gcc.stage2",
                                        command=['nice', '-n', '10',
                                                 make, WithProperties("-j%s" % jobs)],
                                        haltOnFailure = True,
                                        description   = ["compile",
                                                         "llvm-gcc",
                                                         "(stage 2)"],
                                        workdir       = "llvm-gcc.obj.2",
                                        env           = merged_env,
                                        timeout       = timeout * 60))

  # Clean up llvm-gcc install (stage 2).
  if clean:
    f.addStep(ShellCommand(name="rm-llvm-gcc.install.stage2",
                           command=["rm", "-rf", "llvm-gcc.install.2"],
                           haltOnFailure = True,
                           description   = ["rm install dir",
                                            "llvm-gcc",
                                            "(stage 2)"],
                           workdir       = ".",
                           env           = merged_env))

  # Install llvm-gcc.
  f.addStep(WarningCountingShellCommand(name="install.llvm-gcc.stage2",
                                        command = ['nice', '-n', '10',
                                                   make, 'install'],
                                        haltOnFailure = True,
                                        description   = ["install",
                                                         "llvm-gcc",
                                                         "(stage 2)"],
                                        workdir       = "llvm-gcc.obj.2",
                                        env           = merged_env))
  if package_dst:
    addPackageStep(f, package_dst, obj_path = 'llvm-gcc.install.2', env = merged_env)

  return f

import os
def addPackageStep(f, package_dst,
                   obj_path,
                   info_string = '%(phase_id)s',
                   env         = {}):

  # Package and upload.
    name = WithProperties(
      os.path.join("%(builddir)s", obj_path,
                   "llvm-gcc-%s.tar.gz" % info_string))

    f.addStep(ShellCommand(name           = 'pkg.tar',
                           description    = "tar root",
                           command        = ["tar", "zcvf", name, "./"],
                           workdir        = obj_path,
                           env            = env,
                           warnOnFailure  = True,
                           flunkOnFailure = False,
                           haltOnFailure  = False))

    f.addStep(ShellCommand(name           = 'pkg.upload',
                           description    = "upload root",
                           command        = ["scp", name, package_dst],
                           workdir        = ".",
                           env            = env,
                           warnOnFailure  = True,
                           flunkOnFailure = False,
                           haltOnFailure  = False))

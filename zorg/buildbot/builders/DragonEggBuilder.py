import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import Configure, ShellCommand
from buildbot.steps.shell import WarningCountingShellCommand
from buildbot.process.properties import WithProperties

def getCCSetting(gcc, gxx):
  cc_settings = []
  if gcc is not None:
    cc_settings += [WithProperties('CC=' + gcc)]
  if gxx is not None:
    cc_settings += [WithProperties('CXX=' + gxx)]
  return cc_settings

def extractSearchPaths(rc, stdout, stderr):
  mapping = {}
  for l in stdout.split('\n'):
    vals = l.split(': =', 1)
    if len(vals) == 2:
      mapping['gcc_' + vals[0]] = vals[1]
  return mapping

def getDragonEggBootstrapFactory(gcc_repository, extra_languages=[],
                                 extra_gcc_configure_args=[],
                                 extra_llvm_configure_args=[],
                                 clean=True, env={}, jobs='%(jobs)s',
                                 timeout=20):
    # Add gcc configure arguments required by the plugin.
    gcc_configure_args = extra_gcc_configure_args + ['--enable-plugin',
      '--enable-lto', ','.join(['--enable-languages=c,c++'] + extra_languages)]

    llvm_configure_args = extra_llvm_configure_args

    f = buildbot.process.factory.BuildFactory()

    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(name='get_builddir',
                                               command=['pwd'],
                                               property='builddir',
                                               description='set build dir',
                                               workdir='.', env=env))

    # Checkout LLVM sources.
    llvm_src_dir = 'llvm.src'
    f.addStep(SVN(name='svn-llvm', mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk', workdir=llvm_src_dir, env=env))

    # Checkout DragonEgg sources.
    dragonegg_src_dir = 'dragonegg.src'
    f.addStep(SVN(name='svn-dragonegg', mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/dragonegg/',
                  defaultBranch='trunk', workdir=dragonegg_src_dir, env=env))

    # Checkout GCC.  This is usually a specific known good revision (supplied by
    # appending @revision to the URL).  The SVN step can't handle that.  As it
    # provides no mechanism at all for checking out a specific revision, just
    # run the command directly here.
    gcc_src_dir = 'gcc.src'
    svn_co = ['svn', 'checkout', gcc_repository, gcc_src_dir]
    f.addStep(ShellCommand(name='svn-gcc',
                           command=svn_co,
                           haltOnFailure=True,
                           workdir='.', env=env))

    # Do the boostrap.
    cur_env = env
    prev_gcc = None     # C compiler built during the previous stage.
    prev_gxx = None     # C++ compiler built during the previous stage.
    prev_plugin = None  # Plugin built during the previous stage.
    for stage in 'stage1', 'stage2', 'stage3':

      # Build and install GCC.
      gcc_obj_dir = 'gcc.obj.%s' % stage
      gcc_install_dir = 'gcc.install' # Name is embedded in object files, so if
                                      # per-stage would get bootstrap comparison
                                      # failures.
      if clean:
          f.addStep(ShellCommand(name='rm-%s' % gcc_obj_dir,
                                 command=['rm', '-rf', gcc_obj_dir],
                                 haltOnFailure=True,
                                 description=['rm build dir', 'gcc', stage],
                                 workdir='.', env=cur_env))
      f.addStep(Configure(name='configure.gcc.%s' % stage,
                          command=(['../' + gcc_src_dir + '/configure',
                                    WithProperties('--prefix=%%(builddir)s/%s' % gcc_install_dir)] +
                                   gcc_configure_args + getCCSetting(prev_gcc, prev_gxx)),
                          haltOnFailure=True,
                          description=['configure', 'gcc', stage],
                          workdir=gcc_obj_dir, env=cur_env))
      f.addStep(WarningCountingShellCommand(name='compile.gcc.%s' % stage,
                                            command=['nice', '-n', '10',
                                                     'make', WithProperties('-j%s' % jobs)],
                                            haltOnFailure=True,
                                            description=['compile', 'gcc', stage],
                                            workdir=gcc_obj_dir, env=cur_env,
                                            timeout=timeout*60))
      f.addStep(WarningCountingShellCommand(name='install.gcc.%s' % stage,
                                            command=['nice', '-n', '10',
                                                     'make', 'install'],
                                            haltOnFailure=True,
                                            description=['install', 'gcc', stage],
                                            workdir=gcc_obj_dir, env=cur_env))

      # From this point on build everything using the just built GCC.
      prev_gcc = '%(builddir)s/'+gcc_install_dir+'/bin/gcc'
      prev_gxx = '%(builddir)s/'+gcc_install_dir+'/bin/g++'

      # The built libstdc++ and libgcc may well be more recent than the system
      # versions.  Set the library path so that programs compiled with the just
      # built GCC will start successfully, rather than failing due to missing
      # shared library dependencies.
      f.addStep(buildbot.steps.shell.SetProperty(name='gcc.search.paths.%s' % stage,
                                                 command=[WithProperties(prev_gcc),
                                                          '-print-search-dirs'],
                                                 extract_fn=extractSearchPaths,
                                                 haltOnFailure=True,
                                                 description=['gcc', 'search paths',
                                                              stage], env=cur_env))
      cur_env = cur_env.copy();
      if 'LD_LIBRARY_PATH' in env:
        cur_env['LD_LIBRARY_PATH'] = WithProperties('%(gcc_libraries)s'+':'+env['LD_LIBRARY_PATH'])
      else:
        cur_env['LD_LIBRARY_PATH'] = WithProperties('%(gcc_libraries)s')

      # Build everything using the DragonEgg plugin from the previous stage.
      if prev_plugin is not None:
        prev_gcc += ' -fplugin=' + prev_plugin
        prev_gxx += ' -fplugin=' + prev_plugin

      # Build LLVM with the just built GCC and install it.
      llvm_obj_dir = 'llvm.obj.%s' % stage
      llvm_install_dir = 'llvm.install' # Name is embedded in object files, so
                                        # if per-stage would get bootstrap
                                        # comparison failures.
      if clean:
          f.addStep(ShellCommand(name='rm-%s' % llvm_obj_dir,
                                 command=['rm', '-rf', llvm_obj_dir],
                                 haltOnFailure=True,
                                 description=['rm build dir', 'llvm', stage],
                                 workdir='.', env=cur_env))
      f.addStep(Configure(name='configure.llvm.%s' % stage,
                          command=(['../' + llvm_src_dir + '/configure',
                                    WithProperties('--prefix=%%(builddir)s/%s' % llvm_install_dir)] +
                                    llvm_configure_args + getCCSetting(prev_gcc, prev_gxx)),
                          haltOnFailure=True,
                          description=['configure', 'llvm', stage],
                          workdir=llvm_obj_dir, env=cur_env))
      f.addStep(WarningCountingShellCommand(name='compile.llvm.%s' % stage,
                                            command=['nice', '-n', '10',
                                                     'make', WithProperties('-j%s' % jobs)],
                                            haltOnFailure=True,
                                            description=['compile', 'llvm', stage],
                                            workdir=llvm_obj_dir, env=cur_env,
                                            timeout=timeout*60))
      f.addStep(WarningCountingShellCommand(name='install.llvm.%s' % stage,
                                            command=['nice', '-n', '10',
                                                     'make', 'install'],
                                            haltOnFailure=True,
                                            description=['install', 'llvm', stage],
                                            workdir=llvm_obj_dir, env=cur_env))

      # Build dragonegg with the just built LLVM and GCC.
      dragonegg_pre_obj_dir = 'dragonegg.obj.pre.%s' % stage
      if clean:
          f.addStep(ShellCommand(name='rm-%s' % dragonegg_pre_obj_dir,
                                 command=['rm', '-rf', dragonegg_pre_obj_dir],
                                 description=['rm build dir', 'dragonegg pre', stage],
                                 haltOnFailure=True, workdir='.', env=cur_env))
      f.addStep(WarningCountingShellCommand(
              name='compile.dragonegg.pre.%s' % stage,
              command=['nice', '-n', '10',
                       'make', '-f', '../' + dragonegg_src_dir + '/Makefile',
                       WithProperties('-j%s' % jobs),
                       WithProperties('GCC=%(builddir)s/'+gcc_install_dir+'/bin/gcc'),
                       WithProperties('LLVM_CONFIG=%(builddir)s/'+llvm_install_dir+'/bin/llvm-config'),
                       WithProperties('TOP_DIR=%(builddir)s/' + dragonegg_src_dir)
                       ] + getCCSetting(prev_gcc, prev_gxx),
              haltOnFailure=True,
              description=['compile', 'dragonegg pre', stage],
              workdir=dragonegg_pre_obj_dir, env=cur_env,
              timeout=timeout*60))
      prev_gcc = '%(builddir)s/'+gcc_install_dir+'/bin/gcc -fplugin=%(builddir)s/'+dragonegg_pre_obj_dir+'/dragonegg.so'
      prev_gxx = '%(builddir)s/'+gcc_install_dir+'/bin/g++ -fplugin=%(builddir)s/'+dragonegg_pre_obj_dir+'/dragonegg.so'

      # Now build dragonegg again using the just built dragonegg.
      dragonegg_obj_dir = 'dragonegg.obj.%s' % stage
      if clean:
          f.addStep(ShellCommand(name='rm-%s' % dragonegg_obj_dir,
                                 command=['rm', '-rf', dragonegg_obj_dir],
                                 description=['rm build dir', 'dragonegg', stage],
                                 haltOnFailure=True, workdir='.', env=cur_env))
      f.addStep(WarningCountingShellCommand(
              name='compile.dragonegg.%s' % stage,
              command=['nice', '-n', '10',
                       'make', '-f', '../' + dragonegg_src_dir + '/Makefile',
                       'DISABLE_VERSION_CHECK=1',
                       WithProperties('-j%s' % jobs),
                       WithProperties('GCC=%(builddir)s/'+gcc_install_dir+'/bin/gcc'),
                       WithProperties('LLVM_CONFIG=%(builddir)s/'+llvm_install_dir+'/bin/llvm-config'),
                       WithProperties('TOP_DIR=%(builddir)s/' + dragonegg_src_dir)
                       ] + getCCSetting(prev_gcc, prev_gxx),
              description=['compile', 'dragonegg', stage], haltOnFailure=True,
              workdir=dragonegg_obj_dir, env=cur_env, timeout=timeout*60))

      # Ensure that the following stages use the just built plugin.
      prev_plugin = '%(builddir)s/'+dragonegg_obj_dir+'/dragonegg.so'
      prev_gcc = '%(builddir)s/'+gcc_install_dir+'/bin/gcc -fplugin=' + prev_plugin
      prev_gxx = '%(builddir)s/'+gcc_install_dir+'/bin/g++ -fplugin=' + prev_plugin

    # Check that the dragonegg objects didn't change between stages 2 and 3.
    f.addStep(ShellCommand(name='compare.stages',
                           command=['sh', '-c', 'for O in *.o ; do ' +
                                    'cmp --ignore-initial=16 ' +
                                    '../dragonegg.obj.stage2/$O ' +
                                    '../dragonegg.obj.stage3/$O || exit 1 ; ' +
                                    'done'],
                           haltOnFailure=True,
                           description='compare stages 2 and 3',
                           workdir='dragonegg.obj.stage3', env=cur_env))

    return f

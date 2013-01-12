import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import Configure, ShellCommand
from buildbot.steps.shell import WarningCountingShellCommand
from buildbot.process.properties import WithProperties
from zorg.buildbot.commands.LitTestCommand import LitTestCommand
from zorg.buildbot.commands.NightlyTestCommand import NightlyTestCommand

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
                                 check_llvm=True, check_dragonegg=True,
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

    gcc_install_dir = 'gcc.install'     # Names are embedded in object files, so
    llvm_install_dir = 'llvm.install'   # would cause bootstrap comparison fails
                                        # if they were different for each stage.

    # Remove any install directories hanging over from a previous run.
    if clean:
        f.addStep(ShellCommand(name='rm-%s' % gcc_install_dir,
                               command=['rm', '-rf', gcc_install_dir],
                               haltOnFailure=True,
                               description=['rm install dir', 'gcc'],
                               workdir='.', env=env))
        f.addStep(ShellCommand(name='rm-%s' % llvm_install_dir,
                               command=['rm', '-rf', llvm_install_dir],
                               haltOnFailure=True,
                               description=['rm install dir', 'llvm'],
                               workdir='.', env=env))

    # Do the boostrap.
    cur_env = env
    prev_gcc = None     # C compiler built during the previous stage.
    prev_gxx = None     # C++ compiler built during the previous stage.
    prev_plugin = None  # Plugin built during the previous stage.
    for stage in 'stage1', 'stage2', 'stage3':

      # Build and install GCC.
      gcc_obj_dir = 'gcc.obj.%s' % stage
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
      if 'LIBRARY_PATH' in env:
        cur_env['LIBRARY_PATH'] = WithProperties('%(gcc_libraries)s'+':'+env['LIBRARY_PATH'])
      else:
        cur_env['LIBRARY_PATH'] = WithProperties('%(gcc_libraries)s')
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

      # Optionally run the LLVM testsuite.
      if check_llvm:
        f.addStep(LitTestCommand(name='check.llvm.%s' % stage,
                                   command=['nice', '-n', '10', 'make',
                                            WithProperties('LIT_ARGS=-v -j%s' % jobs),
                                            'check-all'
                                            ],
                                   description=['test', 'llvm', stage],
                                   haltOnFailure=True, workdir=llvm_obj_dir,
                                   env=cur_env, timeout=timeout*60))

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

      # Now build dragonegg again using the just built dragonegg.  The build is
      # always done in the same directory to ensure that object files built by
      # the different stages should be the same (the build directory name ends
      # up in object files via debug info), then moved to a per-stage directory.
      dragonegg_bld_dir = 'dragonegg.obj' # The common build directory.
      dragonegg_obj_dir = 'dragonegg.obj.%s' % stage # The per-stage directory.
      f.addStep(ShellCommand(name='rm-%s' % dragonegg_obj_dir,
                             command=['rm', '-rf', dragonegg_bld_dir,
                                      dragonegg_obj_dir],
                             description=['rm build dirs', 'dragonegg', stage],
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
              workdir=dragonegg_bld_dir, env=cur_env, timeout=timeout*60))
      f.addStep(ShellCommand(name='mv-%s' % dragonegg_obj_dir,
                             command=['mv', dragonegg_bld_dir,
                                      dragonegg_obj_dir],
                             description=['mv build dir', 'dragonegg', stage],
                             haltOnFailure=True, workdir='.', env=cur_env))

      # Optionally run the dragonegg testsuite.
      if check_dragonegg:
        f.addStep(LitTestCommand(name='check.dragonegg.%s' % stage,
                                   command=['nice', '-n', '10',
                                            'make', '-f', '../' + dragonegg_src_dir + '/Makefile',
                                            WithProperties('GCC=%(builddir)s/'+gcc_install_dir+'/bin/gcc'),
                                            WithProperties('LLVM_CONFIG=%(builddir)s/' +
                                                           llvm_install_dir + '/bin/llvm-config'),
                                            WithProperties('TOP_DIR=%(builddir)s/' + dragonegg_src_dir),
                                            WithProperties('LIT_ARGS=-v -j%s' % jobs),
                                            'check'
                                            ],
                                   description=['test', 'dragonegg', stage],
                                   haltOnFailure=True, workdir=dragonegg_obj_dir,
                                   env=cur_env, timeout=timeout*60))

      # Ensure that the following stages use the just built plugin.
      prev_plugin = '%(builddir)s/'+dragonegg_obj_dir+'/dragonegg.so'
      prev_gcc = '%(builddir)s/'+gcc_install_dir+'/bin/gcc -fplugin=' + prev_plugin
      prev_gxx = '%(builddir)s/'+gcc_install_dir+'/bin/g++ -fplugin=' + prev_plugin

    # Check that the dragonegg objects didn't change between stages 2 and 3.
    f.addStep(ShellCommand(name='compare.stages',
                           command=['sh', '-c', 'for O in *.o ; do cmp ' +
                                    '../dragonegg.obj.stage2/$O ' +
                                    '../dragonegg.obj.stage3/$O || exit 1 ; ' +
                                    'done'],
                           haltOnFailure=True,
                           description='compare stages 2 and 3',
                           workdir='dragonegg.obj.stage3', env=cur_env))

    return f


def getDragonEggNightlyTestBuildFactory(gcc='gcc', gxx='g++',
                                        llvm_configure_args=[],
                                        testsuite_configure_args=[],
                                        xfails=[], clean=True, env={},
                                        jobs='%(jobs)s', timeout=20):
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

    # Checkout the test-suite sources.
    testsuite_src_dir = 'test-suite.src'
    f.addStep(SVN(name='svn-test-suite', mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/test-suite/',
                  defaultBranch='trunk', workdir=testsuite_src_dir, env=env))

    # Build and install LLVM.
    llvm_obj_dir = 'llvm.obj'
    llvm_install_dir = 'llvm.install'
    if clean:
        f.addStep(ShellCommand(name='rm-%s' % llvm_obj_dir,
                               command=['rm', '-rf', llvm_obj_dir,
                                        llvm_install_dir],
                               description='rm build dir llvm',
                               haltOnFailure=True, workdir='.', env=env))
    f.addStep(Configure(name='configure.llvm',
                        command=(['../' + llvm_src_dir + '/configure',
                                  WithProperties('--prefix=%%(builddir)s/%s' % llvm_install_dir)] +
                                 llvm_configure_args),
                        description='configuring llvm',
                        descriptionDone='configure llvm',
                        haltOnFailure=True, workdir=llvm_obj_dir, env=env))
    f.addStep(WarningCountingShellCommand(name='compile.llvm',
                                          command=['nice', '-n', '10',
                                                   'make', WithProperties('-j%s' % jobs)],
                                          haltOnFailure=True,
                                          description='compiling llvm',
                                          descriptionDone='compile llvm',
                                          workdir=llvm_obj_dir, env=env,
                                          timeout=timeout*60))
    f.addStep(WarningCountingShellCommand(name='install.llvm',
                                          command=['nice', '-n', '10',
                                                   'make', 'install'],
                                          haltOnFailure=True,
                                          description='installing llvm',
                                          descriptionDone='install llvm',
                                          workdir=llvm_obj_dir, env=env))

    # Build dragonegg with the just built LLVM.
    dragonegg_obj_dir = 'dragonegg.obj'
    if clean:
        f.addStep(ShellCommand(name='rm-%s' % dragonegg_obj_dir,
                               command=['rm', '-rf', dragonegg_obj_dir],
                               description='rm build dir dragonegg',
                               haltOnFailure=True, workdir='.', env=env))
    f.addStep(WarningCountingShellCommand(
            name='compile.dragonegg',
            command=['nice', '-n', '10',
                     'make', '-f', '../' + dragonegg_src_dir + '/Makefile',
                     WithProperties('-j%s' % jobs),
                     WithProperties('GCC=' + gcc),
                     WithProperties('LLVM_CONFIG=%(builddir)s/' +
                                    llvm_install_dir + '/bin/llvm-config'),
                     WithProperties('TOP_DIR=%(builddir)s/' + dragonegg_src_dir)
                     ],
            haltOnFailure=True,
            description='compiling dragonegg',
            descriptionDone='compile dragonegg',
            workdir=dragonegg_obj_dir, env=env, timeout=timeout*60))

    # Pretend that DragonEgg is llvm-gcc by creating llvm-gcc and llvm-g++
    # scripts that dispatch to gcc with dragonegg and g++ with dragonegg.
    if clean:
        f.addStep(ShellCommand(name='rm-bin',
                               command=['rm', '-rf', 'bin'],
                               description='rm bin dir',
                               haltOnFailure=True, workdir='.', env=env))
    f.addStep(ShellCommand(name='create.llvm-gcc.script',
                           command=WithProperties('echo "#!/bin/sh" > llvm-gcc'
                             '; echo "exec ' + gcc + ' -fplugin=%(builddir)s/' +
                             dragonegg_obj_dir + '/dragonegg.so \\"\$@\\"" >> llvm-gcc'
                             '; chmod a+x llvm-gcc'),
                           description='create llvm-gcc script',
                           haltOnFailure=True, workdir='bin', env=env))
    f.addStep(ShellCommand(name='create.llvm-g++.script',
                           command=WithProperties('echo "#!/bin/sh" > llvm-g++'
                             '; echo "exec ' + gxx + ' -fplugin=%(builddir)s/' +
                             dragonegg_obj_dir + '/dragonegg.so \\"\$@\\"" >> llvm-g++'
                             '; chmod a+x llvm-g++'),
                           description='create llvm-g++ script',
                           haltOnFailure=True, workdir='bin', env=env))

    # Configure the test-suite.
    testsuite_obj_dir = 'test-suite.obj'
    if clean:
        f.addStep(ShellCommand(name='rm-%s' % testsuite_obj_dir,
                               command=['rm', '-rf', testsuite_obj_dir],
                               description='rm test-suite build dir',
                               haltOnFailure=True, workdir='.', env=env))
    f.addStep(Configure(name='configure.test-suite',
                        command=['../' + testsuite_src_dir + '/configure',
                                 WithProperties('--with-llvmsrc=%(builddir)s/' + llvm_src_dir),
                                 WithProperties('--with-llvmobj=%(builddir)s/' + llvm_obj_dir),
                                 WithProperties('--with-llvmgccdir=%(builddir)s/'),
                                 '--with-llvmcc=llvm-gcc', 'CC=' + gcc, 'CXX=' + gxx] +
                                 testsuite_configure_args,
                        description='configuring nightly test-suite',
                        descriptionDone='configure nightly test-suite',
                        haltOnFailure=True, workdir=testsuite_obj_dir, env=env))

    # Build and test.
    f.addStep(ShellCommand(name='rm.test-suite.report',
                           command=['rm', '-rf', testsuite_obj_dir + '/report',
                                    testsuite_obj_dir + '/report.nightly.raw.out',
                                    testsuite_obj_dir + '/report.nightly.txt'],
                           description='rm test-suite report',
                           haltOnFailure=True, workdir='.', env=env))
    f.addStep(NightlyTestCommand(name='make.test-suite',
                                 command=['make', WithProperties('-j%s' % jobs),
                                          'ENABLE_PARALLEL_REPORT=1',
                                          'DISABLE_CBE=1', 'DISABLE_JIT=1',
                                          'RUNTIMELIMIT=%s' % (timeout*60),
                                          'TEST=nightly', 'report'],
                                 logfiles={'report' : 'report.nightly.txt'},
                                 description='running nightly test-suite',
                                 descriptionDone='run nightly test-suite',
                                 haltOnFailure=True, xfails=xfails,
                                 timeout=timeout*60,
                                 workdir=testsuite_obj_dir, env=env))

    return f


def getDragonEggTestBuildFactory(gcc='gcc', svn_testsuites=[],
                                 llvm_configure_args=[], xfails=[],
                                 clean=True, env={}, jobs='%(jobs)s',
                                 timeout=20):
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

    # Checkout victims for the compilator.
    compilator_dir = dragonegg_src_dir + '/test/compilator'

    # Checkout testsuites held in subversion repositories.  These are usually
    # specified using a known good revision (supplied by appending @revision to
    # the URL).  The SVN step can't handle that.  As it provides no mechanism at
    # all for checking out a specific revision, run the command directly here.
    for svn_testsuite in svn_testsuites:
        url = svn_testsuite[0]
        name = svn_testsuite[1]
        if url is None:
            f.addStep(ShellCommand(name='rm-%s' % name,
                                   command=['rm', '-rf', name],
                                   description=['rm', name], haltOnFailure=True,
                                   workdir=compilator_dir, env=env))
        else:
            svn_co = ['svn', 'checkout', url, name]
            f.addStep(ShellCommand(name=name, command=svn_co,
                                   haltOnFailure=True, workdir=compilator_dir,
                                   env=env))

    # Checkout miscellaneous testsuites.

    # LAPACK.
    f.addStep(ShellCommand(name='wget.lapack',
                           command='wget -N http://www.netlib.org/lapack/lapack-3.4.0.tgz',
                           haltOnFailure=False, workdir=compilator_dir,
                           env=env))
    f.addStep(ShellCommand(name='unpack.lapack',
                           command='tar xzf lapack-3.4.0.tgz',
                           haltOnFailure=True, workdir=compilator_dir,
                           env=env))

    # Nist Fortran 77 test suite.
    f.addStep(ShellCommand(name='wget.nist',
                           command='wget -N http://www.itl.nist.gov/div897/ctg/suites/fcvs21.tar.Z',
                           haltOnFailure=False, workdir=compilator_dir,
                           env=env))
    f.addStep(ShellCommand(name='unpack.nist',
                           command='tar xzf ../fcvs21.tar.Z',
                           haltOnFailure=True, workdir=compilator_dir+'/fcvs21/',
                           env=env))

    # Polyhedron.
    f.addStep(ShellCommand(name='wget.polyhedron',
                           command='wget -N http://www.polyhedron.com/web_images/documents/pb11.zip',
                           haltOnFailure=False, workdir=compilator_dir,
                           env=env))
    f.addStep(ShellCommand(name='unpack.polyhedron',
                           command='unzip -o pb11.zip',
                           haltOnFailure=True, workdir=compilator_dir,
                           env=env))

    # Large single compilation-unit C programs.
    f.addStep(ShellCommand(name='wget.bzip2',
                           command='wget -N http://people.csail.mit.edu/smcc/projects/single-file-programs/bzip2.c',
                           haltOnFailure=False, workdir=compilator_dir,
                           env=env))
    f.addStep(ShellCommand(name='wget.gzip',
                           command='wget -N http://people.csail.mit.edu/smcc/projects/single-file-programs/gzip.c',
                           haltOnFailure=False, workdir=compilator_dir,
                           env=env))
    f.addStep(ShellCommand(name='fix.gzip',
                           command='sed -i "s/^static char \*$/char */" gzip.c',
                           haltOnFailure=True, workdir=compilator_dir,
                           env=env))
    f.addStep(ShellCommand(name='wget.oggenc',
                           command='wget -N http://people.csail.mit.edu/smcc/projects/single-file-programs/oggenc.c',
                           haltOnFailure=False, workdir=compilator_dir,
                           env=env))
    f.addStep(ShellCommand(name='wget.gcc',
                           command='wget -N http://people.csail.mit.edu/smcc/projects/single-file-programs/gcc.c.bz2',
                           haltOnFailure=False, workdir=compilator_dir,
                           env=env))
    f.addStep(ShellCommand(name='unpack.gcc',
                           command='bunzip2 -f -k gcc.c.bz2',
                           haltOnFailure=True, workdir=compilator_dir,
                           env=env))

    # Build and install LLVM.
    llvm_obj_dir = 'llvm.obj'
    llvm_install_dir = 'llvm.install'
    if clean:
        f.addStep(ShellCommand(name='rm-%s' % llvm_obj_dir,
                               command=['rm', '-rf', llvm_obj_dir,
                                        llvm_install_dir],
                               description='rm build dir llvm',
                               haltOnFailure=True, workdir='.', env=env))
    f.addStep(Configure(name='configure.llvm',
                        command=(['../' + llvm_src_dir + '/configure',
                                  WithProperties('--prefix=%%(builddir)s/%s' % llvm_install_dir)] +
                                 llvm_configure_args),
                        description='configuring llvm',
                        descriptionDone='configure llvm',
                        haltOnFailure=True, workdir=llvm_obj_dir, env=env))
    f.addStep(WarningCountingShellCommand(name='compile.llvm',
                                          command=['nice', '-n', '10',
                                                   'make', WithProperties('-j%s' % jobs)],
                                          haltOnFailure=True,
                                          description='compiling llvm',
                                          descriptionDone='compile llvm',
                                          workdir=llvm_obj_dir, env=env,
                                          timeout=timeout*60))
    f.addStep(WarningCountingShellCommand(name='install.llvm',
                                          command=['nice', '-n', '10',
                                                   'make', 'install'],
                                          haltOnFailure=True,
                                          description='installing llvm',
                                          descriptionDone='install llvm',
                                          workdir=llvm_obj_dir, env=env))

    # Build dragonegg with the just built LLVM.
    dragonegg_obj_dir = 'dragonegg.obj'
    if clean:
        f.addStep(ShellCommand(name='rm-%s' % dragonegg_obj_dir,
                               command=['rm', '-rf', dragonegg_obj_dir],
                               description='rm build dir dragonegg',
                               haltOnFailure=True, workdir='.', env=env))
    f.addStep(WarningCountingShellCommand(
            name='compile.dragonegg',
            command=['nice', '-n', '10',
                     'make', '-f', '../' + dragonegg_src_dir + '/Makefile',
                     WithProperties('-j%s' % jobs),
                     WithProperties('GCC=' + gcc),
                     WithProperties('LLVM_CONFIG=%(builddir)s/' +
                                    llvm_install_dir + '/bin/llvm-config'),
                     WithProperties('TOP_DIR=%(builddir)s/' + dragonegg_src_dir)
                     ],
            haltOnFailure=True,
            description='compiling dragonegg',
            descriptionDone='compile dragonegg',
            workdir=dragonegg_obj_dir, env=env, timeout=timeout*60))

    # Run the dragonegg testsuite.
    testsuite_output_dir = dragonegg_obj_dir + '/test/Output'
    if clean:
        f.addStep(ShellCommand(name='rm-%s' % testsuite_output_dir,
                               command=['rm', '-rf', testsuite_output_dir],
                               description='rm test-suite output directory',
                               haltOnFailure=True, workdir='.', env=env))

    f.addStep(LitTestCommand(name='make.check',
                               command=['nice', '-n', '10',
                                        'make', '-f', '../' + dragonegg_src_dir + '/Makefile',
                                        WithProperties('GCC=' + gcc),
                                        WithProperties('LLVM_CONFIG=%(builddir)s/' +
                                                       llvm_install_dir + '/bin/llvm-config'),
                                        WithProperties('TOP_DIR=%(builddir)s/' + dragonegg_src_dir),
                                        WithProperties('LIT_ARGS=-v -j%s' % jobs),
                                        'check'
                                        ],
                               description='running test-suite',
                               descriptionDone='run test-suite',
                               haltOnFailure=True, workdir=dragonegg_obj_dir,
                               env=env, timeout=timeout*60))

    return f

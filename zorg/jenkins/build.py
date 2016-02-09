"""Build and test clangs."""

import sys
import logging
import os
import subprocess
import datetime
import argparse
import urllib
import shutil
import math

SERVER = "labmaster2.local"


NINJA = "/usr/local/bin/ninja"


def readme_name(repo):
    """Given a repo, return the name of the readme file."""
    if repo == "libcxx":
        return "LICENSE.TXT"
    return "README.txt"


def next_section(name):
    """Jenkins is setup to parse @@@ xyz @@@ as a new section of the buildlog
    with title xyz.  The section ends with @@@@@@ """
    footer()
    header(name)


def header(name):
    print "@@@", name, "@@@"


def footer():
    print "@@@@@@"


def quote_sh_string(string):
    """Make things that we print shell safe for copy and paste."""
    return "\\'".join("'" + p + "'" for p in string.split("'"))


class Configuration(object):
    """docstring for Configuration"""
    def __init__(self, args):
        super(Configuration, self).__init__()
        self._args = args
        self.workspace = os.environ.get('WORKSPACE', os.getcwd())
        self._src_dir = os.environ.get('SRC_DIR', 'llvm')
        self._lldb_src_dir = os.environ.get('LLDB_SRC_DIR', 'lldb')
        self._build_dir = os.environ.get('BUILD_DIR', 'clang-build')
        self._lldb_build_dir = os.environ.get('LLDB_BUILD_DIR', 'lldb-build')
        self._install_dir = os.environ.get('BUILD_DIR', 'clang-install')
        self.j_level = os.environ.get('J_LEVEL', None)
        self.max_parallel_tests = os.environ.get('MAX_PARALLEL_TESTS', None)
        self.max_parallel_links = os.environ.get('MAX_PARALLEL_LINKS', None)
        self.host_compiler_url = os.environ.get('HOST_URL',
            'http://labmaster2.local/artifacts/')
        self.artifact_url = os.environ.get('ARTIFACT', 'NONE')
        self.job_name = os.environ.get('JOB_NAME', 'NONE')
        self.build_id = os.environ.get('BUILD_ID', 'NONE')
        self.build_number = os.environ.get('BUILD_NUMBER', 'NONE')
        self.svn_rev = os.environ.get('LLVM_REV', 'NONE')
        self.nobootstrap = True
        self.device = None
        self._svn_url = None

        # Import all of the command line arguments into the config object
        self.__dict__.update(vars(args))

    def builddir(self):
        """The build output directory for this compile."""
        return os.path.join(self.workspace, self._build_dir)

    def srcdir(self):
        """The derived source directory for this build."""
        return os.path.join(self.workspace, self._src_dir)

    def lldbbuilddir(self):
        """The derived source directory for this lldb build."""
        return os.path.join(self.workspace, self._lldb_build_dir)

    def lldbsrcdir(self):
        """The derived source directory for this lldb build."""
        return os.path.join(self.workspace, self._lldb_src_dir)

    def installdir(self):
        """The install directory for the compile."""
        return os.path.join(self.workspace, self._install_dir)

    def CC(self):
        """Location of the host compiler, if one is present in this build."""
        cc_basedir = os.path.join(self.workspace, 'host-compiler/')
        if os.path.exists(cc_basedir):
            clang_exec_path = os.path.join(cc_basedir, 'bin/clang')
            assert os.path.exists(clang_exec_path), "host-compiler present," \
                " but has no clang executable."
            return clang_exec_path
        else:
            return False

    def liblto(self):
        """Location of the host compiler, if one is present"""
        cc_basedir = os.path.join(self.workspace, 'host-compiler/')
        if os.path.exists(cc_basedir):
            clang_liblto_path = os.path.join(cc_basedir, 'lib/')
            assert os.path.exists(clang_liblto_path), "host-compiler present," \
                " but has no liblto."
            return clang_liblto_path
        else:
            return False

    def branch(self):
        """Figure out the branch name from the SVN_URL."""
        try:
            return os.environ['BRANCH']
        except:
            assert self._svn_url is not None
            BRANCH_MARKER = "/branches/"
            if BRANCH_MARKER in self._svn_url:
                wo_branch = self._svn_url.split(BRANCH_MARKER, 1)[1]
                branch = wo_branch.rsplit("@", 1)[0]
                return branch
            else:
                return "master"


    def link_memory_usage(self):
        """Guesstimate the maximum link memory usage for this build.
           We are only building master here so we will just use that value
        """
        #  Determinited experimentally.
        usages = {'master': 3.5}
        if self.branch() == 'master':
            return usages['master']
        else:
            raise NotImplementedError("Unknown link memory usage." + self.branch())


# Global storage for configuration object.
conf = None

def cmake_builder(target):
    check_repo_state(conf.workspace)

    env = []
    if conf.lto and conf.liblto():
        dyld_path = conf.liblto()
        env.extend(["env", "DYLD_LIBRARY_PATH=" + dyld_path])

    cmake_cmd = env + ["/usr/local/bin/cmake", "-G", "Ninja",
                       "-DCMAKE_INSTALL_PREFIX=" + conf.installdir(),
                       conf.srcdir()]

    compiler_flags = conf.compiler_flags
    max_parallel_links = conf.max_parallel_links
    if conf.lto:
        compiler_flags += ['-flto']
        cmake_cmd += ['-DLLVM_BUILD_EXAMPLES=Off']
        if not max_parallel_links:
            max_parallel_links = 1
    else:
        cmake_cmd += ['-DLLVM_BUILD_EXAMPLES=On']

    if compiler_flags:
        cmake_cmd += ["-DCMAKE_C_FLAGS={}".format(' '.join(compiler_flags)),
                      "-DCMAKE_CXX_FLAGS={}".format(' '.join(compiler_flags))]

    if max_parallel_links is not None:
        cmake_cmd += ["-DLLVM_PARALLEL_LINK_JOBS={}".format(max_parallel_links)]

    if conf.CC():
        cmake_cmd += ['-DCMAKE_C_COMPILER=' + conf.CC(),
                      '-DCMAKE_CXX_COMPILER=' + conf.CC() + "++"]

    if conf.cmake_build_type:
        cmake_cmd += ["-DCMAKE_BUILD_TYPE=" + conf.cmake_build_type]
    elif conf.debug:
        cmake_cmd += ["-DCMAKE_BUILD_TYPE=Debug"]
    else:
        cmake_cmd += ["-DCMAKE_BUILD_TYPE=Release"]

    for flag in conf.cmake_flags:
        cmake_cmd += [flag]

    if conf.assertions:
        cmake_cmd += ["-DLLVM_ENABLE_ASSERTIONS=On"]
    else:
        cmake_cmd += ["-DLLVM_ENABLE_ASSERTIONS=Off"]

    # Workaround for PR14109: CMake build for compiler-rt should use
    # just-built clang.
    cmake_cmd += ["-DCOMPILER_RT_BUILD_BUILTINS=Off"]

    lit_flags = ['--xunit-xml-output=testresults.xunit.xml', '-v']
    if conf.max_parallel_tests:
        lit_flags += ['-j', conf.max_parallel_tests]
    cmake_cmd += ['-DLLVM_LIT_ARGS={}'.format(' '.join(lit_flags))]

    ninja_cmd = env + ["/usr/local/bin/ninja"]
    if conf.j_level is not None:
        ninja_cmd += ["-j", conf.j_level]

    if target == 'all' or target == 'build':
        header("Cmake")
        run_cmd(conf.builddir(), cmake_cmd)
        footer()
        header("Ninja build")
        run_cmd(conf.builddir(), ninja_cmd)
        footer()

    if target == 'all' or target == 'test':
        header("Ninja test")
        run_cmd(conf.builddir(), ninja_cmd + ['check', 'check-clang'])
        footer()

    if target == 'all' or target == 'testlong':
        header("Ninja test")
        run_cmd(conf.builddir(), ninja_cmd + ['check-all'])
        footer()


def clang_builder(target):
    """Build to set of commands to compile and test apple-clang"""
    check_repo_state(conf.workspace)
    # get rid of old archives from prior builds

    run_ws(['sh', '-c', 'rm -rfv *gz'])

    if target == "all" or target == "build":
        # Clean the build directory.
        run_ws(['rm', '-rf', 'clang.roots'])
        
        debug_src_dir = 'debuginfo-tests.src'

        sdk_name = 'macosx'

        sdkroot = query_sdk_path(sdk_name)

        next_section("Setup debug-info tests")
        run_ws(['rm', '-rf', 'llvm/tools/clang/test/debuginfo-tests'])
        run_cmd(os.path.join(conf.workspace, 'llvm/tools/clang/test'),
                ['ln', '-sf', os.path.join(conf.workspace, debug_src_dir),
                'debuginfo-tests'])

        project = 'clang'

        clang_br = os.path.join(conf.workspace, conf._build_dir)
        next_section("Build Directory")
        run_ws(["mkdir", "-p", clang_br])

        toolchain = '/Applications/Xcode.app/Contents/Developer' \
            '/Toolchains/XcodeDefault.xctoolchain'

        next_section("Build Clang")
        if conf.nobootstrap:
            if conf.debug or conf.device:
                assert False, "Invalid parameter for clang-builder."
            run_cmd(clang_br, ['mkdir',
                           './Build',
                           './Root'])
            install_prefix =  conf.installdir()
            cmake_command = ["/usr/local/bin/cmake", '-G', 'Ninja', '-C',
            '{}/llvm/tools/clang/cmake/caches/Apple-stage2.cmake'.format(conf.workspace),
            '-DLLVM_ENABLE_ASSERTIONS:BOOL={}'.format("TRUE" if conf.assertions else "FALSE"),
            '-DCMAKE_BUILD_TYPE=RelWithDebInfo',
            '-DCMAKE_MAKE_PROGRAM=' + NINJA,
            '-DLLVM_VERSION_PATCH=99',
            '-DLLVM_VERSION_SUFFIX=""',
            '-DLLVM_BUILD_EXTERNAL_COMPILER_RT=On',
            '-DCLANG_COMPILER_RT_CMAKE_ARGS={}/llvm/tools/clang/cmake/caches/Apple-stage2.cmake'.format(conf.workspace),
            '-DCMAKE_INSTALL_PREFIX={}'.format(install_prefix),
            '-DLLVM_ENABLE_PIC=On', 
            '-DLLVM_REPOSITORY={}'.format(conf._svn_url),
            '-DSVN_REVISION={}'.format(conf.svn_rev),
            '-DLLVM_BUILD_TESTS=On',
            '-DLLVM_INCLUDE_TESTS=On',
            '-DCLANG_INCLUDE_TESTS=On',
            '-DLLVM_INCLUDE_UTILS=On',
            '-DLIBCXX_INSTALL_HEADERS=On',
            '-DLIBCXX_OVERRIDE_DARWIN_INSTALL=On',
            '-DLIBCXX_INSTALL_LIBRARY=Off',
            ]

            if conf.CC():
                cmake_command.extend(['-DCMAKE_C_COMPILER=' + conf.CC(),
                          '-DCMAKE_CXX_COMPILER=' + conf.CC() + "++"])

            lit_flags = ['--xunit-xml-output=testresults.xunit.xml', '-v']
            if conf.max_parallel_tests:
                lit_flags += ['-j', conf.max_parallel_tests]
            cmake_command.extend(['-DLLVM_LIT_ARGS={}'.format(' '.join(lit_flags))])

            if conf.lto:
                cmake_command.extend([
                    '-DCMAKE_C_FLAGS_RELWITHDEBINFO:STRING=-O2 -flto -gline-tables-only -DNDEBUG',
                    '-DCMAKE_CXX_FLAGS_RELWITHDEBINFO:STRING=-O2 -flto -gline-tables-only -DNDEBUG'])
                cmake_command.extend(["-DLLVM_PARALLEL_LINK_JOBS=" + str(max_link_jobs())])
            else:
                cmake_command.extend([
                    '-DCMAKE_C_FLAGS_RELWITHDEBINFO:STRING=-O2 -gline-tables-only -DNDEBUG',
                    '-DCMAKE_CXX_FLAGS_RELWITHDEBINFO:STRING=-O2 -gline-tables-only -DNDEBUG'])


            cmake_command.append("{}/llvm".format(conf.workspace))
            run_cmd(os.path.join(clang_br, 'Build'), cmake_command)
            next_section("Ninja")
            run_cmd(os.path.join(clang_br, 'Build'), [NINJA, '-v', 'install'])

            build_upload_artifact()

        else:
            # Two stage build, via the make files.
            print 'Stage two compile TBD in near future'

    if not conf.device and (target == "test" or target == "all"):
        # Add steps to run the tests.
        next_section("Tests")
        # Auto detect bootstrap and non-bootstrap.
        obj_dir = os.path.join(conf._build_dir, 'Objects/obj-llvm/tools/clang/stage2-bins/')
        if not os.path.exists(obj_dir):
            obj_dir = os.path.join(conf._build_dir, 'Build/')
            obj_dir = os.path.join(conf.workspace, obj_dir)

        cmd = [NINJA, '-v', 'check-all']

        if conf.assertions:
            cmd[-1] += ' --param use_gmalloc=1 ' \
                '--param gmalloc_path=$(xcodebuild -find-library' \
                ' libgmalloc.dylib)'
        run_cmd(obj_dir, cmd, env={'MALLOC_LOG_FILE': '/dev/null'})


def lldb_builder():
    """Do an Xcode build of lldb."""

    # Wipe the build folder

    header("Clean LLDB build directory")
    if os.path.exists(conf.lldbbuilddir()):
        shutil.rmtree(conf.lldbbuilddir())
    footer()

    # Build into the build folder

    xcodebuild_cmd = [
        "xcodebuild",
        "-arch", "x86_64",
        "-configuration", "Debug",
        "-scheme", "desktop",
        "-derivedDataPath", conf.lldbbuilddir(),
        "DEBUGSERVER_USE_FROM_SYSTEM=1"]

    header("Build Xcode desktop scheme")
    run_cmd("lldb", xcodebuild_cmd)
    footer()

    # Run C++ test suite (gtests)

    xcodebuild_cmd = [
        "xcodebuild",
        "-arch", "x86_64",
        "-configuration", "Debug",
        "-scheme", "lldb-gtest",
        "-derivedDataPath", conf.lldbbuilddir(),
        "DEBUGSERVER_USE_FROM_SYSTEM=1"]

    header("Build Xcode lldb-gtest scheme")
    run_cmd("lldb", xcodebuild_cmd)
    footer()

    # Run LLDB Python test suite

    xcodebuild_cmd = [
        "xcodebuild",
        "-arch", "x86_64",
        "-configuration", "Debug",
        "-scheme", "lldb-python-test-suite",
        "-derivedDataPath", conf.lldbbuilddir(),
        "DEBUGSERVER_USE_FROM_SYSTEM=1"]

    header("Build Xcode lldb-python-test-suite target")
    # For the unit tests, we don't want to stop the build if there are
    # build errors.  We allow the JUnit/xUnit parser to pick this up.
    run_cmd_errors_okay("lldb", xcodebuild_cmd)
    footer()

def static_analyzer_benchmarks_builder():
  """Run static analyzer benchmarks"""
  header("Static Analyzer Benchmarks")

  benchmark_script = conf.workspace + "/utils-analyzer/SATestBuild.py"
  benchmarks_dir = conf.workspace + "/test-suite-ClangAnalyzer/"

  compiler_bin_dir = conf.workspace + "/host-compiler/bin/"
  scanbuild_bin_dir = conf.workspace + "/tools-scan-build/bin/"

  old_path = os.environ.get("PATH", "")
  env = dict(os.environ, PATH=compiler_bin_dir + os.pathsep +
                              scanbuild_bin_dir + os.pathsep +
                              old_path)

  benchmark_cmd = [benchmark_script,
                   "--strictness", "2"
                  ]
  run_cmd(benchmarks_dir, benchmark_cmd, env=env)

  footer()

def check_repo_state(path):
    """Check the SVN repo at the path has all the
    nessessary repos checked out.  Check this by
    looking for the README.txt in each repo. """

    if os.environ.get('TESTING', False):
        return

    logging.info("Detecting repos in {}".format(path))
    for r in ['llvm', 'clang', 'clang-tools-extra', 'debuginfo-tests', \
            'compiler-rt', 'libcxx', 'debuginfo-tests']:
        detected_path = derived_path('llvm', tree_path(tree='llvm', repo=r))
        readme = os.path.join(path, detected_path, readme_name(repo=r))
        if os.path.exists(readme):
            logging.info(" - {} found at {}".format(r, detected_path))
        else:
            logging.info(" - {} not found".format(r))


def checkout_path(workspace, repo):
    """Get the checkout path for a repo"""
    return workspace + "/" + repo + ".src"


def tree_path(tree, repo):
    """Get the derived path for a repo"""
    if tree == "llvm":
        if repo == "llvm":
            return ""
        if repo == "clang":
            return "tools/clang"
        if repo == "clang-tools-extra":
            return "tools/clang/tools/extra"
        if repo == "debuginfo-tests":
            return "tools/clang/test/debuginfo-tests"
        if repo == "compiler-rt":
            return "projects/compiler-rt"
        if repo == "libcxx":
            return "projects/libcxx"

    elif tree == "lldb":
        if repo == "lldb":
            return ""
        if repo == "llvm":
            return "llvm"
        if repo == "clang":
            return "llvm/tools/clang"

    else:
        logging.error("Unknown tree '{}'".format(tree))
        sys.exit(1)

    logging.error("Unknown repo '{}' in tree '{}".format(repo, tree))
    sys.exit(1)


def tree_srcdir(conf, tree):
    """Get the srcdir for a tree"""
    if tree == "llvm":
        return conf.srcdir()

    if tree == "lldb":
        return conf.lldbsrcdir()

    logging.error("Unknown tree '{}'".format(tree))
    sys.exit(1)


def derived_path(srcdir, tree_path):
    """Get the derived path from a tree path"""
    if tree_path:
        return srcdir + "/" + tree_path
    return srcdir


def should_exclude(base_path, repo_path):
    """Check wither a repo should be excluded in a given rsync"""
    if base_path == repo_path:
        return False
    if not base_path:
        return True
    if repo_path.startswith(base_path + "/"):
        return True
    return False


def rsync(conf, tree, repo, repos):
    """rsync from the checkout to the derived path"""
    cmd = ["rsync", "-auvh", "--delete", "--exclude=.svn/"]
    path = tree_path(tree=tree, repo=repo)
    for x in repos:
        x_path = tree_path(tree=tree, repo=x)
        if should_exclude(path, x_path):
            cmd.append("--exclude=/" + x_path)

    workspace = conf.workspace
    srcdir = tree_srcdir(conf=conf, tree=tree)
    cmd.append(checkout_path(workspace=workspace, repo=repo) + "/")
    cmd.append(derived_path(srcdir=srcdir, tree_path=path))
    run_cmd(working_dir=srcdir, cmd=cmd)


def derive(tree, repos):
    """Build a derived src tree from all the svn repos.

    Try to do this in a way that is pretty fast if the
    derived tree is already there.
    """
    if 'debuginfo-tests' in repos:
        dest_path = conf.workspace + "/" + 'llvm/tools/clang/test/debuginfo-tests'
        if os.path.exists(dest_path):
            print 'Remove debuginfo-tests from derived source if it exists'
            run_ws(['rm', '-rf', dest_path])

    # Check for src dirs.
    for p in repos:
        full_path = checkout_path(workspace=conf.workspace, repo=p)
        if not os.path.exists(full_path):
            logging.error("Cannot find Repo: in " + full_path)
            sys.exit(1)

    # Make sure destinations exist.
    srcdir = tree_srcdir(conf=conf, tree=tree)
    for p in repos:
        full_path = derived_path(srcdir=srcdir, tree_path=tree_path(tree=tree, repo=p))
        if not os.path.exists(full_path):
            os.makedirs(full_path)

    header("Derive Source")
    for repo in repos:
        rsync(conf=conf, tree=tree, repo=repo, repos=repos)
    footer()


def derive_llvm(repos=['llvm', 'clang', 'libcxx', 'clang-tools-extra', \
        'compiler-rt', 'debuginfo-tests']):
    """Build a derived src tree for LLVM"""
    derive(tree='llvm', repos=repos)


def derive_lldb():
    """Build a derived src tree for LLDB"""
    derive(tree='lldb', repos=['lldb', 'llvm', 'clang'])


def create_builddirs():
    paths = [conf.builddir(), conf.installdir()]
    for p in paths:
        if not os.path.exists(p):
            os.makedirs(p)


def fetch_compiler():
    local_name = "host-compiler.tar.gz"
    url = conf.host_compiler_url + "/" + conf.artifact_url
    header("Fetching Compiler")
    print "Fetching:", url,
    urllib.urlretrieve (url, conf.workspace + "/" + local_name)
    print "done."
    print "Decompressing..."
    if not os.path.exists(conf.workspace + "/host-compiler"):
        os.mkdir(conf.workspace + "/host-compiler")
    run_cmd(conf.workspace + "/host-compiler/", ['tar', 'zxf', "../" + local_name])
    os.unlink(local_name)
    footer()


def build_upload_artifact():
    """Create artifact for this build, and upload to server."""
    if conf.noupload:
        print 'Not uploading artificats'
        return
    assert conf.svn_rev != "NONE"
    prop_file = "last_good_build.properties"

    artifact_name = "clang-r{}-t{}-b{}.tar.gz".format(conf.svn_rev,
        conf.build_id, conf.build_number)
    new_url = conf.job_name + "/" + artifact_name

    with open(prop_file, 'w') as prop_fd:
        prop_fd.write("LLVM_REV={}\n".format(conf.svn_rev))
        prop_fd.write("ARTIFACT={}\n".format(new_url))

    tar = ["tar", "zcvf", "../" + artifact_name, "."]

    run_cmd(conf.installdir(), tar)

    upload_cmd = ["scp", artifact_name,
        "buildslave@" + SERVER + ":/Library/WebServer/Documents/artifacts/" +
        conf.job_name + "/"]

    run_cmd(conf.workspace, upload_cmd)

    upload_cmd = ["scp", prop_file,
        "buildslave@" + SERVER + ":/Library/WebServer/Documents/artifacts/" +
        conf.job_name + "/"]

    run_cmd(conf.workspace, upload_cmd)

    ln_cmd = ["ssh", "buildslave@" + SERVER,
        "ln", "-fs", "/Library/WebServer/Documents/artifacts/" +
        conf.job_name + "/" + artifact_name,
        "/Library/WebServer/Documents/artifacts/" +
        conf.job_name + "/latest" ]

    run_cmd(conf.workspace, ln_cmd)

def run_cmd(working_dir, cmd, env=None, sudo=False, err_okay=False):
    """Run a command in a working directory, and make sure it returns zero."""
    assert type(cmd) == list, "Not a list: {}".format(type(cmd))
    old_cwd = os.getcwd()
    if env:
        envs = []
        for key, value in env.items():
            envs.append("{}={}".format(key, value))
        cmd = ["env"] + envs + cmd
    if sudo:
        cmd = ['sudo'] + cmd

    cmd_to_print = ' '.join([quote_sh_string(x) for x in cmd])
    sys.stdout.write("cd {}\n{}\n".format(working_dir, cmd_to_print))
    sys.stdout.flush()
    return_code = 0
    start_time = datetime.datetime.now()
    if not os.environ.get('TESTING', False):
        try:
            os.chdir(working_dir)
            subprocess.check_call(cmd)
            os.chdir(old_cwd)
        except subprocess.CalledProcessError as excpt:
            if not err_okay:
                raise excpt
            else:
                logging.info("Ignoring failed command.")
                return_code = excpt.returncode
    end_time = datetime.datetime.now()

    logging.info("Command took {} seconds".format(
        (end_time-start_time).seconds))
    return return_code

def run_cmd_errors_okay(working_dir, cmd, env=None):
    """Run a command in a working directory, reporting return value.
    Non-zero exit codes do not generate an exception.
    """
    old_cwd = os.getcwd()
    cmd_to_print = ' '.join([quote_sh_string(x) for x in cmd])
    sys.stdout.write("cd {}\n{}\n".format(working_dir, cmd_to_print))
    sys.stdout.flush()

    start_time = datetime.datetime.now()
    if not os.environ.get('TESTING', False):
        try:
            os.chdir(working_dir)
            result = subprocess.call(cmd, env=env)
        finally:
            os.chdir(old_cwd)
    end_time = datetime.datetime.now()

    logging.info("Command took {} seconds: return code {}".format(
        (end_time-start_time).seconds, result))

KNOWN_TARGETS = ['all', 'build', 'test', 'testlong']
KNOWN_BUILDS = ['clang', 'cmake', 'lldb', 'fetch', 'artifact',
                'derive', 'derive-llvm+clang', 'derive-lldb', 'derive-llvm',
                'static-analyzer-benchmarks']

def query_sdk_path(sdk_name):
    """Get the path to the sdk named using xcrun.

    When $TESTING define, just give a dummy back.  We do this because xcrun
    could fail if the sdk you want is not installed, and that is silly for
    testing.
    """

    if not os.environ.get('TESTING', False):
        cmd = ['xcrun', '--sdk', sdk_name, '--show-sdk-path']
        return run_collect_output(cmd).strip()
    else:
        return "/Applications/Xcode.app/Contents/Developer/Platforms/" \
            "MacOSX.platform/Developer/SDKs/MacOSX10.10.sdk"

def max_link_jobs():
    """Link jobs take about 3.6GB of memory, max."""
    mem_str = run_collect_output(["sysctl", "hw.memsize"])
    mem = float(mem_str.split()[1].strip())
    mem = mem / (1024.0**3)  # Conver to GBs.
    return int(math.ceil(mem/conf.link_memory_usage()))

TEST_VALS = {"sysctl hw.ncpu": "hw.ncpu: 8\n",
             "sysctl hw.memsize": "hw.memsize: 8589934592\n",
             "xcrun --sdk iphoneos --show-sdk-path": "/Foo/bar",
             }

def run_collect_output(cmd):
    """Run cmd, and return the output"""
    if os.getenv("TESTING"):
        return TEST_VALS[' '.join(cmd)]

    return subprocess.check_output(cmd)

def query_sys_tool(sdk_name, tool_name):
    """Get the path of system tool

    When $TESTING define, just give a dummy back.
    """

    if not os.environ.get('TESTING', False):
        cmd = ['xcrun', '--sdk', sdk_name, '--find', tool_name]
        return run_collect_output(cmd).strip()
    else:
        return "/usr/bin/" + tool_name

def run_ws(cmd, env=None):
    """Wrapper to call run_cmd in local workspace.

    Since 99 percent of the time, that is where you want to call things from.
    """
    return run_cmd(conf.workspace, cmd, env)



def parse_args():
    """Get the command line arguments, and make sure they are correct."""

    parser = argparse.ArgumentParser(
        description='Build and test compilers and other things.')

    parser.add_argument("build_type",
                        help="The kind of build to trigger.",
                        choices=KNOWN_BUILDS)

    parser.add_argument("build_target",
                        nargs='?',
                        help="The targets to call (build, check, etc).",
                        choices=KNOWN_TARGETS)

    parser.add_argument('--assertions', dest='assertions', action='store_true')
    parser.add_argument('--lto', dest='lto', action='store_true')
    parser.add_argument('--debug', dest='debug', action='store_true')
    parser.add_argument('--cmake-type', dest='cmake_build_type',
                        help="Override cmake type Release, Debug, "
                        "RelWithDebInfo and MinSizeRel")
    parser.add_argument('--cmake-flag', dest='cmake_flags',
                        action='append', default=[],
                        help='Set an arbitrary cmake flag')
    parser.add_argument('--compiler-flag', dest='compiler_flags',
                        action='append', default=[],
                        help='Set an arbitrary compiler flag')
    parser.add_argument('--noupload', dest='noupload',
                        action='store_true')

    args = parser.parse_args()
    return args


def main():
    """Run a build based on command line args and ENV."""
    global conf
    args = parse_args()
    conf = Configuration(args)

    create_builddirs()
    try:
        if args.build_type == 'clang':
            clang_builder(args.build_target)
        elif args.build_type == 'lldb':
            lldb_builder()
        elif args.build_type == 'cmake':
            cmake_builder(args.build_target)
        elif args.build_type == 'derive':
            derive_llvm()
        elif args.build_type == 'derive-llvm+clang':
            derive_llvm(['llvm', 'clang'])
        elif args.build_type == 'derive-llvm':
            derive_llvm(['llvm'])
        elif args.build_type == 'derive-lldb':
            derive_lldb()
        elif args.build_type == 'fetch':
            fetch_compiler()
        elif args.build_type == 'artifact':
            build_upload_artifact()
        elif args.build_type == 'static-analyzer-benchmarks':
            static_analyzer_benchmarks_builder()
    except subprocess.CalledProcessError as exct:
        print "Command failed", exct.message
        print "Command:", exct.cmd
        sys.exit(1)


if __name__ == '__main__':
    main()

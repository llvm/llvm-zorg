"""Build and test clangs."""

import sys
import logging
import os
import subprocess
import datetime
import time
import argparse
import shutil
import math
import re
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from urllib2 import urlopen, URLError, HTTPError

SERVER = "labmaster2.lab.llvm.org"

NINJA = "/usr/local/bin/ninja"

# Add dependency checker to the Python path.
# For relative reference to the dependency file.
here = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(here + "/../../dep/"))
import dep  # noqa



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
    print "Completed at: " + time.strftime("%FT%T")
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
        self._install_dir = os.environ.get('INSTALL_DIR', 'clang-install')
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
        self._svn_url_cache = None
        self.node_name = os.environ.get('NODE_NAME', None)
        self.lldb_test_archs = os.environ.get('LLDB_TEST_ARCHS', 'x86_64').split()

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

    @property
    def _svn_url(self):
        if self._svn_url_cache:
            return self._svn_url_cache
        # Jenkins uses SVN_URL, and for more than one repo builds, numbers them.
        svn_url = os.environ.get('SVN_URL',
                                 os.environ.get('SVN_URL_1', None))
        if svn_url is None:
            svn_url = self.grab_svn_url()
        self._svn_url_cache = svn_url
        return svn_url

    def grab_svn_url(self):
        if os.environ.get('TESTING', False):
            return '/foo/workspace/llvm.src'
        cmd = ['svn', 'info', '--xml', os.path.join(self.workspace, 'llvm.src')]
        out = run_collect_output(cmd)
        x = ET.fromstring(out)
        url = x.find('entry').find('url').text
        return url

    def link_memory_usage(self):
        """Guesstimate the maximum link memory usage for this build.
           We are only building master here so we will just use that value
        """
        #  Determinited experimentally.
        usages = {'master': 3.5}
        if self.branch() == 'master':
            return usages['master']
        else:
            raise NotImplementedError(
                "Unknown link memory usage." + self.branch())


# Global storage for configuration object.
conf = None  # type: Configuration


def update_svn_checkout(working_dir):
    """Upgrade the svn version.
    
    We always run this upgrade because this
    helps us avoid bot breakage when we
    upgrade Xcode.
    """
    next_section("SVN upgrade")
    out = ""
    try:
        run_collect_output(["/usr/bin/xcrun", "svn", "upgrade"],
                           working_dir=working_dir)
    except subprocess.CalledProcessError as e:
        msg = """Process return code: {}\n
              The working path was: {}\n
              The error was: {}.\n"""
        msg = msg.format(e.returncode, working_dir, out)
        print msg


def cmake_builder(target):
    check_repo_state(conf.workspace)
    if not os.getenv("TESTING"):
        dep.parse_dependencies([here + "/clang_build_dependencies.dep"])

    env = []
    dyld_path = ""
    if conf.lto and conf.liblto():
        dyld_path = conf.liblto()
        env.extend(["env", "DYLD_LIBRARY_PATH=" + dyld_path])

    cmake_cmd = env + ["/usr/local/bin/cmake", "-G", "Ninja",
                       '-DCMAKE_MAKE_PROGRAM=' + NINJA,
                       "-DCMAKE_INSTALL_PREFIX=" + conf.installdir(),
                       conf.srcdir()]

    compiler_flags = conf.compiler_flags
    max_parallel_links = conf.max_parallel_links

    if conf.lto:
        if conf.thinlto:
            cmake_cmd += ["-DLLVM_PARALLEL_LINK_JOBS=1"]
        else:
            cmake_cmd += ["-DLLVM_PARALLEL_LINK_JOBS=" + str(max_link_jobs())]
        cmake_cmd += ['-DLLVM_BUILD_EXAMPLES=Off']
        if not max_parallel_links:
            max_parallel_links = 1
        if dyld_path:
            cmake_cmd += ['-DDYLD_LIBRARY_PATH=' + dyld_path]
    else:
        cmake_cmd += ['-DLLVM_ENABLE_LTO=Off']
        cmake_cmd += ['-DLLVM_BUILD_EXAMPLES=On']

    cmake_cmd += ["-DCMAKE_MACOSX_RPATH=On"]

    libtool_path = query_sys_tool("macosx", "libtool")
    if libtool_path:
        cmake_cmd += ['-DCMAKE_LIBTOOL=' + libtool_path]

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

    cmake_cmd += ["-DLLVM_BUILD_EXTERNAL_COMPILER_RT=On"]

    for flag in conf.cmake_flags:
        cmake_cmd += [flag]

    if conf.assertions:
        cmake_cmd += ["-DLLVM_ENABLE_ASSERTIONS=On"]
    else:
        cmake_cmd += ["-DLLVM_ENABLE_ASSERTIONS=Off"]

    if conf.globalisel:
        cmake_cmd += ["-DLLVM_BUILD_GLOBAL_ISEL=ON"]

    if conf.svn_rev != 'NONE':
        cmake_cmd += ["-DSVN_REVISION={}".format(conf.svn_rev)]

    lit_flags = ['--xunit-xml-output=testresults.xunit.xml', '-v', '--timeout=600']
    if conf.max_parallel_tests:
        lit_flags += ['-j', conf.max_parallel_tests]
    cmake_cmd += ['-DLLVM_LIT_ARGS={}'.format(' '.join(lit_flags))]

    ninja_cmd = env + ["/usr/local/bin/ninja", '-v']
    if conf.j_level is not None:
        ninja_cmd += ["-j", conf.j_level]

    if target == 'all' or target == 'build':
        header("Cmake")
        run_cmd(conf.builddir(), cmake_cmd)
        footer()
        header("Ninja build")

        # Build all if nothing is passed by the user.
        passed_target = conf.cmake_build_targets
        build_target = passed_target if passed_target else ['all']
        run_cmd(conf.builddir(), ninja_cmd + build_target)
        footer()
        if conf.noinstall:
            header("Skip install")
        else:
            header("Ninja install")
            run_cmd(conf.builddir(), ninja_cmd + ['install'])
            build_upload_artifact()
        footer()
    # Run all the test targets.
    ninja_cmd.extend(['-k', '0'])
    if target == 'all' or target == 'test' or target == 'testlong':
        header("Ninja test")

        targets = [
            'check-all'] if target == 'testlong' or target == 'all' else conf.cmake_test_targets

        if not targets:
            # testlong and all do check all, otherwise check and check-clang
            # unless the user asked for something else.
            targets = ['check', 'check-clang']

        run_cmd(conf.builddir(), ninja_cmd + targets)
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
        libtool_path = query_sys_tool(sdk_name, "libtool")

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

        env = []
        dyld_path = ""
        if conf.lto and conf.liblto():
            dyld_path = conf.liblto()
            env.extend(["env", "DYLD_LIBRARY_PATH=" + dyld_path])

        next_section("Build Clang")
        if conf.nobootstrap:
            if conf.debug or conf.device:
                assert False, "Invalid parameter for clang-builder."
            run_cmd(clang_br, ['mkdir',
                               './Build',
                               './Root'])
            install_prefix = conf.installdir()

            # Infer which CMake cache file to use. If ThinLTO we select a specific one.
            cmake_cachefile_thinlto = ''
            if conf.thinlto:
                cmake_cachefile_thinlto = '-ThinLTO'
            cmake_cachefile = '{}/llvm/tools/clang/cmake/caches/Apple-stage2{}.cmake'.format(
                                       conf.workspace, cmake_cachefile_thinlto)

            cmake_command = env + ["/usr/local/bin/cmake", '-G', 'Ninja', '-C',
                                   cmake_cachefile,
                                   '-DLLVM_ENABLE_ASSERTIONS:BOOL={}'.format(
                                       "TRUE" if conf.assertions else "FALSE"),
                                   '-DCMAKE_BUILD_TYPE=RelWithDebInfo',
                                   '-DCMAKE_MAKE_PROGRAM=' + NINJA,
                                   '-DLLVM_VERSION_PATCH=99',
                                   '-DLLVM_VERSION_SUFFIX=""',
                                   '-DLLVM_BUILD_EXTERNAL_COMPILER_RT=On',
                                   '-DCLANG_COMPILER_RT_CMAKE_ARGS={}/llvm/projects/compiler-rt/cmake/caches/Apple.cmake'.format(
                                       conf.workspace),
                                   '-DCOMPILER_RT_BUILD_SANITIZERS=On',
                                   '-DCMAKE_INSTALL_PREFIX={}'.format(
                                       install_prefix),
                                   '-DLLVM_REPOSITORY={}'.format(conf._svn_url),
                                   '-DCLANG_REPOSITORY_STRING={}'.format(
                                       conf.branch()),
                                   '-DCLANG_APPEND_VC_REV=On',
                                   '-DSVN_REVISION={}'.format(conf.svn_rev),
                                   '-DLLVM_BUILD_TESTS=On',
                                   '-DLLVM_INCLUDE_TESTS=On',
                                   '-DCLANG_INCLUDE_TESTS=On',
                                   '-DLLVM_INCLUDE_UTILS=On',
                                   '-DLIBCXX_INSTALL_HEADERS=On',
                                   '-DLIBCXX_OVERRIDE_DARWIN_INSTALL=On',
                                   '-DLIBCXX_INSTALL_LIBRARY=Off',
                                   '-DCMAKE_MACOSX_RPATH=On',
                                   ]

            if dyld_path:
                cmake_command += ['-DDYLD_LIBRARY_PATH=' + dyld_path]

            if libtool_path:
                cmake_command += ['-DCMAKE_LIBTOOL=' + libtool_path]

            if conf.CC():
                cmake_command.extend(['-DCMAKE_C_COMPILER=' + conf.CC(),
                                      '-DCMAKE_CXX_COMPILER=' + conf.CC() + "++"])

            lit_flags = ['--xunit-xml-output=testresults.xunit.xml', '-v', '--timeout=600']
            if conf.max_parallel_tests:
                lit_flags += ['-j', conf.max_parallel_tests]
            cmake_command.extend(
                ['-DLLVM_LIT_ARGS={}'.format(' '.join(lit_flags))])

            if conf.thinlto:
                cmake_command.extend(["-DLLVM_PARALLEL_LINK_JOBS=1"])
            elif conf.lto:
                cmake_command.extend(
                    ["-DLLVM_PARALLEL_LINK_JOBS=" + str(max_link_jobs())])
            else:
                cmake_command.extend(['-DLLVM_ENABLE_LTO=Off'])
                cmake_command.extend([
                    '-DCMAKE_C_FLAGS_RELWITHDEBINFO:STRING=-O2 -gline-tables-only -DNDEBUG',
                    '-DCMAKE_CXX_FLAGS_RELWITHDEBINFO:STRING=-O2 -gline-tables-only -DNDEBUG'])

            for flag in conf.cmake_flags:
                cmake_command += [flag]

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
        obj_dir = os.path.join(conf._build_dir,
                               'Objects/obj-llvm/tools/clang/stage2-bins/')
        if not os.path.exists(obj_dir):
            obj_dir = os.path.join(conf._build_dir, 'Build/')
            obj_dir = os.path.join(conf.workspace, obj_dir)

        cmd = [NINJA, '-v', '-k', '0', 'check-all']

        if conf.assertions:
            cmd[-1] += ' --param use_gmalloc=1 ' \
                       '--param gmalloc_path=$(xcodebuild -find-library' \
                       ' libgmalloc.dylib)'
        run_cmd(obj_dir, cmd, env={'MALLOC_LOG_FILE': '/dev/null'})


def parse_settings_from_output(working_dir, cmd):
    old_dir = os.getcwd()
    try:
        os.chdir(working_dir)
        assignment_regex = re.compile(r"^\s+([^\s=]+)\s*=\s*(.+)$")
        settings = {}
        for line in subprocess.check_output(cmd).splitlines(True):
            match = assignment_regex.match(line)
            if match:
                settings[match.group(1)] = match.group(2)
        return settings
    finally:
        os.chdir(old_dir)


def lldb_builder():
    """Do an Xcode build of lldb."""

    # Wipe the build folder

    header("Clean LLDB build directory")
    if os.path.exists(conf.lldbbuilddir()):
        shutil.rmtree(conf.lldbbuilddir())
    footer()

    # Build into the build folder
    build_configuration = "Release"

    xcodebuild_cmd = [
        "xcodebuild",
        "-arch", "x86_64",
        "-configuration", build_configuration,
        "-scheme", "desktop",
        "-derivedDataPath", conf.lldbbuilddir()
        # It is too fragile to use the Xcode debugserver.  If we add new
        # command line arguments to debugserver, the older Xcode debugserver
        # will fall over and not run.  By commenting out this flag, we
        # are requiring the builder to have the lldb_codesign code signing
        # certificate and we are ensuring we are testing the latest debugserver
        # from lldb.
        # "DEBUGSERVER_USE_FROM_SYSTEM=1"
    ]

    header("Build Xcode desktop scheme")
    run_cmd("lldb", xcodebuild_cmd)
    footer()

    header("Gather Xcode build settings")
    xcodebuild_cmd.append("-showBuildSettings")
    settings = parse_settings_from_output("lldb", xcodebuild_cmd)
    footer()

    build_dir = settings.get("BUILD_DIR", None)
    built_products_dir = settings.get("BUILT_PRODUCTS_DIR", None)
    if build_dir is None or built_products_dir is None:
        raise Exception("failed to retrieve build-related directories "
                        "from Xcode")

    llvm_build_dir = settings.get("LLVM_BUILD_DIR", None)
    llvm_build_dir_arch = settings.get("LLVM_BUILD_DIR_ARCH", None)
    if llvm_build_dir is None or llvm_build_dir_arch is None:
        raise Exception("failed to retrieve LLVM build-related settings "
                        "from Xcode")
    llvm_build_bin_dir = os.path.join(llvm_build_dir, llvm_build_dir_arch, "bin")
    built_clang_path = os.path.join(llvm_build_bin_dir, "clang")
    built_filecheck_path = os.path.join(llvm_build_bin_dir, "FileCheck")
    effective_clang = os.environ.get("LLDB_PYTHON_TESTSUITE_CC",
                                     built_clang_path)

    # Run C++ test suite (gtests)

    xcodebuild_cmd = [
        "xcodebuild",
        "-arch", "x86_64",
        "-configuration", build_configuration,
        "-scheme", "lldb-gtest",
        "-derivedDataPath", conf.lldbbuilddir(),
        # See notes above.
        # "DEBUGSERVER_USE_FROM_SYSTEM=1"
    ]

    header("Build Xcode lldb-gtest scheme")
    run_cmd("lldb", xcodebuild_cmd)
    footer()

    # Run LLDB Python test suite for archs defined in LLDB_TEST_ARCHS
    for arch in conf.lldb_test_archs:
        results_file = os.path.join(build_dir,
                "test-results-{}.xml".format(arch))
        python_testsuite_cmd = [
            "/usr/bin/python",
            "test/dotest.py",
            "--executable", os.path.join(built_products_dir, "lldb"),
            "-C", effective_clang,
            "--arch", arch,
            "--results-formatter",
            "lldbsuite.test_event.formatter.xunit.XunitFormatter",
            "--results-file", results_file,
            "--rerun-all-issues",
            "--env", "TERM=vt100",
            "-O--xpass=ignore",
            "--dsymutil="+os.path.join(os.path.dirname(effective_clang), 'dsymutil'),
            "--filecheck="+built_filecheck_path
        ]

        header("Run LLDB Python-based test suite ({} targets)".format(arch))
        # For the unit tests, we don't want to stop the build if there are
        # build errors.  We allow the JUnit/xUnit parser to pick this up.
        print repr(python_testsuite_cmd)
        run_cmd_errors_okay("lldb", python_testsuite_cmd)
        footer()


def lldb_cmake_builder():
    """Do a CMake build of lldb."""

    test_dir = os.path.join(conf.workspace, 'test')
    log_dir = os.path.join(test_dir, 'logs')
    results_file = os.path.join(test_dir, 'results.xml')
    dest_dir = os.path.join(conf.workspace, 'results', 'lldb')
    run_ws(["mkdir", "-p", conf.lldbbuilddir()])
    cmake_build_type = conf.cmake_build_type if conf.cmake_build_type else 'RelWithDebInfo'
    header("Configure")
    dotest_args=['--arch', 'x86_64', '--build-dir',
                 conf.lldbbuilddir()+'/lldb-test-build.noindex',
                 '-s='+log_dir,
                 '-t',
                 '--env', 'TERM=vt100']
    dotest_args.extend(conf.dotest_flags)
    cmake_cmd = ["/usr/local/bin/cmake", '-G', 'Ninja',
                 conf.srcdir(),
                 '-DLLVM_ENABLE_ASSERTIONS:BOOL={}'.format(
                     "TRUE" if conf.assertions else "FALSE"),
                 '-DCMAKE_BUILD_TYPE='+cmake_build_type,
                 '-DCMAKE_MAKE_PROGRAM=' + NINJA,
                 '-DLLVM_VERSION_PATCH=99',
                 '-DLLVM_ENABLE_MODULES=On',
                 '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
                 '-DCMAKE_INSTALL_PREFIX="%s"'%dest_dir,
                 '-DLLDB_TEST_USER_ARGS='+';'.join(dotest_args),
                 '-DLLVM_LIT_ARGS=--xunit-xml-output=%s -v'%results_file]
    cmake_cmd.extend(conf.cmake_flags)

    if conf.CC():
        cmake_cmd.extend(['-DCMAKE_C_COMPILER=' + conf.CC(),
                          '-DCMAKE_CXX_COMPILER=' + conf.CC() + "++"])

    run_cmd(conf.lldbbuilddir(), cmake_cmd)
    footer()

    header("Build")
    run_cmd(conf.lldbbuilddir(), [NINJA, '-v'])
    footer()

    header("Run Tests")
    run_cmd(conf.lldbbuilddir(), [NINJA, '-v', 'check-debuginfo'])
    run_cmd(conf.lldbbuilddir(), ['/usr/bin/env', 'TERM=vt100', NINJA, '-v',
                                  'check-lldb'])
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
                     "--strictness", "0"
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
        if repo == "lldb":
            return "tools/lldb"

    elif tree == "lldb":
        if repo == "lldb":
            return ""
        if repo == "llvm":
            return "llvm"
        if repo == "clang":
            return "llvm/tools/clang"
        if repo == "compiler-rt":
            return "llvm/projects/compiler-rt"
        if repo == "libcxx":
            return "llvm/projects/libcxx"

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


def http_download(url, dest):
    """Safely download url to dest.

    Print error and exit if download fails.
    """
    try:
        print "GETting", url, "to", dest, "...",
        f = urlopen(url)
        # Open our local file for writing
        with open(dest, "wb") as local_file:
            local_file.write(f.read())

    except HTTPError, e:
        print
        print "HTTP Error:", e.code, url
        sys.exit(1)

    except URLError, e:
        print
        print "URL Error:", e.reason, url
        sys.exit(1)
    print "done."


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
        update_svn_checkout(working_dir=full_path)
        if not os.path.exists(full_path):
            logging.error("Cannot find Repo: in " + full_path)
            sys.exit(1)

    # Make sure destinations exist.
    srcdir = tree_srcdir(conf=conf, tree=tree)
    for p in repos:
        full_path = derived_path(srcdir=srcdir,
                                 tree_path=tree_path(tree=tree, repo=p))
        if not os.path.exists(full_path):
            os.makedirs(full_path)

    header("Derive Source")
    for repo in repos:
        rsync(conf=conf, tree=tree, repo=repo, repos=repos)
    footer()


def derive_llvm(repos=['llvm', 'clang', 'libcxx', 'clang-tools-extra', \
                       'compiler-rt']):
    """Build a derived src tree for LLVM"""
    derive(tree='llvm', repos=repos)


def derive_lldb():
    """Build a derived src tree for LLDB"""
    derive(tree='lldb', repos=['lldb', 'llvm', 'clang'])


def derive_lldb_cmake():
    """Build a derived src tree for LLDB for building with CMake"""
    derive(tree='llvm', repos=['lldb', 'llvm', 'clang', 'libcxx', 'debuginfo-tests'])


def create_builddirs():
    paths = [conf.builddir(), conf.installdir()]
    for p in paths:
        if not os.path.exists(p):
            os.makedirs(p)


def fetch_compiler():
    local_name = "host-compiler.tar.gz"
    url = conf.host_compiler_url + "/" + conf.artifact_url
    header("Fetching Compiler")
    http_download(url, conf.workspace + "/" + local_name)
    print "Decompressing..."
    if os.path.exists(conf.workspace + "/host-compiler"):
        shutil.rmtree(conf.workspace + "/host-compiler")
    os.mkdir(conf.workspace + "/host-compiler")
    run_cmd(conf.workspace + "/host-compiler/",
            ['tar', 'zxf', "../" + local_name])
    os.unlink(local_name)
    footer()


def build_upload_artifact():
    """Create artifact for this build, and upload to server."""
    if conf.noupload:
        print 'Not uploading artificats'
        return
    header("Uploading Artifact")
    assert conf.svn_rev != "NONE"
    prop_file = "last_good_build.properties"

    artifact_name = "clang-r{}-t{}-b{}.tar.gz".format(conf.svn_rev,
                                                      conf.build_id,
                                                      conf.build_number)
    new_url = conf.job_name + "/" + artifact_name

    with open(prop_file, 'w') as prop_fd:
        prop_fd.write("LLVM_REV={}\n".format(conf.svn_rev))
        prop_fd.write("ARTIFACT={}\n".format(new_url))

    # The .a's are big and we don't need them later. Drop the LLVM and clang
    # libraries, but keep the libraries from compiler-rt.
    tar = ["tar", "zcvf", "../" + artifact_name, "--exclude=*libLLVM*.a",
           "--exclude=*libclang[A-Z]*.a", "."]

    run_cmd(conf.installdir(), tar)

    mkdir_cmd = ["ssh", "buildslave@" + SERVER, "mkdir", "-p", "/Library/WebServer/Documents/artifacts/" + conf.job_name]

    run_cmd(conf.workspace, mkdir_cmd)

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
              conf.job_name + "/latest"]

    run_cmd(conf.workspace, ln_cmd)

    lnr_cmd = ["ssh", "buildslave@" + SERVER,
               "ln", "-fs", "/Library/WebServer/Documents/artifacts/" +
               conf.job_name + "/" + artifact_name,
               "/Library/WebServer/Documents/artifacts/" +
               conf.job_name + "/r" + conf.svn_rev]

    run_cmd(conf.workspace, lnr_cmd)


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
        (end_time - start_time).seconds))
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
        (end_time - start_time).seconds, result))


KNOWN_TARGETS = ['all', 'build', 'test', 'testlong']
KNOWN_BUILDS = ['clang', 'cmake', 'lldb', 'lldb-cmake', 'fetch', 'artifact',
                'derive', 'derive-llvm+clang', 'derive-llvm+clang+libcxx', 
                'derive-lldb', 'derive-lldb-cmake',
                'derive-llvm', 'static-analyzer-benchmarks']


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
    mem = mem / (1024.0 ** 3)  # Conver to GBs.
    return int(math.ceil(mem / conf.link_memory_usage()))


TEST_VALS = {"sysctl hw.ncpu": "hw.ncpu: 8\n",
             "sysctl hw.memsize": "hw.memsize: 8589934592\n",
             "xcrun --sdk iphoneos --show-sdk-path": "/Foo/bar",
             "/usr/bin/xcrun svn upgrade": "",
             }


@contextmanager
def cwd(path):
    last_cwd = os.getcwd()
    if path:
        os.chdir(path)
    try:
        yield
    finally:
        os.chdir(last_cwd)


def run_collect_output(cmd, working_dir=None, stderr=None):
    """Run cmd and then return the output.
    
    If working_dir is supplied the cmd will run in
    with a context manager in working_dir.
    """
    if os.getenv("TESTING"):
        print 'TV: ' + ' '.join(cmd)
        return TEST_VALS[' '.join(cmd)]

    with cwd(working_dir):
        return subprocess.check_output(cmd, stderr=stderr)


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
    parser.add_argument('--thinlto', dest='thinlto', action='store_true')
    parser.add_argument('--debug', dest='debug', action='store_true')
    parser.add_argument('--cmake-type', dest='cmake_build_type',
                        help="Override cmake type Release, Debug, "
                             "RelWithDebInfo and MinSizeRel")
    parser.add_argument('--cmake-flag', dest='cmake_flags',
                        action='append', default=[],
                        help='Set an arbitrary cmake flag')
    parser.add_argument('--dotest-flag', dest='dotest_flags',
                        action='append', default=[],
                        help='Set an arbitrary lldb dotest.py flag')
    parser.add_argument('--cmake-test-target', dest='cmake_test_targets',
                        action='append', default=[],
                        help='Targets to build during testing')
    parser.add_argument('--cmake-build-target', dest='cmake_build_targets',
                        action='append', default=[],
                        help='Targets to build during building.')
    parser.add_argument('--compiler-flag', dest='compiler_flags',
                        action='append', default=[],
                        help='Set an arbitrary compiler flag')
    parser.add_argument('--noupload', dest='noupload', action='store_true')
    parser.add_argument('--noinstall', dest='noinstall', action='store_true',
                        help="Disable the install stage, build only.")
    parser.add_argument('--globalisel', dest='globalisel',
                        action='store_true', help="Turn on the experimental"
                                                  " GlobalISel CMake flag.")

    args = parser.parse_args()
    if args.thinlto:
        args.lto = True
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
        elif args.build_type == 'lldb-cmake':
            lldb_cmake_builder()
        elif args.build_type == 'cmake':
            cmake_builder(args.build_target)
        elif args.build_type == 'derive':
            derive_llvm()
        elif args.build_type == 'derive-llvm+clang':
            derive_llvm(['llvm', 'clang'])
        elif args.build_type == 'derive-llvm+clang+libcxx':
            derive_llvm(['llvm', 'clang', 'libcxx'])
        elif args.build_type == 'derive-llvm':
            derive_llvm(['llvm'])
        elif args.build_type == 'derive-lldb':
            derive_lldb()
        elif args.build_type == 'derive-lldb-cmake':
            derive_lldb_cmake()
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

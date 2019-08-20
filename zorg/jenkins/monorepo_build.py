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

MODULE_CACHE_REGEX = re.compile(r'-fmodules-cache-path=([^\"]+)')

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


def create_dirs(paths):
    for p in paths:
        if not os.path.exists(p):
            os.makedirs(p)


def find_system_compiler_module_cache():
    cmd = [
        'xcrun', 'clang', '-fmodules', '-x', 'c', '-', '-o', '/dev/null',
        '-###'
    ]
    output = subprocess.check_output(
        cmd, stderr=subprocess.STDOUT).decode('utf-8')
    module_cache = MODULE_CACHE_REGEX.findall(output)
    if not module_cache:
        return None
    return module_cache[0]


def find_module_caches(path):
    caches = []
    for root, dirs, _ in os.walk(path):
        for d in dirs:
            if d == "module.cache":
                caches.append(os.path.join(root, d))
    return caches

def delete_module_caches(workspace):
    caches = find_module_caches(workspace)
    system_cache = find_system_compiler_module_cache()
    if system_cache:
        caches.append(system_cache)
    for cache in caches:
        if (os.path.exists(cache)):
            print 'Removing module cache: {}'.format(cache)
            shutil.rmtree(cache)


class Configuration(object):
    """docstring for Configuration"""

    def __init__(self, args):
        super(Configuration, self).__init__()
        self._args = args
        self.workspace = os.environ.get('WORKSPACE', os.getcwd())
        self._src_dir = os.environ.get('SRC_DIR', 'llvm-project')
        self._llvm_src_dir = os.environ.get('LLVM_SRC_DIR', 'llvm')
        self._lldb_src_dir = os.environ.get('LLDB_SRC_DIR', 'lldb')
        self._build_dir = os.environ.get('BUILD_DIR', 'clang-build')
        self._lldb_build_dir = os.environ.get('LLDB_BUILD_DIR', 'lldb-build')
        self._lldb_standalone_build_dir = os.environ.get('LLDB_STANDALONE_BUILD_DIR', 'lldb-standalone-build')
        self._lldb_standalone_type = os.environ.get('LLDB_STANDALONE_TYPE', 'build-tree')
        self._lldb_xcode_build_dir = os.environ.get('LLDB_XCODE_BUILD_DIR', 'lldb-xcode-build')
        self._lldb_install_dir = os.environ.get('LLDB_INSTALL_DIR', 'lldb-install')
        self._lldb_test_compiler = os.environ.get('LLDB_TEST_COMPILER', '')
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
        self.git_sha = os.environ.get('GIT_SHA', 'NONE')
        self.git_distance = os.environ.get('GIT_DISTANCE', 'NONE')
        self.nobootstrap = True
        self.device = None
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

    def llvmsrcdir(self):
        """The llvm source directory for this build."""
        return os.path.join(self.workspace, self._src_dir, self._llvm_src_dir)

    def lldbbuilddir(self):
        """The derived source directory for this lldb build."""
        return os.path.join(self.workspace, self._lldb_build_dir)

    def lldbstandalonebuilddir(self, standalone_type):
        """The derived source directory for this lldb standalone build."""
        return os.path.join(self.workspace, standalone_type, self._lldb_standalone_build_dir)

    def lldbxcodebuilddir(self):
        """The derived source directory for this lldb Xcode build."""
        return os.path.join(self.workspace, self._lldb_xcode_build_dir)

    def lldbsrcdir(self):
        """The derived source directory for this lldb build."""
        return os.path.join(self.workspace, self._src_dir, self._lldb_src_dir)

    def lldbinstalldir(self):
        """The install directory for the lldb build."""
        return os.path.join(self.workspace, self._lldb_install_dir)

    def lldbtestcompiler(self):
        """The compiler used to build LLDB tests."""
        return self._lldb_test_compiler

    def installdir(self):
        """The install directory for the compile."""
        return os.path.join(self.workspace, self._install_dir)

    def lldbstandalonetype(self):
        """The type of standalone build: against the build or install tree."""
        return self._lldb_standalone_type;

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
        """Figure out the source branch name.
	   Not using GIT_BRANCH env var from Jenkins as that includes the
           remote name too.
        """
        if not os.environ.get('TESTING', False):
            cmd = ['git', '-C', conf.srcdir(), 'symbolic-ref', '--short', 'HEAD']
            out = run_collect_output(cmd).strip()
            return out
        return 'master'

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

def cmake_builder(target):
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
                       "-DLLVM_ENABLE_PROJECTS=" + conf.llvm_enable_projects,
                       conf.llvmsrcdir()]

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

    lit_flags = ['--xunit-xml-output=testresults.xunit.xml', '-v', '--timeout=600']
    if conf.max_parallel_tests:
        lit_flags += ['-j', conf.max_parallel_tests]
    cmake_cmd += ['-DLLVM_LIT_ARGS={}'.format(' '.join(lit_flags))]

    ninja_cmd = env + ["/usr/local/bin/ninja", '-v']
    if conf.j_level is not None:
        ninja_cmd += ["-j", conf.j_level]

    if target == 'all' or target == 'configure' or target == 'build':
        header("Cmake")
        run_cmd(conf.builddir(), cmake_cmd)
        footer()

    if target == 'all' or target == 'build':
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

    # get rid of old archives from prior builds
    run_ws(['sh', '-c', 'rm -rfv *gz'])

    if target == "all" or target == "build":
        # Clean the build directory.
        run_ws(['rm', '-rf', 'clang.roots'])

        sdk_name = 'macosx'

        sdkroot = query_sdk_path(sdk_name)
        libtool_path = query_sys_tool(sdk_name, "libtool")

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
            cmake_cachefile = '{}/clang/cmake/caches/Apple-stage2{}.cmake'.format(
                                       conf.srcdir(), cmake_cachefile_thinlto)

            cmake_command = env + ["/usr/local/bin/cmake", '-G', 'Ninja', '-C',
                                   cmake_cachefile,
                                   '-DLLVM_ENABLE_ASSERTIONS:BOOL={}'.format(
                                       "TRUE" if conf.assertions else "FALSE"),
                                   '-DCMAKE_BUILD_TYPE=RelWithDebInfo',
                                   '-DLLVM_ENABLE_PROJECTS={}'.format(conf.llvm_enable_projects),
                                   '-DCMAKE_MAKE_PROGRAM=' + NINJA,
                                   '-DLLVM_VERSION_PATCH=99',
                                   '-DLLVM_VERSION_SUFFIX=""',
                                   '-DLLVM_BUILD_EXTERNAL_COMPILER_RT=On',
                                   '-DCLANG_COMPILER_RT_CMAKE_ARGS={}/compiler-rt/cmake/caches/Apple.cmake'.format(
                                       conf.srcdir()),
                                   '-DCOMPILER_RT_BUILD_SANITIZERS=On',
                                   '-DCMAKE_INSTALL_PREFIX={}'.format(
                                       install_prefix),
                                   '-DCLANG_REPOSITORY_STRING={}'.format(
                                       conf.branch()),
                                   '-DCLANG_APPEND_VC_REV=On',
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

            cmake_command.append(conf.llvmsrcdir())
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


def lldb_cmake_builder(target, variant=None):
    """Do a CMake build of lldb."""

    test_dir = os.path.join(conf.workspace, 'test')
    log_dir = os.path.join(test_dir, 'logs')
    results_file = os.path.join(test_dir, 'results.xml')
    create_dirs([conf.lldbbuilddir(), test_dir, log_dir])

    cmake_build_type = conf.cmake_build_type if conf.cmake_build_type else 'RelWithDebInfo'

    # Construct dotest.py arguments.
    dotest_args=['--arch', 'x86_64', '--build-dir',
                 conf.lldbbuilddir()+'/lldb-test-build.noindex',
                 '-s='+log_dir,
                 '-t',
                 '--env', 'TERM=vt100']
    dotest_args.extend(conf.dotest_flags)

    # Construct lit arguments.
    lit_args = ['--xunit-xml-output={}'.format(results_file), '-v']
    if conf.max_parallel_tests:
        lit_args.extend(['-j', conf.max_parallel_tests])
    if variant == 'sanitized':
        lit_args.extend(['--timeout 600'])

    # Construct CMake invocation.
    cmake_cmd = ["/usr/local/bin/cmake", '-G', 'Ninja',
                 conf.llvmsrcdir(),
                 '-DCMAKE_BUILD_TYPE={}'.format(cmake_build_type),
                 '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
                 '-DCMAKE_INSTALL_PREFIX={}'.format(conf.lldbinstalldir()),
                 '-DCMAKE_MAKE_PROGRAM={}'.format(NINJA),
                 '-DLLDB_TEST_USER_ARGS='+';'.join(dotest_args),
                 '-DLLVM_ENABLE_ASSERTIONS:BOOL={}'.format("TRUE" if conf.assertions else "FALSE"),
                 '-DLLVM_ENABLE_MODULES=On',
                 '-DLLVM_ENABLE_PROJECTS={}'.format(conf.llvm_enable_projects),
                 '-DLLVM_LIT_ARGS={}'.format(' '.join(lit_args)),
                 '-DLLVM_VERSION_PATCH=99']


    if variant == 'sanitized':
        cmake_cmd.extend([
            '-DLLVM_TARGETS_TO_BUILD=X86',
            '-DLLVM_USE_SANITIZER=Address;Undefined'
        ])
        # There is no need to compile the lldb tests with an asanified compiler
        # if we have a host compiler available.
        if conf.CC():
            cmake_cmd.extend([
                '-DLLDB_TEST_C_COMPILER=' + conf.CC(),
                '-DLLDB_TEST_CXX_COMPILER=' + conf.CC() + "++"
            ])

    if conf.compiler_flags:
        cmake_cmd.extend([
            "-DCMAKE_C_FLAGS={}".format(' '.join(conf.compiler_flags)),
            "-DCMAKE_CXX_FLAGS={}".format(' '.join(conf.compiler_flags))
        ])

    if conf.lldbtestcompiler():
        cmake_cmd.extend([
            '-DLLDB_TEST_C_COMPILER=' + conf.lldbtestcompiler(),
            '-DLLDB_TEST_CXX_COMPILER=' + conf.lldbtestcompiler() + "++"
        ])

    cmake_cmd.extend(conf.cmake_flags)

    if conf.CC():
        cmake_cmd.extend([
            '-DCMAKE_C_COMPILER=' + conf.CC(),
            '-DCMAKE_CXX_COMPILER=' + conf.CC() + "++"
        ])


    header("Clean")
    delete_module_caches(conf.workspace)
    footer()

    if target == 'all' or target == 'configure' or target == 'build':
        header("Cmake")
        run_cmd(conf.lldbbuilddir(), cmake_cmd)
        footer()

    if target == 'all' or target == 'build':
        header("Build")
        run_cmd(conf.lldbbuilddir(), [NINJA, '-v'])
        footer()

    if target == 'all' or target == 'install':
        header("Install")
        run_cmd(conf.lldbbuilddir(), [NINJA, '-v', 'install'])
        footer()

    if target == 'all' or target == 'testlong':
        header("Run Debug Info Tests")
        run_cmd(conf.lldbbuilddir(), [NINJA, '-v', 'check-debuginfo'])
        footer()

    if target == 'all' or target == 'test' or target == 'testlong':
        header("Run Tests")
        run_cmd(conf.lldbbuilddir(),
                ['/usr/bin/env', 'TERM=vt100', NINJA, '-v', 'check-lldb'])
        footer()

    for test_target in conf.cmake_test_targets:
        header("Run Custom Test: {0}".format(test_target))
        run_cmd(conf.lldbbuilddir(), [NINJA, '-v', test_target])
        footer()


def lldb_cmake_standalone_builder(target):
    """Do a CMake standalone build of lldb."""

    standalone_type = conf.lldbstandalonetype()
    if standalone_type == "install-tree":
        llvm_dir = os.path.join(conf.installdir(), 'lib', 'cmake', 'llvm')
        clang_dir = os.path.join(conf.installdir(), 'lib', 'cmake', 'clang')
    elif standalone_type == "build-tree":
        llvm_dir = os.path.join(conf.builddir(), 'lib', 'cmake', 'llvm')
        clang_dir = os.path.join(conf.builddir(), 'lib', 'cmake', 'clang')
    else:
        raise RuntimeError(
            'Unknown standalone build type: {}'.format(standalone_type))

    test_dir = os.path.join(conf.workspace, 'test')
    log_dir = os.path.join(test_dir, 'logs')
    results_file = os.path.join(test_dir, 'results.xml')
    test_build_dir = os.path.join(conf.lldbstandalonebuilddir(
        standalone_type), 'lldb-test-build.noindex')
    create_dirs([conf.lldbstandalonebuilddir(standalone_type),
                 test_dir, log_dir, test_build_dir])
    cmake_build_type = conf.cmake_build_type if conf.cmake_build_type else 'RelWithDebInfo'
    dotest_args = [
        '--arch', 'x86_64', '--build-dir', test_build_dir,
        '-s={}'.format(log_dir), '-t', '--env', 'TERM=vt100'
    ]
    dotest_args.extend(conf.dotest_flags)

    cmake_cmd = ['/usr/local/bin/cmake', '-G', 'Ninja',
                 conf.lldbsrcdir(),
                 '-DCMAKE_BUILD_TYPE={}'.format(cmake_build_type),
                 '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
                 '-DCMAKE_MAKE_PROGRAM={}'.format(NINJA),
                 '-DLLDB_TEST_USER_ARGS='+';'.join(dotest_args),
                 '-DLLVM_ENABLE_ASSERTIONS:BOOL={}'.format(
                     "TRUE" if conf.assertions else "FALSE"),
                 '-DLLVM_ENABLE_MODULES=Off',
                 '-DLLVM_DIR={}'.format(llvm_dir),
                 '-DClang_DIR={}'.format(clang_dir),
                 '-DLLVM_LIT_ARGS=--xunit-xml-output={} -v'.format(
                     results_file),
                 '-DLLVM_VERSION_PATCH=99']
    cmake_cmd.extend(conf.cmake_flags)

    if standalone_type == "install-tree":
        external_lit = os.path.join(conf.builddir(), 'bin', 'llvm-lit')
        cmake_cmd.extend(['-DLLVM_LIT_ARGS=--xunit-xml-output={} -v'.format(results_file)])

    if conf.CC():
        cmake_cmd.extend(['-DCMAKE_C_COMPILER=' + conf.CC(),
                          '-DCMAKE_CXX_COMPILER=' + conf.CC() + "++"])

    header("Clean")
    delete_module_caches(conf.workspace)
    footer()

    if target == 'all' or target == 'build':
        header("CMake")
        run_cmd(conf.lldbstandalonebuilddir(standalone_type), cmake_cmd)
        footer()

        header("Build")
        run_cmd(conf.lldbstandalonebuilddir(standalone_type), [NINJA, '-v'])
        footer()


def lldb_cmake_xcode_builder(target):
    """Do a CMake standalone build of lldb using the Xcode generator."""

    create_dirs([conf.lldbxcodebuilddir()])

    cmake_build_type = conf.cmake_build_type if conf.cmake_build_type else 'RelWithDebInfo'

    llvm_dir = os.path.join(conf.builddir(), 'lib', 'cmake', 'llvm')
    clang_dir = os.path.join(conf.builddir(), 'lib', 'cmake', 'clang')
    xcode_cache = os.path.join(conf.lldbsrcdir(), 'cmake', 'caches', 'Apple-lldb-Xcode.cmake')

    cmake_cmd = ['/usr/local/bin/cmake',
                 '-C', xcode_cache,
                 '-G', 'Xcode',
                 '-L', conf.lldbsrcdir(),
                 '-DLLVM_ENABLE_ASSERTIONS:BOOL={}'.format("TRUE" if conf.assertions else "FALSE"),
                 '-DLLVM_ENABLE_MODULES=Off',
                 '-DLLVM_DIR={}'.format(llvm_dir),
                 '-DClang_DIR={}'.format(clang_dir),
                 '-DLLVM_VERSION_PATCH=99']
    cmake_cmd.extend(conf.cmake_flags)

    build_cmd = ['/usr/local/bin/cmake',
                 '--build', '.',
                 '--config', cmake_build_type]

    if conf.CC():
        cmake_cmd.extend(['-DCMAKE_C_COMPILER=' + conf.CC(),
                          '-DCMAKE_CXX_COMPILER=' + conf.CC() + "++"])

    header("Clean")
    delete_module_caches(conf.workspace)
    footer()

    if target == 'all' or target == 'build':
        header("CMake")
        run_cmd(conf.lldbxcodebuilddir(), cmake_cmd)
        footer()

        header("Build")
        run_cmd(conf.lldbxcodebuilddir(), build_cmd)
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


def create_builddirs():
    create_dirs([conf.builddir(), conf.installdir()]);


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
    prop_file = "last_good_build.properties"

    artifact_name = "clang-d{}-g{}-t{}-b{}.tar.gz".format(conf.git_distance,
                                                          conf.git_sha,
                                                          conf.build_id,
                                                          conf.build_number)
    new_url = conf.job_name + "/" + artifact_name

    with open(prop_file, 'w') as prop_fd:
        prop_fd.write("LLVM_REV={}\n".format(conf.svn_rev))
        prop_fd.write("GIT_DISTANCE={}\n".format(conf.git_distance))
        prop_fd.write("GIT_SHA={}\n".format(conf.git_sha))
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

    lng_cmd = ["ssh", "buildslave@" + SERVER,
               "ln", "-fs", "/Library/WebServer/Documents/artifacts/" +
               conf.job_name + "/" + artifact_name,
               "/Library/WebServer/Documents/artifacts/" +
               conf.job_name + "/g" + conf.git_sha]
    run_cmd(conf.workspace, lng_cmd)


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


KNOWN_TARGETS = ['all', 'configure', 'build', 'test', 'testlong', 'install']
KNOWN_BUILDS = [
    'clang', 'cmake', 'lldb-cmake', 'lldb-cmake-standalone',
    'lldb-cmake-xcode', 'lldb-cmake-sanitized', 'lldb-cmake-matrix', 'fetch',
    'artifact', 'static-analyzer-benchmarks'
]


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
    parser.add_argument('--projects', dest='llvm_enable_projects',
                        default="clang;clang-tools-extra;compiler-rt;libcxx",
                        help="Semicolon seperated list of projects to build.")

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
        elif args.build_type == 'lldb-cmake':
            lldb_cmake_builder(args.build_target)
        elif args.build_type == 'lldb-cmake-sanitized':
            lldb_cmake_builder(args.build_target, 'sanitized')
        elif args.build_type == 'lldb-cmake-matrix':
            lldb_cmake_builder(args.build_target, 'matrix')
        elif args.build_type == 'lldb-cmake-standalone':
            lldb_cmake_standalone_builder(args.build_target)
        elif args.build_type == 'lldb-cmake-xcode':
            lldb_cmake_xcode_builder(args.build_target)
        elif args.build_type == 'cmake':
            cmake_builder(args.build_target)
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

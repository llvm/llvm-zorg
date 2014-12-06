"""Build and test clangs."""

import sys
import logging
import os
import subprocess
import datetime
import argparse
import urllib
import shutil

SERVER = "labmaster2.local"

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
        self.j_level = os.environ.get('J_LEVEL', '4')
        self.host_compiler_url = os.environ.get('HOST_URL',
            'http://labmaster2.local/artifacts/')
        self.artifact_url = os.environ.get('ARTIFACT', 'NONE')
        self.job_name = os.environ.get('JOB_NAME', 'NONE')
        self.build_id = os.environ.get('BUILD_ID', 'NONE')
        self.build_number = os.environ.get('BUILD_NUMBER', 'NONE')
        self.svn_rev = os.environ.get('LLVM_REV', 'NONE')

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

# Global storage for configuration object.
conf = None


def cmake_builder(target):
    """Run a build_type build using cmake and ninja."""
    check_repo_state(conf.workspace)
    if conf.assertions:
        assert False, "Unimplemented, all builds have assertions"

    cmake_cmd = ["/usr/local/bin/cmake",
        "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Debug","-DLLVM_ENABLE_ASSERTIONS=On",
        "-DCMAKE_INSTALL_PREFIX=" + conf.installdir(),
        conf.srcdir(),
        '-DLLVM_LIT_ARGS=--xunit-xml-output=testresults.xunit.xml -v']

    if target == 'all' or target == 'build':
        header("Cmake")
        run_cmd(conf.builddir(), cmake_cmd)
        footer()
        header("Ninja build")
        run_cmd(conf.builddir(), ["/usr/local/bin/ninja"])
        footer()

    if target == 'all' or target == 'test':
        header("Ninja test")
        run_cmd(conf.builddir(), ["/usr/local/bin/ninja",
            'check', 'check-clang'])
        footer()

    if target == 'all' or target == 'testlong':
        header("Ninja test")
        run_cmd(conf.builddir(), ["/usr/local/bin/ninja", 'check-all'])
        footer()


def clang_builder(target):
    """Do a configure + make build of clang. Target is the type of build."""
    check_repo_state(conf.workspace)
    configure_cmd = [conf.srcdir() + "/configure"]

    if conf.assertions:
        configure_cmd.append("--enable-assertions")
    else:
        configure_cmd.append("--disable-assertions")

    if conf.lto:
        configure_cmd.extend(['--with-extra-options=-flto -gline-tables-only'])

    configure_cmd.extend(["--enable-optimized",
        "--disable-bindings", "--enable-targets=x86,x86_64,arm,aarch64",
        "--prefix=" + conf.installdir(), "--enable-libcpp"])
    if conf.CC():
        configure_cmd.append('CC='+conf.CC())
        configure_cmd.append('CXX='+conf.CC()+"++")

    rev_str =  "CLANG_REPOSITORY_STRING={}".format(conf.job_name) 
    svn_rev_str = "SVN_REVISION={}".format(conf.svn_rev)
    llvm_rev = "LLVM_VERSION_INFO= ({}: trunk {})".format(
        conf.job_name, conf.svn_rev)

    make_all = ["make", "-j", conf.j_level, "VERBOSE=1",
        rev_str, svn_rev_str, llvm_rev]

    if conf.lto and conf.liblto():
        dyld_path = conf.liblto()
        make_all.append("DYLD_LIBRARY_PATH=" + dyld_path)

    make_install = ["make", "install-clang", "-j", conf.j_level]

    make_check = ["make", "VERBOSE=1", "check-all", 'LIT_ARGS=--xunit-xml-output=testresults.xunit.xml -v']

    if target == 'build' or target == 'all':
        header("Configure")
        run_cmd(conf.builddir(), configure_cmd)
        footer()
        header("Make All")
        run_cmd(conf.builddir(), make_all)
        footer()
        header("Make Install")
        run_cmd(conf.builddir(), make_install)
        footer()
        header("Upload artifact")
        build_upload_artifact()
        footer()
        
    if target == 'test' or target == 'all':
        header("Make Check")
        run_cmd(conf.builddir(), make_check)
        footer()
        # run_cmd(conf.builddir(), make_check_debug)

def lldb_builder():
    """Do an Xcode build of lldb."""

    # Wipe the build folder

    header("Clean LLDB build directory")
    if os.path.exists(conf.lldbbuilddir()):
        shutil.rmtree(conf.lldbbuilddir())
    footer()

    # Build into the build folder

    xcodebuild_cmd = ["xcodebuild", "-arch", "x86_64", "-configuration", "BuildAndIntegration", "-scheme", "lldb-tool", "-derivedDataPath", conf.lldbbuilddir()]

    header("Make lldb-tool")
    run_cmd("lldb", xcodebuild_cmd)
    footer()
        
def check_repo_state(path):
    """Check the SVN repo at the path has all the
    nessessary repos checked out.  Check this by
    looking for the README.txt in each repo. """

    if os.environ.get('TESTING', False):
        return

    repo_readme_paths = ["llvm/README.txt",
                         "llvm/tools/clang/README.txt",
                         "llvm/tools/clang/tools/extra/README.txt",
                         "llvm/projects/compiler-rt/README.txt",
                         "llvm/projects/libcxx/LICENSE.TXT"]

    for readme in repo_readme_paths:
        full_readme_path = os.path.join(path, readme)
        if not os.path.exists(full_readme_path):
            logging.error("Cannot find Repo: " +
                readme + " in " + full_readme_path)
            sys.exit(1)


def derive():
    """Build a derived src tree from all the svn repos.

    Try to do this in a way that is pretty fast if the 
    derived tree is already there.
    """
    input_subpaths = ["llvm.src", "clang.src", "libcxx.src",
        "clang-tools-extra.src", "compiler-rt.src", "libcxx.src",
        "debuginfo-tests.src"]
    # Check for src dirs.
    for p in input_subpaths:
        full_path = os.path.join(conf.workspace, p)
        if not os.path.exists(full_path):
            logging.error("Cannot find Repo: in " + full_path)
            sys.exit(1)
    # Make sure destinations exist.
    tree_paths = ["tools/clang/test/debuginfo-tests",
                  "tools/clang/tools/extra",
                  "projects/compiler-rt",
                  "projects/libcxx",
                  ""
                  "tools/clang",]

    full_paths = [os.path.join(conf.srcdir(), x) for x in tree_paths]

    for p in full_paths:
        if not os.path.exists(p):
            os.makedirs(p)
    header("Derive Source")
    rsync_base_cmd = ["rsync", "-auvh", "--delete", "--exclude=.svn/"]

    llvm_rsync = ["--exclude=/tools/clang/",
        "--exclude=/projects/compiler-rt/", "--exclude=/projects/libcxx/",
         conf.workspace + "/llvm.src/", conf.srcdir()]

    run_cmd(conf.workspace, rsync_base_cmd + llvm_rsync)

    compile_rt_rsync = [ conf.workspace + "/compiler-rt.src/",
        conf.srcdir() + "/projects/compiler-rt"]

    run_cmd(conf.workspace, rsync_base_cmd + compile_rt_rsync)

    libcxx_rsync = [conf.workspace + "/libcxx.src/",
        conf.srcdir() + "/projects/libcxx"]

    run_cmd(conf.workspace, rsync_base_cmd + libcxx_rsync)

    clang_rsync = ["--exclude=/tools/extra", "--exclude=/test/debuginfo-tests/",
        conf.workspace + "/clang.src/", conf.srcdir() + "/tools/clang"]

    run_cmd(conf.workspace, rsync_base_cmd + clang_rsync)

    extra_rsync = [conf.workspace + "/clang-tools-extra.src/", conf.srcdir() + "/tools/clang/tools/extra"]

    run_cmd(conf.workspace, rsync_base_cmd + extra_rsync)

    dbg_rsync = [conf.workspace + "/debuginfo-tests.src/", conf.srcdir() + "/tools/clang/test/debuginfo-tests"]

    run_cmd(conf.workspace, rsync_base_cmd + dbg_rsync)
    footer()

def derive_lldb():
    """Build a derived src tree from all the svn repos.

    Try to do this in a way that is pretty fast if the 
    derived tree is already there.

    This is specific to LLDB builds
    """
    # Check for src dirs.
    input_subpaths = ["llvm.src", "clang.src", "lldb.src"]

    for p in input_subpaths:
        full_path = os.path.join(conf.workspace, p)
        if not os.path.exists(full_path):
            logging.error("Cannot find Repo: in " + full_path)
            sys.exit(1)

    # Make sure destinations exist.
    tree_paths = ["lldb/llvm/tools/clang",]
    full_paths = [os.path.join(conf.srcdir(), x) for x in tree_paths]

    for p in full_paths:
        if not os.path.exists(p):
            os.makedirs(p)

    # Rsync from the .src folders into the build tree
    header("Derive Source")
    rsync_base_cmd = ["rsync", "-auvh", "--delete", "--exclude=.svn/"]

    lldb_rsync = ["--exclude=/llvm",
         conf.workspace + "/lldb.src/", conf.lldbsrcdir()]

    llvm_rsync = ["--exclude=/tools/clang",
         conf.workspace + "/llvm.src/", conf.lldbsrcdir() + "/llvm"]

    clang_rsync = [
         conf.workspace + "/clang.src/", conf.lldbsrcdir() + "/llvm/tools/clang"]

    run_cmd(conf.workspace, rsync_base_cmd + lldb_rsync)
    run_cmd(conf.workspace, rsync_base_cmd + llvm_rsync)
    run_cmd(conf.workspace, rsync_base_cmd + clang_rsync)

    footer()


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


def run_cmd(working_dir, cmd):
    """Run a command in a working directory, and make sure it returns zero."""
    old_cwd = os.getcwd()
    cmd_to_print = ' '.join([quote_sh_string(x) for x in cmd])
    sys.stdout.write("cd {}\n{}\n".format(working_dir, cmd_to_print))
    sys.stdout.flush()

    start_time = datetime.datetime.now()
    if not os.environ.get('TESTING', False):
        os.chdir(working_dir)
        subprocess.check_call(cmd)
        os.chdir(old_cwd)
    end_time = datetime.datetime.now()
    
    logging.info("Command took {} seconds".format(
        (end_time-start_time).seconds))


KNOWN_TARGETS = ['all', 'build', 'test', 'testlong']
KNOWN_BUILDS = ['clang', 'cmake', 'lldb', 'derive', 'derive-lldb', 'fetch', 'artifact']


def parse_args():
    """Get the command line arguments, and make sure they are correct."""

    parser = argparse.ArgumentParser(
        description='Build and test compilers and other things.')

    parser.add_argument("build_type",
        help="The kind of build to trigger.", choices=KNOWN_BUILDS)

    parser.add_argument("build_target",  nargs='?',
        help="The targets to call (build, check, etc).", choices=KNOWN_TARGETS)

    parser.add_argument('--assertions', dest='assertions', action='store_true')
    parser.add_argument('--lto', dest='lto', action='store_true')

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
            derive()
        elif args.build_type == 'derive-lldb':
            derive_lldb()
        elif args.build_type == 'fetch':
            fetch_compiler()
        elif args.build_type == 'artifact':
            build_upload_artifact()
    except subprocess.CalledProcessError as exct:
        print "Command failed", exct.message
        print "Command:", exct.cmd
        sys.exit(1)


if __name__ == '__main__':
    main()

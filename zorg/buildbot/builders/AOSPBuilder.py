import buildbot
from buildbot.steps.shell import ShellCommand
from buildbot.steps.source import SVN
from zorg.buildbot.builders import PollyBuilder

# Setting up the build envrionment for building AOSP on Ubuntu (>=15.04).
# $ sudo apt-get update
# $ sudo apt-get install openjdk-8-jdk
# For older Ubuntu versions, refer to the following link for detailed instructions.
# https://source.android.com/source/initializing.html
#
# Downloading AOSP source.
# $ curl https://storage.googleapis.com/git-repo-downloads/repo > REPO_PATH/repo
# $ chmod a+x REPO_PATH/repo
# $ mkdir aosp && cd aosp
# $ REPO_PATH/repo init -u https://android.googlesource.com/platform/manifest -b BRANCH_NAME
# $ REPO_PATH/repo sync
# Refer to the following link for detailed instructions:
# http://source.android.com/source/downloading.html


def getAOSPBuildCommand(
    device,                # Target device for AOSP build
    timeout=None,          # Maximum CPU time in seconds, umlimited if 'None'
    target_clang=None,     # Path to the Clang used for AOSP target build
                           # Set target_clang to None to use AOSP's default Clang
    target_flags=None,     # Extra C/CXX flags for AOSP target build
    jobs=None,             # Number of concurrent jobs
    extra_make_args=None): # Extra args for the make command
    command = "source build/envsetup.sh"
    command += " && lunch aosp_%s-userdebug" % device
    command += " && make -k"
    if timeout:
        command += " TIMEOUT=%s" % timeout
    if target_clang:
        command += " TARGET_CLANG=%s" % target_clang
    if target_flags:
        command += " TARGET_FLAGS='%s'" % target_flags
    if extra_make_args:
        command += " " + extra_make_args
    if jobs:
        command += " -j" + str(jobs)
    return command


def getAOSPBuildFactory(
    device,                # Target device for AOSP build
    build_clang=False,     # Flag to control building Clang for AOSP target build
    extra_cmake_args=[],   # Extra args for the LLVM cmake command
                           # This flag is ignored if build_clang is False
    timeout=None,          # Maximum CPU time in seconds, umlimited if 'None'
    target_clang=None,     # Path to the Clang used for AOSP target build
                           # Set target_clang to None to use AOSP's default Clang
                           # This flag is ignored if build_clang is True
    target_flags=None,     # Extra C/CXX flags for AOSP target build
    jobs=None,             # Number of concurrent jobs
    extra_make_args=None,  # Extra args for the make command
    env={},                # Environmen variables for all steps
    clean=False,           # Flag to control whether AOSP repo is cleaned
    sync=False,            # Flag to control whether AOSP repo is synced
    patch=None):           # Name of the patch to apply to AOSP source
    f = buildbot.process.factory.BuildFactory()
    clang_dir = target_clang

    # Build Clang for AOSP target build
    if build_clang:
        f = PollyBuilder.getPollyBuildFactory(clean=True,
                                              install=True,
                                              make='ninja',
                                              jobs=jobs,
                                              env=env,
                                              extraCmakeArgs=extra_cmake_args)
        clang_dir = 'llvm.inst/bin'

    # Restore AOSP repo to a clean state
    if clean:
        f.addStep(ShellCommand(name="clean-repo",
                               command=['repo', 'forall', '-c',
                                        'git reset --hard; git clean -fdx'],
                               haltOnFailure=False,
                               description=["clean repo"],
                               workdir=".",
                               env=env))

    # Sync AOSP repo
    if sync:
        f.addStep(ShellCommand(name="sync-repo",
                               command=['repo', 'sync', '-c', '--no-tags'],
                               haltOnFailure=False,
                               description=["sync repo"],
                               workdir=".",
                               env=env))

    # Patch AOSP build system to allow switching Clang for target build
    if patch:
        f.addStep(ShellCommand(name="patch-aosp",
                               command=['patch', '-p1', '-i',
                                        'patches/%s.patch' % patch],
                               haltOnFailure=True,
                               description=["patch aosp"],
                               workdir=".",
                               env=env))

    # Delete existing output dir
    f.addStep(ShellCommand(name="delete-out-dir",
                           command=['rm', '-rf', 'out'],
                           haltOnFailure=False,
                           description=["delete out dir"],
                           workdir=".",
                           env=env))

    # Build AOSP
    f.addStep(ShellCommand(name="build-aosp",
                           command=getAOSPBuildCommand(device=device,
                                                       timeout=timeout,
                                                       target_clang=clang_dir,
                                                       target_flags=target_flags,
                                                       jobs=jobs,
                                                       extra_make_args=extra_make_args),
                           haltOnFailure=True,
                           description=["build aosp"],
                           workdir=".",
                           env=env))
    return f

import re
from zope.interface import implementer

from buildbot import interfaces
from buildbot import util
from buildbot.process.properties import Interpolate
from buildbot.plugins import reporters

import config
from zorg.buildbot.util.InformativeMailNotifier import LLVMInformativeMailNotifier

from twisted.python import log

# Should be a single e-mail address
status_email = str(config.options.get('Master Options', 'status_email')).split(',')

@implementer(interfaces.IEmailLookup)
class LLVMEmailLookup(util.ComparableMixin):
    compare_attrs = ("reNoreply")

    def __init__(self):
        # Casing does not matter in email addresses.
        self.reNoreply = re.compile(r"\bnoreply\b",re.I)

    def getAddress(self, name):
        """
        If name is already an email address, pass it through,
        unless email address contains the word "noreply".
        """
        if '@' in name:
            # Skip noreply address.
            return None if self.reNoreply.search(name) else name
        return None # Skip invalid or not complete email address.


# Returns a list of Status Targets. The results of each build will be
# pushed to these targets. buildbot.plugins reporters has a variety
# to choose from, including email senders, and IRC bots.
def getReporters():
    if not config.options.getboolean('Master Options', 'is_production'):
        # Staging buildbot does not report issues.
        log.msg(">>> getReporters: Staging buildbot does not report issues.")
        return []

    # Otherwise this is a production instance which reports issues.
    log.msg(">>> getReporters: Production mode. All reporters are registered.")
    return [

        # Report github status for all the release builders,
        # i.e. those with the "release" tag.
        reporters.GitHubStatusPush(
            str(config.options.get('GitHub Status', 'token')),
            context = Interpolate("%(prop:buildername)s"),
            verbose = True, # TODO: Turn off the verbosity once this is working reliably.
            builders = [
                    b.get('name') for b in config.builders.all
                    if 'silent' not in b.get('tags', [])
                ] + [
                    b.get('name') for b in config.release_builders.all
                    if 'release' in b.get('tags', [])
                ]
            ),

        reporters.IRC(
            useColors = False,
            host = str(config.options.get('IRC', 'host')),
            nick = str(config.options.get('IRC', 'nick')),
            channels = str(config.options.get('IRC', 'channels')).split(','),
            #authz=... # TODO: Consider allowing "harmful" operations to authorizes users.
            useRevisions = False, # FIXME: There is a bug in the buildbot
            showBlameList = True,
            notify_events = str(config.options.get('IRC', 'notify_events')).split(','),
            ),

        reporters.MailNotifier(
            mode = ('problem',),
            fromaddr = "llvm.buildmaster@lab.llvm.org", # TODO: Change this to buildmaster@lab.llvm.org.
            extraRecipients = status_email,
            extraHeaders = {
                "Reply-To": status_email[0], # The first from the list.
                # Tags for Mailgun analyses.
                # TODO: Consider this being configured in local.cfg.
                "X-Mailgun-Tag" : Interpolate("builder=%(prop:buildername)s"),
            },
            lookup = LLVMEmailLookup(),
            messageFormatter = LLVMInformativeMailNotifier,
            # TODO: For debug purposes only. Remove later.
            dumpMailsToLog = True,
            builders = [
                    b.get('name') for b in config.builders.all
                    if 'silent' not in b.get('tags', [])
                ]
            ),

        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["gribozavr@gmail.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["clang-x86_64-debian-fast"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["tbaeder@redhat.com", "tstellar@redhat.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["llvm-x86_64-debian-dylib"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["llvm.buildmaster@quicinc.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["clang-hexagon-elf"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["Ulrich.Weigand@de.ibm.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["clang-s390x-linux", "clang-s390x-linux-multistage",
                        "clang-s390x-linux-lnt", "mlir-s390x-linux",
                        "openmp-s390x-linux"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["sunil_srivastava@playstation.sony.com",
                                "warren_ristow@playstation.sony.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["clang-x86_64-linux-abi-test"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["gkistanova@gmail.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["lld-x86_64-win",
                        "lld-x86_64-freebsd",
                        "clang-x86_64-linux-abi-test",
                        "clang-with-lto-ubuntu", "clang-with-thin-lto-ubuntu",
                        "llvm-clang-x86_64-expensive-checks-win",
                        "llvm-clang-x86_64-expensive-checks-ubuntu"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["efriedma@codeaurora.org", "huihuiz@codeaurora.org"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["polly-arm-linux",
                        "aosp-O3-polly-before-vectorizer-unprofitable"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["mgrang@codeaurora.org"],
            subject = "Build %(builder)s Failure",
            mode = "problem",
            builders = ["reverse-iteration"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["tra+buildbot@google.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["clang-cuda-k80", "clang-cuda-p4", "clang-cuda-t4"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["asb@lowrisc.org"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["llvm-riscv-linux"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["gongsu@us.ibm.com", "alexe@us.ibm.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["mlir-s390x-linux-werror"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["phosek@google.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["fuchsia-x86_64-linux"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["labath@google.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["lldb-x86_64-debian"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["vvereschaka@accesssoftek.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["llvm-clang-x86_64-win-fast","lld-x86_64-ubuntu-fast",
                        "llvm-clang-x86_64-expensive-checks-ubuntu",
                        "llvm-clang-win-x-armv7l", "llvm-clang-win-x-aarch64",
                        "llvm-nvptx-nvidia-ubuntu", "llvm-nvptx64-nvidia-ubuntu",
                        "llvm-nvptx-nvidia-win", "llvm-nvptx64-nvidia-win"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["llvm.buildbot@emea.nec.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["clang-ve-ninja"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["lntue@google.com", "michaelrj@google.com",
                            "ndesaulniers@google.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["libc-x86_64-debian", "libc-x86_64_debian-dbg",
                        "libc-x86_64-debian-dbg-runtimes-build",
                        "libc-x86_64-debian-dbg-asan", "libc-aarch64-ubuntu-dbg",
                        "libc-x86_64-windows-dbg", "libc-arm32-debian-dbg",
                        "libc-aarch64-ubuntu-fullbuild-dbg",
                        "libc-x86_64-debian-fullbuild-dbg",
                        "libc-x86_64-debian-gcc-fullbuild-dbg",
                        "libc-x86_64-debian-fullbuild-dbg-asan",
                        "libc-riscv64-debian-dbg",
                        "libc-riscv64-debian-fullbuild-dbg",
                        "libc-x86_64-debian-dbg-lint"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["aaron@aaronballman.com"],
            subject = "Sphinx build %(builder)s Failure",
            mode = "failing",
            builders = ["publish-sphinx-docs"]),
        reporters.MailNotifier(
            fromaddr="llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients=[
                "mlcompileropt-buildbot@google.com"],
            subject = "ML Compiler Opt Failure: %(builder)s",
            mode = "failing",
            builders = [
                "ml-opt-dev-x86-64", "ml-opt-rel-x86-64", "ml-opt-devrel-x86-64"]),
        reporters.MailNotifier(
            fromaddr="llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients=[
                "tejohnson@google.com"],
            subject = "ThinLTO WPD Failure: %(builder)s",
            mode = "failing",
            builders = ["clang-with-thin-lto-wpd-ubuntu"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["douglas.yung@sony.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["llvm-clang-x86_64-sie-ubuntu-fast",
                        "llvm-clang-x86_64-sie-win",
                        "llvm-clang-x86_64-sie-win-release",
                        "llvm-clang-x86_64-gcc-ubuntu",
                        "llvm-clang-x86_64-gcc-ubuntu-release",
                        "cross-project-tests-sie-ubuntu",
                        "cross-project-tests-sie-ubuntu-dwarf5",
                        "clang-x86_64-linux-abi-test",
                        "llvm-clang-x86_64-darwin",
                        "llvm-clang-aarch64-darwin"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["tom.weaver@sony.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["llvm-clang-x86_64-sie-ubuntu-fast",
                        "llvm-clang-x86_64-sie-win",
                        "llvm-clang-x86_64-gcc-ubuntu"]),
        reporters.MailNotifier(
            fromaddr="llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients=[
                "joker.eph@gmail.com"],
            subject = "MLIR Build Failure: %(builder)s",
            mode = "failing",
            builders = ["mlir-nvidia", "mlir-nvidia-gcc7"]),
        reporters.MailNotifier(
            fromaddr="llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients=[
                "mlir-bugs-external+buildbot@googlegroups.com"],
            subject = "MLIR Build Failure: %(builder)s",
            mode = "failing",
            builders = ["mlir-nvidia",
                        "ppc64le-mlir-rhel-clang"]),
        reporters.MailNotifier(
            fromaddr="llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients=["dl.gcr.lightning.buildbot@amd.com"],
            subject = "Build Failure: %(builder)s",
            mode = "failing",
            builders = ["clang-hip-vega20"]),
        reporters.MailNotifier(
            fromaddr="llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients=["llvm_arc_buildbot@synopsys.com", "heli@synopsys.com"],
            subject = "Build Failure: %(builder)s",
            mode = "failing",
            builders = ["arc-builder"]),
        reporters.MailNotifier(
            fromaddr="llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients=["dl.gcr.lightning.buildbot@amd.com"],
            subject = "Build Failure: %(builder)s",
            mode = "failing",
            builders = ["openmp-offload-amdgpu-runtime"]),
        reporters.MailNotifier(
            fromaddr="llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients=["dl.mlse.buildbot@amd.com"],
            subject = "Build Failure: %(builder)s",
            mode = "failing",
            builders = ["mlir-rocm-mi200"]),
        reporters.MailNotifier(
            fromaddr="llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients=["flangbuilder@meinersbur.de"],
            subject = "Build Failure (flang): %(builder)s",
            mode = "failing",
            builders = ["flang-x86_64-windows"]),
        reporters.MailNotifier(
            fromaddr="llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients=["offloadbuilder@meinersbur.de"],
            subject = "Build Failure (offload): %(builder)s",
            mode = "failing",
            builders = ["openmp-offload-cuda-project","openmp-offload-cuda-runtime"]),
        reporters.MailNotifier(
            fromaddr="llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients=["pollybuilder@meinersbur.de"],
            subject = "Build Failure (polly): %(builder)s",
            mode = "failing",
            builders = [
                    "polly-x86_64-linux",
                    "polly-x86_64-linux-noassert",
                    "polly-x86_64-linux-plugin",
                    "polly-x86_64-linux-shared",
                    "polly-x86_64-linux-shared-plugin",
                    "polly-x86_64-linux-shlib",
                    "polly-x86_64-linux-shlib-plugin",
                    "polly-sphinx-docs",
                ]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["orlando.hyams@sony.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["cross-project-tests-sie-ubuntu",
                        "llvm-clang-x86_64-sie-win"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["kkleine@redhat.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["standalone-build-x86_64"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["llvm-bolt@meta.com"],
            subject = "BOLT NFC checks mismatch",
            mode = ("warnings",),
            builders = ["bolt-x86_64-ubuntu-nfc"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["luweining@loongson.cn", "chenli@loongson.cn"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["clang-loongarch64-linux"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["kadircet@google.com", "sammccall@google.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["clangd-ubuntu-tsan"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["kadircet@google.com", "ibiryukov@google.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["clang-debian-cpp20"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["llvm.buildbot.notification@intel.com"],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ["clang-cmake-x86_64-avx512-linux"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            messageFormatter = LLVMInformativeMailNotifier,
            extraRecipients = ["llvm-premerge-buildbots@google.com"],
            mode = "failing",
            builders = ["premerge-monolithic-windows", "premerge-monolithic-linux"]),
        reporters.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            messageFormatter = LLVMInformativeMailNotifier,
            extraRecipients = ["szakharin@nvidia.com"],
            subject = "Build Failure (flang-runtime): %(builder)s",
            mode = "failing",
            builders = ["flang-runtime-cuda-gcc", "flang-runtime-cuda-clang"]),
    ]

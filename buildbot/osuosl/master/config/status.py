import re
from zope.interface import implementer

from buildbot import interfaces
from buildbot import util
from buildbot.process.properties import Interpolate
from buildbot.plugins import reporters
from buildbot.reporters.generators.build import BuildStartEndStatusGenerator
from buildbot.reporters.message import MessageFormatterRenderable
from twisted.python import log

import config
from zorg.buildbot.util.InformativeMailNotifier import (
    LLVMInformativeMailGenerator,
    LLVMDefaultBuildStatusGenerator
)

# Should be a single e-mail address
status_email_fromaddr = str(config.options.get('Master Options', 'status_email_fromaddr',
                            fallback='llvm.buildmaster@lab.llvm.org'))

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
    if not config.options.getboolean('Master Options', 'is_production', fallback=False):
        # Staging buildbot does not report issues.
        log.msg(">>> getReporters: Staging buildbot does not report issues.")
        return []

    # Otherwise this is a production instance which reports issues.
    log.msg(">>> getReporters: Production mode. All reporters are registered.")

    r=[]

    if config.options.has_option('GitHub Status', 'token'):
        start_formatter = MessageFormatterRenderable('Build started.')
        end_formatter = MessageFormatterRenderable('Build done.')

        # Report github status for all the release builders,
        # i.e. those with the "release" tag.
        r.append(
            reporters.GitHubStatusPush(
                str(config.options.get('GitHub Status', 'token')),
                context = Interpolate("%(prop:buildername)s"),
                verbose = True, # TODO: Turn off the verbosity once this is working reliably.
                generators = [
                    BuildStartEndStatusGenerator(
                        start_formatter = start_formatter,
                        end_formatter = end_formatter,
                        builders = [
                            b.get('name') for b in config.builders.all
                            if 'silent' not in b.get('tags', [])
                        ] + [
                            b.get('name') for b in config.release_builders.all
                            if 'release' in b.get('tags', [])
                        ]
                    ),
                ]))
    else:
        log.msg("Warning: No 'GitHub Status' notifier has been configured.")

    if config.options.has_section("IRC"):
        r.append(
            reporters.IRC(
                useColors = False,
                host = str(config.options.get('IRC', 'host')),
                nick = str(config.options.get('IRC', 'nick')),
                channels = str(config.options.get('IRC', 'channels')).split(','),
                #authz=... # TODO: Consider allowing "harmful" operations to authorizes users.
                useRevisions = False, # FIXME: There is a bug in the buildbot
                showBlameList = True,
                notify_events = str(config.options.get('IRC', 'notify_events')).split(','),
            ))
    else:
        log.msg("Warning: No 'IRC' notifier has been configured.")

    r.extend([
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            extraRecipients = [status_email_fromaddr],
            extraHeaders = {
                "Reply-To": status_email_fromaddr,
                # Tags for Mailgun analyses.
                # TODO: Consider this being configured in local.cfg.
                "X-Mailgun-Tag" : Interpolate("builder=%(prop:buildername)s"),
            },
            lookup = LLVMEmailLookup(),
            # TODO: For debug purposes only. Remove later.
            dumpMailsToLog = True,
            generators = [
                LLVMInformativeMailGenerator(
                    builders = [
                        b.get('name') for b in config.builders.all
                        if 'silent' not in b.get('tags', [])
                    ])
            ]),

        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["gribozavr@gmail.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = ["clang-x86_64-debian-fast"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["tbaeder@redhat.com", "tstellar@redhat.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = ["llvm-x86_64-debian-dylib"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["llvm.buildmaster@quicinc.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = ["clang-hexagon-elf"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["Ulrich.Weigand@de.ibm.com"],
            generators = [
               LLVMDefaultBuildStatusGenerator(
                   builders = [
                       "clang-s390x-linux",
                       "clang-s390x-linux-multistage",
                       "clang-s390x-linux-lnt",
                       "mlir-s390x-linux"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["sunil_srivastava@playstation.sony.com",
                                "warren_ristow@playstation.sony.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = ["clang-x86_64-linux-abi-test"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["gkistanova@gmail.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = [
                        "lld-x86_64-win",
                        "lld-x86_64-freebsd",
                        "clang-x86_64-linux-abi-test",
                        "clang-with-lto-ubuntu", "clang-with-thin-lto-ubuntu",
                        "llvm-clang-x86_64-expensive-checks-win",
                        "llvm-clang-x86_64-expensive-checks-ubuntu"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["efriedma@codeaurora.org", "huihuiz@codeaurora.org"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = [
                        "polly-arm-linux",
                        "aosp-O3-polly-before-vectorizer-unprofitable"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["mgrang@codeaurora.org"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    mode = "problem",
                    builders = ["reverse-iteration"]),
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["tra+buildbot@google.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = [
                        "clang-cuda-l4",
                        "clang-cuda-p4",
                        "clang-cuda-t4"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["asb@lowrisc.org"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = ["llvm-riscv-linux"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["gongsu@us.ibm.com", "alexe@us.ibm.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = ["mlir-s390x-linux-werror"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["phosek@google.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = ["fuchsia-x86_64-linux"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["labath@google.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = ["lldb-x86_64-debian"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["vvereschaka@accesssoftek.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = [
                        "llvm-clang-x86_64-win-fast","lld-x86_64-ubuntu-fast",
                        "llvm-clang-x86_64-expensive-checks-ubuntu",
                        "llvm-clang-win-x-armv7l", "llvm-clang-win-x-aarch64",
                        "llvm-nvptx-nvidia-ubuntu", "llvm-nvptx64-nvidia-ubuntu",
                        "llvm-nvptx-nvidia-win", "llvm-nvptx64-nvidia-win"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["llvm.buildbot@emea.nec.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = ["clang-ve-ninja"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["lntue@google.com", "michaelrj@google.com",
                            "ndesaulniers@google.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = [
                        "libc-x86_64-debian",
                        "libc-x86_64_debian-dbg",
                        "libc-x86_64-debian-dbg-runtimes-build",
                        "libc-x86_64-debian-dbg-asan",
                        "libc-aarch64-ubuntu-dbg",
                        "libc-x86_64-windows-dbg",
                        "libc-arm32-debian-dbg",
                        "libc-aarch64-ubuntu-fullbuild-dbg",
                        "libc-x86_64-debian-fullbuild-dbg",
                        "libc-x86_64-debian-gcc-fullbuild-dbg",
                        "libc-x86_64-debian-fullbuild-dbg-asan",
                        "libc-riscv64-debian-dbg",
                        "libc-riscv64-debian-fullbuild-dbg",
                        "libc-x86_64-debian-dbg-lint"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["aaron@aaronballman.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    subject = "Sphinx build %(builder)s Failure",
                    builders = ["publish-sphinx-docs"])
            ]),
        reporters.MailNotifier(
            fromaddr=status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients=[
                "mlcompileropt-buildbot@google.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    subject = "ML Compiler Opt Failure: %(builder)s",
                    builders = [
                        "ml-opt-dev-x86-64",
                        "ml-opt-rel-x86-64",
                        "ml-opt-devrel-x86-64"])
            ]),
        reporters.MailNotifier(
            fromaddr=status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients=[
                "tejohnson@google.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    subject = "ThinLTO WPD Failure: %(builder)s",
                    builders = ["clang-with-thin-lto-wpd-ubuntu"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["douglas.yung@sony.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = [
                        "llvm-clang-x86_64-sie-ubuntu-fast",
                        "llvm-clang-x86_64-sie-win",
                        "llvm-clang-x86_64-sie-win-release",
                        "llvm-clang-x86_64-gcc-ubuntu",
                        "llvm-clang-x86_64-gcc-ubuntu-release",
                        "cross-project-tests-sie-ubuntu",
                        "cross-project-tests-sie-ubuntu-dwarf5",
                        "clang-x86_64-linux-abi-test",
                        "llvm-clang-x86_64-darwin",
                        "llvm-clang-aarch64-darwin",
                        "llvm-clang-aarch64-darwin-release"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["tom.weaver@sony.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = [
                        "llvm-clang-x86_64-sie-ubuntu-fast",
                        "llvm-clang-x86_64-sie-win",
                        "llvm-clang-x86_64-gcc-ubuntu"])
            ]),
        reporters.MailNotifier(
            fromaddr=status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = [
                "jeremy.morse.llvm@gmail.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    subject = "Build %(builder)s Failure",
                    builders = [
                        "llvm-new-debug-iterators"])
            ]),
        reporters.MailNotifier(
            fromaddr=status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients=[
                "joker.eph@gmail.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    subject = "MLIR Build Failure: %(builder)s",
                    builders = [
                        "mlir-nvidia",
                        "mlir-nvidia-gcc7"])
            ]),
        reporters.MailNotifier(
            fromaddr=status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients=[
                "mlir-bugs-external+buildbot@googlegroups.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    subject = "MLIR Build Failure: %(builder)s",
                    builders = [
                        "mlir-nvidia",
                        "ppc64le-mlir-rhel-clang"])
            ]),
        reporters.MailNotifier(
            fromaddr=status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients=["dl.gcr.lightning.buildbot@amd.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    subject = "Build Failure: %(builder)s",
                    builders = ["clang-hip-vega20"])
            ]),
        reporters.MailNotifier(
            fromaddr=status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients=["llvm_arc_buildbot@synopsys.com", "heli@synopsys.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    subject = "Build Failure: %(builder)s",
                    builders = ["arc-builder"])
            ]),
        reporters.MailNotifier(
            fromaddr=status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients=["dl.gcr.lightning.buildbot@amd.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    subject = "Build Failure: %(builder)s",
                    builders = ["openmp-offload-amdgpu-runtime"])
            ]),
        reporters.MailNotifier(
            fromaddr=status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients=["dl.mlse.buildbot@amd.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    subject = "Build Failure: %(builder)s",
                    builders = ["mlir-rocm-mi200"])
            ]),
        reporters.MailNotifier(
            fromaddr=status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients=["flangbuilder@meinersbur.de"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    subject = "Build Failure (flang): %(builder)s",
                    builders = ["flang-x86_64-windows"])
            ]),
        reporters.MailNotifier(
            fromaddr=status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients=["offloadbuilder@meinersbur.de"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    subject = "Build Failure (offload): %(builder)s",
                    builders = [
                        "openmp-offload-cuda-project",
                        "openmp-offload-cuda-runtime"])
            ]),
        reporters.MailNotifier(
            fromaddr=status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients=["pollybuilder@meinersbur.de"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    subject = "Build Failure (polly): %(builder)s",
                    builders = [
                        "polly-x86_64-linux",
                        "polly-x86_64-linux-noassert",
                        "polly-x86_64-linux-plugin",
                        "polly-x86_64-linux-shared",
                        "polly-x86_64-linux-shared-plugin",
                        "polly-x86_64-linux-shlib",
                        "polly-x86_64-linux-shlib-plugin",
                        "polly-sphinx-docs",
                    ])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["orlando.hyams@sony.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = [
                        "cross-project-tests-sie-ubuntu",
                        "llvm-clang-x86_64-sie-win"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["kkleine@redhat.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = ["standalone-build-x86_64"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["llvm-bolt@meta.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    subject = "BOLT NFC checks mismatch",
                    mode = ("warnings",),
                    builders = ["bolt-x86_64-ubuntu-nfc"]),
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["luweining@loongson.cn", "chenli@loongson.cn"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = ["clang-loongarch64-linux"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["kadircet@google.com", "sammccall@google.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = ["clangd-ubuntu-tsan"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["kadircet@google.com", "ibiryukov@google.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = ["clang-debian-cpp20"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["llvm.buildbot.notification@intel.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = ["clang-cmake-x86_64-avx512-linux"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["llvm-premerge-buildbots@google.com", "joker.eph@gmail.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = [
                        "premerge-monolithic-windows",
                        "premerge-monolithic-linux"])
            ]),
        reporters.MailNotifier(
            fromaddr = status_email_fromaddr,
            sendToInterestedUsers = False,
            extraRecipients = ["szakharin@nvidia.com"],
            generators = [
                LLVMDefaultBuildStatusGenerator(
                    builders = [
                        "flang-runtime-cuda-gcc",
                        "flang-runtime-cuda-clang"])
            ]),
    ])

    return r

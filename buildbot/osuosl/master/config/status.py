import re
from importlib import reload
from zope.interface import implementer

from buildbot import interfaces
from buildbot import util
from buildbot.process.properties import Interpolate
from buildbot.process.results import FAILURE
from buildbot.plugins import reporters
from buildbot.reporters.generators.build import BuildStartEndStatusGenerator
from buildbot.reporters.message import MessageFormatterMissingWorker
from twisted.python import log

import config

from zorg.buildbot.reporters import utils
reload(utils)

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


# Return True only if we need to label this PR.
def is_message_needed_nvptx_backend(build):
    try:
        for step in build["steps"]:
            if step["results"] != FAILURE:
                continue
            if step["name"] not in [
                "build-unified-tree",
                "test-build-unified-tree-check-llvm",
            ]:
                continue
            # Process all logs. The first failed log may be not NVPTX related.
            for i, _log in enumerate(step["logs"]):
                log_fail = None
                log_stdio = None
                if _log["name"].startswith("FAIL: "):
                    log_fail = _log["content"]["content"]
                if _log["type"] == "s":
                    log_stdio = _log["content"]["content"]
                log_fail = log_fail or log_stdio
                if not log_fail:
                    continue
                for line in log_fail.splitlines():
                    # if log_fail == log_stdio and line[:1] in ["h", "o", "e"]:
                    #    line = line[1:] # Remove stdio line prefix.
                    if "ptxas fatal" in line:
                        return True
                    if (
                        "*** TEST " in line
                        and "NVPTX" in line.upper()
                        and " FAILED ***" in line
                    ):
                        return True
                    # Assert: Stack dump: N. Running pass 'NVPTX ...
                    if "Running pass 'NVPTX " in line:
                        return True
                    # Assert: LLVM ERROR: Support for ... introduced in PTX ISA version 6.0 and requires target sm_30.
                    if "introduced in PTX ISA version" in line:
                        return True

    except Exception as err:
        log.msg(f"EXCEPTION in is_message_needed_nvptx_backend(): {err}")
    return False


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
        token = str(config.options.get('GitHub Status', 'token'))
        r.append(
            utils.LLVMFailGitHubReporter(
                token = token,
                generators = [
                    utils.LLVMFailBuildGenerator(
                        builders = [
                            b.get('name') for b in config.builders.all
                            if 'silent' not in b.get('tags', [])
                        ]
                    )
                ]
            )
        )

        r.append(
            utils.LLVMFailGitHubLabeler(
                token = token,
                generators = [
                    utils.LLVMFailBuildGenerator(
                        message_formatter = utils.LLVMLabelFormatter(label='backend:NVPTX'),
                        is_message_needed_filter = is_message_needed_nvptx_backend,
                        builders = [
                            'llvm-nvptx-nvidia-ubuntu',
                            'llvm-nvptx-nvidia-win',
                            'llvm-nvptx64-nvidia-ubuntu',
                            'llvm-nvptx64-nvidia-win'
                        ]
                    )
                ]
            )
        )

        # Report github status for all the release builders,
        # i.e. those with the "release" tag.
        r.append(
            reporters.GitHubStatusPush(
                token = token,
                context = Interpolate("%(prop:buildername)s"),
                verbose = True, # TODO: Turn off the verbosity once this is working reliably.
                generators = [
                    BuildStartEndStatusGenerator(
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
                utils.LLVMInformativeMailGenerator(
                    builders = [
                        b.get('name') for b in config.builders.all
                        if 'silent' not in b.get('tags', [])
                    ])
            ]),

        utils.LLVMDefaultMailNotifier(
            fromaddr = status_email_fromaddr,
            generators = [
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["gribozavr@gmail.com"],
                    builders=["clang-x86_64-debian-fast"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["tbaeder@redhat.com", "tstellar@redhat.com"],
                    builders=["llvm-x86_64-debian-dylib"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["llvm.buildmaster@quicinc.com"],
                    builders=["clang-hexagon-elf"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["Ulrich.Weigand@de.ibm.com"],
                    builders=[
                        "clang-s390x-linux",
                        "clang-s390x-linux-multistage",
                        "clang-s390x-linux-lnt",
                        "mlir-s390x-linux",
                        "openmp-s390x-linux",
                    ],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=[
                        "sunil_srivastava@playstation.sony.com",
                        "warren_ristow@playstation.sony.com",
                    ],
                    builders=["clang-x86_64-linux-abi-test"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["gkistanova@gmail.com"],
                    builders=[
                        "lld-x86_64-win",
                        "lld-x86_64-freebsd",
                        "clang-x86_64-linux-abi-test",
                        "clang-with-lto-ubuntu",
                        "clang-with-thin-lto-ubuntu",
                        "llvm-clang-x86_64-expensive-checks-win",
                        "llvm-clang-x86_64-expensive-checks-ubuntu",
                    ],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=[
                        "efriedma@codeaurora.org",
                        "huihuiz@codeaurora.org",
                    ],
                    builders=[
                        "polly-arm-linux",
                        "aosp-O3-polly-before-vectorizer-unprofitable",
                    ],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    mode="problem",
                    recipients=["mgrang@codeaurora.org"],
                    builders=["reverse-iteration"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["tra+buildbot@google.com"],
                    builders=["clang-cuda-l4", "clang-cuda-p4", "clang-cuda-t4"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["asb@lowrisc.org"],
                    builders=["llvm-riscv-linux"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["gongsu@us.ibm.com", "alexe@us.ibm.com"],
                    builders=["mlir-s390x-linux-werror"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["phosek@google.com"],
                    builders=["fuchsia-x86_64-linux"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["vvereschaka@accesssoftek.com"],
                    builders=[
                        "llvm-clang-x86_64-win-fast",
                        "lld-x86_64-ubuntu-fast",
                        "llvm-clang-x86_64-expensive-checks-ubuntu",
                        "llvm-clang-win-x-armv7l",
                        "llvm-clang-win-x-aarch64",
                        "llvm-nvptx-nvidia-ubuntu",
                        "llvm-nvptx64-nvidia-ubuntu",
                        "llvm-nvptx-nvidia-win",
                        "llvm-nvptx64-nvidia-win",
                        "lldb-remote-linux-ubuntu",
                        "lldb-remote-linux-win",
                        "lldb-x86_64-win",
                        "llvm-clang-ubuntu-x-aarch64-pac-ret",
                        "llvm-clang-ubuntu-x-aarch64-pauthtest",
                    ],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["dvassiliev@accesssoftek.com"],
                    builders=[
                        "llvm-nvptx-nvidia-ubuntu",
                        "llvm-nvptx64-nvidia-ubuntu",
                        "llvm-nvptx-nvidia-win",
                        "llvm-nvptx64-nvidia-win",
                        "flang-runtime-cuda-gcc",
                        "nvhpc-offload-nvgpu-x86_64-linux",
                    ],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=[
                        "dvassiliev@accesssoftek.com",
                        "vdzhidzhoev@accesssoftek.com",
                    ],
                    builders=[
                        "lldb-remote-linux-ubuntu",
                        "lldb-remote-linux-win",
                        "lldb-x86_64-win",
                    ],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=[
                        "atrosinenko@accesssoftek.com",
                        "dkovalev@accesssoftek.com",
                    ],
                    builders=[
                        "llvm-clang-ubuntu-x-aarch64-pac-ret",
                        "llvm-clang-ubuntu-x-aarch64-pauthtest",
                    ],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["llvm.buildbot@emea.nec.com"],
                    builders=["clang-ve-ninja"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=[
                        "lntue@google.com",
                        "michaelrj@google.com",
                    ],
                    builders=[
                        "libc-aarch64-ubuntu-dbg",
                        "libc-aarch64-ubuntu-fullbuild-dbg",
                        "libc-arm32-qemu-debian-dbg",
                        "libc-riscv64-debian-dbg",
                        "libc-riscv64-debian-fullbuild-dbg",
                        "libc-x86_64-debian",
                        "libc-x86_64-debian-dbg-asan",
                        "libc-x86_64-debian-dbg-bootstrap-build",
                        "libc-x86_64-debian-dbg-lint",
                        "libc-x86_64-debian-fullbuild-dbg",
                        "libc-x86_64-debian-fullbuild-dbg-asan",
                        "libc-x86_64-debian-gcc-fullbuild-dbg",
                        "libc-x86_64-windows-dbg",
                        "libc-x86_64_debian-dbg",
                    ],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=[
                        "douglas.yung@sony.com",
                        "douglasyung.llvm@gmail.com",
                    ],
                    builders=[
                        "llvm-clang-x86_64-sie-ubuntu-fast",
                        "llvm-clang-x86_64-sie-ps5-fast",
                        "llvm-clang-x86_64-sie-win",
                        "llvm-clang-x86_64-sie-win-release",
                        "llvm-clang-x86_64-gcc-ubuntu",
                        "llvm-clang-x86_64-gcc-ubuntu-release",
                        "llvm-clang-x86_64-gcc-ubuntu-no-asserts",
                        "cross-project-tests-sie-ubuntu",
                        "cross-project-tests-sie-ubuntu-dwarf5",
                        "clang-x86_64-linux-abi-test",
                        "llvm-clang-x86_64-darwin",
                        "llvm-clang-aarch64-darwin",
                        "llvm-clang-aarch64-darwin-release",
                        "llvm-x86_64-debugify-coverage",
                    ],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["tom.weaver@sony.com"],
                    builders=[
                        "llvm-clang-x86_64-sie-ubuntu-fast",
                        "llvm-clang-x86_64-sie-win",
                        "llvm-clang-x86_64-gcc-ubuntu",
                    ],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=[
                        "llvm_arc_buildbot@synopsys.com",
                        "heli@synopsys.com",
                    ],
                    builders=["arc-builder"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["dl.gcr.lightning.buildbot@amd.com"],
                    builders=[
                        "clang-hip-vega20",
                        "openmp-offload-amdgpu-runtime",
                        "openmp-offload-amdgpu-runtime-2",
                        "openmp-offload-libc-amdgpu-runtime",
                        "amdgpu-offload-ubuntu-22-cmake-build-only",
                        "amdgpu-offload-build-only",
                        "amdgpu-hip-blender",
                        "amdgpu-hip-tpl",
                        "amdgpu-clang-flang",
                    ],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["dl.mlse.buildbot@amd.com"],
                    builders=["mlir-rocm-mi200"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["orlando.hyams@sony.com"],
                    builders=[
                        "cross-project-tests-sie-ubuntu",
                        "llvm-clang-x86_64-sie-win",
                    ],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["kkleine@redhat.com"],
                    builders=["standalone-build-x86_64"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["luweining@loongson.cn", "chenli@loongson.cn"],
                    builders=["clang-loongarch64-linux"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["kadircet@google.com", "sammccall@google.com"],
                    builders=["clangd-ubuntu-tsan"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["kadircet@google.com", "ibiryukov@google.com"],
                    builders=["clang-debian-cpp20"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["llvm.buildbot.notification@intel.com"],
                    builders=["clang-cmake-x86_64-avx512-linux"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["szakharin@nvidia.com"],
                    builders=["flang-runtime-cuda-gcc"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=[
                        "nvhpc-llvm-offload-buildbot-watchers@nvidia.com"
                    ],
                    builders=["nvhpc-offload-nvgpu-x86_64-linux"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["stephen.tozer@sony.com"],
                    builders=["llvm-x86_64-debugify-coverage"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["profcheck-buildbot@google.com"],
                    builders=["profcheck"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=[
                        "llvm-presubmit-infra@google.com",
                        "aidengrossman@google.com",
                        "cmtice@google.com",
                    ],
                    subject="Premerge Buildbot Failure: {{ buildername }}",
                    builders=[
                        "premerge-monolithic-linux",
                        "premerge-monolithic-windows",
                    ],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["google-integrate-buildbot@google.com"],
                    builders=["release-noassertions-warnings"],
                ),
            ],
        ),

        utils.LLVMDefaultMailNotifier(
            dumpMailsToLog=True,  # TODO: For debug purposes only. Remove this later.
            fromaddr=status_email_fromaddr,
            generators=[
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["aaron@aaronballman.com"],
                    subject="Sphinx build {{ buildername }} Failure",
                    builders=["publish-sphinx-docs"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["mlcompileropt-buildbot@google.com"],
                    subject="ML Compiler Opt Failure: {{ buildername }}",
                    builders=[
                        "ml-opt-dev-x86-64",
                        "ml-opt-rel-x86-64",
                        "ml-opt-devrel-x86-64",
                    ],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["tejohnson@google.com"],
                    subject="ThinLTO WPD Failure: {{ buildername }}",
                    builders=["clang-with-thin-lto-wpd-ubuntu"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["joker.eph@gmail.com"],
                    subject="MLIR Build Failure: {{ buildername }}",
                    builders=["mlir-nvidia", "mlir-nvidia-gcc7"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=[
                        "mlir-bugs-external+buildbot@googlegroups.com"
                    ],
                    subject="MLIR Build Failure: {{ buildername }}",
                    builders=["mlir-nvidia", "ppc64le-mlir-rhel-clang"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["flangbuilder@meinersbur.de"],
                    subject="Build Failure (flang): {{ buildername }}",
                    builders=["flang-x86_64-windows"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["offloadbuilder@meinersbur.de"],
                    subject="Build Failure (offload): {{ buildername }}",
                    builders=[
                        "openmp-offload-cuda-project",
                        "openmp-offload-cuda-runtime",
                    ],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["pollybuilder@meinersbur.de"],
                    subject="Build Failure (polly): {{ buildername }}",
                    builders=[
                        "polly-x86_64-linux",
                        "polly-x86_64-linux-noassert",
                        "polly-x86_64-linux-plugin",
                        "polly-x86_64-linux-shared",
                        "polly-x86_64-linux-shared-plugin",
                        "polly-x86_64-linux-shlib",
                        "polly-x86_64-linux-shlib-plugin",
                        "polly-sphinx-docs",
                    ],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["llvm-bolt@meta.com"],
                    subject="BOLT NFC checks mismatch (X86)",
                    mode=("warnings",),
                    builders=["bolt-x86_64-ubuntu-nfc"],
                ),
                utils.LLVMDefaultBuildStatusGenerator(
                    recipients=["llvm-bolt@arm.com", "llvm-bolt@meta.com"],
                    subject="BOLT NFC checks mismatch (AArch64)",
                    mode=("warnings",),
                    builders=["bolt-aarch64-ubuntu-nfc"],
                ),
            ],
        ),

        reporters.MailNotifier(
            dumpMailsToLog=True,  # TODO: For debug purposes only. Remove this later.
            fromaddr=status_email_fromaddr,
            sendToInterestedUsers=False,
            extraRecipients=["joker.eph@gmail.com"],
            generators=[
                reporters.WorkerMissingGenerator(
                    workers=["mlir-nvidia"],
                    message_formatter=MessageFormatterMissingWorker(),
                )
            ],
        ),
    ])

    return r

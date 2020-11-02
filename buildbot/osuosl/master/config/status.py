from buildbot.process.properties import Interpolate
from buildbot.plugins import reporters

import config
from zorg.buildbot.util.InformativeMailNotifier import LLVMInformativeMailNotifier

# Should be a single e-mail address
status_email = str(config.options.get('Master Options', 'status_email')).split(',')

all = [

    # Note: reporters.GitHubStatusPush requires txrequests package to allow
    # interaction with GitHub REST API.
    reporters.GitHubStatusPush(
        str(config.options.get('GitHub Status', 'token')),
        context = Interpolate("%(prop:buildername)s"),
        verbose = True, # TODO: Turn off the verbosity once this is working reliably.
        builders = [
            "llvm-clang-x86_64-expensive-checks-ubuntu",
            "llvm-clang-x86_64-win-fast",
            "clang-x86_64-debian-fast",
            "llvm-clang-x86_64-expensive-checks-debian",
        ]),

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
        extraHeaders = {"Reply-To": status_email[0]}, # The first from the list.
        lookup = "lab.llvm.org",
        messageFormatter = LLVMInformativeMailNotifier,
        # TODO: For debug purposes only. Remove later.
        dumpMailsToLog = True,
        ),

    # In addition to that the following notifiers are defined for special
    # cases.
    reporters.MailNotifier(
        fromaddr = "llvm.buildmaster@lab.llvm.org",
        sendToInterestedUsers = False,
        extraRecipients = ["leandro.nunes@arm.com"],
        subject = "Build %(builder)s Failure",
        mode = "failing",
        builders = ["clang-aarch64-linux-build-cache", "clang-armv7-linux-build-cache"]),
    reporters.MailNotifier(
        fromaddr = "llvm.buildmaster@lab.llvm.org",
        sendToInterestedUsers = False,
        extraRecipients = ["gribozavr@gmail.com"],
        subject = "Build %(builder)s Failure",
        mode = "failing",
        builders = ["clang-x86_64-debian-fast"]),
    reporters.MailNotifier(
        fromaddr = "llvm.buildmaster@lab.llvm.org",
        sendToInterestedUsers =  False,
        extraRecipients = ["mstester.llvm@gmail.com"],
        subject = "Build %(builder)s Failure",
        mode = "failing",
        builders = ["clang-x64-ninja-win7"]),
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
                    "clang-s390x-linux-lnt"]),
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
        extraRecipients = ["me@dylanmckay.io"],
        subject = "Build %(builder)s Failure",
        mode = "failing",
        builders = ["llvm-avr-linux"]),
    reporters.MailNotifier(
        fromaddr = "llvm.buildmaster@lab.llvm.org",
        sendToInterestedUsers = False,
        extraRecipients = ["gkistanova@gmail.com"],
        subject = "Build %(builder)s Failure",
        mode = "failing",
        builders = ["lld-x86_64-win",
                    "lld-x86_64-freebsd", "lld-x86_64-darwin",
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
        extraRecipients = ["stilis@microsoft.com", "jonas@devlieghere.com",
                           "diprou@microsoft.com", "makudrya@microsoft.com"],
        subject = "Build %(builder)s Failure",
        mode = "failing",
        builders = ["lldb-x64-windows-ninja"]),
    reporters.MailNotifier(
        fromaddr = "llvm.buildmaster@lab.llvm.org",
        sendToInterestedUsers = False,
        extraRecipients = ["stilis@microsoft.com", "namcvica@microsoft.com"],
        subject = "Build %(builder)s Failure",
        mode = "failing",
        builders = ["mlir-windows"]),
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
        extraRecipients = ["jan.kratochvil@redhat.com"],
        subject = "Build %(builder)s Failure",
        mode = "failing",
        builders = ["lldb-x86_64-fedora"]),
    reporters.MailNotifier(
        fromaddr = "llvm.buildmaster@lab.llvm.org",
        sendToInterestedUsers = False,
        extraRecipients = ["kkleine@redhat.com"],
        subject = "Build %(builder)s Failure",
        mode = "failing",
        builders = ["fedora-llvm-x86_64", "x86_64-fedora-clang"]),
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
        extraRecipients = ["omair.javaid@linaro.org"],
        subject = "Build %(builder)s Failure",
        mode = "failing",
        builders = ["lldb-arm-ubuntu","lldb-aarch64-ubuntu"]),
    reporters.MailNotifier(
        fromaddr = "llvm.buildmaster@lab.llvm.org",
        sendToInterestedUsers = False,
        extraRecipients = ["vvereschaka@accesssoftek.com"],
        subject = "Build %(builder)s Failure",
        mode = "failing",
        builders = ["llvm-clang-x86_64-win-fast","lld-x86_64-ubuntu-fast",
                    "llvm-clang-x86_64-expensive-checks-ubuntu",
                    "llvm-clang-win-x-armv7l", "llvm-clang-win-x-aarch64"]),
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
        extraRecipients = ["sivachandra@google.com", "paulatoth@google.com"],
        subject = "Build %(builder)s Failure",
        mode = "failing",
        builders = ["libc-x86_64-debian", "libc-x86_64_debian-dbg",
                    "libc-x86_64-debian-dbg-asan"]),
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
        fromaddr = "llvm.buildmaster@lab.llvm.org",
        sendToInterestedUsers = False,
        extraRecipients = [
            "caroline.concatto@arm.com", "flang_llvm_buildbots@arm.com"],
        subject = "Build %(builder)s Failure",
        mode = "failing",
        builders = [
            "flang-aarch64-ubuntu", "flang-aarch64-ubuntu-clang",
            "flang-aarch64-ubuntu-gcc10"]),
    reporters.MailNotifier(
        fromaddr="llvm.buildmaster@lab.llvm.org",
        sendToInterestedUsers = False,
        extraRecipients=[
            "tejohnson@google.com"],
        subject = "ThinLTO WPD Failure: %(builder)s",
        mode = "failing",
        builders = ["thinlto-x86-64-bot1"]),

]

# Returns a list of Status Targets. The results of each build will be
# pushed to these targets. buildbot.plugins reporters has a variety
# to choose from, including email senders, and IRC bots.
def getReporters():
    if config.options.getboolean('Master Options', 'is_production'):
        return all
    else:
        # Staging buildbot does not report issues.
        return []

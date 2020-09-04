import os
import buildbot
import buildbot.status.html
import buildbot.status.mail
import buildbot.status.words

import config
from zorg.buildbot.util.ConfigEmailLookup import ConfigEmailLookup
from zorg.buildbot.util.InformativeMailNotifier import InformativeMailNotifier
from zorg.buildbot.status.github import GitHubStatus

# Returns a list of Status Targets. The results of each build will be
# pushed to these targets. buildbot/status/*.py has a variety to choose from,
# including web pages, email senders, and IRC bots.

def get_status_targets(standard_builders, standard_categories=None):

    from buildbot.status import html
    from buildbot.status.web import auth, authz
    authz_cfg=authz.Authz(
                      # change any of these to True to enable; see the manual for more
                      # options
                      gracefulShutdown   = False,
                      forceBuild         = True, # use this to test your slave once it is set up
                      forceAllBuilds     = False,
                      pingBuilder        = True,
                      stopBuild          = True,
                      stopAllBuilds      = False,
                      cancelPendingBuild = True,
                      )

    default_email = config.options.get('Master Options', 'default_email')
    github_token = config.options.get('GitHub Status', 'token')

    return [
        buildbot.status.html.WebStatus(
            order_console_by_time=True,
            http_port = 8011, authz=authz_cfg),

        GitHubStatus(
            token=github_token,
            repoOwner='llvm',
            repoName='llvm-project',
            builders_to_report = [
                "llvm-clang-x86_64-expensive-checks-ubuntu",
                "llvm-clang-x86_64-win-fast",
                "clang-x86_64-debian-fast",
                "llvm-clang-x86_64-expensive-checks-debian",
            ]),

        # All the standard builders send e-mail and IRC notifications.
        buildbot.status.mail.MailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            extraRecipients = [default_email],
            lookup = ConfigEmailLookup(os.path.join(os.path.dirname(__file__),
                                                    "llvmauthors.cfg"),
                                       default_email),
            mode = "problem",
            builders = standard_builders),
        buildbot.status.words.IRC(
            host = "irc.oftc.net", nick = "llvmbb-llvm-build",
            channels = ["#llvm-build"],
            allowForce = True,
            categories = standard_categories,
            notify_events = ['successToFailure', 'failureToSuccess']),

        # In addition to that the following notifiers are defined for special
        # cases.
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers= False,
            extraRecipients = ["leandro.nunes@arm.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["clang-aarch64-linux-build-cache", "clang-armv7-linux-build-cache"],
            addLogs=False,
            num_lines = 15),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers= False,
            extraRecipients = ["gribozavr@gmail.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["clang-x86_64-debian-fast"],
            addLogs=False,
            num_lines = 15),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers= False,
            extraRecipients = ["mstester.llvm@gmail.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["clang-x64-ninja-win7"],
            addLogs=False,
            num_lines = 15),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers= False,
            extraRecipients = ["llvm.buildmaster@quicinc.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["clang-hexagon-elf"],
            addLogs=False,
            num_lines = 15),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers= False,
            extraRecipients = ["Ulrich.Weigand@de.ibm.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["clang-s390x-linux", "clang-s390x-linux-multistage",
                        "clang-s390x-linux-lnt"],
            addLogs=False,
            num_lines = 15),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers= False,
            extraRecipients = ["sunil_srivastava@playstation.sony.com",
                               "warren_ristow@playstation.sony.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["clang-x86_64-linux-abi-test"],
            addLogs=False,
            num_lines = 15),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["me@dylanmckay.io"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["llvm-avr-linux"],
            addLogs=False,
            num_lines = 15),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers= False,
            extraRecipients = ["gkistanova@gmail.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["lld-x86_64-win",
                        "lld-x86_64-freebsd", "lld-x86_64-darwin",
                        "clang-x86_64-linux-abi-test",
                        "clang-with-lto-ubuntu", "clang-with-thin-lto-ubuntu",
                        "llvm-clang-x86_64-expensive-checks-win",
                        "llvm-clang-x86_64-expensive-checks-ubuntu"],
            addLogs=False),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers= False,
            extraRecipients = ["efriedma@codeaurora.org", "huihuiz@codeaurora.org"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["polly-arm-linux",
                        "aosp-O3-polly-before-vectorizer-unprofitable"],
            addLogs=False,
            num_lines = 15),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers= True,
            extraRecipients = ["mgrang@codeaurora.org"],
            subject="Build %(builder)s Failure",
            mode = "problem",
            builders = ["reverse-iteration"],
            addLogs=False,
            num_lines = 15),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers= False,
            extraRecipients = ["tra+buildbot@google.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["clang-cuda-k80", "clang-cuda-p4", "clang-cuda-t4"],
            addLogs=False,
            num_lines = 15),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["asb@lowrisc.org"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["llvm-riscv-linux"],
            addLogs=False,
            num_lines = 15),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["stilis@microsoft.com", "jonas@devlieghere.com", "diprou@microsoft.com", "makudrya@microsoft.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["lldb-x64-windows-ninja"],
            addLogs=False,
            num_lines = 15),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["stilis@microsoft.com", "namcvica@microsoft.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["mlir-windows"],
            addLogs=False,
            num_lines = 15),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers= False,
            extraRecipients = ["phosek@google.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["fuchsia-x86_64-linux"],
            addLogs=False),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = True,
            extraRecipients = ["jan.kratochvil@redhat.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["lldb-x86_64-fedora"],
            addLogs=False),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = True,
            extraRecipients = ["labath@google.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["lldb-x86_64-debian"],
            addLogs=False),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = True,
            extraRecipients = ["omair.javaid@linaro.org"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["lldb-arm-ubuntu","lldb-aarch64-ubuntu"],
            addLogs=False),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = True,
            extraRecipients = ["vvereschaka@accesssoftek.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["llvm-clang-x86_64-win-fast","lld-x86_64-ubuntu-fast",
                        "llvm-clang-x86_64-expensive-checks-ubuntu",
                        "llvm-clang-win-x-armv7l", "llvm-clang-win-x-aarch64"],
            addLogs=False),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = ["llvm.buildbot@emea.nec.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["clang-ve-ninja"],
            addLogs=False),
         InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = True,
            extraRecipients = ["sivachandra@google.com", "paulatoth@google.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["libc-x86_64-debian", "libc-x86_64_debian-dbg",
                        "libc-x86_64-debian-dbg-asan"],
            addLogs=False),
         InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = True,
            extraRecipients = ["aaron@aaronballman.com"],
            subject="Sphinx build %(builder)s Failure",
            mode = "failing",
            builders = ["publish-sphinx-docs"],
            addLogs=False),
        InformativeMailNotifier(fromaddr="llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers=True,
            extraRecipients=[
                "mlcompileropt-buildbot@google.com"],
            subject="ML Compiler Opt Failure: %(builder)s",
            mode="failing",
            builders=[
                "ml-opt-dev-x86-64", "ml-opt-rel-x86-64", "ml-opt-devrel-x86-64"],
            addLogs=False),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers = False,
            extraRecipients = [
                "caroline.concatto@arm.com", "flang_llvm_buildbots@arm.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = [
                "flang-aarch64-ubuntu", "flang-aarch64-ubuntu-clang", 
                "flang-aarch64-ubuntu-gcc10"],
            addLogs=False,
            num_lines = 15),
        ]

import os
import buildbot
import buildbot.status.html
import buildbot.status.mail
import buildbot.status.words

import config
from zorg.buildbot.util.ConfigEmailLookup import ConfigEmailLookup
from zorg.buildbot.util.InformativeMailNotifier import InformativeMailNotifier

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

    return [
        buildbot.status.html.WebStatus(
            http_port = 8011, authz=authz_cfg),

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
            host = "irc.oftc.net", nick = "llvmbb",
            channels = ["#llvm"],
            allowForce = True,
            categories = standard_categories,
            notify_events = ['successToFailure', 'failureToSuccess']),
        # Use different nick's in the different channels to support ignoring
        # one bot or the other.
        # (Note: /ignore applies to all channels on the network)
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
            extraRecipients = ["tobias@grosser.es"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["polly-amd64-linux"],
            addLogs=False,
            num_lines = 15),
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
            builders = ["clang-atom-d525-fedora-rel", "clang-x64-ninja-win7"],
            addLogs=False,
            num_lines = 15),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers= False,
            extraRecipients = ["llvm.buildmaster@quicinc.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["llvm-hexagon-elf", "clang-hexagon-elf"],
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
            builders = ["clang-lld-x86_64-2stage", "lld-x86_64-win7",
                        "lld-x86_64-freebsd", "lld-x86_64-darwin13",
                        "clang-x86_64-linux-abi-test",
                        "llvm-clang-lld-x86_64-scei-ps4-ubuntu-fast",
                        "clang-with-lto-ubuntu", "clang-with-thin-lto-ubuntu",
                        "llvm-clang-lld-x86_64-scei-ps4-windows10pro-fast",
                        "llvm-clang-x86_64-expensive-checks-win"],
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
            builders = ["clang-cuda-build"],
            addLogs=False,
            num_lines = 15),
        InformativeMailNotifier(
            fromaddr = "llvm.buildmaster@lab.llvm.org",
            sendToInterestedUsers= False,
            extraRecipients = ["n54@gmx.com", "mgorny@NetBSD.org"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["netbsd-amd64"],
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
            extraRecipients = ["stilis@microsoft.com"],
            subject="Build %(builder)s Failure",
            mode = "failing",
            builders = ["lldb-x64-windows-ninja"],
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
            builders = ["llvm-clang-x86_64-win-fast","lld-x86_64-ubuntu-fast"],
            addLogs=False),
        ]

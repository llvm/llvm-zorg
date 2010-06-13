import os
import buildbot
import buildbot.status.html
import buildbot.status.mail
import buildbot.status.words

import config
from zorg.buildbot.util.ConfigEmailLookup import ConfigEmailLookup

from buildbot.status.web import auth, authz
authz_cfg=authz.Authz(
    gracefulShutdown = False,
    forceBuild = False,
    forceAllBuilds = False,
    pingBuilder = False,
    stopBuild = False,
    stopAllBuilds = False,
    cancelPendingBuild = False,
)

def get_status_targets(standard_builders):
    default_email = config.options.get('Master Options', 'default_email')
    return [
        buildbot.status.html.WebStatus(
            http_port = 8010, authz=authz_cfg),
        buildbot.status.mail.MailNotifier(
            fromaddr = "klee-buildmaster@klee.minormatter.com",
            extraRecipients = [default_email],
            lookup = ConfigEmailLookup(os.path.join(os.path.dirname(__file__),
                                                    "llvmauthors.cfg"),
                                       default_email),
            mode = "problem",
            builders = standard_builders),
        buildbot.status.words.IRC(
            host = "irc.oftc.net", nick = "kleebb", channels = ["#klee"],
            allowForce = True,
            notify_events = ['successToFailure', 'failureToSuccess']),
        ]

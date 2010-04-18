import os
import buildbot
import buildbot.status.html
import buildbot.status.mail
import buildbot.status.words

import config
from zorg.buildbot.util.ConfigEmailLookup import ConfigEmailLookup

def get_status_targets(standard_builders):
    default_email = config.options.get('Master Options', 'default_email')
    return [
        buildbot.status.html.WebStatus(
            http_port = 8011, allowForce = True),
        buildbot.status.mail.MailNotifier(
            fromaddr = "buildbot@google1.osuosl.org",
            extraRecipients = [default_email],
            lookup = ConfigEmailLookup(os.path.join(os.path.dirname(__file__),
                                                    "llvmauthors.cfg"),
                                       default_email),
            mode = "problem",
            builders = standard_builders),
        buildbot.status.words.IRC(
            host = "irc.oftc.net", nick = "llvmbb", channels = ["#llvm"],
            allowForce = True,
            notify_events = ['successToFailure', 'failureToSuccess']),
        ]

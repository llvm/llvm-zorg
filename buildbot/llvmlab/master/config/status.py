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
            http_port = 8013, allowForce = True),
        buildbot.status.mail.MailNotifier(
            fromaddr = 'david_dean@apple.com',
            extraRecipients = ['daniel_dunbar@apple.com','david_dean@apple.com'],
            sendToInterestedUsers=False,
            mode = 'problem',
            relayhost="mail-in2.apple.com",),
        ]

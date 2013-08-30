import buildbot
import buildbot.status.html
import buildbot.status.mail
import buildbot.status.words
import config
import os

from zorg.buildbot.util.phasedbuilderutils import set_config_option
from zorg.buildbot.util.ConfigEmailLookup import ConfigEmailLookup
from zorg.buildbot.util.InformativeMailNotifier import InformativeMailNotifier 


def get_status_targets(standard_builders):
    # Get from/to email addresses.
    from_email = set_config_option('Master Options', 'from_email')
    default_email = set_config_option('Master Options', 'default_email')

    # Check whether we are in testing mode, if so, just add minimal and verbose
    # status clients.
    is_production = set_config_option('Master Options', 'is_production', False)
    if not is_production:
        return [
            buildbot.status.html.WebStatus(
                http_port = 8013, allowForce = True),

            InformativeMailNotifier(fromaddr = from_email,
                                    extraRecipients = ['david_dean@apple.com',
                                                       'mgottesman@apple.com'],
                                    sendToInterestedUsers = False,
                                    mode = 'change',
                                    addLogs = False,
                                    num_lines = 15),
            ]

    # Get the path to the authors file we use for email lookup.
    llvm_authors_path = set_config_option('Master Options', 'llvm_authors_path')

    # Construct a lookup object to be used for public builders.
    public_lookup = ConfigEmailLookup(
        llvm_authors_path, default_address = 'llvm-testresults@cs.uiuc.edu')

    return [
        buildbot.status.html.WebStatus(
            http_port = 8013, allowForce = True),
        buildbot.status.words.IRC('irc.oftc.net', 'phased-bb-llvmlab',
                  port=6668,
                  channels=['llvm'],
                  allowForce=False,
                  password='smooshy',
                  notify_events=['successToFailure', 'failureToSuccess'],
                  categories=['status']),

        # Experimental failing build notifier.
        #
        # These emails only go to the catch-all list.
        InformativeMailNotifier(
            fromaddr = from_email,
            extraRecipients = ['llvm-testresults@cs.uiuc.edu'],
            sendToInterestedUsers = False,
            mode = 'failing',
            categories = ['experimental'],
            addLogs = False,
            num_lines = 15),

        # Regular problem build notifier.
        #
        # These emails go to the interested public_users, and the catch-all
        # list.
        InformativeMailNotifier(
            fromaddr = from_email,
            lookup = public_lookup,
            extraRecipients = ['llvm-testresults@cs.uiuc.edu'],
            sendToInterestedUsers = True,
            mode = 'problem',
            categories = ['build-public', 'test-public', 'status'],
            addLogs = False,
            num_lines = 15),

        # Regular failing build notifier.
        #
        # These emails only go to the catch-all list.
        #
        # FIXME: Eventually, these should also go to the current build czars.
        # TODO: change subject to differentiate these from the problem emails
        InformativeMailNotifier(
            fromaddr = from_email,
            sendToInterestedUsers = False,
            extraRecipients = ['llvm-testresults@cs.uiuc.edu'],
            mode = 'failing',
            categories = ['build-public', 'test-public'],
            addLogs = False,
            num_lines = 15),

        # Phase status change notifier.
        #
        # These emails only go to the catch-all list.
        buildbot.status.mail.MailNotifier(
            fromaddr = from_email,
            sendToInterestedUsers = False,
            extraRecipients = ['llvm-testresults@cs.uiuc.edu'],
            mode = 'change',
            categories = ['status']),
        
        # Send email to Howard Hinnant if the libcxx builder fails.
        InformativeMailNotifier(
            fromaddr = from_email,
            sendToInterestedUsers = False,
            extraRecipients = ['hhinnant@apple.com'],
            subject = "Build %(builder)s Failure",
            mode = "failing",
            builders = ['libcxx_clang-x86_64-darwin11-RA'],
            addLogs = False,
            num_lines = 15),
        ]

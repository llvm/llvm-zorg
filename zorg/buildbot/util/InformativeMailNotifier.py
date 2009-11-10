from buildbot import util, interfaces
from zope.interface import implements
from buildbot.status import builder, mail

class InformativeMailNotifier(mail.MailNotifier):
    """MailNotifier subclass which provides additional information about the
    build failure inside the email."""

    implements(interfaces.IEmailSender)
    compare_attrs = (mail.MailNotifier.compare_attrs +
                     ["num_lines", "only_failure_logs"])

    # Remove customMesg from the compare_attrs, that would lead to
    # recursion, and is checked by the class test.
    compare_attrs.remove("customMesg")

    # FIXME: The customMessage interface is fairly inefficient, switch to
    # something new when it becomes available.

    def __init__(self, 
                 num_lines = 10, only_failure_logs = True,
                 *attrs, **kwargs):
        mail.MailNotifier.__init__(self, customMesg=self.customMessage, 
                                   *attrs, **kwargs)
        self.num_lines = num_lines
        self.only_failure_logs = only_failure_logs

    def customMessage(self, attrs):
        # FIXME: It would be nice to find a way to communicate with
        # the lookup mechanism so that we could note any committers
        # who we weren't able to send email to.

        # Get the standard message.
        data = mail.message(attrs)[0]

        data += '\n' + '='*80 + '\n\n'

        # Append addition information on the changes.
        data += 'CHANGES:\n'
        data += '\n\n'.join([c.asText() for c in attrs['changes']])
        data += '\n\n'
    
        # Append log files.
        if self.num_lines:
            data += 'LOGS:\n'
            for name, url, lines, logstatus in attrs['logs']:
                if (self.only_failure_logs and logstatus != builder.FAILURE):
                    continue

                data += "Last %d lines of '%s':\n" % (self.num_lines, name)
                data += '\t' + '\n\t'.join(lines[-self.num_lines:])
                data += '\n\n'

        return (data, 'plain')

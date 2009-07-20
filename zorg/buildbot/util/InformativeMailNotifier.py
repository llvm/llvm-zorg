from buildbot.status import builder, mail

class InformativeMailNotifier(mail.MailNotifier):
    """MailNotifier subclass which provides additional information about the
    build failure inside the email."""

    # FIXME: The customMessage interface is fairly inefficient, switch to
    # something new when it becomes available.

    def __init__(self, 
                 numLines = 10, onlyFailureLogs = True,
                 *attrs, **kwargs):
        mail.MailNotifier.__init__(self, customMesg=self.customMessage, 
                                   *attrs, **kwargs)
        self.numLines = numLines
        self.onlyFailureLogs = onlyFailureLogs

    def customMessage(self, attrs):
        # Get the standard message.
        data = mail.message(attrs)[0]

        data += '\n' + '='*80 + '\n\n'

        # Append addition information on the changes.
        data += 'CHANGES:\n'
        data += '\n\n'.join([c.asText() for c in attrs['changes']])
        data += '\n\n'
    
        # Append log files.
        if self.numLines:
            data += 'LOGS:\n'
            for name, url, lines, logstatus in attrs['logs']:
                if (self.onlyFailureLogs and logstatus != builder.FAILURE):
                    continue

                data += "Last %d lines of '%s':\n" % (self.numLines, name)
                data += '\t' + '\n\t'.join(lines[-self.numLines:])
                data += '\n\n'

        return (data, 'plain')

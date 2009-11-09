from buildbot.steps.transfer import FileDownload

class BatchFileDownload(FileDownload):
    # FIXME: It would be nice to form a BatchedShellCommand step out of this.
    def __init__(self, **kwargs):
        if 'command' in kwargs:
            if 'mastersrc' in kwargs:
                raise ValueError,"Unexpected 'mastersrc' argument."
            if 'slavedest' in kwargs:
                raise ValueError,"Unexpected 'slavedest' argument."

            # This is the initial construction, create a temporary
            # batch file to run the command.
            import os
            import tempfile

            command = kwargs.pop('command')
            tf = tempfile.NamedTemporaryFile(delete=False)
            print >>tf, '@echo on'
            print >>tf, ' '.join('"%s"' % a for a in command)
            tf.close()

            remotename = kwargs.get('name', 'batched-command')
            kwargs['mastersrc'] = os.path.abspath(tf.name)
            kwargs['slavedest'] = '%s.bat' % remotename

        FileDownload.__init__(self, **kwargs)

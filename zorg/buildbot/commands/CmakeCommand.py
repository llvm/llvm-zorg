from buildbot.process.properties import WithProperties
from buildbot.steps.shell import WarningCountingShellCommand

from zorg.buildbot.util.helpers import stripQuotationMarks

class CmakeCommand(WarningCountingShellCommand):

    @staticmethod
    def applyRequiredOptions(options, required):
        # required is a list of tuples in form of (<opt name>, <opt value>),
        # where all the values are properly formatted to terminate
        # control symbols.
        # TODO: Support cmake params with types, like -DCMAKE_CXX_FLAGS:STRING='-stdlib=libc++'.
        options = [
            a
            for a in options
            if not any(stripQuotationMarks(a).startswith(r) for r,_ in required)
        ]
        + [k + v for k,v in required]

    @staticmethod
    def applyDefaultOptions(options, defaults):
        # We assume the one options item for, let's say, -G, i.e. in form of
        # '-GUnix Makefiles' or -G "Unix Makefiles".
        # defaults is a list of tuples in form of (<opt name>, <opt value>),
        # where all the values are properly formatted to terminate
        # control symbols.
        # TODO: Support cmake params with types, like -DCMAKE_CXX_FLAGS:STRING='-stdlib=libc++'.
        for k,v in defaults:
            if not any(stripQuotationMarks(a).startswith(k) for a in options):
                options.append(k + v)

    @staticmethod
    def appendFlags(options, append):
        # append is a list of tuples in form of (<opt name>, [<flag values>]).
        # In this routine we are after cmake arguments with multiple values,
        # like compiler or linker flags. So we want
        # <cmake_arg>=["]<list of flags separated by space>["] and
        # do not care of other options like, let's say, -G.
        # TODO: Support cmake params with types, like -DCMAKE_CXX_FLAGS:STRING='-stdlib=libc++'.
        for k,v in append:

            o = None
            for i,a in enumerate(options):
                # Strip surraunding quotation marks if any.
                a = stripQuotationMarks(a)
                if a.startswith(k):
                    append_to = a.split("=", 1)
                    flags = stripQuotationMarks(append_to[1]).split() + v
                    seen = set()
                    seen_add = seen.add # To avoid resolving in the loop.
                    flags = [
                        f for f in flags
                        if not (f in seen or seen_add(f))
                        ]
                    flags = ' '.join(flags)
                    if ' ' in flags:
                        flags = "\"%s\"" % flags
                    append_to[1] = flags
                    o = options[i] = '='.join(append_to)

            if o is None:
                # We do not have the option to merge with,
                # so, let's just set it.
                flags = ' '.join(v)
                if ' ' in flags:
                    flags = "\"%s\"" % flags
                append_this = k.split("=", 1)
                append_this[1] = flags
                options.append('='.join(append_this))

    def __init__(self, prefixCommand=None, options=None, path=None, **kwargs):
        self.prefixCommand = prefixCommand
        self.path = [path]

        if options is None:
            self.options = list()
        else:
            self.options = list(options)

        command = []
        if prefixCommand:
            command += prefixCommand

        command += ["cmake"]

        # Set some default options.
        CmakeCommand.applyDefaultOptions(self.options, [
            ('-DCMAKE_BUILD_TYPE=',        'Release'),
            ('-DLLVM_ENABLE_WERROR=',      'ON'),
            ('-DLLVM_OPTIMIZED_TABLEGEN=', 'ON'),
            ])

        if self.options:
            command += self.options

        if self.path:
            command += self.path

        # Note: We will remove all the empty items from the command at start.
        kwargs['command'] = command

        # And upcall to let the base class do its work
        WarningCountingShellCommand.__init__(self, **kwargs)

        self.addFactoryArguments(prefixCommand=prefixCommand,
                                 options=self.options,
                                 path=path)

    def start(self):
        # Don't forget to remove all the empty items from the command,
        # which we could get because of WithProperties rendered as empty strings.
        self.command = filter(bool, self.command)
        # Then upcall.
        WarningCountingShellCommand.start(self)

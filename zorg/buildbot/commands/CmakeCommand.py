from buildbot.steps.shell import WarningCountingShellCommand

from zorg.buildbot.util.helpers import stripQuotationMarks

class CmakeCommand(WarningCountingShellCommand):

    @staticmethod
    def sanitize_kwargs(kwargs):
        # kwargs we could get and must not pass through
        # to the buildstep.RemoteShellCommand constructor.
        # Note: This is a workaround of the buildbot design issue,
        # thus should be removed once the original issue gets fixed.
        consume_kwargs = [
                             "jobs",
                             "loadaverage",
                         ]

        sanitized_kwargs = kwargs.copy()
        for k in consume_kwargs:
            if k in sanitized_kwargs.keys():
                del sanitized_kwargs[k]

        return sanitized_kwargs


    @staticmethod
    def applyRequiredOptions(options, required):
        # required is a list of tuples in form of (<opt name>, <opt value>),
        # where all the values are properly formatted to terminate
        # control symbols.
        # TODO: Support cmake params with types, like -DCMAKE_CXX_FLAGS:STRING='-stdlib=libc++'.
        for k,v in required:

            o = None
            for i,a in enumerate(options):
                # We cannot process some options because of WithProperties and such,
                # but let's at least work around them gracefully.
                try:
                    # Strip surraunding quotation marks if any.
                    a = stripQuotationMarks(a)
                    if a.startswith(k):
                        # Replace the existing one by the one from required.
                        o = options[i] = k + v
                        break
                except Exception:
                    pass 

            if o is None:
                # We do not have the option to replace,
                # so, let's just add a new one.
                options.append(k + v)


    @staticmethod
    def applyDefaultOptions(options, defaults):
        # We assume the one options item for, let's say, -G, i.e. in form of
        # '-GUnix Makefiles' or -G "Unix Makefiles".
        # defaults is a list of tuples in form of (<opt name>, <opt value>),
        # where all the values are properly formatted to terminate
        # control symbols.
        # TODO: Support cmake params with types, like -DCMAKE_CXX_FLAGS:STRING='-stdlib=libc++'.
        for k,v in defaults:

            o = None
            for i,a in enumerate(options):
                # We cannot process some options because of WithProperties and such,
                # but let's at least work around them gracefully.
                try:
                    if stripQuotationMarks(a).startswith(k):
                        o = options[i]
                        break
                except Exception:
                    pass

            if o is None:
                # We do not have the option already set,
                # so, apply the default one.
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
                # We cannot process some options because of WithProperties and such,
                # but let's at least work around them gracefully.
                try:
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
                        append_to[1] = flags
                        o = options[i] = '='.join(append_to)
                        break
                except Exception:
                    pass

            if o is None:
                # We do not have the option to merge with,
                # so, let's just set it.
                flags = ' '.join(v)
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

        # Remove here all the kwargs any of our LLVM buildbot command could consume.
        # Note: We will remove all the empty items from the command at start, as we
        # still didn't get yet WithProperties rendered.
        sanitized_kwargs = self.sanitize_kwargs(kwargs)

        sanitized_kwargs["command"] = command

        # And upcall to let the base class do its work
        WarningCountingShellCommand.__init__(self, **sanitized_kwargs)

        self.addFactoryArguments(prefixCommand=prefixCommand,
                                 options=self.options,
                                 path=path)


    def start(self):
        # Don't forget to remove all the empty items from the command,
        # which we could get because of WithProperties rendered as empty strings.
        self.command = filter(bool, self.command)
        # Then upcall.
        WarningCountingShellCommand.start(self)

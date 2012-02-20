"""
Utilities for working with Valgrind.
"""

from lnt.testing.util.commands import warning

# See:
#   http://valgrind.org/docs/manual/cl-format.html#cl-format.overview
# for reference on the calltree data format specification.

class CalltreeParseError(Exception):
    pass

class CalltreeData(object):
    @staticmethod
    def frompath(path):
        with open(path) as file:
            return CalltreeData.fromfile(file, path)

    @staticmethod
    def fromfile(file, path):
        # I love valgrind, but this is really a horribly lame data format. Oh
        # well.

        it = iter(file)

        # Read the header.
        description_lines = []
        command = None
        events = None
        positions = initial_positions = ['line']
        for ln in it:
            # If there is no colon in the line, we have reached the end of the
            # header.
            if ':' not in ln:
                break

            key,value = ln.split(':', 1)
            if key == 'desc':
                description_lines.append(value.strip())
            elif key == 'cmd':
                if command is not None:
                    warning("unexpected multiple 'cmd' keys in %r" % (path,))
                command = value.strip()
            elif key == 'events':
                if events is not None:
                    warning("unexpected multiple 'events' keys in %r" % (path,))
                events = value.split()
            elif key == 'positions':
                if positions is not initial_positions:
                    warning("unexpected multiple 'positions' keys in %r" % (
                            path,))
                positions = value.split()
            else:
                warning("found unknown key %r in %r" % (key, path))

        # Validate that required fields were present.
        if events is None:
            raise CalltreeParseError("missing required 'events' key in header")

        # Construct an instance.
        data = CalltreeData(events, "\n".join(description_lines), command)

        # Read the file data.
        num_samples = len(positions) + len(events)
        current_file = None
        current_function = None
        summary_samples = None
        for ln in it:
            # Check if this is the closing summary line.
            if ln.startswith('summary'):
                key,value = ln.split(':', 1)
                summary_samples = map(int, value.split())
                break

            # Check if this is an update to the current file or function.
            if ln.startswith('fl='):
                current_file = ln[3:-1]
            elif ln.startswith('fn='):
                current_function = ln[3:-1]
            else:
                # Otherwise, this is a data record.
                samples = map(int, ln.split())
                if len(samples) != num_samples:
                    raise CalltreeParseError(
                        "invalid record line, unexpected sample count")
                data.records.append((current_file,
                                     current_function,
                                     samples))

        # Validate that there are no more remaining records.
        for ln in it:
            raise CalltreeParseError("unexpected line in footer: %r" % (ln,))

        # Validate that the summary line was present.
        if summary_samples is None:
            raise CalltreeParseError("missing required 'summary' key in footer")

        data.summary = summary_samples

        return data

    def __init__(self, events, description=None, command=None):
        self.events = events
        self.description = description
        self.command = command
        self.records = []
        self.summary = None

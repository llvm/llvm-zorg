"""
Summary information for the dashboard.

Connects the active CI configuration with the status information to track the
current high-level status.
"""

import sys

class Summary(object):
    def __init__(self, config, status):
        self.config = config
        self.status = status

    def get_current_status(self):
        """
        get_current_status() -> ...

        Compute information on the current status.
        """

        # For each configured builder, compute the:
        #   a. current build(s),
        #   b. last passing build,
        #   c. last failing build,
        #   d. last completed build
        info = {}
        for builder in self.config.builders:
            builds = self.status.builders.get(builder.name)

            current = []
            passing = failing = completed = None
            if builds is None:
                # FIXME: Logging!
                print >>sys.stderr, "warning: no status for '%s'" % (
                    builder.name)
                info[builder.name] = None
            else:
                for build in builds[::-1]:
                    # Check if this is an active build.
                    if build.start_time is not None and build.end_time is None:
                        current.append(build)
                        continue

                    # Otherwise, check the status.
                    if completed is None:
                        completed = build

                    # Track the (a) most recent passing build and (b) oldest
                    # failure which happened after a passing build.
                    if passing is None:
                        if build.result == 0:
                            passing = build
                        else:
                            failing = build

            info[builder.name] = {
                'current' : current,
                'passing' : passing,
                'failing' : failing,
                'completed' : completed }

        return info

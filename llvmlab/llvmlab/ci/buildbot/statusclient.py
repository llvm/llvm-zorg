import time
import traceback
import urllib2
import StringIO
from flask import json

###

# Custom Exception Classes
#
# We generally only care about either proper 404 results or "other" failures.
class ResultMissing(Exception):
    pass
class UnknownFailure(Exception):
    pass

###

class BuilderInfo(object):
    """
    BuilderInfo object for tracking per-builder status information being
    monitored.
    """

    @staticmethod
    def fromdata(data):
        version = data['version']
        if version != 0:
            raise ValueError, "Unknown version"

        return BuilderInfo(data['name'], data['last_build_number'],
                           set(data['active_builds']), data['last_poll'])

    def todata(self):
        return { 'version' : 0,
                 'name' : self.name,
                 'last_build_number' : self.last_build_number,
                 'active_builds' : list(self.active_builds),
                 'last_poll' : self.last_poll }

    def __init__(self, name, last_build_number = None,
                 active_builds = [],  last_poll = -1):
        self.name = name
        self.last_build_number = last_build_number
        self.active_builds = set(active_builds)
        self.last_poll = last_poll

class StatusClient(object):
    """
    StatusClient object for watching a buildbot master and dispatching signals
    on changes.

    Currently, the client primarily is worried about tracking builders.
    """

    @staticmethod
    def fromdata(data):
        version = data['version']
        if version != 0:
            raise ValueError, "Unknown version"

        sc = StatusClient(data['master_url'], data['builders_poll_rate'],
                          data['builder_poll_rate'])
        builders = [BuilderInfo.fromdata(b)
                    for b in data['builders']]
        sc.builders = dict((b.name, b) for b in builders)
        sc.last_builders_poll = data['last_builders_poll']
        return sc

    def todata(self):
        return { 'version' : 0,
                 'master_url' : self.master_url,
                 'builder_poll_rate' : self.builder_poll_rate,
                 'builders_poll_rate' : self.builders_poll_rate,
                 'builders' : [b.todata()
                               for b in self.builders.values()],
                 'last_builders_poll' : self.last_builders_poll }

    def __init__(self, master_url,
                 builders_poll_rate = 60.0,
                 builder_poll_rate = 5.0):
        # Normalize the master URL.
        self.master_url = master_url
        if self.master_url.endswith('/'):
            self.master_url += '/'

        # Initialize the data we track.
        self.builders = {}

        # Set poll rates (how frequently we are willing to recontact the
        # master).
        self.builders_poll_rate = float(builders_poll_rate)
        self.builder_poll_rate = float(builder_poll_rate)

        # Set last poll time so we will repoll on startup.
        self.last_builders_poll = -1

        # Option logger object.
        self.logger = None

    def get_json_result(self, query_items, arguments=None):
        path = '/json/' + '/'.join(urllib2.quote(item)
                                   for item in query_items)
        if arguments is not None:
            path += '?' + urllib2.urlencode(arguments)

        url = self.master_url + path
        try:
            request = urllib2.urlopen(url)
        except urllib2.HTTPError, err:
            # Turn 404 into a result missing error.
            if err.code == 404:
                raise ResultMissing

            # Log this failure.
            os = StringIO.StringIO()
            print >>os, "*** ERROR: failure in 'get_json_result(%r, %r)' ***" %(
                query_items, arguments)
            print >>os, "URL: %r" % url
            print >>os, "\n-- Traceback --"
            traceback.print_exc(file = os)
            if self.logger:
                self.logger.warning(os.getvalue())
            else:
                print >>sys.stderr, os.getvalue()
            raise UnknownFailure
        data = request.read()
        request.close()

        obj = json.loads(data)
        return obj

    def pull_events(self):
        current_time = time.time()

        # Update the builders set, but not all the time (there is no short query
        # for this in the buildbot JSON interface).
        if current_time - self.last_builders_poll >= self.builders_poll_rate:
            for event in self.pull_builders():
                yield event

        # Update the current builds for each known builder.
        for builder in self.builders.values():
            if current_time - builder.last_poll >= self.builder_poll_rate:
                for event in self.pull_builder(builder):
                    yield event

    def pull_builders(self):
        # Pull the builder names.
        #
        # FIXME: BuildBot should provide a more efficient query for this.
        #yield ('poll_builders',)
        try:
            res = self.get_json_result(('builders',))
        except ResultMissing:
            # This should never happen, but don't crash if it does.
            return
        except UnknownFailure:
            # Presumably a transient network issue, just wait a while and retry.
            #
            # FIXME: Evaluate decay algorithm.
            self.last_builders_poll = time.time() + 60.
            return

        builder_names = set(res.keys())
        current_builders = set(self.builders)

        for name in builder_names - current_builders:
            yield ('added_builder', name)
            self.builders[name] = BuilderInfo(name)
        for name in current_builders - builder_names:
            yield ('removed_builder', name)
            self.builders.pop(name)

        self.last_builders_poll = time.time()

    def pull_builder(self, builder):
        # Get the latest build number.
        try:
            res = self.get_json_result(('builders', builder.name, 'builds',
                                        '-1'))
            number = res['number']
        except ResultMissing:
            # If the server returned 404, then either we gave a bogus builder
            # name (which is bad), or there are no builds yet.
            #
            # We assume that bogus builder's will be figured out elsewhere, so
            # just assume there are no builds.
            builder.last_poll = time.time()
            number = None
        except UnknownFailure:
            # Presumably a transient network issue, just wait a while and retry.
            #
            # FIXME: Evaluate decay algorithm.
            builder.last_poll = time.time() + 60.
            return

        # Check if we don't have any builds.
        if number is None:
            # Check if we need to start or reset the state.
            if builder.last_build_number is not None:
                yield ('reset_builder', builder.name)
        else:
            # Check if we need to start or reset the state.
            if (builder.last_build_number is None or
                number < builder.last_build_number):
                # Send a reset event.
                yield ('reset_builder', builder.name)
                builder.last_build_number = number - 1

            # Add any potentially active builds.
            for id in range(builder.last_build_number + 1, number + 1):
                yield ('add_build', builder.name, id)
                builder.active_builds.add(id)

        # Update the latest build number.
        builder.last_build_number = number

        # Analyze the active builds.
        builds = list(builder.active_builds)
        builds.sort()
        for id in builds:
            # Get the result for this build.
            try:
                res = self.get_json_result(('builders', builder.name, 'builds',
                                            str(id)))
            except ResultMissing:
                # This probably shouldn't ever happen, but if it does then trust
                # the response.
                res = {}
            except UnknownFailure:
                # Presumably a transient network issue, just wait a while and
                # retry.
                #
                # FIXME: Evaluate decay algorithm.
                builder.last_poll = time.time() + 60.
                return

            times = res.get('times')

            # In rare circumstances, we could have accessed an invalid build,
            # check for this.
            if times is None or len(times) != 2:
                yield ('invalid_build', builder.name, id)
                builder.active_builds.remove(id)
                continue

            # Otherwise, just check to see if the build is done.
            if times[1] is not None:
                yield ('completed_build', builder.name, id)
                builder.active_builds.remove(id)

        builder.last_poll = time.time()

###

def main():
    import os
    import sys
    from optparse import OptionParser, OptionGroup
    parser = OptionParser("""\
%%prog [options] <path> <master url>

A simple tool for testing the BuildBot StatusClient.
""")
    opts, args = parser.parse_args()
    if len(args) != 2:
        parser.error("invalid arguments")

    path,master_url = args

    # Load the static client object if it exists.
    sc = None
    if os.path.exists(path):
        file = open(path)
        object = json.load(file)
        file.close()

        sc = StatusClient.fromdata(object)

        # Check that this instance matches what the user requested.
        if (sc.master_url != master_url):
            sc = None

    # Create a new client instance if necessary.
    if sc is None:
        sc = StatusClient(master_url)

    # Now wait for events and print them
    try:
        while 1:
            for event in sc.pull_events():
                print time.time(), event
            time.sleep(.1)
    except KeyboardInterrupt:
        print "(interrupted, stopping)"

    # Save the current instance.
    file = open(path, "w")
    json.dump(sc.todata(), file)
    file.close()

if __name__ == '__main__':
    main()


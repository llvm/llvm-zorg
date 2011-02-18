import time
import urllib2
from flask import json

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

        return BuilderInfo(data['name'], set(data['builds']), data['last_poll'])

    def todata(self):
        return { 'version' : 0,
                 'name' : self.name,
                 'builds' : list(self.builds),
                 'last_poll' : self.last_poll }

    def __init__(self, name, builds, last_poll):
        self.name = name
        self.builds = builds
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

    def get_json_result(self, query_items, arguments=None):
        path = '/json/' + '/'.join(urllib2.quote(item)
                                   for item in query_items)
        if arguments is not None:
            path += '?' + urllib2.urlencode(arguments)

        url = self.master_url + path
        request = urllib2.urlopen(url)
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
        yield ('poll_builders',)
        res = self.get_json_result(('builders',))
        builder_names = set(res.keys())
        current_builders = set(self.builders)

        for name in builder_names - current_builders:
            yield ('added_builder', name)
            self.builders[name] = BuilderInfo(name, set(), -1)
        for name in current_builders - builder_names:
            yield ('removed_builder', name)
            self.builders.remove(name)

        self.last_builders_poll = time.time()

    def pull_builder(self, builder):
        # Pull the builder data.
        yield ('poll_builder', builder.name)
        res = self.get_json_result(('builders', builder.name))
        builds = set(res['cachedBuilds'])

        for id in builds - builder.builds:
            yield ('add_build', builder.name, id)
            builder.builds.add(id)
        for id in builder.builds - builds:
            yield ('remove_build', builder.name, id)
            builder.builds.remove(id)

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


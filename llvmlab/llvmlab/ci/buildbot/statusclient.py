import time
import urllib2
from flask import json

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
        sc.builders = set(data['builders'])
        sc.builds = dict((name, set(items))
                         for name, items in data['builds'])
        sc.last_builders_poll = data['last_builders_poll']
        sc.last_builder_poll = data['last_builder_poll']
        return sc

    def todata(self):
        return { 'version' : 0,
                 'master_url' : self.master_url,
                 'builder_poll_rate' : self.builder_poll_rate,
                 'builders_poll_rate' : self.builders_poll_rate,
                 'builders' : list(self.builders),
                 'builds' : [(name, list(items))
                            for name,items in self.builds.items()],
                 'last_builders_poll' : self.last_builders_poll,
                 'last_builder_poll' : self.last_builder_poll }

    def __init__(self, master_url,
                 builders_poll_rate = 60.0,
                 builder_poll_rate = 5.0):
        # Normalize the master URL.
        self.master_url = master_url
        if self.master_url.endswith('/'):
            self.master_url += '/'

        # Initialize the data we track.
        self.builders = set()
        self.builds = {}

        # Set poll rates (how frequently we are willing to recontact the
        # master).
        self.builders_poll_rate = float(builders_poll_rate)
        self.builder_poll_rate = float(builder_poll_rate)

        # Set last poll times so we will repoll on startup.
        self.last_builders_poll = -1
        self.last_builder_poll = {}

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
        for builder in self.builders:
            last_poll = self.last_builder_poll.get(builder, -1)
            if current_time - last_poll >= self.builder_poll_rate:
                for event in self.pull_builder(builder):
                    yield event

    def add_builder(self, name):
        yield ('added_builder', name)
        self.builders.add(name)
        self.last_builder_poll[name] = -1
        self.builds[name] = set()

    def remove_builder(self, name):
        yield ('removed_builder', name)
        self.builders.remove(name)
        self.last_builder_poll.pop(name)
        self.builds.pop(name)

    def add_build(self, name, id):
        yield ('add_build', name, id)
        self.builds[name].add(id)
    def remove_build(self, name, id):
        yield ('remove_build', name, id)
        self.builds[name].remove(id)

    def pull_builders(self):
        # Pull the builder names.
        #
        # FIXME: BuildBot should provide a more efficient query for this.
        yield ('poll_builders',)
        builders = self.get_json_result(('builders',))
        builder_names = set(builders.keys())

        for name in builder_names - self.builders:
            for event in self.add_builder(name):
                yield event
        for name in self.builders - builder_names:
            for event in self.remove_builder(name):
                yield event

        self.last_builders_poll = time.time()

    def pull_builder(self, name):
        # Pull the builder data.
        yield ('poll_builder', name)
        builder = self.get_json_result(('builders', name))
        builds = set(builder['cachedBuilds'])

        for id in builds - self.builds[name]:
            for event in self.add_build(name, id):
                yield event
        for id in self.builds[name] - builds:
            for event in self.remove_build(name, id):
                yield event

        self.last_builder_poll[name] = time.time()

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


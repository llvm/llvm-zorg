import time
import urllib2
from flask import json

class StatusClient(object):
    """
    StatusClient object for watching a buildbot master and dispatching signals
    on changes.

    Currently, the client primarily is worried about tracking builders.
    """

    def __init__(self, master_url,
                 builders_poll_rate = 60.0):
        self.master_url = master_url
        self.builders = set()

        # Normalize the master URL.
        if self.master_url.endswith('/'):
            self.master_url += '/'

        # Set poll rates (how frequently we are willing to recontact the
        # master).
        self.builders_poll_rate = float(builders_poll_rate)

        # Set last poll times so we will repoll on startup.
        self.last_builders_poll = -1

    def get_json_result(self, query_items, arguments=None):
        path = '/json/' + ','.join(urllib2.quote(item)
                                   for item in query_items)
        if arguments is not None:
            path += '?' + urllib2.urlencode(arguments)

        url = self.master_url + path
        print url

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

        yield 1

    def pull_builders(self):
        # Pull the builder names.
        #
        # FIXME: BuildBot should provide a more efficient query for this.
        builders = self.get_json_result(('builders',))
        builder_names = set(builders.keys())

        for name in builder_names - self.builders:
            yield ('added_builder', name)
        for name in self.builders - builder_names:
            yield ('removed_builder', name)

        self.builders = builder_names
        self.last_builders_poll = time.time()

if __name__ == '__main__':
    sc = StatusClient("http://lab.llvm.org:8013")
    while 1:
        for event in sc.pull_events():
            print time.time(), event
        time.sleep(.1)


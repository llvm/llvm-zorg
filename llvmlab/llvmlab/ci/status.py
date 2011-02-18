"""
Status information for the CI infrastructure, for use by the dashboard.
"""

from llvmlab import util
import buildbot.statusclient

class BuildStatus(util.simple_repr_mixin):
    @staticmethod
    def fromdata(data):
        version = data['version']
        if version != 0:
            raise ValueError, "Unknown version"

        return BuildStatus(data['name'], data['number'], data['source_stamp'],
                           data['result'], data['start_time'], data['end_time'])

    def todata(self):
        return { 'version' : 0,
                 'name' : self.name,
                 'number' : self.number,
                 'source_stamp' : self.source_stamp,
                 'result' : self.result,
                 'start_time' : self.start_time,
                 'end_time' : self.end_time }

    def __init__(self, name, number, source_stamp,
                 result, start_time, end_time):
        self.name = name
        self.number = number
        self.source_stamp = source_stamp
        self.result = result
        self.start_time = start_time
        self.end_time = end_time

class Status(util.simple_repr_mixin):
    @staticmethod
    def fromdata(data):
        version = data['version']
        if version != 0:
            raise ValueError, "Unknown version"

        sc = data.get('statusclient')
        if sc:
            sc = buildbot.statusclient.StatusClient.fromdata(sc)
        return Status(data['master_url'],
                      dict((name, [BuildStatus.fromdata(b)
                                   for b in builds])
                           for name,builds in data['builders']),
                      sc)

    def todata(self):
        return { 'version' : 0,
                 'master_url' : self.master_url,
                 'builders' : [(name, [b.todata()
                                       for b in builds])
                               for name,builds in self.builders.items()],
                 'statusclient' : self.statusclient.todata() }

    def __init__(self, master_url, builders, statusclient = None):
        self.master_url = master_url
        self.builders = builders
        if statusclient is None and master_url:
            statusclient = buildbot.statusclient.StatusClient(master_url)
        self.statusclient = statusclient

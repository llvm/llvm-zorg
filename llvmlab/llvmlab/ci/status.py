"""
Status information for the CI infrastructure, for use by the dashboard.
"""

from llvmlab import util

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

        return Status([BuildStatus.fromdata(item)
                       for item in data['builds']])

    def todata(self):
        return { 'version' : 0,
                 'builds' : [item.todata()
                             for item in self.builds] }

    def __init__(self, builds):
        self.builds = builds

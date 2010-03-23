"""
Utilities for working with the LNT test format.
"""

import time
import datetime
import json

def normalize_time(t):
    if isinstance(t,float):
        t = datetime.datetime.utcfromtimestamp(t)
    elif not isinstance(t, datatime.datetime):
        t = time.strptime(start_time, '%Y-%m-%d %H:%M:%S')
    return t.strftime('%Y-%m-%d %H:%M:%S')

class Machine:
    def __init__(self, name, info={}):
        self.name = str(name)
        self.info = dict((str(key),str(value))
                         for key,value in info.items())

    def render(self):
        return { 'Name' : self.name,
                 'Info' : self.info }

class Run:
    def __init__(self, start_time, end_time, info={}):
        if start_time is None:
            start_time = datetime.datetime.now()
        if end_time is None:
            end_time = datetime.datetime.now()

        self.start_time = normalize_time(start_time)
        self.end_time = normalize_time(end_time)
        self.info = dict((str(key),str(value))
                         for key,value in info.items())

    def render(self):
        return { 'Start Time' : self.start_time,
                 'End Time' : self.end_time,
                 'Info' : self.info }

class TestSamples:
    def __init__(self, name, data, info={}):
        self.name = str(name)
        self.info = dict((str(key),str(value))
                         for key,value in info.items())
        self.data = map(float, data)

    def render(self):
        return { 'Name' : self.name,
                 'Info' : self.info,
                 'Data' : self.data }

class Report:
    def __init__(self, machine, run, tests):
        self.machine = machine
        self.run = run
        self.tests = list(tests)

        assert isinstance(self.machine, Machine)
        assert isinstance(self.run, Run)
        for t in self.tests:
            assert isinstance(t, TestSamples)

    def render(self):
        return json.dumps({ 'Machine' : self.machine.render(),
                            'Run' : self.run.render(),
                            'Tests' : [t.render() for t in self.tests] },
                          sort_keys=True, indent=4)

__all__ = ['Machine', 'Run', 'TestSamples', 'Report']

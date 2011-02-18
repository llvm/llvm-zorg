"""
Status information for the CI infrastructure, for use by the dashboard.
"""

import threading
import time

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

class StatusMonitor(threading.Thread):
    def __init__(self, app, status):
        threading.Thread.__init__(self)
        self.app = app
        self.status = status

    def run(self):
        # Constantly read events from the status client.
        while 1:
            for event in self.status.statusclient.pull_events():
                # Log the event (for debugging).
                self.status.event_log.append((time.time(), event))
                self.status.event_log = self.status.event_log[-100:]

                kind = event[0]
                if kind == 'added_builder':
                    name = event[1]
                    if name not in self.status.builders:
                        self.status.builders[name] = []
                        self.status.build_map[name] = {}
                elif kind == 'removed_builder':
                    name = event[1]
                    self.status.builders.pop(name)
                    self.status.build_map.pop(name)
                elif kind == 'reset_builder':
                    name = event[1]
                    self.status.builders[name] = []
                    self.status.build_map[name] = {}
                elif kind == 'invalid_build':
                    _,name,id = event
                    build = self.status.build_map[name].get(id)
                    if build is not None:
                        self.status.builders[name].remove(build)
                        self.status.build_map[name].pop(id)
                elif kind in ('add_build', 'completed_build'):
                    _,name,id = event
                    build = self.status.build_map[name].get(id)
                    if build is None:
                        build = BuildStatus(name, id, None, None, None, None)
                        self.status.build_map[name][id] = build

                        # Add to the builds list, maintaining order.
                        builds = self.status.builders[name]
                        builds.append(build)
                        if len(builds)>1 and build.number < builds[-2].number:
                            builds.sort(key = lambda b: b.number)

                    # Get the build information.
                    res = self.status.statusclient.get_json_result((
                            'builders', name, 'builds', str(build.number)))
                    build.result = res['results']
                    build.source_stamp = res['sourceStamp']['revision']
                    build.start_time = res['times'][0]
                    build.end_time = res['times'][1]
                else:
                    # FIXME: Use flask logging APIs.
                    print >>sys.stderr,"warning: unknown event '%r'" % (event,)

                # FIXME: Don't save this frequently, we really just want to
                # checkpoint and make sure we save on restart.
                self.app.save_status()

            time.sleep(.1)
        
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

        # Transient data.
        self.event_log = []
        self.build_map = dict((name, dict((b.number, b)
                                          for b in builds))
                              for name,builds in self.builders.items())

    def start_monitor(self, app):
        if self.statusclient:
            monitor = StatusMonitor(app, self)
            monitor.start()
            return monitor

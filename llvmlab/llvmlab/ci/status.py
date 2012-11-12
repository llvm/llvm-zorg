"""
Status information for the CI infrastructure, for use by the dashboard.
"""

import threading
import time
import traceback
import StringIO

from llvmlab import util
import buildbot.statusclient

class BuildStatus(util.simple_repr_mixin):
    @staticmethod
    def fromdata(data):
        version = data['version']
        if version not in (0, 1):
            raise ValueError, "Unknown version"

        if version == 0:
            slave = None
        else:
            slave = data['slave']
        return BuildStatus(data['name'], data['number'], data['source_stamp'],
                           data['result'], data['start_time'], data['end_time'],
                           slave)

    def todata(self):
        return { 'version' : 1,
                 'name' : self.name,
                 'number' : self.number,
                 'source_stamp' : self.source_stamp,
                 'result' : self.result,
                 'start_time' : self.start_time,
                 'end_time' : self.end_time,
                 'slave' : self.slave }

    def __init__(self, name, number, source_stamp,
                 result, start_time, end_time, slave):
        self.name = name
        self.number = number
        self.source_stamp = source_stamp
        self.result = result
        self.start_time = start_time
        self.end_time = end_time
        self.slave = slave

class StatusMonitor(threading.Thread):
    def __init__(self, app, status):
        threading.Thread.__init__(self)
        self.daemon = True
        self.app = app
        self.status = status

    def run(self):
        while 1:
            try:
                self.read_events()
            except:
                # Log this failure.
                os = StringIO.StringIO()
                print >>os, "*** ERROR: failure in buildbot monitor"
                print >>os, "\n-- Traceback --"
                traceback.print_exc(file = os)
                self.app.logger.error(os.getvalue())

                # Sleep for a while, then restart.
                time.sleep(60)

    def read_events(self):
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
                    if name in self.status.builders:
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
                    add_build = False
                    if build is None:
                        add_build = True
                        build = BuildStatus(name, id, None, None, None, None,
                                            None)

                    # Get the build information.
                    try:
                        res = self.status.statusclient.get_json_result((
                                'builders', name, 'builds', str(build.number)))
                    except:
                        res = None

                    if res:
                        build.result = res['results']
                        if 'sourceStamps' in res:
                            build.source_stamp = res['sourceStamps'][0]['revision']
                        else:
                            build.source_stamp = res['sourceStamp']['revision']
                        build.start_time = res['times'][0]
                        build.end_time = res['times'][1]
                        build.slave = res['slave']

                        if add_build:
                            # Add to the builds list, maintaining order.
                            self.status.build_map[name][id] = build
                            builds = self.status.builders[name]
                            builds.append(build)
                            if (len(builds) > 1 and
                                build.number < builds[-2].number):
                                builds.sort(key = lambda b: b.number)
                else:
                    self.app.logger.warning("unknown event '%r'" % (event,))

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
            self.statusclient.logger = app.logger

            monitor = StatusMonitor(app, self)
            monitor.start()
            return monitor

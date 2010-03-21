#!/usr/bin/env python
# -*- Python -*-

import sys
import os

# These were just some local hacks I used at some point to enable testing with
# MySQL. We were running afoul of cimport issues, I think. Revisit when we care
# about MySQL.
if 0:
    os.environ['PATH'] += ':/usr/local/mysql/bin'

    os.environ['PYTHON_EGG_CACHE'] = '/tmp'
    import MySQLdb

    import PerfDB
    db = PerfDB.PerfDB("mysql://root:admin@localhost/nt_internal")
    from PerfDB import Machine
    q = db.session.query(Machine.name).distinct().order_by(Machine.name)
    for i in q[:1]:
        break

def create_publisher():
    import warnings
    warnings.simplefilter("ignore", category=DeprecationWarning)

    # We expect the config file to be adjacent to the absolute path of
    # the cgi script.
    configPath = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                          "zorg.cfg")
    configData = {}
    exec open(configPath) in configData

    # Find the zorg installation dir.
    zorgDir = os.path.join(os.path.dirname(configPath),
                           configData.get('zorg', ''))
    if zorgDir and zorgDir not in sys.path:
        sys.path.append(zorgDir)

    from viewer import publisher
    return publisher.create_publisher(configPath, configData)

if __name__ == '__main__':
    from quixote.server import cgi_server
    cgi_server.run(create_publisher)

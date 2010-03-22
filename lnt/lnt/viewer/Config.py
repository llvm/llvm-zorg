"""
LNT Config object for tracking user-configurable installation parameters.
"""

import os

class DBInfo:
    @staticmethod
    def fromData(baseDir, dict):
        dbPath = dict.get('path')
        if not dbPath.startswith('mysql://'):
            dbPath = os.path.join(baseDir, dbPath)
        return DBInfo(dbPath,
                      bool(dict.get('showNightlytest')),
                      bool(dict.get('showGeneral')))

    def __init__(self, path, showNightlytest, showGeneral):
        self.path = path
        self.showNightlytest = showNightlytest
        self.showGeneral = showGeneral

class Config:
    @staticmethod
    def fromData(path, data):
        # Paths are resolved relative to the absolute real path of the
        # config file.
        baseDir = os.path.dirname(os.path.abspath(path))

        ntEmailer = data.get('nt_emailer')
        if ntEmailer:
            ntEmailEnabled = bool(ntEmailer.get('enabled'))
            ntEmailHost = str(ntEmailer.get('host'))
            ntEmailFrom = str(ntEmailer.get('from'))

            # The email to field can either be a string, or a list of tuples of
            # the form [(accept-regexp-pattern, to-address)].
            item = ntEmailer.get('to')
            if isinstance(item, str):
                ntEmailTo = item
            else:
                ntEmailTo = [(str(a),str(b))
                             for a,b in item]
        else:
            ntEmailEnabled = False
            ntEmailHost = ntEmailFrom = ntEmailTo = ""

        return Config(os.path.join(baseDir, data['zorg']),
                      data['zorgURL'],
                      dict([(k,DBInfo.fromData(baseDir, v))
                            for k,v in data['databases'].items()]),
                      ntEmailEnabled, ntEmailHost, ntEmailFrom, ntEmailTo)

    def __init__(self, zorgDir, zorgURL, databases,
                 ntEmailEnabled, ntEmailHost, ntEmailFrom, ntEmailTo):
        self.zorgDir = zorgDir
        self.zorgURL = zorgURL
        self.tempDir = os.path.join(zorgDir, 'viewer', 'resources', 'graphs')
        while self.zorgURL.endswith('/'):
            self.zorgURL = zorgURL[:-1]
        self.databases = databases
        self.ntEmailEnabled = ntEmailEnabled
        self.ntEmailHost = ntEmailHost
        self.ntEmailFrom = ntEmailFrom
        self.ntEmailTo = ntEmailTo

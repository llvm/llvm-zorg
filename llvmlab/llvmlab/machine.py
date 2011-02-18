"""
LLVM-Lab Machine Objects
"""

from llvmlab import util

class Machine(util.simple_repr_mixin):
    @staticmethod
    def fromdata(data):
        version = data['version']
        if version != 0:
            raise ValueError, "Unknown version"

        return Machine(data['id'], data['hostname'], data['admin'])

    def todata(self):
        return { 'version' : 0,
                 'id' : self.id,
                 'hostname' : self.hostname,
                 'admin' : self.admin }

    def __init__(self, id, hostname, admin):
        self.id = id
        self.hostname = hostname
        self.admin = admin

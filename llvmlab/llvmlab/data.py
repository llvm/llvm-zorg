"""
LLVM-Lab Data Management
"""

from llvmlab import util
from llvmlab import machine, user

class Data(util.simple_repr_mixin):
    @staticmethod
    def fromdata(data):
        version = data['version']
        if version != 0:
            raise ValueError, "Unknown version"

        users = [user.User.fromdata(u)
                 for u in data['users']]
        machines = [machine.Machine.fromdata(u)
                    for u in data['machines']]
        return Data(users, machines)

    def todata(self):
        return { 'version' : 0,
                 'users' : [item.todata()
                            for item in self.users.values()
                            if item is not self.admin_user],
                 'machines' : [item.todata()
                               for item in self.machines.values()] }

    def __init__(self, users, machines):
        self.machines = dict((item.id, item) for item in machines)
        self.users = dict((item.id, item) for item in users)
        self.admin_user = None

    def set_admin_user(self, user):
        if user.id in self.users:
            raise ValueError, "database contains admin user %r" % user.id

        self.admin_user = user
        self.users[user.id] = user

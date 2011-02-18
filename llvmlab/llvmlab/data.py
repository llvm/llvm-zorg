"""
LLVM-Lab Data Management
"""

from llvmlab import util
from llvmlab import user

class Data(util.simple_repr_mixin):
    @staticmethod
    def fromdata(data):
        version = data['version']
        if version != 0:
            raise ValueError, "Unknown version"

        users = [user.User.fromdata(u)
                 for u in data['users']]
        return Data(users)

    def todata(self):
        return { 'version' : 0,
                 'users' : [u.todata()
                            for u in self.users.values()
                            if u is not self.admin_user] }

    def __init__(self, users):
        self.users = dict((u.id, u) for u in users)
        self.admin_user = None

    def set_admin_user(self, user):
        if user.id in self.users:
            raise ValueError, "database contains admin user %r" % user.id

        self.admin_user = user
        self.users[user.id] = user


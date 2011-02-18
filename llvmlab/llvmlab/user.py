"""
LLVM-Lab User Objects
"""

from llvmlab import util

class User(util.simple_repr_mixin):
    @staticmethod
    def fromdata(data):
        version = data['version']
        if version != 0:
            raise ValueError, "Unknown version"

        return User(data['id'], data['passhash'],
                    data['name'], data['email'],
                    data['htpasswd'])

    def todata(self):
        return { 'version' : 0,
                 'id' : self.id,
                 'passhash' : self.passhash,
                 'name' : self.name,
                 'email' : self.email,
                 'htpasswd' : self.htpasswd }

    def __init__(self, id, passhash, name, email, htpasswd):
        self.id = id
        self.passhash = passhash
        self.name = name
        self.email = email
        self.htpasswd = htpasswd

    def has_lab_access(self):
        """has_lab_access() -> bool

        Is this user allowed access to the lab? Users with lab access can
        add/modify/remove machines and update other physical lab information.
        """
        return True

import sqlalchemy
import testsuite

class V4DB(object):
    def __init__(self, path, echo=False):
        assert (path.startswith('mysql://') or
                path.startswith('sqlite://')), "invalid database path"

        self.path = path
        self.engine = sqlalchemy.create_engine(path, echo=echo)

        # Create the common tables in case this is a new database.
        testsuite.Base.metadata.create_all(self.engine)

        self.session = sqlalchemy.orm.sessionmaker(self.engine)()

        # Add several shortcut aliases.
        self.add = self.session.add
        self.commit = self.session.commit
        self.query = self.session.query

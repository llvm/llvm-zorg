import sqlalchemy
import testsuite
import testsuitedb

class V4DB(object):
    """
    Wrapper object for LNT v0.4+ databases.
    """

    class TestSuiteAccessor(object):
        def __init__(self, v4db):
            self.v4db = v4db

        def __getitem__(self, name):
            # Get the test suite object.
            ts = self.v4db.query(testsuite.TestSuite).\
                filter(testsuite.TestSuite.name == name).first()
            if ts is None:
                raise IndexError,name

            # Instantiate the per-test suite wrapper object for this test suite.
            return testsuitedb.TestSuiteDB(self.v4db, ts)

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

    @property
    def testsuite(self):
        # This is the start of "magic" part of V4DB, which allows us to get
        # fully bound SA instances for databases which are effectively described
        # by the TestSuites table.

        # The magic starts by returning a object which will allow us to use
        # array access to get the per-test suite database wrapper.
        return V4DB.TestSuiteAccessor(self)

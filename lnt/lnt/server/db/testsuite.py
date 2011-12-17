"""
Database models for the TestSuites abstraction.
"""

import lnt

import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.orm
from sqlalchemy import *
from sqlalchemy.schema import Index
from sqlalchemy.orm import relation

Base = sqlalchemy.ext.declarative.declarative_base()

class SampleType(Base):
    """
    The SampleType table describes an enumeration for the possible types clients
    can configure for different sample fields.
    """
    __tablename__ = 'SampleType'

    id = Column("ID", Integer, primary_key=True)
    name = Column("Name", String(256), unique=True)

    # FIXME: We expect the database to have a limited number of instances of
    # this class, we should just provide static class variables for the various
    # types once bound.

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '%s%r' % (self.__class__.__name__, (self.name,))

class StatusKind(Base):
    """
    The StatusKind table describes an enumeration for the possible values
    clients can use for "Status" typed samples. This is designed to match the
    values which are in use by test produces and are defined in the lnt.testing
    module.
    """

    __tablename__ = 'StatusKind'

    id = Column("ID", Integer, primary_key=True)
    name = Column("Name", String(256), unique=True)
    
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '%s%r' % (self.__class__.__name__, (self.name,))

class TestSuite(Base):
    __tablename__ = 'TestSuite'

    id = Column("ID", Integer, primary_key=True)
    name = Column("Name", String(256), unique=True)

    # The name we use to prefix the per-testsuite databases.
    db_key_name = Column("DBKeyName", String(256))

    # The version of the schema used for the per-testsuite databases (encoded as
    # the LNT version).
    version = Column("Version", String(16))

    machine_fields = relation('MachineField', backref='test_suite')
    order_fields = relation('OrderField', backref='test_suite')
    run_fields = relation('RunField', backref='test_suite')
    sample_fields = relation('SampleField', backref='test_suite')

    def __init__(self, name, db_key_name):
        self.name = name
        self.db_key_name = db_key_name
        self.version = lnt.__version__

    def __repr__(self):
        return '%s%r' % (self.__class__.__name__, (self.name, self.db_key_name,
                                                   self.version))

class MachineField(Base):
    __tablename__ = 'TestSuiteMachineFields'

    id = Column("ID", Integer, primary_key=True)
    test_suite_id = Column("TestSuiteID", Integer, ForeignKey('TestSuite.ID'),
                           index=True)
    name = Column("Name", String(256))

    # The info key describes the key to expect this field to be present as in
    # the reported machine information. Missing keys result in NULL values in
    # the database.
    info_key = Column("InfoKey", String(256))

    def __init__(self, name, info_key):
        self.name = name
        self.info_key = info_key

    def __repr__(self):
        return '%s%r' % (self.__class__.__name__, (self.name, self.info_key))

class OrderField(Base):
    __tablename__ = 'TestSuiteOrderFields'

    id = Column("ID", Integer, primary_key=True)
    test_suite_id = Column("TestSuiteID", Integer, ForeignKey('TestSuite.ID'),
                           index=True)
    name = Column("Name", String(256))

    # The info key describes the key to expect this field to be present as in
    # the reported machine information. Missing keys result in NULL values in
    # the database.
    info_key = Column("InfoKey", String(256))

    # The ordinal index this field should be used at for creating a
    # lexicographic ordering amongst runs.
    ordinal = Column("Ordinal", Integer)

    def __init__(self, name, info_key, ordinal):
        assert isinstance(ordinal, int) and ordinal >= 0

        self.name = name
        self.info_key = info_key
        self.ordinal = ordinal

    def __repr__(self):
        return '%s%r' % (self.__class__.__name__, (self.name, self.info_key,
                                                   self.ordinal))

class RunField(Base):
    __tablename__ = 'TestSuiteRunFields'

    id = Column("ID", Integer, primary_key=True)
    test_suite_id = Column("TestSuiteID", Integer, ForeignKey('TestSuite.ID'),
                           index=True)
    name = Column("Name", String(256))

    # The info key describes the key to expect this field to be present as in
    # the reported machine information. Missing keys result in NULL values in
    # the database.
    info_key = Column("InfoKey", String(256))

    def __init__(self, name, info_key):
        self.name = name
        self.info_key = info_key

    def __repr__(self):
        return '%s%r' % (self.__class__.__name__, (self.name, self.info_key))

class SampleField(Base):
    __tablename__ = 'TestSuiteSampleFields'

    id = Column("ID", Integer, primary_key=True)
    test_suite_id = Column("TestSuiteID", Integer, ForeignKey('TestSuite.ID'),
                           index=True)
    name = Column("Name", String(256))

    # The type of sample this is.
    type_id = Column("Type", Integer, ForeignKey('SampleType.ID'))

    # The info key describes the key to expect this field to be present as in
    # the reported machine information. Missing keys result in NULL values in
    # the database.
    info_key = Column("InfoKey", String(256))

    type = relation(SampleType)

    def __init__(self, name, type, info_key):
        self.name = name
        self.type = type
        self.info_key = info_key

    def __repr__(self):
        return '%s%r' % (self.__class__.__name__, (self.name, self.type,
                                                   self.info_key))

"""
Database models for the TestSuites abstraction.
"""

import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.orm
from sqlalchemy import *
from sqlalchemy.schema import Index
from sqlalchemy.orm import relation

Base = sqlalchemy.ext.declarative.declarative_base()
class SampleType(Base):
    __tablename__ = 'SampleType'

    id = Column("ID", Integer, primary_key=True)
    name = Column("Name", String(256))
    
    def __init__(self, name):
        self.name = name

class StatusKind(Base):
    __tablename__ = 'StatusKind'

    id = Column("ID", Integer, primary_key=True)
    name = Column("Name", String(256))
    
    def __init__(self, name):
        self.name = name

class TestSuite(Base):
    __tablename__ = 'TestSuite'

    id = Column("ID", Integer, primary_key=True)
    name = Column("Name", String(256))
    db_key_name = Column("DBKeyName", String(256))
    version = Column("Version", Integer)

    machine_fields = relation('MachineField', backref='test_suite')
    order_fields = relation('OrderField', backref='test_suite')
    run_fields = relation('RunField', backref='test_suite')
    sample_fields = relation('SampleField', backref='test_suite')

    def __init__(self, name, db_key_name, version):
        self.name = name
        self.db_key_name = db_key_name
        self.version = version

    def __repr__(self):
        return '%s%r' % (self.__class__.__name__, (self.name, self.db_key_name,
                                                   self.version))

class MachineField(Base):
    __tablename__ = 'TestSuiteMachineFields'

    id = Column("ID", Integer, primary_key=True)
    test_suite_id = Column("TestSuiteID", Integer, ForeignKey('TestSuite.ID'))
    name = Column("Name", String(256))
    info_key = Column("InfoKey", String(256))

    def __init__(self, name, info_key):
        self.name = name
        self.info_key = info_key

class OrderField(Base):
    __tablename__ = 'TestSuiteOrderFields'

    id = Column("ID", Integer, primary_key=True)
    test_suite_id = Column("TestSuiteID", Integer, ForeignKey('TestSuite.ID'))
    name = Column("Name", String(256))
    info_key = Column("InfoKey", String(256))
    ordinal = Column("Ordinal", Integer)

    def __init__(self, name, info_key, ordinal):
        assert isinstance(ordinal, int) and ordinal >= 0

        self.name = name
        self.info_key = info_key
        self.ordinal = ordinal

class RunField(Base):
    __tablename__ = 'TestSuiteRunFields'

    id = Column("ID", Integer, primary_key=True)
    test_suite_id = Column("TestSuiteID", Integer, ForeignKey('TestSuite.ID'))
    name = Column("Name", String(256))
    info_key = Column("InfoKey", String(256))

    def __init__(self, name, info_key):
        self.name = name
        self.info_key = info_key

class SampleField(Base):
    __tablename__ = 'TestSuiteSampleFields'

    id = Column("ID", Integer, primary_key=True)
    test_suite_id = Column("TestSuiteID", Integer, ForeignKey('TestSuite.ID'))
    name = Column("Name", String(256))
    type = Column("Type", Integer, ForeignKey('SampleType.ID'))
    info_key = Column("InfoKey", String(256))

    def __init__(self, name, info_key):
        self.name = name
        self.info_key = info_key

"""
Database models for the TestSuite databases themselves.

These are a bit magical because the models themselves are driven by the test
suite metadata, so we only create the classes at runtime.
"""

import sqlalchemy
from sqlalchemy import *

import testsuite

class TestSuiteDB(object):
    def __init__(self, v4db, test_suite):
        self.v4db = v4db
        self.test_suite = test_suite

        self.base = sqlalchemy.ext.declarative.declarative_base()

        # Create parameterized model classes for this test suite.
        db_key_name = self.test_suite.db_key_name
        class Machine(self.base):
            __tablename__ = db_key_name + '_Machine'

            id = Column("ID", Integer, primary_key=True)
            name = Column("Name", String(256))
            number = Column("Number", Integer)
            parameters = Column("Parameters", Binary)

            # Dynamically create fields for all of the test suite defined
            # machine fields.
            class_dict = locals()
            for item in test_suite.machine_fields:
                if item.name in class_dict:
                    raise ValueError,"test suite defines reserved key %r" % (
                        name,)

                class_dict[item.name] = Column(item.name, String(256))

            def __init__(self, name, number):
                self.name = name
                self.number = number

            def __repr__(self):
                return '%s_%s%r' % (db_key_name, self.__class__.__name__,
                                    (self.name, self.number))
                
        class Order(self.base):
            __tablename__ = db_key_name + '_Order'

            id = Column("ID", Integer, primary_key=True)

            # Dynamically create fields for all of the test suite defined order
            # fields.
            class_dict = locals()
            for item in test_suite.order_fields:
                if item.name in class_dict:
                    raise ValueError,"test suite defines reserved key %r" % (
                        name,)

                class_dict[item.name] = Column(item.name, String(256))

            def __init__(self):
                pass

            def __repr__(self):
                return '%s_%s%r' % (db_key_name, self.__class__.__name__,
                                    ())

        class Run(self.base):
            __tablename__ = db_key_name + '_Run'

            id = Column("ID", Integer, primary_key=True)
            machine_id = Column("MachineID", Integer, ForeignKey(Machine.id))
            order_id = Column("OrderID", Integer, ForeignKey(Order.id))
            imported_from = Column("ImportedFrom", String(512))
            start_time = Column("StartTime", DateTime)
            end_time = Column("EndTime", DateTime)
            parameters = Column("Parameters", Binary)

            machine = sqlalchemy.orm.relation(Machine)
            order = sqlalchemy.orm.relation(Order)

            # Dynamically create fields for all of the test suite defined run
            # fields.
            class_dict = locals()
            for item in test_suite.run_fields:
                if item.name in class_dict:
                    raise ValueError,"test suite defines reserved key %r" % (
                        name,)

                class_dict[item.name] = Column(item.name, String(256))

            def __init__(self, machine, order, start_time, end_time):
                self.machine = machine
                self.order = order
                self.start_time = start_time
                self.end_time = end_time
                self.imported_from = None

            def __repr__(self):
                return '%s_%s%r' % (db_key_name, self.__class__.__name__,
                                    (self.machine, self.order, self.start_time,
                                     self.end_time))

        class Test(self.base):
            __tablename__ = db_key_name + '_Test'

            id = Column("ID", Integer, primary_key=True)
            name = Column("Name", String(256))

            def __init__(self, name):
                self.name = name

            def __repr__(self):
                return '%s_%s%r' % (db_key_name, self.__class__.__name__,
                                    (self.name))

        class Sample(self.base):
            __tablename__ = db_key_name + '_Sample'

            id = Column("ID", Integer, primary_key=True)
            run_id = Column("RunID", Integer, ForeignKey(Run.id))
            test_id = Column("TestID", Integer, ForeignKey(Test.id))

            run = sqlalchemy.orm.relation(Run)
            test = sqlalchemy.orm.relation(Test)

            # Dynamically create fields for all of the test suite defined sample
            # fields.
            class_dict = locals()
            for item in test_suite.sample_fields:
                if item.name in class_dict:
                    raise ValueError,"test suite defines reserved key %r" % (
                        name,)

                if item.type.name == 'Real':
                    class_dict[item.name] = Column(item.name, Float)
                elif item.type.name == 'Status':
                    class_dict[item.name] = Column(item.name, Integer,
                                                    ForeignKey(
                            testsuite.StatusKind.id))
                else:
                    raise ValueError,(
                        "test suite defines unknown sample type %r" (
                            item.type.name,))

            def __init__(self, run, test):
                self.run = run
                self.test = test

            def __repr__(self):
                return '%s_%s%r' % (db_key_name, self.__class__.__name__,
                                    (self.run, self.test, self.value))

        self.Machine = Machine
        self.Run = Run
        self.Test = Test
        self.Sample = Sample
        self.Order = Order

        # Create the test suite database tables in case this is a new database.
        self.base.metadata.create_all(self.v4db.engine)

        # Add several shortcut aliases, similar to the ones on the v4db.
        self.add = self.v4db.add
        self.commit = self.v4db.commit
        self.query = self.v4db.query

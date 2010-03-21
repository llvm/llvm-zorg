#!/usr/bin/python

###
# SQLAlchemy database layer

import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.orm
from sqlalchemy import *
from sqlalchemy.orm import relation, backref
from sqlalchemy.orm.collections import attribute_mapped_collection

Base = sqlalchemy.ext.declarative.declarative_base()
class Machine(Base):
    __tablename__ = 'Machine'

    id = Column("ID", Integer, primary_key=True)
    name = Column("Name", String(256))
    number = Column("Number", Integer)

    info = relation('MachineInfo',
                    collection_class=attribute_mapped_collection('key'),
                    backref=backref('machine'))

    def __init__(self, name, number):
        self.name = name
        self.number = number

    def __repr__(self):
        return '%s%r' % (self.__class__.__name__, (self.name, self.number))

class MachineInfo(Base):
    __tablename__ = 'MachineInfo'

    id = Column("ID", Integer, primary_key=True)
    machine_id = Column("Machine", Integer, ForeignKey('Machine.ID'))
    key = Column("Key", String(256))
    value = Column("Value", String(4096))

    def __init__(self, machine, key, value):
        self.machine = machine
        self.key = key
        self.value = value

    def __repr__(self):
        return '%s%r' % (self.__class__.__name__,
                         (self.machine, self.key, self.value))

class Run(Base):
    __tablename__ = 'Run'

    id = Column("ID", Integer, primary_key=True)
    machine_id = Column("MachineID", Integer, ForeignKey('Machine.ID'))
    start_time = Column("StartTime", DateTime)
    end_time = Column("EndTime", DateTime)

    machine = relation(Machine)

    info = relation('RunInfo',
                    collection_class=attribute_mapped_collection('key'),
                    backref=backref('run'))

    def __init__(self, machine, start_time, end_time):
        self.machine = machine
        self.start_time = start_time
        self.end_time = end_time

    def __repr__(self):
        return '%s%r' % (self.__class__.__name__,
                         (self.machine, self.start_time, self.end_time))

class RunInfo(Base):
    __tablename__ = 'RunInfo'

    id = Column("ID", Integer, primary_key=True)
    run_id = Column("Run", Integer, ForeignKey('Run.ID'))
    key = Column("Key", String(256))
    value = Column("Value", String(4096))

    def __init__(self, run, key, value):
        self.run = run
        self.key = key
        self.value = value

    def __repr__(self):
        return '%s%r' % (self.__class__.__name__,
                         (self.run, self.key, self.value))

class Test(Base):
    __tablename__ = 'Test'

    id = Column("ID", Integer, primary_key=True)
    name = Column("Name", String(512))

    info = relation('TestInfo',
                    collection_class=attribute_mapped_collection('key'),
                    backref=backref('test'))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '%s%r' % (self.__class__.__name__,
                         (self.name,))

class TestInfo(Base):
    __tablename__ = 'TestInfo'

    id = Column("ID", Integer, primary_key=True)
    test_id = Column("Test", Integer, ForeignKey('Test.ID'))
    key = Column("Key", String(256))
    value = Column("Value", String(4096))

    def __init__(self, test, key, value):
        self.test = test
        self.key = key
        self.value = value

    def __repr__(self):
        return '%s%r' % (self.__class__.__name__,
                         (self.test, self.key, self.value))

class Sample(Base):
    __tablename__ = 'Sample'

    id = Column("ID", Integer, primary_key=True)
    run_id = Column("RunID", Integer, ForeignKey('Run.ID'))
    test_id = Column("TestID", Integer, ForeignKey('Test.ID'))
    value = Column("Value", Float)

    run = relation(Run)
    test = relation(Test)

    def __init__(self, run, test, value):
        self.run = run
        self.test = test
        self.value = value

    def __repr__(self):
        return '%s%r' % (self.__class__.__name__,
                         (self.run, self.test, self.value))

###
# PerfDB wrapper, to avoid direct SA dependency when possible.

def info_eq(a, b):
    a = list(a)
    b = list(b)
    a.sort()
    b.sort()
    return a == b

class PerfDB:
    def __init__(self, path, echo=False):
        if (not path.startswith('mysql://') and
            not path.startswith('sqlite://')):
            path = 'sqlite:///' + path
        self.engine = sqlalchemy.create_engine(path, echo=echo)

        # Create the tables in case this is a new database.
        Base.metadata.create_all(self.engine)

        self.session = sqlalchemy.orm.sessionmaker(self.engine)()

    def machines(self, name=None):
        q = self.session.query(Machine)
        if name:
            q = q.filter_by(name=name)
        return q

    def tests(self, name=None):
        q = self.session.query(Test)
        if name:
            q = q.filter_by(name=name)
        return q

    def runs(self, machine=None):
        q = self.session.query(Run)
        if machine:
            q = q.filter_by(machine=machine)
        return q

    def samples(self, run=None, test=None):
        q = self.session.query(Sample)
        if run:
            q = q.filter_by(run_id=run.id)
        if test:
            q = q.filter_by(test_id=test.id)
        return q

    def getNumMachines(self):
        return self.machines().count()

    def getNumRuns(self):
        return self.runs().count()

    def getNumTests(self):
        return self.tests().count()

    def getNumSamples(self):
        return self.samples().count()

    def getMachine(self, id):
        return self.session.query(Machine).filter_by(id=id).one()

    def getRun(self, id):
        return self.session.query(Run).filter_by(id=id).one()

    def getTest(self, id):
        return self.session.query(Test).filter_by(id=id).one()

    def getOrCreateMachine(self, name, info):
        # FIXME: Not really the right way...
        number = 1
        for m in self.machines(name=name):
            if info_eq([(i.key, i.value) for i in m.info.values()], info):
                return m,False
            number += 1

        # Make a new record
        m = Machine(name, number)
        m.info = dict((k,MachineInfo(m,k,v)) for k,v in info)
        self.session.add(m)
        return m,True

    def getOrCreateTest(self, name, info):
        # FIXME: Not really the right way...
        for t in self.tests(name):
            if info_eq([(i.key, i.value) for i in t.info.values()], info):
                return t,False

        t = Test(name)
        t.info = dict((k,TestInfo(t,k,v)) for k,v in info)
        self.session.add(t)
        return t,True

    def getOrCreateRun(self, machine, start_time, end_time, info):
        from datetime import datetime
        start_time = datetime.strptime(start_time,
                                       "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(end_time,
                                     "%Y-%m-%d %H:%M:%S")

        # FIXME: Not really the right way...
        for r in self.session.query(Run).filter_by(machine=machine):
            # FIXME: Execute this filter in SQL, but resolve the
            # normalization issue w.r.t. SQLAlchemy first. I think we
            # may be running afoul of SQLite not normalizing the
            # datetime. If I don't do this then sqlalchemy issues a
            # query in the format YYYY-MM-DD HH:MM:SS.ssss which
            # doesn't work.
            if r.start_time != start_time or r.end_time != end_time:
                continue
            if info_eq([(i.key, i.value) for i in r.info.values()], info):
                return r,False

        # Make a new record
        r = Run(machine, start_time, end_time)
        r.info = dict((k,RunInfo(r,k,v)) for k,v in info)
        self.session.add(r)
        return r,True

    def addSample(self, run, test, value):
        s = Sample(run, test, value)
        self.session.add(s)
        return s

    def addSamples(self, samples):
        """addSamples([(run_id, test_id, value), ...]) -> None

        Batch insert a list of samples."""

        # Flush to keep session consistent.
        self.session.flush()

        for run_id,test_id,value in samples:
            q = Sample.__table__.insert().values(RunID = run_id,
                                                 TestID = test_id,
                                                 Value = value)
            self.session.execute(q)

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()

def importDataFromDict(db, data):
    # FIXME: Validate data
    machineData = data['Machine']
    runData = data['Run']
    testsData = data['Tests']

    # Get the machine
    # FIXME: Validate machine
    machine,_ = db.getOrCreateMachine(machineData['Name'],
                                      machineData['Info'].items())

    # Accept 'Time' as an alias for 'Start Time'
    if 'Start Time' not in runData and 'Time' in runData:
        import time
        t = time.strptime(runData['Time'],
                          "%a, %d %b %Y %H:%M:%S -0700 (PDT)")
        runData['Start Time'] = time.strftime('%Y-%m-%d %H:%M', t)

    # Create the run.
    run,inserted = db.getOrCreateRun(machine,
                                     runData.get('Start Time',''),
                                     runData.get('End Time',''),
                                     runData.get('Info',{}).items())
    if not inserted:
        return False,(machine,run)

    # Batch load the set of tests instead of repeatedly querying to unique.
    #
    # FIXME: Add explicit config object.
    test_info = {}
    for id,k,v in db.session.query(TestInfo.test_id, TestInfo.key,
                                   TestInfo.value):
        test_info[id] = (str(k),str(v))

    testMap = {}
    for test_id,test_name in db.session.query(Test.id, Test.name):
        info = test_info.get(test_id,[])
        info.sort()
        testMap[(str(test_name),tuple(info))] = test_id

    # Create the tests up front, so we can resolve IDs.
    test_ids = []
    late_ids = []
    for i,testData in enumerate(testsData):
        name = str(testData['Name'])
        info = [(str(k),str(v)) for k,v in testData['Info'].items()]
        info.sort()
        test_id = testMap.get((name,tuple(info)))
        if test_id is None:
            test,created = db.getOrCreateTest(testData['Name'],testData['Info'])
            assert created
            late_ids.append((i,test))
        test_ids.append(test_id)

    # Flush now to resolve test and run ids.
    #
    # FIXME: Surely there is a cleaner way to handle this?
    db.session.flush()

    if late_ids:
        for i,t in late_ids:
            test_ids[i] = t.id

    db.addSamples([(run.id, test_id, value)
                   for test_id,testData in zip(test_ids, testsData)
                   for value in testData['Data']])

    return True,(machine,run)

def test_sa_db(dbpath):
    if not dbpath.startswith('mysql://'):
        dbpath = 'sqlite:///' + dbpath
    engine = sqlalchemy.create_engine(dbpath)

    Session = sqlalchemy.orm.sessionmaker(engine)
    Session.configure(bind=engine)

    session = Session()

    m = session.query(Machine).first()
    print m
    print m.info

    r = session.query(Run).first()
    print r
    print r.info

    t = session.query(Test)[20]
    print t
    print t.info

    s = session.query(Sample)[20]
    print s

    import time
    start = time.time()
    print
    q = session.query(Sample)
    q = q.filter(Sample.run_id == 994)
    print
    res = session.execute(q)
    print res
    N = 0
    for row in res:
        if N == 1:
            print row
        N += 1
    print N, time.time() - start
    print

    start = time.time()
    N = 0
    for row in q:
        if N == 1:
            print row
        N += 1
    print N, time.time() - start

def main():
    global opts
    from optparse import OptionParser
    parser = OptionParser("usage: %prog dbpath")
    opts,args = parser.parse_args()

    if len(args) != 1:
        parser.error("incorrect number of argments")

    dbpath, = args

    # Test the SQLAlchemy layer.
    test_sa_db(dbpath)

    # Test the PerfDB wrapper.
    db = PerfDB(dbpath)

    print "Opened %r" % dbpath

    for m in db.machines():
        print m
        for r in db.runs(m):
            print '  run - id:%r, start:%r,'\
                ' # samples: %d.' % (r.id, r.start_time,
                                     db.samples(run=r).count())

if __name__ == '__main__':
    main()

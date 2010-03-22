# RUN: rm -f %t.db
# RUN: sqlite3 %t.db ".read %src_root/db/CreateTables.sql"
# RUN: python %s %t.db

import sys
from lnt.viewer.PerfDB import PerfDB, Run

# Check creation.

db = PerfDB(sys.argv[1])

assert db.getNumMachines() == 0
assert db.getNumRuns() == 0
assert db.getNumTests() == 0

m,created = db.getOrCreateMachine("machine-0", [('m_key','m_value')])
assert created

r,created = db.getOrCreateRun(m, '2000-01-02 03:04:05', '2006-07-08 09:10:11',
                              [('r_key','r_value')])

assert created
t,created = db.getOrCreateTest("test-0", [('t_key','t_value')])
assert created

s = db.addSample(r, t, 1.0)

print m
print r
print t

db.commit()

# Check uniquing.

db2 = PerfDB(sys.argv[1])
assert [m.id] == [i.id for i in db2.machines()]
assert [r.id] == [i.id for i in db2.runs().all()]
assert [t.id] == [i.id for i in db2.tests().all()]
assert [s.id] == [i.id for i in db2.samples().all()]

m2,created = db2.getOrCreateMachine("machine-0", [('m_key','m_value')])
assert m.id == m2.id and not created

r2,created = db2.getOrCreateRun(m, '2000-01-02 03:04:05', '2006-07-08 09:10:11',
                              [('r_key','r_value')])
assert r.id == r2.id and not created

t2,created = db2.getOrCreateTest("test-0", [('t_key','t_value')])
assert t.id == t2.id and not created

s2 = db2.addSample(r2, t2, 2.0)
assert s.id != s2.id

assert r.id == s.run.id == s2.run.id
assert t.id == s.test.id == s2.test.id

db2.commit()

# Check load.

db3 = PerfDB(sys.argv[1])
m3 = db3.machines().one()
r3 = db3.runs().one()
t3 = db3.tests().one()
s3a,s3b = db3.samples().all()
print m3,r3,t3,s3a,s3b

assert m.id == m3.id
assert r.id == r3.id
assert t.id == t3.id
assert s.id == s3a.id
assert s2.id == s3b.id

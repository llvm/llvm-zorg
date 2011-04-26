# RUN: rm -rf %t.install
# RUN: lnt create %t.install

# RUN: lnt import %t.install %S/Inputs/sample-a-small.plist --commit=1 --show-sample-count |\
# RUN:   FileCheck -check-prefix=IMPORT-A-1 %s

# IMPORT-A-1: Added Machines: 1
# IMPORT-A-1: Added Runs : 1
# IMPORT-A-1: Added Tests : 8
# IMPORT-A-1: Added Samples : 8

# RUN: lnt import %t.install %S/Inputs/sample-b-small.plist --commit=1 --show-sample-count |\
# RUN:   FileCheck -check-prefix=IMPORT-B %s

# IMPORT-B: Added Runs : 1

# RUN: lnt import %t.install %S/Inputs/sample-a-small.plist --commit=1 --show-sample-count |\
# RUN:   FileCheck -check-prefix=IMPORT-A-2 %s

# IMPORT-A-2: This submission is a duplicate of run 1

# RUN: python %s %t.install/data/lnt.db

import datetime, sys
from lnt.db.perfdb import PerfDB, Run, Test

db = PerfDB(sys.argv[1])

m = db.machines().one()
assert m.id == 1
assert m.name == 'LNT SAMPLE MACHINE'

info = dict((i.key,i.value) for i in m.info.values())
assert 'os' in info
assert info['os'] == ' Darwin 10.2.0'

runs = db.runs().all()
assert len(runs) == 2
rA,rB = runs
assert rA.machine == m
assert rB.machine == m
assert rA.start_time == datetime.datetime(2009, 11, 17, 2, 12, 25)
assert rA.end_time == datetime.datetime(2009, 11, 17, 3, 44, 48)
assert rA.info['tag'].key == 'tag'
assert rA.info['tag'].value == 'nightlytest'

t = db.tests().order_by(Test.name)[4]
assert t.name == 'nightlytest.SingleSource/Benchmarks/BenchmarkGame/fannkuch.llc.compile.success'
assert t.info.values() == []

samples = db.samples(test=t).all()
assert len(samples) == 2
sA,sB = samples
assert sA.run == rA
assert sB.run == rB
assert sA.value == 1.0
assert sB.value == 1.0

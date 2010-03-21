# RUN: rm -f %t.db
# RUN: sqlite3 %t.db ".read %src_root/db/CreateTables.sql"

# RUN: %src_root/import/ImportData --show-sample-count \
# RUN:     %t.db %S/Inputs/sample-a-small.plist |\
# RUN:   FileCheck -check-prefix=IMPORT-A-1 %s

# IMPORT-A-1: ADDED: 1 machines
# IMPORT-A-1: ADDED: 1 runs
# IMPORT-A-1: ADDED: 90 tests
# IMPORT-A-1: ADDED: 90 samples

# RUN: %src_root/import/ImportData --show-sample-count \
# RUN:     %t.db %S/Inputs/sample-b-small.plist |\
# RUN:   FileCheck -check-prefix=IMPORT-B %s

# IMPORT-B: ADDED: 0 machines
# IMPORT-B: ADDED: 1 runs
# IMPORT-B: ADDED: 0 tests
# IMPORT-B: ADDED: 90 samples

# RUN: %src_root/import/ImportData --show-sample-count \
# RUN:     %t.db %S/Inputs/sample-a-small.plist |\
# RUN:   FileCheck -check-prefix=IMPORT-A-2 %s

# IMPORT-A-2: IGNORING DUPLICATE RUN
# IMPORT-A-2: ADDED: 0 machines
# IMPORT-A-2: ADDED: 0 runs
# IMPORT-A-2: ADDED: 0 tests
# IMPORT-A-2: ADDED: 0 samples

# RUN: python %s %t.db

import datetime, sys
from viewer.PerfDB import PerfDB, Run, Test

db = PerfDB(sys.argv[1])

m = db.machines().one()
assert m.id == 1
assert m.name == 'smoosh-01.apple.com'

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

t = db.tests().order_by(Test.name)[20]
assert t.name == 'nightlytest.SingleSource/Benchmarks/BenchmarkGame/fannkuch.llc.compile.success'
assert t.info.values() == []

samples = db.samples(test=t).all()
assert len(samples) == 2
sA,sB = samples
assert sA.run == rA
assert sB.run == rB
assert sA.value == 1.0
assert sB.value == 1.0

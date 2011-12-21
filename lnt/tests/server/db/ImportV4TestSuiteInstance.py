# Check the import process into a v4 test suite DB.
#
# We first construct a temporary LNT instance.
# RUN: rm -rf %t.install
# RUN: lnt create --use-v4 %t.install

# Import the first test set.
# RUN: lnt import %t.install %S/Inputs/sample-a-small.plist \
# RUN:     --commit=1 --show-sample-count > %t1.log
# RUN: FileCheck -check-prefix=IMPORT-A-1 %s < %t1.log
#
# IMPORT-A-1: Added Machines: 1
# IMPORT-A-1: Added Runs : 1
# IMPORT-A-1: Added Tests : 1
# IMPORT-A-1: Added Samples : 1

# Import the second test set.
# RUN: lnt import %t.install %S/Inputs/sample-b-small.plist \
# RUN:     --commit=1 --show-sample-count --show-sql > %t2.log
# RUN: FileCheck -check-prefix=IMPORT-B %s < %t2.log
#
# IMPORT-B: Added Runs : 1
# IMPORT-B: Added Samples : 1

# Check that reimporting the first test set properly reports as a duplicate.
# RUN: lnt import %t.install %S/Inputs/sample-a-small.plist \
# RUN:     --commit=1 --show-sample-count > %t3.log
# RUN: FileCheck -check-prefix=IMPORT-A-2 %s < %t3.log
#
# IMPORT-A-2: This submission is a duplicate of run 1

# Dump a copy of the database, so it will show up in logs.
# RUN: sqlite3 %t.install/data/lnt.db .dump

# Run consistency checks on the final database, to validate the import.
# RUN: python %s %t.install/data/lnt.db

import datetime, sys

import lnt.testing
from lnt.server.db import testsuite
from lnt.server.db import v4db

# Load the test database.
db = v4db.V4DB("sqlite:///%s" % sys.argv[1], echo=True)

# Get the status kinds, and validate the IDs align with the testing IDs.
pass_kind = db.query(db.StatusKind).filter_by(id = lnt.testing.PASS).one()
assert pass_kind.name == "PASS"
fail_kind = db.query(db.StatusKind).filter_by(id = lnt.testing.FAIL).one()
assert fail_kind.name == "FAIL"
xfail_kind = db.query(db.StatusKind).filter_by(id = lnt.testing.XFAIL).one()
assert xfail_kind.name == "XFAIL"

# Load the imported test suite.
ts = db.testsuite['nt']

# Validate the machine.
machines = list(ts.query(ts.Machine))
assert len(machines) == 1
machine = machines[0]
assert machine.name == 'LNT SAMPLE MACHINE'
assert machine.hardware == "x86_64"
assert machine.os == "SAMPLE OS"
parameters = machine.parameters
assert len(parameters) == 1
assert parameters['extrakey'] == u'extravalue'

# Validate the tests.
tests = list(ts.query(ts.Test))
assert len(tests) == 1
test = tests[0]
assert tests[0].name == 'sampletest'

# Validate the orders.
orders = list(ts.query(ts.Order).order_by(ts.Order.ordinal))
assert len(orders) == 2
order_a,order_b = orders
assert order_a.ordinal == 0
assert order_a.llvm_project_revision == u'% 7d' % 1
assert order_b.ordinal == 1
assert order_b.llvm_project_revision == u'% 7d' % 2

# Validate the runs.
runs = list(ts.query(ts.Run))
assert len(runs) == 2
run_a,run_b = runs
assert run_a.machine is machine
assert run_b.machine is machine
assert run_a.order is order_a
assert run_b.order is order_b
# FIXME: Set imported_from correctly.
assert run_a.imported_from is None
assert run_b.imported_from is None
assert run_a.start_time == datetime.datetime(2009, 11, 17, 2, 12, 25)
assert run_a.end_time == datetime.datetime(2009, 11, 17, 3, 44, 48)
assert not run_a.parameters
assert not run_b.parameters

# Validate the samples.
samples = list(ts.query(ts.Sample))
assert len(samples) == 2
sample_a,sample_b = samples
assert sample_a.run is run_a
assert sample_b.run is run_b
assert sample_a.test is test
assert sample_b.test is test
assert sample_a.compile_time == 0.019
assert sample_a.compile_status == lnt.testing.PASS
assert sample_a.execution_time == 0.3
assert sample_a.execution_status == lnt.testing.PASS
assert sample_b.compile_time == 0.022
assert sample_b.compile_status == lnt.testing.PASS
assert sample_b.execution_time == 0.32
assert sample_b.execution_status == lnt.testing.PASS

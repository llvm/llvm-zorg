# Check the model bindings for test suite instances.
#
# RUN: rm -f %t.db
# RUN: python %s %t.db

import datetime

from lnt.server.db import testsuite
from lnt.server.db import v4db

# Create an in memory database.
db = v4db.V4DB("sqlite:///:memory:", echo=True)

# Create a new TestSuite.
ts = testsuite.TestSuite("nt", "NT")

# Define the default sample types.
real_sample_type = testsuite.SampleType("Real")
status_sample_type = testsuite.SampleType("Status")

# Add reasonable definitions for the machine, run, order, and sample fields.
ts.machine_fields.append(testsuite.MachineField("uname", "uname"))
ts.order_fields.append(testsuite.OrderField("llvm_revision", "llvm_revision",
                                            1))
ts.run_fields.append(testsuite.RunField("arch", "ARCH"))
ts.sample_fields.append(testsuite.SampleField("value", real_sample_type,
                                              ".value"))
ts.sample_fields.append(testsuite.SampleField("status", status_sample_type,
                                              ".value.status"))
db.add(ts)

db.commit()

# Get the test suite wrapper.
ts_db = db.testsuite['nt']

# Check that we can construct and access all of the primary fields for the test
# suite database objects.

# Create the objects.
start_time = datetime.datetime.utcnow()
end_time = datetime.datetime.utcnow()

machine = ts_db.Machine("test-machine")
machine.uname = "test-uname"
order = ts_db.Order()
order.llvm_revision = "test-revision"
run = ts_db.Run(machine, order, start_time, end_time)
run.arch = "test-arch"
test = ts_db.Test("test-a")
sample = ts_db.Sample(run, test)
sample.value = 1.0

# Add and commit.
ts_db.add(machine)
ts_db.add(order)
ts_db.add(run)
ts_db.add(test)
ts_db.add(sample)
ts_db.commit()
del machine, order, run, test, sample

# Fetch the added objects.
machines = ts_db.query(ts_db.Machine).all()
assert len(machines) == 1
machine = machines[0]

orders = ts_db.query(ts_db.Order).all()
assert len(orders) == 1
order = orders[0]

runs = ts_db.query(ts_db.Run).all()
assert len(runs) == 1
run = runs[0]

tests = ts_db.query(ts_db.Test).all()
assert len(tests) == 1
test = tests[0]

samples = ts_db.query(ts_db.Sample).all()
assert len(samples) == 1
sample = samples[0]

# Audit the various fields.
assert machine.name == "test-machine"
assert machine.uname == "test-uname"

assert order.next_order_id is None
assert order.previous_order_id is None
assert order.llvm_revision == "test-revision"

assert run.machine is machine
assert run.order is order
assert run.start_time == start_time
assert run.end_time == end_time
assert run.arch == "test-arch"

assert test.name == "test-a"

assert sample.run is run
assert sample.test is test
assert sample.value == 1.0

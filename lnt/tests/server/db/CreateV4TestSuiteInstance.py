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
ts = testsuite.TestSuite("nt", "NT", 0)
db.add(ts)

db.commit()

# Get the test suite wrapper.
ts_db = db.testsuite['nt']

# Check that we can construct and access all of the primary fields for the test
# suite database objects.

# Create the objects.
start_time = datetime.datetime.utcnow()
end_time = datetime.datetime.utcnow()

machine = ts_db.Machine("test-machine", 1)
order = ts_db.Order()
run = ts_db.Run(machine, order, start_time, end_time)
test = ts_db.Test("test-a")
sample = ts_db.Sample(run, test, 1.0)

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
assert machine.number == 1

assert run.machine is machine
assert run.order is order
assert run.start_time == start_time
assert run.end_time == end_time

assert test.name == "test-a"

assert sample.run is run
assert sample.test is test
assert sample.value == 1.0

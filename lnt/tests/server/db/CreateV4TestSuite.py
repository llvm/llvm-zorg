# This test just checks that we can construct and manipulate the test suite
# model itself. The heavy lifting of constructing a test suite's databases,
# etc. is checked in CreateV4TestSuiteInstance.
#
# RUN: rm -f %t.db
# RUN: python %s %t.db

import sys
from lnt.server.db import testsuite
from lnt.server.db import v4db

# Create an in memory database.
db = v4db.V4DB("sqlite:///:memory:", echo=True)

# Create a new TestSuite.
ts = testsuite.TestSuite("nt", "NT")
db.add(ts)

db.commit()

test_suites = list(db.query(testsuite.TestSuite))
assert len(test_suites) == 1
ts = test_suites[0]

assert ts.name == "nt"
assert ts.db_key_name == "NT"
assert len(ts.machine_fields) == 0
assert len(ts.order_fields) == 0
assert len(ts.run_fields) == 0

# Add a field of each type.
ts.machine_fields.append(testsuite.MachineField("uname", "uname"))
ts.order_fields.append(testsuite.OrderField("llvm", "llvm", 0))
ts.run_fields.append(testsuite.RunField("arch", "ARCH"))
db.commit()

ts = db.query(testsuite.TestSuite).first()
assert len(ts.machine_fields) == 1
assert len(ts.order_fields) == 1
assert len(ts.run_fields) == 1
assert ts.machine_fields[0].name == "uname"
assert ts.order_fields[0].name == "llvm"
assert ts.run_fields[0].name == "arch"
assert ts.machine_fields[0].test_suite is ts
assert ts.order_fields[0].test_suite is ts
assert ts.run_fields[0].test_suite is ts

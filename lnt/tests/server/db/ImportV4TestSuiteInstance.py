# Check the import process into a v4 test suite DB.
#
# We first construct a temporary LNT instance.
# RUN: rm -rf %t.install
# RUN: lnt create --use-v4 %t.install

# Import the first test set.
# RUNX: lnt import %t.install %S/Inputs/sample-a-small.plist \
# RUNX:     --commit=1 --show-sample-count | \
# RUNX:   FileCheck -check-prefix=IMPORT-A-1 %s
#
# IMPORT-A-1: Added Machines: 1
# IMPORT-A-1: Added Runs : 1
# IMPORT-A-1: Added Tests : 8
# IMPORT-A-1: Added Samples : 8

# Import the second test set.
# RUNX: lnt import %t.install %S/Inputs/sample-b-small.plist \
# RUNX:     --commit=1 --show-sample-count |\
# RUNX:   FileCheck -check-prefix=IMPORT-B %s
#
# IMPORT-B: Added Runs : 1
# IMPORT-B: Added Samples : 8

# Check that reimporting the first test set properly reports as a duplicate.
# RUNX: lnt import %t.install %S/Inputs/sample-a-small.plist \
# RUNX:     --commit=1 --show-sample-count | \
# RUNX:   FileCheck -check-prefix=IMPORT-A-2 %s
#
# IMPORT-A-2: This submission is a duplicate of run 1

# Run consistency checks on the final database, to validate the import.
# RUN: python %s %t.install/data/lnt.db

import datetime, sys

from lnt.server.db import testsuite
from lnt.server.db import v4db

# Load the test database.
db = v4db.V4DB("sqlite:///%s" % sys.argv[1], echo=True)

# Load the imported test suite.
ts = db.testsuite['nt']

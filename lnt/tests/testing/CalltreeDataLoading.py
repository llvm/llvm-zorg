# Check the model bindings for test suite instances.
#
# RUN: rm -f %t.db
# RUN: python %s %S/Inputs/test-input-01.out

import sys

from lnt.testing.util import valgrind

data = valgrind.CalltreeData.frompath(sys.argv[1])
print data

assert data.command == 'true'
assert tuple(data.events) == ('Ir', 'I1mr', 'ILmr', 'Dr', 'D1mr', 'DLmr',
                              'Dw', 'D1mw', 'DLmw',)

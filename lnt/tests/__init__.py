import os
from lit import lit

def test_all():
    return lit.load_test_suite([os.path.dirname(__file__)])

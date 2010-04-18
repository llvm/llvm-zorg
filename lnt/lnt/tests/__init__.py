"""
Access to built-in tests.
"""

# FIXME: There are better ways to do this, no doubt. We also would like this to
# be extensible outside of the installation. Lookup how 'nose' handles this.

known_tests = set(['nt'])

def get_test_names():
    """get_test_names() -> list

    Return the list of known built-in test names.
    """

    return known_tests

def get_test_instance(name):
    """get_test_instance(name) -> lnt.test.BuiltinTest

    Return an instance of the named test.
    """

    if name not in known_tests:
        raise KeyError,name

    module = getattr(__import__('lnt.tests.%s' % name, level=0).tests,
                     name)
    return module.create_instance()

def get_test_description(name):
    """get_test_description(name) -> str

    Return the description of the given test.
    """

    return get_test_instance(name).describe()

__all__ = ['get_test_names', 'get_test_instance', 'get_test_description']

import pytest




@pytest.fixture
def stubargs():
    class TestArgs(object):
        dependencies = ['./Dependencies0']
        command = 'verify'
    return TestArgs()
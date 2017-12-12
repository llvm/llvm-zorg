# COPYRIGHT LINE: FIXME

"""
dbsign.result

result classes for debugsign
"""

from __future__ import print_function

import dbsign.logger as logger


log = logger.get_logger(__name__)


#
# Result class
#

class Result(object):
    def __init__(self, value):  # type: () -> ()
        self._checked = False
        self._value = value

    def __del__(self):  # type: () -> ()
        assert self._checked

    def __nonzero__(self):  # type: () -> bool
        raise NotImplementedError("{} does not support boolean evaluation".
                                  format(self.__class__.__name__))

    def __repr__(self):  # type: () -> str
        return "{0.__class__.__name__}({0._value!r})".format(self)

    @property
    def checked(self):  # type: () -> bool
        return self._checked

    @property
    def value(self):  # type: () -> str
        self._checked = True
        return self._value

    def renew(self):  # type: () -> Result
        self._checked = False
        return self


class Failure(Result):
    def __nonzero__(self):  # type: () -> bool
        self._checked = True
        return False


class Success(Result):
    def __nonzero__(self):  # type: () -> bool
        self._checked = True
        return True

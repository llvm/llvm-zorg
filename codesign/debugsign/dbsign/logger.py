# COPYRIGHT LINE: FIXME

"""
dbsign.logger

logging configuration for debugsign
"""


from __future__ import print_function

import logging
import os


DATE_FORMAT = "%H:%M:%S"
LOG_FORMAT = "%(asctime)s %(name)13s:%(lineno)-4s %(levelname)7s %(message)s"
BASE_LOGLEVEL = logging.WARNING
LOGLEVEL = os.getenv('DEBUGSIGN_LOGLEVEL', BASE_LOGLEVEL)

logging.basicConfig(format=LOG_FORMAT,
                    datefmt=DATE_FORMAT,
                    level=LOGLEVEL)

_root = logging.getLogger()
log = logging.getLogger(__name__)


def get_logger(name):  # type: (str) -> logging.Logger
    log.debug("Fetching logger for '%s'", name)
    return logging.getLogger(name)


def set_level(level):  # type: (int) -> int
    # must be done on root logger or it won't propagage to other loggers
    _root.setLevel(level)
    return _root.getEffectiveLevel()


def normalize(level):  # type: (int) -> int
    if level < logging.DEBUG:
        return logging.DEBUG
    if level > logging.CRITICAL:
        return logging.CRITICAL
    return level

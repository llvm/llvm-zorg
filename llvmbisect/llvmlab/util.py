import ConfigParser
import datetime
import inspect
import os
import sys
import traceback

__all__ = []

def _write_message(kind, message):
    # Get the file/line where this message was generated.
    f = inspect.currentframe()
    # Step out of _write_message, and then out of wrapper.
    f = f.f_back.f_back
    file,line,_,_,_ = inspect.getframeinfo(f)
    location = '%s:%d' % (os.path.basename(file), line)

    print >>sys.stderr, '%s: %s: %s' % (location, kind, message)

note = lambda message: _write_message('note', message)
warning = lambda message: _write_message('warning', message)
error = lambda message: _write_message('error', message)
fatal = lambda message: (_write_message('fatal error', message), sys.exit(1))


def sorted(l, **kwargs):
    l = list(l)
    l.sort(**kwargs)
    return l

def list_split(list, item):
    parts = []
    while item in list:
        index = list.index(item)
        parts.append(list[:index])
        list = list[index+1:]
    parts.append(list)
    return parts

def pairs(l):
    return zip(l, l[1:])

###

class EnumVal(object):
    def __init__(self, enum, name, value):
        self.enum = enum
        self.name = name
        self.value = value

    def __repr__(self):
        return '%s.%s' % (self.enum._name, self.name)

class Enum(object):
    def __init__(self, name, **kwargs):
        self._name = name
        self.__items = dict((name, EnumVal(self, name, value))
                            for name,value in kwargs.items())
        self.__reverse_map = dict((e.value,e.name)
                                  for e in self.__items.values())
        self.__dict__.update(self.__items)

    def get_value(self, name):
        return self.__items.get(name)

    def get_name(self, value):
        return self.__reverse_map.get(value)

    def get_by_value(self, value):
        return self.__items.get(self.__reverse_map.get(value))

    def contains(self, item):
        if not isinstance(item, EnumVal):
            return False
        return item.enum == self

class multidict:
    def __init__(self, elts=()):
        self.data = {}
        for key,value in elts:
            self[key] = value

    def __contains__(self, item):
        return item in self.data
    def __getitem__(self, item):
        return self.data[item]
    def __setitem__(self, key, value):
        if key in self.data:
            self.data[key].append(value)
        else:
            self.data[key] = [value]
    def items(self):
        return self.data.items()
    def values(self):
        return self.data.values()
    def keys(self):
        return self.data.keys()
    def __len__(self):
        return len(self.data)
    def get(self, key, default=None):
        return self.data.get(key, default)
    def todict(self):
        return self.data.copy()

###

class Preferences(object):
    def __init__(self, path):
        self.path = path
        self.config_path = os.path.join(path, "config")
        self.options = ConfigParser.RawConfigParser()

        # Load the config file, if present.
        if os.path.exists(self.config_path):
            self.options.read(self.config_path)

    def save(self):
        file = open(self.config_path, "w")
        try:
            self.options.write(file)
        finally:
            file.close()

    def get(self, section, option, default = None):
        if self.options.has_option(section, option):
            return self.options.get(section, option)
        else:
            return default

    def getboolean(self, section, option, default = None):
        if self.options.has_option(section, option):
            return self.options.getboolean(section, option)
        else:
            return default

    def setboolean(self, section, option, value):
        return self.options.set(section, option, str(value))

_prefs = None
def get_prefs():
    global _prefs
    if _prefs is None:
        _prefs = Preferences(os.path.expanduser("~/.llvmlab"))

        # Allow dynamic override of only_use_cache option.
        if os.environ.get("LLVMLAB_ONLY_USE_CACHE"):
            _prefs.setboolean("ci", "only_use_cache", True)

    return _prefs

###

import threading
import Queue

def detect_num_cpus():
    """
    Detects the number of CPUs on a system. Cribbed from pp.
    """
    # Linux, Unix and MacOS:
    if hasattr(os, "sysconf"):
        if os.sysconf_names.has_key("SC_NPROCESSORS_ONLN"):
            # Linux & Unix:
            ncpus = os.sysconf("SC_NPROCESSORS_ONLN")
            if isinstance(ncpus, int) and ncpus > 0:
                return ncpus
        else: # OSX:
            return int(os.popen2("sysctl -n hw.ncpu")[1].read())
    # Windows:
    if os.environ.has_key("NUMBER_OF_PROCESSORS"):
        ncpus = int(os.environ["NUMBER_OF_PROCESSORS"])
        if ncpus > 0:
            return ncpus
    return 1 # Default

def execute_task_on_threads(fn, iterable, num_threads = None):
    """execute_task_on_threads(fn, iterable) -> iterable

    Given a task function to run on an iterable list of work items, execute the
    task on each item in the list using some number of threads, and yield the
    results of the task function.

    If a task function throws an exception, the exception will be
    printed but not returned to the caller. Clients which wish to
    control exceptions should handle them inside the task function.
    """
    def push_work():
        for item in iterable:
            work_queue.put(item)

        # Push sentinels to cause workers to terminate.
        for i in range(num_threads):
            work_queue.put(_sentinel)
    def do_work():
        while True:
            # Read a work item.
            item = work_queue.get()

            # If we hit a sentinel, propogate it to the output queue and
            # terminate.
            if item is _sentinel:
                output_queue.put(_sentinel)
                break

            # Otherwise, execute the task and push to the output queue.
            try:
                output = (None, fn(item))
            except Exception, e:
                output = ('error', sys.exc_info())

            output_queue.put(output)

    # Compute the number of threads to use.
    if num_threads is None:
        num_threads = detect_num_cpus()

    # Create two queues, one for feeding items to the works and another for
    # consuming the output.
    work_queue = Queue.Queue()
    output_queue = Queue.Queue()

    # Create our unique sentinel object.
    _sentinel = []

    # Create and run thread to push items onto the work queue.
    threading.Thread(target=push_work).start()

    # Create and run the worker threads.
    for i in range(num_threads):
        t = threading.Thread(target=do_work)
        t.daemon = True
        t.start()

    # Read items from the output queue until all threads are finished.
    finished = 0
    while finished != num_threads:
        item = output_queue.get()

        # Check for termination marker.
        if item is _sentinel:
            finished += 1
            continue

        # Check for exceptions.
        if item[0] == 'error':
            _,(t,v,tb) = item
            traceback.print_exception(t, v, tb)
            continue

        assert item[0] is None
        yield item[1]

def timestamp():
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

###

import collections

class orderedset(object):
    def __init__(self, items=None):
        self.base = collections.OrderedDict()
        if items is not None:
            self.update(items)

    def update(self, items):
        for item in items:
            self.add(item)

    def add(self, item):
        self.base[item] = None

    def remove(self, item):
        del self.base[item]

    def __nonzero__(self):
        return bool(self.base)

    def __len__(self):
        return len(self.base)

    def __iter__(self):
        return iter(self.base)

    def __contains__(self, item):
        return item in self.base

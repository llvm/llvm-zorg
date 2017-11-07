import importlib
import logging
import pkgutil

# Load all repository handlers.
modules = dict()
_required_functions = ('verify', 'resolve_latest', 'get_artifact',
                       'repro_arg')
for importer, modname, ispkg in pkgutil.walk_packages(path=__path__,
                                                      prefix=__name__+'.'):
    module = importlib.import_module(modname)
    bad_module = False
    for function in _required_functions:
        if not hasattr(module, function):
            logging.error('Ignoring %s: No %s function' % function)
            bad_module = True
    if bad_module:
        continue
    assert modname.startswith('%s.' % __name__)
    shortname = modname[len('%s.' % __name__):]
    modules[shortname] = module

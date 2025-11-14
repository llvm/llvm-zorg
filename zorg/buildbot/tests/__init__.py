# -*- python -*-
# ex: set filetype=python:

import buildbot.process.properties

__all__ = []

DEFAULT_ENV = {'TERM': 'dumb', 'NINJA_STATUS': '%e [%u/%r/%f] '}

#Note:
# - this function currently supports only %(kw:*)s formatting for the Interpolates.
# - this function does not support the substitutions for arguments (such as '%(kw:arg:-)s' & etc).
# - this function does not support the other types of the renderables except Interpolate
#   (such as WithProperties and os on).
def partly_rendered(r):
    if isinstance(r, buildbot.process.properties.Interpolate):
        interpolations = {}
        for k, v in r.kwargs.items():
            interpolations[f"kw:{k}"] = v if v else ""
        return r.fmtstring % interpolations
    elif type(r) == str:
        return r

    return "unsupported_rendering"

def factory_has_num_steps(f, expected_num):
    assert f
    if len(f.steps) != expected_num:
        print(f"error: factory_has_num_steps: {len(f.steps)}, expected {expected_num}")
    return len(f.steps) == expected_num

def factory_has_step(f, name, hasarg=None, contains=None):
    assert f
    assert name

    result = False

    for s in f.steps:
        v = partly_rendered(s.kwargs.get("name"))
        if v == name:
            result = True
            # check that the step has that argument
            arg_value = None
            if hasarg:
                if not hasarg in s.kwargs:
                    print(f"error: step '{v}': missing expected step argument '{hasarg}'")
                    return False

                arg_value = s.kwargs.get(hasarg)

            # Check for contained content if requested.
            if arg_value and contains:
                if type(contains) == type(arg_value) == dict:
                    result = contains.items() <= arg_value.items()
                elif type(contains) == type(arg_value) == list:
                    result = contains <= arg_value
                elif type(contains) == type(arg_value):
                    result = contains == arg_value
                else:
                    print(f"error: step '{v}', argument '{hasarg}': unsupported type to compare, expected is '{type(contains)}', actual is '{type(arg_value)}'")
                    return False

                if not result:
                    print(f"error: step '{v}', argument '{hasarg}': expected\n\t{contains}\nactual:\n\t{arg_value}")

            return result

    print(f"error: missing expected step '{name}'")

    return False

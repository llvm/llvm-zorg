import colorsys
import math

def detectCPUs():
    """
    Detects the number of CPUs on a system. Cribbed from pp.
    """
    import os
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
        ncpus = int(os.environ["NUMBER_OF_PROCESSORS"]);
        if ncpus > 0:
            return ncpus
        return 1 # Default

def pairs(list):
    return zip(list[:-1],list[1:])

def safediv(a, b, default=None):
    try:
        return a/b
    except ZeroDivisionError:
        return default

def makeDarkColor(h):
    h = h%1.
    s = 0.95
    v = 0.8
    return colorsys.hsv_to_rgb(h,0.9+s*.1,v)

def makeMediumColor(h):
    h = h%1.
    s = .68
    v = 0.92
    return colorsys.hsv_to_rgb(h,s,v)

def makeLightColor(h):
    h = h%1.
    s = (0.5,0.4)[h>0.5 and h<0.8]
    v = 1.0
    return colorsys.hsv_to_rgb(h,s,v)

def makeBetterColor(h):
    h = math.cos(h*math.pi*.5)
    s = .8 + ((math.cos(h * math.pi*.5) + 1)*.5) * .2
    v = .88
    return colorsys.hsv_to_rgb(h,s,v)

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

def any_true(list, predicate):
    for i in list:
        if predicate(i):
            return True
    return False

def any_false(list, predicate):
    return any_true(list, lambda x: not predicate(x))

def all_true(list, predicate):
    return not any_false(list, predicate)

def all_false(list, predicate):
    return not any_true(list, predicate)

def geometric_mean(l):
    iPow = 1./len(l)
    return reduce(lambda a,b: a*b, [v**iPow for v in l])

def mean(l):
    return sum(l) / len(l)

def median(l):
    l = list(l)
    l.sort()
    N = len(l)
    return (l[(N - 1)//2] +
            l[(N + 0)//2]) * .5

def prependLines(prependStr, str):
    return ('\n'+prependStr).join(str.splitlines())

def pprint(object, useRepr=True):
    def recur(ob):
        return pprint(ob, useRepr)
    def wrapString(prefix, string, suffix):
        return '%s%s%s' % (prefix,
                           prependLines(' ' * len(prefix),
                                        string),
                           suffix)
    def pprintArgs(name, args):
        return wrapString(name + '(', ',\n'.join(map(recur,args)), ')')

    if isinstance(object, tuple):
        return wrapString('(', ',\n'.join(map(recur,object)),
                          [')',',)'][len(object) == 1])
    elif isinstance(object, list):
        return wrapString('[', ',\n'.join(map(recur,object)), ']')
    elif isinstance(object, set):
        return pprintArgs('set', list(object))
    elif isinstance(object, dict):
        elts = []
        for k,v in object.items():
            kr = recur(k)
            vr = recur(v)
            elts.append('%s : %s' % (kr,
                                     prependLines(' ' * (3 + len(kr.splitlines()[-1])),
                                                  vr)))
        return wrapString('{', ',\n'.join(elts), '}')
    else:
        if useRepr:
            return repr(object)
        return str(object)

def prefixAndPPrint(prefix, object, useRepr=True):
    return prefix + prependLines(' '*len(prefix), pprint(object, useRepr))

def clamp(v, minVal, maxVal):
    return min(max(v, minVal), maxVal)

def lerp(a,b,t):
    t_ = 1. - t
    return tuple([av*t_ + bv*t for av,bv in zip(a,b)])

class PctCell:
    # Color levels
    kNeutralColor = (1,1,1)
    kNegativeColor = (0,1,0)
    kPositiveColor = (1,0,0)
    # Invalid color
    kNANColor = (.86,.86,.86)
    kInvalidColor = (0,0,1)

    def __init__(self, value, reverse=False, precision=2, delta=False):
        if delta and isinstance(value, float):
            value -= 1
        self.value = value
        self.reverse = reverse
        self.precision = precision

    def getColor(self):
        v = self.value
        if not isinstance(v, float):
            return self.kNANColor

        # Clamp value.
        v = clamp(v, -1, 1)

        if self.reverse:
            v = -v
        if v < 0:
            c = self.kNegativeColor
        else:
            c = self.kPositiveColor
        t = abs(v)

        # Smooth mapping to put first 20% of change into 50% of range, although
        # really we should compensate for luma.
        t = math.sin((t ** .477) * math.pi * .5)
        return lerp(self.kNeutralColor, c, t)

    def getValue(self):
        if self.value is None:
            return ""
        if not isinstance(self.value, float):
            return self.value
        return '%.*f%%' % (self.precision, self.value*100)

    def render(self):
        r,g,b = [clamp(int(v*255), 0, 255)
                 for v in self.getColor()]
        res = '<td bgcolor="#%02x%02x%02x">%s</td>' % (r,g,b, self.getValue())
        return res

def sorted(l, *args, **kwargs):
    l = list(l)
    l.sort(*args, **kwargs)
    return l

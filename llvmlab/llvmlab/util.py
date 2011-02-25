import colorsys

__all__ = []

class simple_repr_mixin(object):
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,
                           ", ".join("%s=%r" % (k,v)
                                     for k,v in sorted(self.__dict__.items())))

def sorted(items):
    items = list(items)
    items.sort()
    return items

def make_dark_color(h):
    h = h % 1.
    s = 0.95
    v = 0.8
    return colorsys.hsv_to_rgb(h,0.9+s*.1,v)

class multidict(object):
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

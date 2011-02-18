import colorsys

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

__all__ = []

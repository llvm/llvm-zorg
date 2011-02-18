__all__ = []

def sorted(items):
    items = list(items)
    items.sort()
    return items

class simple_repr_mixin(object):
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,
                           ", ".join("%s=%r" % (k,v)
                                     for k,v in sorted(self.__dict__.items())))

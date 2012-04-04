import datetime

class TeeStream(object):
    """File-like object for writing to multiple output streams."""

    def __init__(self, a, b, noclose_b = False):
        self.a = a
        self.b = b
        self.noclose_b = noclose_b

    def __del__(self):
        del self.a
        if not self.noclose_b:
            del self.b

    def close(self):
        self.a.close()
        if not self.noclose_b:
            self.b.close()

    def write(self, value):
        self.a.write(value)
        self.b.write(value)

    def flush(self):
        self.a.flush()
        self.b.flush()

def timestamp():
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

import datetime

class TeeStream(object):
    """File-like object for writing to multiple output streams."""

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __del__(self):
        del self.a
        del self.b

    def close(self):
        self.a.close()
        self.b.close()

    def write(self, value):
        self.a.write(value)
        self.b.write(value)

    def flush(self):
        self.a.flush()
        self.b.flush()

def timestamp():
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

import time
from quixote.publish import Publisher

# FIXME: This is a bit of a hack.
class ExtPublisher(Publisher):
    def __init__(self, *args, **kwargs):
        Publisher.__init__(self, *args, **kwargs)
        self.create_time = time.time()

    def process_request(self, request):
        request.start_time = time.time()
        return Publisher.process_request(self, request)

class ThreadedPublisher(ExtPublisher):
    is_thread_safe = True

    def __init__ (self, root_namespace, *args, **kwargs):
        ExtPublisher.__init__(self, root_namespace, *args, **kwargs)
        self._request_dict = {}

    def _set_request(self, request):
        import thread
        self._request_dict[thread.get_ident()] = request

    def _clear_request(self):
        import thread
        try:
            del self._request_dict[thread.get_ident()]
        except KeyError:
            pass

    def get_request(self):
        import thread
        return self._request_dict.get(thread.get_ident())

def create_publisher(configPath, configData, threaded=False):
    import Config
    config = Config.Config.fromData(configPath, configData)

    from quixote import enable_ptl
    enable_ptl()

    from root import RootDirectory
    if threaded:
        publisher_class = ThreadedPublisher
    else:
        publisher_class = ExtPublisher
    return publisher_class(RootDirectory(config), display_exceptions='plain')

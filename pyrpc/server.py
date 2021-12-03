from socketserver import TCPServer, UnixStreamServer, ThreadingMixIn
import threading
import traceback
import time
import os

from . import handler as handlermod


class Server:
    synchronous = False
    address = None
    callee = None
    callee_type = None
    retype_exceptions = False 
    handler = 'Handler'

    nonblocking = False
    request_clean_interval = 60

    def __init__(self, address=None, **kwargs):
        self.address = address or self.address
        for k, v in kwargs.items():
            setattr(self, k, v)
        if self.callee is None: 
            if self.callee_type is not None:
                self.callee = self.callee_type()
            else:
                self.callee = self
        if self.nonblocking:
            self._id_request = {}
            threading.Thread(
                target=self.__clean_timedout_requests, daemon=True
            ).start()
            Handler = handlermod.NbHandler
        else:
            Handler = getattr(handlermod, self.handler)
        if isinstance(self.address, str):
            if os.path.exists(self.address):
                os.remove(self.address)
            if self.synchronous:
                self.__server = _SyncUnixServer(self, self.address, Handler)
            else:
                self.__server = _AsyncUnixServer(self, self.address, Handler)
        else:
            if self.synchronous:
                self.__server = _SyncTCPServer(self, self.address, Handler)
            else:
                self.__server = _AsyncTCPServer(self, self.address, Handler)

    def __clean_timedout_requests(self):
        while True:
            try:
                t = time.time()
                todel = []
                for id_, data in self._id_request.items():
                    if t>data['due_time']:
                        todel.append(id_)
                for id_ in todel:
                    try:
                        del self._id_request[id_]
                    except KeyError:
                        pass
            except Exception:
                traceback.print_exc()
            finally:
                time.sleep(self.request_clean_interval)

    def log_exception(self, exc, methodName, args, kwargs):
        log = self.get_exception_logging_func()
        if not log:
            return 
        prefix = '{}(args={!r}, kwargs={!r})'.format(
            methodName, args, kwargs
        )
        if len(prefix) > 60:
            prefix = prefix[:60] + '...)'
        suffix = ' -> {!r}'.format(exc)[:120-len(prefix)]
        log(prefix+suffix)

    def log_call(self, ret, methodName, args, kwargs):
        log = self.get_call_logging_func()
        if not log:
            return 
        prefix = '{}(args={!r}, kwargs={!r})'.format(
            methodName, args, kwargs
        )
        if len(prefix) > 60:
            prefix = prefix[:60] + '...)'
        suffix = ' -> {!r}'.format(ret)[:120-len(prefix)]
        log(prefix+suffix)

    def get_exception_logging_func(self):
        return None

    def get_call_logging_func(self):
        return None

    def start_in_thread(self):
        threading.Thread(target=self.start, daemon=True).start()

    def start(self):
        self.__server.serve_forever()

    def shutdown(self, delay=0.1):
        def func():
            time.sleep(delay)
            self.__server.shutdown()
            self.__server.socket.close()
            if isinstance(self.address, str) and os.path.exists(self.address):
                os.remove(self.address)
        threading.Thread(target=func, daemon=True).start()

    def shutdown_sync(self):
        self.__server.shutdown()
        self.__server.socket.close()
        if isinstance(self.address, str) and os.path.exists(self.address):
            os.remove(self.address)

    def connected(self):
        return True


class _ServerMixin:
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 100000

    def __init__(self, parent, address, Handler):
        self.parent = parent
        super().__init__(address, Handler)


class _SyncUnixServer(_ServerMixin, UnixStreamServer):pass
class _AsyncUnixServer(_ServerMixin, ThreadingMixIn, UnixStreamServer):pass
class _SyncTCPServer(_ServerMixin, TCPServer):pass
class _AsyncTCPServer(_ServerMixin, ThreadingMixIn, TCPServer):pass

import time

from .nbrelay import NbRelay
from .relay import Relay


class Client:
    address = None
    call_timeout = None 
    socket_connect_timeout = 10
    socket_send_timeout = 10
    socket_recv_timeout = 0.1 # can be 0.0 - non-blocking socket
                              # socket_recv_timeout+read_header_tick = 
                              # min responsiveness for call_timeout'n > 
                              # socket_header_recv_timeout
    read_header_tick = 0.01
    nolog_methods = None
    loop = None
    nb_fetch_timeout = 5
    nb_fetch_tick = 1

    def __init__(self, address=None, **kwargs):
        self.address = address or self.address
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getattr__(self, method_name):
        if method_name.startswith('co_'):
            return Corelay(self, method_name[3:], self.loop)
        elif method_name.startswith('nb_'):
            return NbRelay(self, method_name[3:])
        else:
            return Relay(self, method_name)

    def _handle_exception(self, callmsg, exc):
        method_name, args, kwargs, *_ = callmsg
        if isinstance(exc, KeyboardInterrupt):
            return 
        if  exc.traceback and method_name != 'connected':
            h = '{}: {}(args={!r}, kwargs={!r})'.format(
                type(self).__name__, method_name, args, kwargs
            )[:60] + '\n'
            msg = h + exc.traceback
            self.log_exception(msg)
        raise exc

    def log_exception(self, msg):
        log = self.get_exception_logging_func()
        if not log:
            return 
        log(msg)

    def log_call(self, callmsg, result):
        log = self.get_call_logging_func()
        if not log:
            return 
        method_name, *_ = callmsg
        if self.nolog_methods and method_name in self.nolog_methods:
            return
        if method_name == 'connected':
            return 
        msg = '    %s -> %s' % (method_name, repr(result)[:60])
        log(msg)

    def get_exception_logging_func(self):
        return None

    def get_call_logging_func(self):
        return None

    def connected(self, timeout=0.1):
        try:
            Relay(self, 'connected')(call_timeout=timeout)
        except Exception:
            return False
        return True

    def shutdown(self, **kwargs):
        Relay(self, 'shutdown')(**kwargs)
        # to ensure server shutdown upon return
        time.sleep(0.2) 

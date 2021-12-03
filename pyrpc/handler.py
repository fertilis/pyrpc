from socketserver import BaseRequestHandler
import traceback
import threading
import pickle


class Handler(BaseRequestHandler):
    '''Server protocol:
    req: len(4) + pickled callmsg
    resp: len(4) + pickled (ret, exc)
    
    If used with a sync server, the method should never stall.
    Otherwise the server will become unresponsive.
    '''
    def handle(self):
        ret, exc = None, None
        try:
            nbytes = int.from_bytes(self._read(4), 'big')
            body = self._read(nbytes)
            method_name, args, kwargs = pickle.loads(body)
        except Exception:
            return 
        try:
            method = getattr(self.server.parent.callee, method_name)
            ret = method(*args, **kwargs)
        except Exception as e:
            if self.server.parent.retype_exceptions:
                e2 = Exception(*e.args)
                e2.className = type(e).__name__
                e = e2
            e.traceback = traceback.format_exc()
            exc = e
        msg = pickle.dumps((ret, exc))
        try:
            msg = len(msg).to_bytes(4, 'big') + msg
            self.request.sendall(msg)
        except BrokenPipeError:
            pass
        if exc is not None:
            self.server.parent.log_exception(exc, method_name, args, kwargs)
        else:
            self.server.parent.log_call(ret, method_name, args, kwargs)

    def _read(self, n):
        received = 0
        chunks = []
        while received < n:
            try:
                chunk = self.request.recv(n-received)
            except InterruptedError:
                continue
            if not chunk:
                break
            chunks.append(chunk)
            received += len(chunk)
        data = b''.join(chunks)
        if len(data) != n:
            raise Exception()
        return data




class NbHandler(BaseRequestHandler):
    _read = Handler._read

    def handle(self):
        try:
            nbytes = int.from_bytes(self._read(4), 'big')
            body = self._read(nbytes)
            data = pickle.loads(body)
        except Exception as exc:
            self._send_output((None, Exception('read_error')))
            return 

        if isinstance(data, tuple):
            self._make_blocking_call(data)
            return 
        elif isinstance(data, dict):
            self._make_nonblocking_call(data)
        else:
            self._send_output((None, Exception('protocol_error')))

    def _make_blocking_call(self, data):
        method_name, args, kwargs = data
        ret, exc = None, None
        try:
            method = getattr(self.server.parent.callee, method_name)
            ret = method(*args, **kwargs)
        except Exception as e:
            if self.server.parent.retype_exceptions:
                e2 = Exception(*e.args)
                e2.className = type(e).__name__
                e = e2
            e.traceback = traceback.format_exc()
            exc = e

        self._send_output((ret, exc))

        if exc is not None:
            self.server.parent.log_exception(exc, method_name, args, kwargs)
        else:
            self.server.parent.log_call(ret, method_name, args, kwargs)

    def _make_nonblocking_call(self, data):
        if data['predicate'] == 'put':
            request = data
            self.server.parent._id_request[request['id']] = request
            _NbCall(self.server.parent, request).start()
            output = None
        else: # get
            request = self.server.parent._id_request[data['id']]
            if request['status'] == 1:
                ret = request['ret']
                exc = request['exc']
                output = ret, exc
                if exc is not None:
                    self.server.parent.log_exception(
                        exc, 
                        request['method_name'], 
                        request['args'], 
                        request['kwargs'],
                    )
                else:
                    self.server.parent.log_call(
                        ret, 
                        request['method_name'], 
                        request['args'], 
                        request['kwargs'],
                    )
            else:
                output = None

        self._send_output(output)

    def _send_output(self, output):
        try:
            msg = pickle.dumps(output)
            msg = len(msg).to_bytes(4, 'big') + msg
            self.request.sendall(msg)
        except BrokenPipeError:
            pass


class _NbCall(threading.Thread):
    daemon = True
    
    def __init__(self, parent, request):
        self._parent = parent
        self._request = request
        super().__init__()

    def run(self):
        ret, exc = None, None
        try:
            method_name = self._request['method_name']
            args = self._request['args']
            kwargs = self._request['kwargs']
            method = getattr(self._parent.callee, method_name)
            ret = method(*args, **kwargs)
        except Exception as e:
            if self._parent.retype_exceptions:
                e2 = Exception(*e.args)
                e2.className = type(e).__name__
                e = e2
            e.traceback = traceback.format_exc()
            exc = e
        self._request['ret'] = ret
        self._request['exc'] = exc
        self._request['status'] = 1

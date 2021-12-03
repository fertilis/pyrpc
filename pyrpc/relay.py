import traceback
import pickle
import socket
import time

from . import ut


class Relay:
    def __init__(self, client, method_name):
        self._client = client
        self._method_name = method_name

    def __call__(self, *args, **kwargs):
        kwargs = self._consume_kwargs(kwargs)
        callmsg = self._method_name, args, kwargs
        indata = callmsg
        try:
            output = self._make_call(indata)
            ret, exc = output
        except Exception as e:
            ret = None
            exc = e
        if exc is not None:
            self._client._handle_exception(callmsg, exc)
        else:
            self._client.log_call(callmsg, ret)
            return ret

    def _make_call(self, indata):
        try:
            due_time = time.time() + self._timeout
            indata = pickle.dumps(indata)
            indata = (len(indata)).to_bytes(4, 'big') + indata
            self._connect()
            self._sock.settimeout(self._socket_send_timeout)
            try:
                self._sock.sendall(indata)
            except Exception:
                raise ut.Timeout('send')
            self._sock.settimeout(self._socket_recv_timeout)
            nbytes = self._read_header()
            timeout = max(due_time-time.time(), self._socket_recv_timeout)
            self._sock.settimeout(timeout)
            try:
                body = self._read(nbytes)
            except Exception:
                raise ut.Timeout('read_body')
            output = pickle.loads(body)
            return output
        except Exception as e:
            if isinstance(e, (ut.Timeout, ut.NoSocket, ut.ProtocolError)):
                e.traceback = ''
            else:
                e.traceback = traceback.format_exc()
            raise e
        finally:
            if self._sock:
                self._sock.close()

    def _consume_kwargs(self, kwargs):
        to = self._timeout = (
            kwargs.pop('call_timeout', None) or 
            self._client.call_timeout or 
            86400
        )
        self._socket_connect_timeout = min(to, (
            kwargs.pop('socket_connect_timeout', None) or
            self._client.socket_connect_timeout
        ))
        self._socket_send_timeout = min(to, (
            kwargs.pop('socket_send_timeout', None) or
            self._client.socket_send_timeout
        ))
        self._socket_recv_timeout = min(to, (
            kwargs.pop('socket_recv_timeout', None) or
            self._client.socket_recv_timeout
        ))
        self._nolog = kwargs.pop('nolog', None)
        return kwargs

    def _connect(self):
        if isinstance(self._client.address, str):
            family = socket.AF_UNIX
        else:
            family = socket.AF_INET
        self._sock = socket.socket(family, socket.SOCK_STREAM)
        self._sock.settimeout(self._socket_connect_timeout)
        try:
            self._sock.connect(self._client.address)
        except Exception:
            raise ut.NoSocket(self._error_msg('connect'))

    def _read_header(self):
        if self._timeout <= self._socket_recv_timeout:
            try:
                header = self._read(4)
            except Exception:
                raise ut.Timeout(self._error_msg('read_header'))
        else:
            hasRead = False
            start = time.time()
            while time.time()-start < self._timeout:
                try:
                    header = self._read(4)
                    hasRead = True
                    break
                except Exception:
                    time.sleep(self._client.read_header_tick)
            if not hasRead:
                raise ut.Timeout(self._error_msg('read_header'))
        nbytes = int.from_bytes(header, 'big')
        if nbytes == 0:
            raise ut.ProtocolError(self._error_msg('read_header'))
        return nbytes

    def _read(self, n):
        received = 0
        chunks = []
        while received < n:
            try:
                chunk = self._sock.recv(n-received)
            except InterruptedError:
                continue
            if not chunk:
                break
            chunks.append(chunk)
            received += len(chunk)
        data = b''.join(chunks)
        if len(data) != n:
            raise ut.ProtocolError(self._error_msg('read'))
        return data

    def _error_msg(self, prefix=''):
        return '{} {}.{}()'.format(
            prefix, self._client.__class__.__name__, self._method_name
        )

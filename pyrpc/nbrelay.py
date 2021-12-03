import time
import uuid

from .relay import Relay
from . import ut


class NbRelay:
    _make_call = Relay._make_call
    _connect = Relay._connect
    _read_header = Relay._read_header
    _read = Relay._read
    _error_msg = Relay._error_msg

    def __init__(self, client, method_name):
        self._client = client
        self._method_name = method_name

    def __call__(self, *args, **kwargs):
        kwargs = self._consume_kwargs(kwargs)
        callmsg = self._method_name, args, kwargs

        request = {
            'id':uuid.uuid4(),
            'due_time':time.time()+self._general_timeout+max(10, 2*self._nb_fetch_tick),
            'predicate':'put',
            'status':0,
            'method_name':self._method_name,
            'args':args,
            'kwargs':kwargs,
            'ret':None,
            'exc':None
        }
        try:
            self._make_call(request)
        except Exception as exc:
            self._client._handle_exception(callmsg, exc)
            return 

        request2 = {
            'id':request['id'],
            'predicate':'get',
        }
        ret, exc = None, None
        output = None
        start_time = time.time()
        while time.time()-start_time < self._general_timeout:
            try:
                output = self._make_call(request2)
                if isinstance(output, tuple) and len(output) == 2:
                    break
            except Exception:
                pass
            finally:
                time.sleep(self._nb_fetch_tick)

        if output:
            ret, exc = output
        else:
            exc = ut.Timeout('nb')
            exc.traceback = ''

        if exc is not None:
            self._client._handle_exception(callmsg, exc)
        else:
            self._client.log_call(callmsg, ret)
            return ret

    def _consume_kwargs(self, kwargs):
        kwargs = Relay._consume_kwargs(self, kwargs)
        self._nb_fetch_tick = (
            kwargs.pop('nb_fetch_tick', None) or
            self._client.nb_fetch_tick
        )
        self._nb_fetch_timeout = (
            kwargs.pop('nb_fetch_timeout', None) or
            self._client.nb_fetch_timeout
        )
        self._general_timeout = self._timeout
        self._timeout = self._nb_fetch_timeout
        return kwargs

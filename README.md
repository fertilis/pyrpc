# Pyrpc

## Description

This library implements remote procedure calls between python processes.
It defines `Client` and `Server` classes.
`Client` can be used directly. `Server` is intended to be used as the base class
for subclasses defining remotely called methods.
Logging and timeouts can be controlled. Non-blocking calls with periodic polling
are possible.

## How to use

Make sure `pyrcp` module can be imported by python

Implement the server:

```python
from pyrpc import Server

class EchoServer(Server):
    address = ('', 50300) # can also be a unix socket (e. g. '/tmp/echo_server_socket')

    def echo(self, *args, **kwargs):
        return args, kwargs

if __name__ == '__main__':
    EchoServer().start()
```

Call it from the client:

```python
from pyrpc import Client

if __name__ == '__main__':
    client = Client(address=('', 50300))
    ret = client.echo(1, foo='foo')
    print(ret)
```

You can quickly try the library by running `tests/test.py`

## Features

+ This library tries to make remote calls work as if normal function calls are made.
So, if a remotely called method raises an exception the same exception will be raised
on the client side.

+ `Client` accepts some special keyword arguments that will not be passed to
the `Server`. These arguments affect communication. Most frequently used is `call_timeout`.
If a call is not completed in `call_timeout` seconds, `pyrpc.Timeout` exception will be raised.

+ Non-blocking server calls are possible. Non-blocking here means that the `Client` will
first send a call message to the `Server` without waiting for return and then it will
periodically poll the `Server` for the response. To make a non-blocking call, just add
"nb_" to the method name. The `Server`, though, must be instantiated with `nonblocking=True`

E.g. 

```python
import time

from pyrpc import Client, Server

def echo(args, **kwargs):
    time.sleep(10)
    return args, kwargs

server = Server(address='/tmp/echo_server_socket', nonblocking=True)
server.echo = echo
server.start_in_thread()

client = Client(address='/tmp/echo_server_socket')

# will poll every 500 ms and in 10 sec it will return
ret = client.nb_echo(1, foo='foo', nb_fetch_tick=0.5) 
print(ret)
```

In this example, `client.nb_echo()` by itself will block. But internally it will run a loop
to poll the server for the result of `echo()` call.

Non-blocking calls are especially useful, if calls can take a very long time, say 30 minutes.
If a blocking call is made, within 30 minutes connection may be lost. With a non-blocking call
each polling request is made with a separate connection.

Polling interval is controlled with `nb_fetch_tick` argument.
This argument will be stripped from kwargs and the server will not see it.

+ The `Server` can be started in the main thread with `Server.start()` or in a separate 
thread with `Server.start_in_thread()`

+ The `Server` accepts `callee` argument. If passed, function calls will be redirected
to the object pointed by the `callee`.

+ The `Server` cleans up responses not consumed by the `Client` (e. g. in case of network problems)

+ Every `Server` can be checked with `connected()` call. 

+ Logging on the server side can be setup by defining `get_call_logging_func()` and `get_call_logging_func()`
methods in the `Server` subclass.

+ Network addresses can be TCP or UNIX sockets.

## Copyright

Egor Kalinin

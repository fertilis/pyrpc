import asyncio
import time
import sys
import os

sys.path.append(os.path.abspath(__file__+'/../..'))

from procb import Client, Server


#address = '/tmp/foo'
address = '', 50300

#big = b'1'*16*45*1024
big = b'1'*500*1024**2

class S(Server):
    address = address
    synchronous = True

    def echo(self, *args, **kwargs):
        return args, kwargs

    def big(self):
        return big


s = S(nonblocking=True, request_clean_interval=1)
s.start_in_thread()

c = Client(address=address)
#ret = c.nb_echo(1, foo=2, call_timeout=5)
#ret = c.big(call_timeout=10)
#print(len(ret))

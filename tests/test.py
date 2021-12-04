#!/usr/bin/env python3
import time
import sys
import os

sys.path.append(os.path.abspath(__file__+'/../..'))

from pyrpc import Client, Server, Timeout

ADDRESS = ('', 50300)
#ADDRESS = '/tmp/foo'

class CustomServer(Server):
    address = ADDRESS
    synchronous = True
    big_array = b'1'*500*1024**2

    def echo(self, *args, **kwargs):
        return args, kwargs

    def get_big_array(self):
        return self.big_array


def main():
    server = CustomServer()
    server.start_in_thread()
    print('started server in a thread')
    client = Client(address=ADDRESS)
    start_time = time.time()
    ret = client.echo(1, foo=2)
    print('call to echo() returned: {} in {:.6f} sec'.format(
        ret, time.time()-start_time))
    try:
        ret = client.get_big_array(call_timeout=0.1)
    except Timeout:
        print('cannot get transfer big array in 100 ms')

    start_time = time.time()
    ret = client.get_big_array(call_timeout=10)
    print(
        ('call to get_big_array() returned a big array '
         'with length {} in {:.6f} sec').format(
        len(ret), time.time()-start_time))


if __name__ == '__main__':
    main()
         

import socket


class codes:
    error = b'\x00'
    send = b'\x01'
    sent = b'\x02'
    poll = b'\x03'
    polled = b'\x05'
    fetch = b'\x06'
    fetched = b'\x07'


def family(address):
    if isinstance(address, str):
        return socket.AF_UNIX
    else:
        return socket.AF_INET

def stream_socket(address):
    if isinstance(address, str):
        family = socket.AF_UNIX
    else:
        family = socket.AF_INET
    return socket.socket(family, socket.SOCK_STREAM)


def readSocket(sock, n):
    received = 0
    chunks = []
    while received < n:
        try:
            chunk = sock.recv(n-received)
        except InterruptedError:
            continue
        if not chunk:
            break
        chunks.append(chunk)
        received += len(chunk)
    return b''.join(chunks)


class NoSocket(Exception):pass
class ProtocolError(Exception):pass
class Timeout(socket.timeout):pass

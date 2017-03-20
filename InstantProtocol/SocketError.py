import socket
import random
import log

class SocketError(object):
    def __init__(self, domain, transport, rate):
        self._sock = socket.socket(domain, transport)
        self.error = rate

    def sendto(self, *p):
        test = random.randint(1,100)
        if test > self.error:
            return self._sock.sendto(*p)
        else :
            log.debug(">> Packet loss")

    def recvfrom(self, *p):
        return self._sock.recvfrom(*p)

    def close(self):
        return self._sock.close()

    def bind(self, addr):
        return self._sock.bind(addr)

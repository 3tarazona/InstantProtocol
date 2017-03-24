# SocketError.py
# Copyright (C) 2017
# Jesus Alberto Polo <jesus.pologarcia@imt-atlantique.net>
# Erika Tarazona <erika.tarazona@imt-atlantique.net>

import socket
import random
import logging as log

class SocketError(object):
    def __init__(self, domain, transport, rate):
        self.sock = socket.socket(domain, transport)
        self.error = rate

    def sendto(self, *p):
        test = random.randint(1,100)
        if test > self.error:
            return self.sock.sendto(*p)
        else :
            log.warn("Packet loss")

    def recvfrom(self, *p):
        return self.sock.recvfrom(*p)

    def close(self):
        return self.sock.close()

    def bind(self, addr):
        return self.sock.bind(addr)

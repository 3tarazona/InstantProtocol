# -*- coding: utf-8 -*
import sys
import socket

sock = None
address = ('', 1111)

if len(sys.argv) == 2:
    if (sys.argv[1] == 'udp'):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        sock.sendto('Message', address)

    elif (sys.argv[1] == 'tcp'):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # UDP
        sock.connect(address)
        sock.sendall('Message')
        data = sock.recv(1024)
        print data
        sock.close()

    else:
        raise Exception('Invalid argument')

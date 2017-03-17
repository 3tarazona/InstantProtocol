import socket
import sys
import struct

port = 1212

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
sock.bind(('localhost', port))
while True:
    data, address = sock.recvfrom(port)
    #struct.calcsize(FORMAT)
    sock.sendto(data, address)

sock.close()

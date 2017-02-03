# -*- coding: utf-8 -*
import socket
import sys

port = 1212

if (len(sys.argv) == 2):
    port = int(sys.argv[1])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
sock.bind(('localhost', port))
# Establish first connections
data, address1 = sock.recvfrom(1)
print 'Client1 lié:', address1
data, address2 = sock.recvfrom(1)
print 'Client1 lié:', address2
# Wait for connections
while (True):
    data, addr_rec = sock.recvfrom(1024)
    # chr(26) is EOF in ASCII
    if (data == chr(26)):
        sock.sendto(chr(26), address2)
        sock.close()
        break
    # From em to rec
    if (addr_rec == address1):
        print('{} -> {}: {}'.format(address1, address2, data))
        sock.sendto(data, address2)

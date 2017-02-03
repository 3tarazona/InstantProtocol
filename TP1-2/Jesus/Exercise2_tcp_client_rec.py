import socket
import sys

address = ('localhost', 1212)

if (len(sys.argv) == 3):
    address = (sys.argv[1], int(sys.argv[2]))

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCP
sock.bind(('localhost', 1202))
sock.connect(address)
# Get KeyboardInterrupt to close the socket
try:
    while (True):
        data = sock.recv(1024)
        if not data: break
        print data
except KeyboardInterrupt:
    sock.close()
    print

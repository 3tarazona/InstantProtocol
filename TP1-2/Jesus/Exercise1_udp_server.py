import socket
import sys

port = 1212

if (len(sys.argv) == 2):
    port = int(sys.argv[1])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
sock.bind(('localhost', port))
# Wait for connections
while (True):
    data = sock.recv(port)
    # chr(26) is EOF in ASCII
    if (data == chr(26)):
        sock.close()
        break
    print data

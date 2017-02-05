import socket
import sys

address = ('localhost', 1212)

if (len(sys.argv) == 3):
    address = (sys.argv[1], int(sys.argv[2]))

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCP
sock.connect(address)
mode = sock.recv(1)
print 'Client mode:', mode
# Get KeyboardInterrupt to close the socket
try:
    while (True):
        if (mode == '1'):
            message = raw_input('Ecrivez votre message: ')
            sock.send(message)
        elif (mode == '2'):
            data = sock.recv(1024)
            if not data: break
            print data
except KeyboardInterrupt:
    sock.close()
    print

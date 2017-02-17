import socket
import sys
import os

address = ('localhost', 1212)

if (len(sys.argv) == 3):
    address = (sys.argv[1], int(sys.argv[2]))

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP

# Get KeyboardInterrupt to close the socket
try:
    pid = os.fork()
    if (pid == 0):
        # Child process (recv from 1 and send to 2)
        while (True):
            data, _ = sock.recvfrom(1024)
            if not data: break
            print data
    else:
        # Parent process (recv from 2 and send to 1)
        while (True):
            message = raw_input() #raw_input('Ecrivez votre message: ')
            sock.sendto(message, address)

except KeyboardInterrupt:
    # chr(26) is EOF in ASCII
    sock.sendto(chr(26), address)
    sock.close()
    print

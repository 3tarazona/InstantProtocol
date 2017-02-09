# -*- coding: utf-8 -*
import socket
import sys
import os

port = 1212

if (len(sys.argv) == 2):
    port = int(sys.argv[1])

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCP
sock.bind(('localhost', port))
sock.listen(2) # 2 incoming connections
conn1, address1 = sock.accept()
print 'Client1 lié:', address1
conn2, address2 = sock.accept()
print 'Client2 lié:', address2

try:
    pid = os.fork()
    if (pid == 0):
        # Child process (recv from 1 and send to 2)
        while (True):
            data = conn1.recv(1024)
            if not data: break
            print('{} -> {}: {}'.format(address1, address2, data))
            conn2.send(data)
    else:
        # Parent process (recv from 2 and send to 1)
        while (True):
            data = conn2.recv(1024)
            if not data: break
            print('{} -> {}: {}'.format(address2, address1, data))
            conn1.send(data)

except KeyboardInterrupt:
    print('Closing ports')
    conn1.close()
    conn2.close()
    sock.close()

# -*- coding: utf-8 -*
import socket
import sys

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
    while (True):
        data = conn1.recv(1024)
        if not data: break
        print('{} -> {}: {}'.format(address1, address2, data))
        conn2.send(data)
except KeyboardInterrupt:
    print('Closing ports')
    conn1.close()
    conn2.close()
    sock.close()

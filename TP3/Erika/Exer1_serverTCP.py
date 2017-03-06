# -*- coding: utf-8 -*
import socket
import sys
import os

port = 1212

if (len(sys.argv) == 2):
    port = int(sys.argv[1])

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
sock.bind(('localhost', port))
sock.listen(25)  
conn1, add1 = sock.accept()
conn2, add2 = sock.accept()



pid = os.fork()
if (pid == 0):
        
    while (True):
        data = conn1.recv(1024)
        print(data)
        conn2.send(data)
else:
        
    while (True):
        data = conn2.recv(1024)
        print(data)
        conn1.send(data)


conn1.close()
conn2.close()
sock.close()

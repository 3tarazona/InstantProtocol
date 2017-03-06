import socket
import sys
import os

add = ('localhost', 1212)

if (len(sys.argv) == 3):
    add = (sys.argv[1], int(sys.argv[2]))

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
sock.connect(add)


pid = os.fork()
if (pid == 0):
    while (True):
        data = sock.recv(1024)
        print (data)
else:
    
    while (True):
        data = raw_input() 
        sock.send(data)
        

sock.close()
print

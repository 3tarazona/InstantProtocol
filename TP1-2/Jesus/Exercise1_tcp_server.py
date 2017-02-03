import socket
import sys

port = 1212

if (len(sys.argv) == 2):
    port = int(sys.argv[1])

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCP
sock.bind(('localhost', port))
sock.listen(1) # 1 incoming connection
conn, client_address = sock.accept()
print 'Client address:', client_address
while (True):
    data = conn.recv(1024)
    if not data: break
    print data
    #conn.sendall(data + ' from server')
conn.close()
sock.close()

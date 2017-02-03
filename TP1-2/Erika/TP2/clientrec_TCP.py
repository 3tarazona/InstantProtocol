import socket
import sys

address= ('127.0.0.1', 1212 )

if len(sys.argv)==3:
	address= (sys.argv[1], int(sys.argv[2]))
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('127.0.0.1', 1202))
s.connect(address)
while True:

	data = s.recv(65535)
	if not data: break
	print data
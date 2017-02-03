
import socket
import sys

port= 1212
if len(sys.argv)==2:
	port= int(sys.argv[1])
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

s.bind(('127.0.0.1', port))



while True:
	
	recv = s.recv(port)
	
	print(recv)
	if recv == 'q':
		s.close()
		break





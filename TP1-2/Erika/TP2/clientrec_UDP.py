import socket
import sys

address= ('127.0.0.1', 1212 )

if len(sys.argv)==3:
	address= (sys.argv[1], int(sys.argv[2]))
s= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

s.sendto('',address)
while True:
	
	recv= s.recv(65550)
	print(recv)
	if recv == 'q':
		
		s.close()

		break




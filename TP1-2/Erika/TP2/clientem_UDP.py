import socket
import sys

address= ('127.0.0.1', 1212 )

if len(sys.argv)==3:
	address= (sys.argv[1], int(sys.argv[2]))
s= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

s.sendto('',address)
while True:
	string= raw_input('Entrez une phrase: ')
	s.sendto(string,address)
	if string == 'q':
		break

		


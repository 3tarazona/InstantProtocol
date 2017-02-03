import socket
import sys

port= 1212
if len(sys.argv)==2:
	port= int(sys.argv[1])
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

s.bind(('127.0.0.1', port))

(recv, add1) = s.recvfrom(1024)
print(recv, add1)

(recv, add2)= s.recvfrom(1024)
print(recv, add2)

while True:
	
	(data, add) = s.recvfrom(1024)
	if add == add1:
		s.sendto(data, add2)
		print(data)
	if data == 'q':
		s.sendto('q', add2)
		s.close()
		break
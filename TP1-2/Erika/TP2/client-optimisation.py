import socket
import sys

address= ('127.0.0.1', 1212 )

if len(sys.argv)==3:
	address= (sys.argv[1], int(sys.argv[2]))
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#s.bind(('127.0.0.1', 1201))
s.connect(address)

string = s.recv(65535)
print string

if string == '1':

	while True:
		string= raw_input('Entrez une phrase')
		s.send(string)

elif string == '2':
	print "Listener"

	while True:

		data = s.recv(65535)
		
		if not data: break
		print data
#print(s.recv(65535))
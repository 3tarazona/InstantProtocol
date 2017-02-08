import socket
import sys

port= 1212

if len(sys.argv)==2:
	print 'ddd'
	port= int(sys.argv[1])

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.bind(('127.0.0.1', port))

s.listen(2)

conn1, addr1 = s.accept()
print(addr1, 'connected')
conn2, addr2 = s.accept()
print(addr2, 'connected')

conn1.send('1')
conn2.send('2')

while True:

	data = conn1.recv(65535)
	if not data: break
	print data
	conn2.send(data)

#s.close()
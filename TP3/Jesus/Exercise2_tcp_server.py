# -*- coding: utf-8 -*
import socket
import sys
import os
import select

port = 1212

if (len(sys.argv) == 2):
    port = int(sys.argv[1])

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCP
server.bind(('localhost', port))
server.listen(2) # 2 incoming connections
inputs = [ server ]

try:
    while (True):
        readable, _, _ = select.select(inputs, [], [])
        # Iterate over the readable descriptors
        for source in readable:
            # If the server is ready for writing (someone wants to connect)
            if source is server:
                conn, address = server.accept()
                print 'Client lié:', address
                inputs.append(conn)
            else:
                try:
                    data = source.recv(1024)
                    if not data: break
                    # Send to all inputs but server and sender
                    for destination in inputs:
                        if destination is not server and destination is not source:
                            print('{} -> {}: {}'.format(source.getpeername(), destination.getpeername(), data))
                            destination.send(data)
                except:
                    print 'Client desconnected'
                    source.close()
                    inputs.remove(source)

except KeyboardInterrupt:
    print('Closing connections')
    for conn in inputs:
        if conn is not server:
            conn.close()
    server.close()

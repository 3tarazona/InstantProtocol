# -*- coding: utf-8 -*
import socket
import sys
import os
import select

port = 1212

if (len(sys.argv) == 2):
    port = int(sys.argv[1])

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
server.bind(('localhost', port))
inputs = [ server ] # Server will be the only one input (no connections)
clients = []

try:
    while (True):
        readable, _, _ = select.select(inputs, [], [])
        # Iterate over the readable descriptors (only the server...), does this function make sense?
        for source in readable:
            # if source is not server
            data, address = server.recvfrom(1024)
            # Client closes the communication
            if (data == chr(26)):
                if address in clients:
                    print 'Client removed:', address
                    clients.remove(address)
            else:
                if address not in clients:
                    print 'Client added:', address
                    clients.append(address)
                # Send to all clients but sender
                for destination in clients:
                    if destination != address:
                        print('{} -> {}: {}'.format(address, destination, data))
                        try:
                            server.sendto(data, destination)
                        except:
                            print 'Client disconnected'
                            clients.remove(destination)

except KeyboardInterrupt:
    print('Closing connections')
    server.close()

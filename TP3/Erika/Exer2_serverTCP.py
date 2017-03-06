# -*- coding: utf-8 -*
import socket
import sys
import os
import select
import Queue

port = 1212

if (len(sys.argv) == 2):
    port = int(sys.argv[1])

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCP
s.bind(('localhost', port))
s.listen(2) 
inputS = [ s ]
outputS = []



while inputS:  

    readable, writable, exceptional = select.select(inputS, [], [])
    
    for sock in readable:   
    
        if sock is s:
            conn, add = s.accept() 
            inputS.append(conn)
        
        else:
          
            data = sock.recv(1024)
            
            for destination in inputS:
                if destination is not s and destination is not sock
                    print(data)
                    destination.send(data)

            sock.close()
            inputS.remove(sock)



for conn in inputS:
    if conn is not s:
        conn.close()
s.close()

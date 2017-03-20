import socket
import sys
import os
import logging as log
import time
import select

# Temporal
execfile('InstantProtocol.py')
execfile('ClientSession.py')

class Client(object):
    SERVER_ID = 0x00

    def __init__(self, server_address=('localhost', 1313), buffer=socket.SO_RCVBUF):
        self.connected = False
        self.server_address = server_address
        self.username = None # asked later
        self.client_id = 0 # changed later
        self.group_id = 1 # public by default
        self.group_type = 0 # centralized by default (centralized = 0, decentralized = 1)
        self.user_list = None
        self.server_session = ClientSession(self, 'server', self.SERVER_ID, server_address)
        self.users_sessions = None # it stores others' sessions in decentralized mode
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        self.inputs = [ self.sock, sys.stdin ] # (inputs of select) socket reception and user input
        self.buffer = buffer

    # Execute chat
    def run(self):
        try:
            # 1. Connection (Set username and get unique Client ID from server)
            while True:
                username = raw_input('Choose a username: ')
                self.server_session.connection_request(username)
                data, _ = self.sock.recvfrom(self.buffer)
                message = InstantProtocolMessage(rawdata=data)

                if (message.type == ConnectionAccept.TYPE):
                    self.server_session.connection_accept(message) # connection accepted
                    self.server_session.user_list_request() # ask for user list
                    break
                elif (message.type == ConnectionReject.TYPE):
                    self.server_session.connection_reject(message)

            # 2. Main state
            while True:
                readable, _, _ = select.select(self.inputs, [], [])
                for source in readable:
                    if (source == self.sock):
                        data, _ = self.sock.recvfrom(self.buffer)
                        message = InstantProtocolMessage(rawdata=data)
                        if (message.type == UserListResponse.TYPE): self.server_session.user_list_response(message)
                        #elif (message.type == DataMessage.TYPE): self.ser
                        elif (message.type == UpdateList.TYPE): self.server_session.update_list(message)
                        elif (message.type == UpdateDisconnection.TYPE): self.server_session.update_disconnection(message)

                        log.debug(message)
                        #print 'Message received: {}'.format(message.options.payload)
                    elif (source == sys.stdin):
                        user_input = sys.stdin.readline()
                        # If input starts with '/' means that it's a command
                        if (user_input.startswith('/')):
                            arguments = user_input.split(' ')
                            if (arguments[0] == '/create_group'):
                                group_type = arguments[1]
                                raw_client_ids = arguments[2:]
                                if (raw_client_ids > 0):
                                    client_ids = list()
                                    [client_ids.append(int(i)) for i in raw_client_ids]
                                    log.debug(client_ids)
                                    message_send = InstantProtocolMessage(dictdata={'type': GroupCreationRequest.TYPE, 'sequence':0, 'ack':0,
                                                        'source_id': self.client_id, 'group_id': 0x00, 'options': {'type':group_type, 'client_ids': client_ids}})
                                else:
                                    print('Error: Client IDs are required to create a group')

                            # TODO... Problem
                            elif (arguments[0] == '/invite_group'):
                                if (self.group_id > 0):
                                    group_type = arguments[1]
                                    raw_client_ids = arguments[2:]
                                    if (raw_client_ids > 0):
                                        client_ids = list()
                                        [client_ids.append(int(i)) for i in raw_client_ids]
                                        print client_ids
                                        message_send = InstantProtocolMessage(dictdata={'type': GroupInvitationRequest.TYPE, 'sequence':0, 'ack':0,
                                                            'source_id': self.client_id, 'group_id': 0x00, 'options': {'type': group_type, 'client_ids': client_ids}})
                                        log.debug(message_send)
                                    else:
                                        print('Error: Client IDs are required to invite clients to a group')

                                else:
                                    print('Error: You are not in a private group')

                            elif (arguments[0] == '/exit'):
                                message_send = InstantProtocolMessage(dictdata={'type': DisconnectionRequest.TYPE, 'sequence':0, 'ack':0,
                                                    'source_id': self.client_id, 'group_id': 0x00})
                                self.sock.sendto(message_send.serialize(), self.server_address)
                                data, _ = self.sock.recvfrom(1024)

                            else:
                                # centralized mode
                                if (self.group_type == 0):
                                    self.server_session.send()

        except KeyboardInterrupt:
            log.info('Closing client...')
            # send DisconnectionRequest
            self.sock.close()
            sys.exit(0)

# Execution
if __name__ == '__main__':
    log.basicConfig(format='%(levelname)s: %(message)s', level=log.DEBUG)
    sys.exit(Client().run())

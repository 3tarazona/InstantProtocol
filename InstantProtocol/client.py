import socket
import sys
import os
import threading
import signal
import logging as log
import time

# Temporal
execfile('InstantProtocol.py')

class Client(object):
    def __init__(self, server_address=('localhost', 1313), buffer=1024):
        self.server_address = server_address
        self.username = None # asked later
        self.client_id = 0 # changed later
        self.group_id = 1 # public by default
        self.group_type = 0 # centralized by default (centralized = 0, decentralized = 1)
        self.user_list = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        self.buffer = buffer

    # Execute chat
    def run(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN) # Ignore Ctrl+C
        signal.signal(signal.SIGUSR1, self._close) # Signal to close main thread
        ## 1. Connection & User List
        self._initialize()
        # New thread for text input
        self.chatting_thread = threading.Thread(target=self._chatting)
        self.chatting_thread.start()
        # Main thread (this) will be waiting for messages from server or other users
        while True:
            data, _ = self.sock.recvfrom(1024)
            message = InstantProtocolMessage(rawdata=data)
            log.debug(message)
            print 'Message received: {}'.format(message.options.payload)

    ## Internal functions
    def _initialize(self):
        # 1. Set username and get unique Client ID from server
        while True:
            self.username = raw_input('Choose a username: ')
            conn_req = InstantProtocolMessage(
                dictdata={'type': ConnectionRequest.TYPE, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'username': self.username}})

            log.debug(conn_req)
            # Send request and wait for response (blocking)
            self.sock.sendto(conn_req.serialize(), self.server_address)
            data, _ = self.sock.recvfrom(1024)
            message = InstantProtocolMessage(rawdata=data)
            log.debug(message)

            if (message.type == ConnectionAccept.TYPE):
                self.client_id = message.options.client_id
                log.info('System: Logged in as {}'.format(self.username))
                ack_connection = InstantProtocolMessage(dictdata={'type': ConnectionAccept.TYPE, 'sequence':1, 'ack':1, 'source_id': self.client_id, 'group_id': self.group_id})
                self.sock.sendto(ack_connection.serialize(), self.server_address)
                break # successful! -> out of the loop!
            elif (message.type == ConnectionReject.TYPE):
                if (message.options.error == 0):
                    print('Error: Maximum number of user reached')
                else:
                    print('Error: Username already taken')
            else:
                raise InstantProtocolException('Unexpected message received')

        #time.sleep(1)
        ## 2. Obtain user list
        user_list_req = InstantProtocolMessage(dictdata={'type': UserListRequest.TYPE, 'sequence':0, 'ack':0, 'source_id': self.client_id, 'group_id': self.group_id})
        self.sock.sendto(user_list_req.serialize(), self.server_address)

        data, _ = self.sock.recvfrom(1024)
        message = InstantProtocolMessage(rawdata=data)
        log.debug(message)
        self.user_list = message.options.user_list
        ack_list = InstantProtocolMessage(dictdata={'type': UserListResponse.TYPE, 'sequence': message.sequence, 'ack':1, 'source_id': self.client_id, 'group_id': self.group_id})
        self.sock.sendto(ack_list.serialize(), self.server_address)
        # Connection done and list requested

    # Thread function (for reading user's input)
    def _chatting(self):
        log.debug('Client ID: {}'.format(self.client_id))
        while True:
            user_input = raw_input()
            if not user_input: continue
            # Command or messaging text
            message_send = None

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
                    os.kill(os.getpid(), signal.SIGUSR1) # Close main thread
                    return # Exit thread

                elif (arguments[0] == ''):
                    pass

                else:
                    print('Error: Command not found')

            else:
                message_send = InstantProtocolMessage(dictdata={'type': DataMessage.TYPE, 'sequence':0, 'ack':0,
                                    'source_id': self.client_id, 'group_id': self.group_id, 'options': {'data_length': len(user_input), 'payload': user_input}})
                log.debug('User input: {}'.format(user_input))


            # Send message to the server
            # Check if is data message and the group is decentralized
            if ((self.group_id > 1) and (self.group_type == 1)):
                pass
            else:
                self.sock.sendto(message_send.serialize(), self.server_address)
        # To be closed by the main thread

    # Handler to close main thread, signal SIGUSR1 (chat thread receives exit command from user)
    def _close(self, signum, _):
        log.info('Closing client...')
        #self.chatting_thread.shutdown = True
        self.sock.close()
        sys.exit(0)


# Execution
if __name__ == '__main__':
    log.basicConfig(format='%(levelname)s: %(message)s', level=log.DEBUG)
    sys.exit(Client().run())




"""

"""

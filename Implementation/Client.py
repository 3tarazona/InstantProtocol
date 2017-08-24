# Client.py
# Copyright (C) 2017
# Jesus Alberto Polo <jesus.pologarcia@imt-atlantique.net>
# Erika Tarazona <erika.tarazona@imt-atlantique.net>

import socket
import sys
import select
import logging as log

from InstantProtocol import *
from SocketError import *
from ClientSession import *

class Client(object):
    SERVER_ID = 0x00
    PUBLIC_GROUP_ID = 0x01
    STATE_NORMAL = 0
    STATE_PENDING_CONN = 1
    STATE_PENDING_DISC = 2
    STATE_WAIT_GROUP = 3 # Group Creation
    STATE_PENDING_INV = 4 # Group Invitation
    STATE_DISJOINT = 5
    STATE_DISCONNECTED = 6

    def __init__(self, server_address=('localhost', 1313), buffer=1024, loss_rate=5):
        self.server_address = server_address
        self.username = None # asked later
        self.client_id = 0 # changed later
        self.group_id = 1 # public by default
        self.decentralized = False # centralized by default
        self.state = self.STATE_PENDING_CONN
        self.user_list = list() # it stores all users' information (ClientInfo) -> small database
        self.server_session = ClientSessionServer(self, server_address)
        self.user_sessions = list() # it stores others' sessions in decentralized mode
        self.sock = SocketError(socket.AF_INET, socket.SOCK_DGRAM, loss_rate) # UDP with some packet loss
        self.inputs = [ self.sock.sock, sys.stdin ] # (inputs of select) socket reception and user input
        self.buffer = buffer

    # Execute chat
    def run(self):
        # 1. Connection (Set username and get unique Client ID from server)
        while (self.state == self.STATE_PENDING_CONN):
            try:
                username = raw_input('Choose a username: ')
                if (not username):
                    continue
                self.server_session.connection_request(username)
                # readable used because of its timer (otherwise it doesn't make sense for one UDP socket)
                readable, _, _ = select.select([ self.sock.sock ], [], [], 3) # wait 1 second
                if (not readable):
                    print('Server unreachable')
                    sys.exit(1) # error
                else:
                    data, _ = self.sock.recvfrom(self.buffer)
                    message = InstantProtocolMessage(rawdata=data)
                    if (message.type == ConnectionAccept.TYPE):
                        self.server_session.connection_accept(message) # connection accepted
                        self.server_session.user_list_request() # ask for user list
                        break # end of loop
                    elif (message.type == ConnectionReject.TYPE):
                        self.server_session.connection_reject(message)
            except KeyboardInterrupt: # Ctrl + C
                sys.exit(0)

        # 2. Chat & Group Management (general)
        while (self.state != self.STATE_DISCONNECTED): # when DisconnectionRequest ACK is received -> connected = False
            try:
                readable, _, _ = select.select(self.inputs, [], [])
                # Check again if the state is disconnected because we can stay locked inside the select function and a thread changes the state (in other context)
                if (self.state == self.STATE_DISCONNECTED):
                    break
                # Check the source and make decisions
                for source in readable:
                    # Reception (from socket)
                    if (source == self.sock.sock):
                        data, _ = self.sock.recvfrom(self.buffer)
                        message_recv = InstantProtocolMessage(rawdata=data)
                        log.debug(message_recv)

                        if (message_recv.ack == Acknowledgement.FLAG): # ACK
                            if (message_recv.source_id == self.SERVER_ID):
                                self.server_session.acknowledgement(message_recv)
                            else:
                                # Look for session in decentralized mode
                                for session in self.user_sessions:
                                    if (session.client_id == message_recv.source_id):
                                        session.acknowledgement(message_recv)
                                        break
                        elif (message_recv.type == ConnectionAccept.TYPE): # if ACK after ConnectionAccept has been lost
                            self.server_session.connection_accept(message)
                        elif (message_recv.type == UserListResponse.TYPE):
                            self.server_session.user_list_response(message_recv)
                        elif (message_recv.type == DataMessage.TYPE):
                            if (not self.decentralized):
                                self.server_session.data_message_reception(message_recv)
                            else:
                                # Look for session in decentralized mode
                                for session in self.user_sessions:
                                    if (session.client_id == message_recv.source_id):
                                        session.data_message_reception(message_recv)
                                        break
                        elif (message_recv.type == GroupCreationAccept.TYPE):
                            self.server_session.group_creation_accept(message_recv)
                        elif (message_recv.type == GroupCreationReject.TYPE):
                            self.server_session.group_creation_reject(message_recv)
                        elif (message_recv.type == GroupInvitationRequest.TYPE):
                            self.server_session.group_invitation_request_reception(message_recv)
                        elif (message_recv.type == GroupInvitationAccept.TYPE):
                            self.server_session.group_invitation_accept_reception(message_recv)
                        elif (message_recv.type == GroupInvitationReject.TYPE):
                            self.server_session.group_invitation_reject_reception(message_recv)
                        elif (message_recv.type == GroupDissolution.TYPE):
                            self.server_session.group_dissolution(message_recv)
                        elif (message_recv.type == UpdateList.TYPE):
                            self.server_session.update_list(message_recv)
                        elif (message_recv.type == UpdateDisconnection.TYPE):
                            self.server_session.update_disconnection(message_recv)

                        if (self.state == self.STATE_PENDING_INV):
                            print('\033[1mDo you want to join the {} group {}\033[0m? (yes or no)'.format(
                                'centralized' if (not self.server_session.temporal_group_type) else 'decentralized', self.server_session.temporal_group_id))

                    # Sending (from user's input)
                    elif (source == sys.stdin):
                        user_input = sys.stdin.readline().rstrip('\n') # read line and remove '\n'
                        # When invitation, we wait for user answer
                        if (self.state == self.STATE_PENDING_INV):
                            if ((user_input == 'yes') or (user_input == 'y')):
                                self.server_session.group_invitation_accept_send()
                            elif ((user_input == 'no') or (user_input == 'n')):
                                self.server_session.group_invitation_reject_send()
                            continue
                        # If input starts with '/' -> it's a command
                        if (user_input.startswith('/')):
                            arguments = user_input.split(' ')
                            if (arguments[0] == '/create_group'):
                                # '/create_group 0 erika jesus' (<command> <type> [<client usernames>])
                                try:
                                    group_type = int(arguments[1])
                                except ValueError:
                                    print('\033[1mCannot create group from the given arguments\033[0m')
                                    continue
                                self.server_session.group_creation_request(group_type, arguments[2:])
                            elif (arguments[0] == '/invite_group'):
                                self.server_session.group_invitation_request_send(arguments[1:])
                            elif (arguments[0] == '/disjoint'):
                                self.server_session.group_disjoint_request()
                            elif (arguments[0] == '/exit'):
                                self.server_session.disconnection_request()
                            elif (arguments[0] == '/list'):
                                print('\033[1muser\t\tgroup\033[0m')
                                for user in self.user_list:
                                    print('{0:8}\t{1}'.format(user.username, user.group_id))
                            elif (arguments[0] == '/help'):
                                print('\033[1mCommands\n\033[0m/create_group <0|1> <usernames> (where 0 is centralized and 1 decentralized)\n/invite_group <username>\n/disjoint\n/exit\n/list')
                        else:
                            if (user_input): # ignore if user press enter
                                # Centralized mode
                                if (not self.decentralized):
                                    self.server_session.data_message_send(user_input)
                                else:
                                    for user in self.user_sessions:
                                        user.data_message_send(user_input)

            except KeyboardInterrupt: # Ctrl + C
                # Sending message to server asking for disconnection and wait for ACK as usual
                if (self.state != self.STATE_PENDING_DISC):
                    self.server_session.disconnection_request()
                continue

        if (self.state == self.STATE_DISCONNECTED):
            log.info('Closing client...')
            self.sock.close()

# Execution
if __name__ == '__main__':
    # Comment following line of code to disable log output
    #log.basicConfig(format='%(levelname)s: %(message)s', level=log.WARN) # DEBUG, INFO, WARN, CRITICAL
    sys.exit(Client(loss_rate=0.1).run())

# ClientSession.py
# Copyright (C) 2017
# Jesus Alberto Polo <jesus.pologarcia@imt-atlantique.net>
# Erika Tarazona <erika.tarazona@imt-atlantique.net>

import threading
import logging as log

from InstantProtocol import *

# Entry for each user (list as small database)
class ClientInfo(object):
    def __init__(self, username, client_id, group_id, address):
        self.username = username
        self.client_id = client_id
        self.group_id = group_id
        self.address = address

    def __repr__(self):
        return 'ClientInfo(username={}, client_id={}, group_id={}, address={})'.format(self.username, self.client_id, self.group_id, self.address)

# Exception when a Session is not found
class SessionNotFound(Exception):
    pass

# Base object for session used for server (always) and other clients (decentralized mode)
class ClientSession(object):
    NO_GROUP_ID = 0x00
    STATE_IDLE = 0 # ready to send
    STATE_ACK = 1 # waiting for ack
    RESEND_TIMER = 0.5 # resend in 500ms

    def __init__(self, client, address):
        self.client = client
        self.address = address
        self.state = self.STATE_IDLE
        self.last_seq_sent = 0
        self.last_seq_recv = 0
        self.message_queue = list()
        self.timer = None

    # At least, this methods have to be implemented
    #def data_message_send(self, text)
    #def data_message_reception(self, message)
    #def acknowledgement(self, message)
    #def _send(self, dictdata, retry=1)

# Class for sessions used by server (always used), it implements its own functions
class ClientSessionServer(ClientSession):
    INVITATION_TIMER = 15 # invitation will be available for 15 seconds

    def __init__(self, client, address):
        super(ClientSessionServer,self).__init__(client, address)
        self.temporal_group_id = 0x00
        self.temporal_group_type = 0x00
        self.invitation_timer = None

    def __repr__(self):
        return 'ClientSessionServer(client={}, address={}, last_seq_sent={}, last_seq_recv={}, state={}, message_queue={}, timer={}, temporal_group_id={}, temporal_group_type={}, invitation_timer={})'.format(
            self.client, self.address, self.last_seq_sent, self.last_seq_recv, self.state, self.message_queue, self.timer, self.temporal_group_id, self.temporal_group_type, self.invitation_timer)

    def connection_request(self, username):
        if (self.client.state == self.client.STATE_PENDING_CONN):
            self.client.username = ('{0: <8}'.format(username)).strip() # only 8 bytes
            log.info('[Connection Request] username={}'.format(username))
            self._send(dictdata={'type': ConnectionRequest.TYPE, 'ack': 0, 'source_id': 0x00, 'group_id': self.NO_GROUP_ID, 'options': {'username': username}})

    # only for server (id = 0x00)
    def connection_accept(self, message):
        if (self.client.state == self.client.STATE_PENDING_CONN):
            self.client.state = self.client.STATE_NORMAL
            self.client.client_id = message.options.client_id
            self.timer.cancel() # stop timer (implicit ACK)
            self.state = self.STATE_IDLE
            log.info('[Connection] username={}, id={}'.format(self.client.username, self.client.client_id))
            print('\033[1mLogged in as {}\033[0m'.format(self.client.username))
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID})

    # only for server (id = 0x00)
    def connection_reject(self, message):
        if (self.client.state == self.client.STATE_PENDING_CONN):
            self.timer.cancel() # stop timer (implicit ACK)
            self.state = self.STATE_IDLE
            if (message.options.error == 0):
                log.info('[Connection] (Failed -> maximum reached')
                print('\033[1mConnection failed -> maximum number of users reached\033[0m')
            elif (message.options.error == 1):
                log.info('[Connection] (Failed -> username already taken)')
                print('\033[1mConnection failed -> username already taken\033[0m')
            else:
                print('\033[1mConnection failed\033[0m')
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID})

    def user_list_request(self):
        log.info('[User List Request] username={}'.format(self.client.username))
        self._send(dictdata={'type': UserListRequest.TYPE, 'ack': 0, 'source_id': self.client.client_id, 'group_id': self.client.group_id})

    def user_list_response(self, message):
        if (message.sequence != self.last_seq_recv): # we always send an ACK even if the message is repeated (lost ACK)
            self.timer.cancel() # stop timer (implicit ACK)
            self.state = self.STATE_IDLE # response has implicit ACK
            # Create list (add also ourselves)
            for user in message.options.user_list:
                self.client.user_list.append(ClientInfo(user['username'], user['client_id'], user['group_id'], (user['ip_address'], user['port'])))
            log.info('[User List Response] list={}'.format(self.client.user_list))
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID})

    def data_message_send(self, text):
        log.info('[Data Message] (Send message) text={}'.format(text))
        self._send(dictdata={'type': DataMessage.TYPE, 'ack': 0, 'source_id': self.client.client_id, 'group_id': self.client.group_id, 'options': {'data_length': len(text), 'payload': text}})

    def data_message_reception(self, message):
        # Centralized mode (server_session handles this messages)
        if (message.sequence != self.last_seq_recv):
            log.info('[Data Message] (Receive message) text={}'.format(message.options.payload))
            for user in self.client.user_list:
                if (user.client_id == message.source_id):
                    print('\033[1m{}:\033[0m {}'.format(user.username, message.options.payload))
                    break
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID})

    def group_creation_request(self, group_type, raw_clients):
        # Create Group only when client is in Public Group
        if (self.client.state == self.client.STATE_NORMAL) and (self.client.group_id == self.client.PUBLIC_GROUP_ID):
            if ((len(raw_clients) > 0) and ((group_type == 0) or (group_type == 1))):
                client_ids = list()
                for user in self.client.user_list:
                    if ((user.username in raw_clients) and (user.username != self.client.username)):
                        client_ids.append(user.client_id)
                log.info('[Group Creation] (Request send) group_type={}, client_ids={}'.format(group_type, client_ids))
                self.client.state = self.client.STATE_WAIT_GROUP
                self._send(dictdata={'type': GroupCreationRequest.TYPE, 'ack': 0, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID, 'options': {'type': group_type, 'client_ids': client_ids}})
            else:
                print('\033[1mCannot create group from the given arguments\033[0m')
        else:
            print('\033[1mCannot create a group under your current situation\033[0m')

    def group_creation_accept(self, message):
        if (message.sequence != self.last_seq_recv):
            if (self.client.state == self.client.STATE_WAIT_GROUP):
                log.info('[Group Creation] (Accept receive) group_type={}, group_id={}'.format(message.options.type, message.options.group_id))
                self.client.state = self.client.STATE_NORMAL
                self.client.group_id = message.options.group_id
                self.client.decentralized = bool(message.options.type)
                # Update user in the list
                for user in self.client.user_list:
                    if (user.client_id == self.client.client_id):
                        user.group_id = message.options.group_id
                        break
                # Sessions in decentralized mode will be created based on UpdateList messages
                print('\033[1mChanging to group {} in {} mode\033[0m'.format(self.client.group_id, 'centralized' if (not self.client.decentralized) else 'decentralized'))
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID})

    def group_creation_reject(self, message):
        if (message.sequence != self.last_seq_recv):
            if (self.client.state == self.client.STATE_WAIT_GROUP):
                log.info('[Group Creation] (Reject receive)')
                self.client.state = self.client.STATE_NORMAL
                print('\033[1mGroup creation rejected\033[0m')
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID})

    def group_invitation_request_send(self, usernames):
        if (self.client.group_id != self.client.PUBLIC_GROUP_ID): # We can only invite to a private group
            log.info('[Group Invitation] (Resquest send) group_id={}, group_type={}, usernames={}'.format(self.client.group_id, int(self.client.decentralized), usernames))
            for user in self.client.user_list:
                if ((user.username in usernames) and (user.username != self.client.username)):
                    self._send(dictdata={'type': GroupInvitationRequest.TYPE, 'ack': 0, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID, 'options': {'type': int(self.client.decentralized), 'group_id': self.client.group_id, 'client_id': user.client_id}})
        else:
            print('Cannot invite users to public group')

    def group_invitation_request_reception(self, message):
        if (message.sequence != self.last_seq_recv):
            # Send ACK and after we'll send a reject if it isn't possible to invite
            if (self.client.state == self.client.STATE_NORMAL):
                log.info('[Group Invitation] (Request receive) group_type={}, group_id={}'.format(message.options.type, message.options.group_id))
                self.client.state = self.client.STATE_PENDING_INV
                self.temporal_group_id = message.options.group_id
                self.temporal_group_type = message.options.type
                self.invitation_timer = threading.Timer(self.INVITATION_TIMER, self._invitation_expired)
                self.invitation_timer.start()
            else:
                self._send(dictdata={'type': GroupInvitationReject.TYPE, 'ack': 0, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID, 'options': {'type': message.options.type, 'group_id': message.options.group_id, 'client_id': message.options.client_id}})
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID})

    def group_invitation_accept_send(self):
        if (self.client.state == self.client.STATE_PENDING_INV):
            log.info('[Group Invitation] (Accept send) group_type={}, group_id={}'.format(self.temporal_group_type, self.temporal_group_id))
            self.client.state = self.client.STATE_NORMAL
            self.invitation_timer.cancel()
            self.client.group_id = self.temporal_group_id
            self.client.decentralized = bool(self.temporal_group_type)
            self._send(dictdata={'type': GroupInvitationAccept.TYPE, 'ack': 0, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID, 'options': {'type': self.temporal_group_type, 'group_id': self.temporal_group_id, 'client_id': self.client.client_id}})
            self.temporal_group_id = self.temporal_group_type = 0
            print('\033[1mChanging to group {} in {} mode\033[0m'.format(self.client.group_id, 'centralized' if (not self.client.decentralized) else 'decentralized'))
            # Update user in the list
            for user in self.client.user_list:
                if (user.client_id == self.client.client_id):
                    user.group_id = self.client.group_id
                    break
            # Create sessions in decentralized mode
            if (self.client.decentralized):
                self.client.user_sessions = list() # empty list
                for user in self.client.user_list:
                    if ((user.group_id == self.client.group_id) and (user.client_id != self.client.client_id)):
                        log.debug('[Group Invitation Accept] (Session created in decentralized) username={}'.format(user.username))
                        self.client.user_sessions.append(ClientSessionClient(self.client, user.username, user.client_id, user.address))

    def group_invitation_accept_reception(self, message):
        if (message.sequence != self.last_seq_recv):
            # Changes in UpdateList
            log.info('[Group Invitation] (Accept receive) client_id={}'.format(message.source_id))
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID})

    def group_invitation_reject_send(self):
        if (self.client.state == self.client.STATE_PENDING_INV):
            log.info('[Group Invitation] (Reject send) group_type={}, group_id={}'.format(self.temporal_group_type, self.temporal_group_id))
            self.client.state = self.client.STATE_NORMAL
            self.invitation_timer.cancel()
            self._send(dictdata={'type': GroupInvitationReject.TYPE, 'ack': 0, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID, 'options': {'type': self.temporal_group_type, 'group_id': self.temporal_group_id, 'client_id': self.client.client_id}})
            self.temporal_group_id = self.temporal_group_type = 0

    def group_invitation_reject_reception(self, message):
        if (message.sequence != self.last_seq_recv):
            log.info('[Group Invitation] (Reject receive) client_id={}'.format(message.source_id))
            for user in self.client.user_list:
                if (user.client_id == message.source_id):
                    print('\033[1mInvitation rejected by {}\033[0m'.format(user.username))
                    break
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID})

    def group_disjoint_request(self):
        if (self.client.group_id != self.client.PUBLIC_GROUP_ID):
            log.info('[Group Disjoint] (Requested)')
            self.client.group_id = self.client.PUBLIC_GROUP_ID
            self.client.decentralized = False # centralized by default
            self.client.user_sessions = list() # empty list
            self._send(dictdata={'type': GroupDisjointRequest.TYPE, 'ack':0, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID})
            print('\033[1mYou have left the group\033[0m')
        else:
            print('\033[1mCannot disjoint from Public Group\033[0m')

    def group_dissolution(self, message):
        if (message.sequence != self.last_seq_recv):
            log.info('[Group Dissolution] (Obliged)')
            if (self.client.decentralized):
                self.client.user_sessions = list() # empty list
            self.client.group_id = self.client.PUBLIC_GROUP_ID
            self.client.decentralized = False # centralized by default
            print('\033[1mYou have left the group (you were alone)\033[0m')
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID})

    def update_list(self, message):
        if (message.sequence != self.last_seq_recv):
            for new_user in message.options.user_list:
                found = False
                for old_user in self.client.user_list:
                    if (old_user.client_id == new_user['client_id']):
                        if (old_user.group_id == self.client.group_id): # we were in the same group
                            print('\033[1m{} has left the group\033[0m'.format(old_user.username))
                            if (self.client.decentralized):
                                for session in self.client.user_sessions:
                                    if (session.client_id == old_user.client_id):
                                        self.client.user_sessions.remove(session)
                        old_user.group_id = new_user['group_id'] # in this protocol, only group_id can change (other values are fixed)
                        # Are we in the same group now?
                        if (new_user['group_id'] == self.client.group_id):
                            print('\033[1m{} has joined the group\033[0m'.format(old_user.username))
                            if (self.client.decentralized):
                                self.client.user_sessions.append(ClientSessionClient(self.client, new_user['username'], new_user['client_id'], (new_user['ip_address'], new_user['port'])))
                        found = True
                        break
                if (not found): # if he is new in the system -> he is in Public Group
                    self.client.user_list.append(ClientInfo(new_user['username'], new_user['client_id'], new_user['group_id'], (new_user['ip_address'], new_user['port'])))
                    if (self.client.group_id == self.client.PUBLIC_GROUP_ID):
                        print('\033[1m{} has joined the group\033[0m'.format(new_user['username']))

            log.info('[Update List] list={}'.format(self.client.user_list))
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID})

    def update_disconnection(self, message):
        if (message.sequence != self.last_seq_recv):
            for user in self.client.user_list:
                if (user.client_id == message.options.client_id): # it is possible we don't have this user
                    log.info('[Update Disconnection] client_id={}'.format(user.client_id))
                    self.client.user_list.remove(user)
                    # If we are in a decentralized group and the client is in our group
                    if (user.group_id == self.client.group_id):
                        print('\033[1m{} has left the group\033[0m'.format(user.username))
                        if (self.client.decentralized):
                            for session in self.client.user_sessions:
                                if (session.client_id == message.options.client_id):
                                    self.client.user_sessions.remove(session)
                    break # we found the user -> out of loop
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID})

    def disconnection_request(self):
        log.info('[Disconnection Request] username={}'.format(self.client.username))
        self.client.state = self.client.STATE_PENDING_DISC
        self._send(dictdata={'type': DisconnectionRequest.TYPE, 'ack': 0, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID})

    def acknowledgement(self, message):
        if (message.sequence == self.last_seq_sent): # it can be for connection or any other message
            log.debug('[ACK] ACK received')
            self.state = self.STATE_IDLE
            self.timer.cancel() # stop timer
            if (len(self.message_queue)): # send first message in queue if exists
                self._send(self.message_queue.pop(0))
                log.debug('[STATE_IDLE] Message dequeued')
            # if user waits for DisconnectionACK
            if ((message.type == DisconnectionRequest.TYPE) and (self.client.state == self.client.STATE_PENDING_DISC)):
                self.client.state = self.client.STATE_DISCONNECTED

    # Private function (send with reliability)
    def _send(self, dictdata, retry=5):
        # When ACK there's no UDP reliability
        if ((dictdata.get('ack') == 0x01)):
            self.last_seq_recv = dictdata.get('sequence') # client always replies with an ACK
            message = InstantProtocolMessage(dictdata=dictdata)
            log.debug('[---] Sending ACK -> {}'.format(message))
            self.client.sock.sendto(message.serialize(), self.address)
        ## UDP reliability
        elif (retry == 5): # first attempt
            # Can we send?
            if (self.state == self.STATE_IDLE):
                self.last_seq_sent = 1 - self.last_seq_sent # swap: 0 to 1 and viceversa
                dictdata['sequence'] = self.last_seq_sent # set sequence (different each message)
                message = InstantProtocolMessage(dictdata=dictdata)
                log.debug('[STATE_IDLE] Sending message (retry={}) -> {}'.format(retry, message))
                self.client.sock.sendto(message.serialize(), self.address)
                # ACK mode and timer to resend
                self.state = self.STATE_ACK
                self.timer = threading.Timer(self.RESEND_TIMER, self._send, [dictdata, retry - 1])
                self.timer.start()

            else: # self.state == self.STATE_ACK
                log.debug('[STATE_ACK] (Message queued') # don't print the message because it doesn't have sequence yet
                self.message_queue.append(dictdata)

        elif (retry > -1): # next attempts
            message = InstantProtocolMessage(dictdata=dictdata)
            log.debug('[STATE_IDLE] Sending message (retry={}) -> {}'.format(retry, message))
            self.client.sock.sendto(message.serialize(), self.address)
            self.timer = threading.Timer(self.RESEND_TIMER, self._send, [dictdata, retry - 1])
            self.timer.start()

        elif (retry == -1): # last attempt expired -> not connected
            # Server unreachable or server unreachable for disconnection -> disconnected automatically
            log.info('[Server unreachable] (Timer expired)')
            #print('Server unreachable')
            self.client.state = self.client.STATE_DISCONNECTED

    # This function is called when invitation timer expires (15 seconds to answer)
    def _invitation_expired(self):
        log.debug('[Invitation] Invitation expired')
        self.client.state = self.client.STATE_NORMAL
        print('\033[1mYour invitation to the {} group {} has expired\033[0m'.format(
            'centralized' if (not self.temporal_group_type) else 'decentralized', self.temporal_group_id))

# Class for sessions used by other clients (only decentralized mode)
class ClientSessionClient(ClientSession):
    def __init__(self, client, username, client_id, address):
        super(ClientSessionClient,self).__init__(client, address)
        self.username = username
        self.client_id = client_id # self.group_id is not required because session is created in decentralized mode (only users of the same group)

    def __repr__(self):
        return 'ClientSessionClient(client={}, address={}, last_seq_sent={}, last_seq_recv={}, state={}, message_queue={}, timer={}, username={}, client_id={}'.format(
            self.client, self.address, self.last_seq_sent, self.last_seq_recv, self.state, self.message_queue, self.username, self.client_id)

    def data_message_send(self, text):
        log.info('[Data Message] (Send message) text={}'.format(text))
        self._send(dictdata={'type': DataMessage.TYPE, 'ack': 0, 'source_id': self.client.client_id, 'group_id': self.client.group_id, 'options': {'data_length': len(text), 'payload': text}})

    def data_message_reception(self, message):
        if (message.sequence != self.last_seq_recv):
            log.info('[Data Message] (Receive message) text={}'.format(message.options.payload))
            print('\033[1m{}:\033[0m {}'.format(self.username, message.options.payload))
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': self.NO_GROUP_ID})

    def acknowledgement(self, message):
        if (message.sequence == self.last_seq_sent): # it can be for connection or any other message
            log.debug('[ACK] ACK received')
            self.state = self.STATE_IDLE
            self.timer.cancel() # stop timer
            #log.debug('[STATE_ACK] Stop timer -> {}'.format(message))
            if (len(self.message_queue)): # send first message in queue if exists
                self._send(self.message_queue.pop(0))
                log.debug('[STATE_IDLE] Message dequeued')

    # Private function (send with reliability)
    def _send(self, dictdata, retry=5):
        # When ACK there's no UDP reliability
        if ((dictdata.get('ack') == 0x01)):
            self.last_seq_recv = dictdata.get('sequence') # if we send an ACK, we are acknowledging the last sequence
            message = InstantProtocolMessage(dictdata=dictdata)
            log.debug('[---] Sending ACK -> {}'.format(message))
            self.client.sock.sendto(message.serialize(), self.address)
        ## UDP reliability
        elif (retry == 5): # first attempt
            # Can we send?
            if (self.state == self.STATE_IDLE):
                self.last_seq_sent = 1 - self.last_seq_sent # swap: 0 to 1 and viceversa
                dictdata['sequence'] = self.last_seq_sent # set sequence (different each message)
                message = InstantProtocolMessage(dictdata=dictdata)
                log.debug('[STATE_IDLE] Sending message (retry={}) -> {}'.format(retry, message))
                self.client.sock.sendto(message.serialize(), self.address)
                # ACK mode and timer to resend
                self.state = self.STATE_ACK
                self.timer = threading.Timer(self.RESEND_TIMER, self._send, [dictdata, retry - 1])
                self.timer.start()

            else: # self.state == self.STATE_ACK
                log.debug('[STATE_ACK] Message queued') # don't print the message because it doesn't have sequence yet
                self.message_queue.append(dictdata)

        elif (retry > -1): # next attempts
            message = InstantProtocolMessage(dictdata=dictdata)
            log.debug('[STATE_IDLE] Sending message (retry={}) -> {}'.format(retry, message))
            self.client.sock.sendto(message.serialize(), self.address)
            self.timer = threading.Timer(self.RESEND_TIMER, self._send, [dictdata, retry - 1])
            self.timer.start()

        elif (retry == -1): # last attempt expired -> not connected
            log.info('[User unreachable] (Timer expired) username={}'.format(self.username))
            if (self in self.client.user_sessions):
                self.client.user_sessions.remove(self) # remove itself from the list (no message to server, it will realize later)

# ClientSession.py
# Copyright (C) 2017
# Jesus Alberto Polo <jesus.pologarcia@imt-atlantique.net>
# Erika Tarazona <erika.tarazona@imt-atlantique.net>

import threading
import logging as log

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
    def __init__(self, client, address):
        super(ClientSessionServer,self).__init__(client, address)
        self.temporal_group_id = 0
        self.temporal_group_type = 0

    def __repr__(self):
        return 'ClientSessionServer(username={}, client_id={}, address={}, last_seq_sent={}, last_seq_recv={}, state={}, message_queue={})'.format(
            'Server', self.client.SERVER_ID, self.address, self.last_seq_sent, self.last_seq_recv, self.state, self.message_queue)

    def connection_request(self, username):
        if (self.client.state == self.client.STATE_PENDING_CONN):
            self.client.username = ('{0: <8}'.format(username)).strip() # only 8 bytes
            log.info('[Connection Request] username={}'.format(username))
            self._send(dictdata={'type': ConnectionRequest.TYPE, 'ack': 0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'username': username}})

    # only for server (id = 0x00)
    def connection_accept(self, message):
        if (self.client.state == self.client.STATE_PENDING_CONN):
            self.client.state = self.client.STATE_NORMAL
            self.client.client_id = message.options.client_id
            self.timer.cancel() # stop timer
            self.state = self.STATE_IDLE
            log.info('[Connection] username={}, id={}'.format(self.client.username, self.client.client_id))
            self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': 0x00})

    # only for server (id = 0x00)
    def connection_reject(self, message):
        if (self.client.state == self.client.STATE_PENDING_CONN):
            self.timer.cancel() # stop timer
            self.state = self.STATE_IDLE
            if (message.options.error == 0):
                log.info('[Connection] (Failed -> maximum reached')
                print('Connection failed -> maximum number of users reached')
            else:
                log.info('[Connection] (Failed -> username already taken)')
                print('Connection failed -> username already taken')
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': 0x00})

    def user_list_request(self):
        log.info('[User List Request] username={}'.format(self.client.username))
        self._send(dictdata={'type': UserListRequest.TYPE, 'ack': 0, 'source_id': self.client.client_id, 'group_id': self.client.group_id})

    def user_list_response(self, message):
        if (message.sequence != self.last_seq_recv): # we always send an ACK even if the message is repeated (lost ACK)
            self.timer.cancel() # stop timer
            self.state = self.STATE_IDLE # response has implicit ACK
            # Create list (add also ourselves)
            for user in message.options.user_list:
                self.client.user_list.append(ClientInfo(user['username'], user['client_id'], user['group_id'], (user['ip_address'], user['port'])))
            log.info('[User List Response] list={}'.format(self.client.user_list))
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': 0x00})

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
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': 0x00})

    def group_creation_request(self, group_type, raw_clients):
        if (self.client.state == self.client.STATE_NORMAL) and (self.client.group_id == self.client.PUBLIC_GROUP_ID):
            if ((len(raw_clients) > 0) and ((group_type == 0) or (group_type == 1))):
                client_ids = list()
                for user in self.client.user_list:
                    if ((user.username in raw_clients) and (user.username != self.client.username)):
                        client_ids.append(user.client_id)
                log.info('[Group Creation] (Request send) group_type={}, client_ids={}'.format(group_type, client_ids))
                self.client.state = self.client.STATE_WAIT_GROUP
                self._send(dictdata={'type': GroupCreationRequest.TYPE, 'ack': 0, 'source_id': self.client.client_id, 'group_id': 0x00, 'options': {'type': group_type, 'client_ids': client_ids}})
            else:
                print('Cannot create group from the given arguments')

    def group_creation_accept_send(self):
        pass

    def group_creation_accept_reception(self, message):
        if (message.sequence != self.last_seq_recv):
            if (self.client.state == self.client.STATE_WAIT_GROUP):
                log.info('[Group Creation] (Accept receive) group_type={}, group_id={}'.format(message.options.type, message.options.group_id))
                self.client.state = self.client.STATE_NORMAL
                self.client.group_id = message.options.group_id
                self.client.decentralized = bool(message.options.type)
                # Sessions in decentralized mode will be created based on UpdateList messages
                self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': 0x00})

    def group_creation_reject_reception(self, message):
        if (message.sequence != self.last_seq_recv):
            if (self.client.state == self.client.STATE_WAIT_GROUP):
                log.info('[Group Creation] (Reject receive) group_type={}, group_id={}'.format(message.options.type, message.options.group_id))
                self.client.state = self.client.STATE_NORMAL
                print('Group creation rejected')

    def group_invitation_request_send(self, usernames):
        if (self.client.group_id != self.client.PUBLIC_GROUP_ID): # We can only invite to a private group
            log.info('[Group Invitation] (Resquest send) group_id={}, group_type={}, usernames={}'.format(self.client.group_id, int(self.client.decentralized), usernames))
            for user in self.client.user_list:
                if ((user.username in usernames) and (user.username != self.client.username)):
                    self._send(dictdata={'type': GroupInvitationRequest.TYPE, 'ack': 0, 'source_id': self.client.client_id, 'group_id': 0x00, 'options': {'type': int(self.client.decentralized), 'group_id': self.client.group_id, 'client_id': user.client_id}})
        else:
            print('Cannot invite users to public group')

    def group_invitation_request_reception(self, message):
        if (message.sequence != self.last_seq_recv):
            # Send ACK and after we'll send a reject if it isn't possible to invite
            self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': 0x00})
            if (self.client.state == self.client.STATE_NORMAL):
                log.info('[Group Invitation] (Request receive) group_type={}, group_id={}'.format(message.options.type, message.options.group_id))
                self.client.state = self.client.STATE_PENDING_INV
                self.temporal_group_id = message.options.group_id
                self.temporal_group_type = message.options.type
            else:
                self._send(dictdata={'type': GroupInvitationReject.TYPE, 'ack': 0, 'source_id': self.client.client_id, 'group_id': 0x00, 'options': {'type': message.options.type, 'group_id': message.options.group_id, 'client_id': message.options.client_id}})

    def group_invitation_accept_send(self):
        if (self.client.state == self.client.STATE_PENDING_INV):
            log.info('[Group Invitation] (Accept send) group_type={}, group_id={}'.format(self.temporal_group_type, self.temporal_group_id))
            self.client.state = self.client.STATE_NORMAL
            self.client.group_id = self.temporal_group_id
            self.client.decentralized = bool(self.temporal_group_type)
            self.temporal_group_id = 0
            self.temporal_group_type = 0
            self._send(dictdata={'type': GroupInvitationAccept.TYPE, 'ack': 0, 'source_id': self.client.client_id, 'group_id': 0x00, 'options': {'type': int(self.client.decentralized), 'group_id': self.client.group_id, 'client_id': self.client.client_id}})
            # Create sessions in decentralized mode
            if (self.client.decentralized):
                for user in self.client.user_list:
                    if ((user.group_id == self.client.group_id) and (user.client_id != self.client.client_id)):
                        log.debug('[Group Invitation Accept] (Session created in decentralized) username={}'.format(user.username))
                        self.user_sessions.append(ClientSessionClient(self, user.username, user.client_id, user.address))

    def group_invitation_accept_reception(self, message):
        if (message.sequence != self.last_seq_recv):
            log.info('[Group Invitation] (Accept receive) client_id={}'.format(message.client_id))
            # Create sessions in decentralized mode
            if (self.client.decentralized):
                for user in self.client.user_list:
                    if (user.client_id == message.source_id):
                        log.debug('[Group Invitation Accept] (Session created in decentralized) username={}'.format(user.username))
                        self.user_sessions.append(ClientSessionClient(self, user.username, user.client_id, user.address))
                        break
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': 0x00})

    def group_invitation_reject_send(self):
        pass

    def group_invitation_reject_reception(self):
        pass

    def group_disjoint_request(self):
        pass

    def group_dissolution(self):
        pass

    # TODO: Check if the user is in our group, we are in decentralized and delete session
    def update_list(self, message):
        if (message.sequence != self.last_seq_recv):
            for new_user in message.options.user_list:
                found = False
                for old_user in self.client.user_list:
                    if (old_user.client_id == new_user['client_id']):
                        old_user.group_id = new_user['group_id'] # in this protocol, only group_id can change (other values are fixed)
                        found = True
                if (not found):
                    self.client.user_list.append(ClientInfo(new_user['username'], new_user['client_id'], new_user['group_id'], (new_user['ip_address'], new_user['port'])))
            log.info('[Update List] list={}'.format(self.client.user_list))
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': 0x00})

    def update_disconnection(self, message):
        # TODO: Check if the user is in our group, we are in decentralized and delete session
        if (message.sequence != self.last_seq_recv):
            for user in self.client.user_list:
                if (user.client_id == message.options.client_id): # it is possible we don't have this user
                    log.info('[Update Disconnection] client_id={}'.format(user.client_id))
                    self.client.user_list.remove(user)
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': 0x00})

    def disconnection_request(self):
        log.info('[Disconnection Request] username={}'.format(self.client.username))
        self.client.state = self.client.STATE_PENDING_DISC
        self._send(dictdata={'type': DisconnectionRequest.TYPE, 'ack': 0, 'source_id': self.client.client_id, 'group_id': 0x00})

    def acknowledgement(self, message):
        if (message.sequence == self.last_seq_sent): # it can be for connection or any other message
            log.debug('[ACK] ACK received')
            self.state = self.STATE_IDLE
            self.timer.cancel() # stop timer
            #log.debug('[STATE_ACK] Stop timer -> {}'.format(message))
            if (len(self.message_queue)): # send first message in queue if exists
                self._send(self.message_queue.pop(0))
                log.debug('[STATE_IDLE] Message dequeued')
            # if user waits for DisconnectionACK
            if (self.client.state == self.client.STATE_PENDING_DISC):
                self.client.state = self.client.STATE_DISCONNECTED

    # Private function (send with reliability)
    def _send(self, dictdata, retry=1):
        # When ACK there's no UDP reliability
        if ((dictdata.get('ack') == 0x01)):
            self.last_seq_recv = dictdata.get('sequence') # client always replies with an ACK
            message = InstantProtocolMessage(dictdata=dictdata)
            log.debug('[---] Sending ACK -> {}'.format(message))
            self.client.sock.sendto(message.serialize(), self.address)
        ## UDP reliability
        elif (retry == 1): # first attempt
            # Can we send?
            if (self.state == self.STATE_IDLE):
                self.last_seq_sent = 1 - self.last_seq_sent # swap: 0 to 1 and viceversa
                dictdata['sequence'] = self.last_seq_sent # set sequence (different each message)
                message = InstantProtocolMessage(dictdata=dictdata)
                log.debug('[STATE_IDLE] Sending message (retry=1) -> {}'.format(message))
                self.client.sock.sendto(message.serialize(), self.address)
                # ACK mode and timer to resend
                self.state = self.STATE_ACK
                self.timer = threading.Timer(self.RESEND_TIMER, self._send, [dictdata, retry - 1])
                self.timer.start()

            else: # self.state == self.STATE_ACK
                log.debug('[STATE_ACK] Message queued') # don't print the message because it doesn't have sequence yet
                self.message_queue.append(dictdata)

        elif (retry == 0): # last attempt
            message = InstantProtocolMessage(dictdata=dictdata)
            log.debug('[STATE_IDLE] Sending message (retry=0) -> {}'.format(message))
            self.client.sock.sendto(message.serialize(), self.address)
            self.timer = threading.Timer(self.RESEND_TIMER, self._send, [dictdata, retry - 1])
            self.timer.start()

        elif (retry == -1): # last attempt expired -> not connected
            # Server unreachable or server unreachable for disconnection -> disconnected automatically
            if (self.client.state == self.client.STATE_PENDING_CONN) or (self.client.state == self.client.STATE_PENDING_DISC):
                log.info('[Server unreachable] (Timer expired)')
                self.client.state = self.client.STATE_DISCONNECTED

# Class for sessions used by other clients (only decentralized mode)
class ClientSessionClient(ClientSession):
    def __init__(self, client, username, client_id, address):
        super(ClientSessionClient,self).__init__(client, address)
        self.username = username
        self.client_id = client_id # self.group_id is not required because session is created in decentralized mode (only users of the same group)

    def __repr__(self):
        return 'ClientSessionClient(username={}, client_id={}, address={}, last_seq_sent={}, last_seq_recv={}, state={}, message_queue={})'.format(
            self.username, self.client_id, self.address, self.last_seq_sent, self.last_seq_recv, self.state, self.message_queue)

    def data_message_send(self, text):
        log.info('[Data Message] (Send message) text={}'.format(text))
        self._send(dictdata={'type': DataMessage.type, 'ack': 0, 'source_id': self.client.client_id, 'group_id': self.client.group_id})

    def data_message_reception(self, message):
        log.info('[Data Message] (Receive message) text={}'.format(message.options.payload))
        print('{}: {}'.format(self.username, message.options.payload))
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': 0x00})

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
    def _send(self, dictdata, retry=1):
        # When ACK there's no UDP reliability
        if ((dictdata.get('ack') == 0x01)):
            message = InstantProtocolMessage(dictdata=dictdata)
            log.debug('[---] Sending ACK -> {}'.format(message))
            self.client.sock.sendto(message.serialize(), self.address)
        ## UDP reliability
        elif (retry == 1): # first attempt
            # Can we send?
            if (self.state == self.STATE_IDLE):
                self.last_seq_sent = 1 - self.last_seq_sent # swap: 0 to 1 and viceversa
                dictdata['sequence'] = self.last_seq_sent # set sequence (different each message)
                message = InstantProtocolMessage(dictdata=dictdata)
                log.debug('[STATE_IDLE] Sending message (retry=1) -> {}'.format(message))
                self.client.sock.sendto(message.serialize(), self.address)
                # ACK mode and timer to resend
                self.state = self.STATE_ACK
                self.timer = threading.Timer(self.RESEND_TIMER, self._send, [dictdata, retry - 1])
                self.timer.start()

            else: # self.state == self.STATE_ACK
                log.debug('[STATE_ACK] Message queued') # don't print the message because it doesn't have sequence yet
                self.message_queue.append(dictdata)

        elif (retry == 0): # last attempt
            message = InstantProtocolMessage(dictdata=dictdata)
            log.debug('[STATE_IDLE] Sending message (retry=0) -> {}'.format(message))
            self.client.sock.sendto(message.serialize(), self.address)
            self.timer = threading.Timer(self.RESEND_TIMER, self._send, [dictdata, retry - 1])
            self.timer.start()

        elif (retry == -1): # last attempt expired -> not connected
            log.info('[User unreachable] (Timer expired) username={}'.format(self.username))
            if (self in self.client.user_sessions):
                self.client.user_sessions.remove(self) # remove itself from the list (no message to server, it will realize later)

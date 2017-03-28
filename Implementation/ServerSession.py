# ServerSession.py
# Copyright (C) 2017
# Jesus Alberto Polo <jesus.pologarcia@imt-atlantique.net>
# Erika Tarazona <erika.tarazona@imt-atlantique.net>

import threading
import logging as log

# Temporal
execfile('InstantProtocol.py')

# Exception when a Session is not found
class SessionNotFound(Exception):
    pass

# Session for each client
class ServerSession(object):
    SERVER_ID = 0x00
    PUBLIC_GROUP_ID = 0x01
    PUBLIC_GROUP_TYPE = 0x0
    NO_GROUP_ID = 0x00 # when group is set to 0 because the destination is not a group
    STATE_IDLE = 0 # ready to send
    STATE_ACK = 1 # waiting for ack
    STATE_PENDING_CONN = 2 # client connection
    RESEND_TIMER = 0.5 # resend in 500ms
    GROUP_TIMER = 15 # timer for Group Creation or Invitation Request (sends Group Creation Reject or Invitation Reject if not stopped)

    def __init__(self, server, username, client_id, address):
        self.server = server
        self.username = username # asked later
        self.client_id = client_id
        self.group_id = self.PUBLIC_GROUP_ID # public by default
        self.group_type = 0 # centralized by default (centralized = 0, decentralized = 1)
        self.address = address
        self.state = self.STATE_PENDING_CONN
        self.last_seq_sent = 0
        self.last_seq_recv = 0
        self.message_queue = list() # saving dictdata so sequence can be changed
        self.timer = None
        self.creating_group = False # waiting for a group creation
        self.num_invited_clients = 0 # number of clients invited when creating group
        self.inviting = False # waiting for an invitation response
        self.invitation_timer = None # timer for group creation or invitation
        self.invited_by = None # session of the user who invited us to join a group (invitation or creation)

        # Send message to user -> Connection Accept (and session created for this user)
        self._send(dictdata={'type': ConnectionAccept.TYPE, 'ack':0, 'source_id': self.SERVER_ID, 'group_id': self.NO_GROUP_ID, 'options': {'client_id': self.client_id}})

    def __repr__(self):
        return 'ServerSession(username={}, client_id={}, group_id={}, group_type={}, last_seq_sent={}, last_seq_recv={}, state={}, message_queue={}, timer={}, creating_group={}, num_invited_clients={}, inviting={}, invitation_timer={}, invited_by={})'.format(
            self.username, self.client_id, self.group_id, self.group_type, self.last_seq_sent, self.last_seq_recv, self.state, self.message_queue, self.timer, self.creating_group, self.num_invited_clients, self.inviting, self.invitation_timer, self.invited_by)

    def user_list_response(self, message):
        log.info('[User List] username={}'.format(self.username))
        self.last_seq_recv = message.sequence # first message after creating the session (setting last_seq_recv for the first time)
        users = list()
        for user in self.server.session_list:
            item = dict(client_id=user.client_id, group_id=user.group_id, username=user.username, ip_address=user.address[0], port=user.address[1])
            users.append(item)
        self._send(dictdata={'type': UserListResponse.TYPE, 'ack': 0, 'source_id': self.SERVER_ID, 'group_id': self.group_id, 'options': {'user_list': users}})

    def data_message(self, message):
        if (message.sequence != self.last_seq_recv):
            log.info('[Data message] username={}, payload={}'.format(self.username, message.options.payload))
            for session in self.server.session_list:
                if ((session.client_id != self.client_id) and (session.group_id == self.group_id)):
                    session._send(dictdata={'type': message.type, 'ack': 0, 'source_id': message.source_id, 'group_id': message.group_id, 'options': {'data_length': message.options.data_length, 'payload': message.options.payload}})
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.SERVER_ID, 'group_id': self.NO_GROUP_ID})

    def group_creation_request(self, message):
        if (message.sequence != self.last_seq_recv):
            group_id = self.server.pool_group_ids.pop(0)
            log.info('[Group Creation Request] username={}, group_id={}, client_ids={}'.format(self.username, group_id, message.options.client_ids))
            self.num_invited_clients = len(message.options.client_ids)
            self.creating_group = True
            for session in self.server.session_list:
                if (session.client_id in message.options.client_ids):
                    session.invited_by = self
                    session.invitation_timer = threading.Timer(self.GROUP_TIMER, self.group_creation_reject, []) # set a timer and group_creation_reject (of the sender) will be called when it expires
                    session.invitation_timer.start()
                    session._send(dictdata={'type': GroupInvitationRequest.TYPE, 'ack': 0, 'source_id': message.source_id, 'group_id': message.group_id, 'options': {'type': message.options.type, 'group_id': group_id, 'client_id': session.client_id}})
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.SERVER_ID, 'group_id': self.NO_GROUP_ID})

    def group_creation_accept(self, group_type, group_id):
        log.info('[Group Creation Accept] group_id={}, grop_type={}'.format(group_type, group_id))
        self.creating_group = False
        self.num_invited_clients = 0
        self.group_type = group_type
        self.group_id = group_id
        print('\033[1mGroup {} created in {} mode\033[0m'.format(self.group_id, 'centralized' if self.group_type == 0 else 'decentralized'))
        self._send(dictdata={'type': GroupCreationAccept.TYPE, 'ack': 0, 'source_id': self.SERVER_ID, 'group_id': self.NO_GROUP_ID, 'options': {'type': group_type, 'group_id': group_id}})
        for session in self.server.session_list:
            if (session != self):
                session.update_list([self])

    def group_creation_reject(self):
        if (self.creating_group): # timer expired (called by group creation request for each invitation failed)
            if (self.num_invited_clients == 1): # last invited client (then we cancel Group Creation)
                self.creating_group = False
                self.num_invited_clients = 0
                self._send(dictdata={'type': GroupCreationReject.TYPE, 'ack':0, 'source_id': self.SERVER_ID, 'group_id': self.NO_GROUP_ID})
            else:
                self.num_invited_clients -= 1

    def group_invitation_request(self, message):
        if (message.sequence != self.last_seq_recv):
            log.info('[Group Invitation Request] username={}, group_id={}, client_ids={}'.format(self.username, self.group_id, message.options.client_id))
            for session in self.server.session_list:
                if (session.client_id == message.options.client_id):
                    if (session.invited_by == None): # client is not being invited at this moment
                        session.invited_by = self
                        session.invitation_timer = threading.Timer(self.GROUP_TIMER, session.group_invitation_reject, [])
                        session.invitation_timer.start()
                        session._send(dictdata={'type': GroupInvitationRequest.TYPE, 'ack': 0, 'source_id': message.source_id, 'group_id': self.NO_GROUP_ID, 'options': {'type': message.options.type, 'group_id': self.group_id, 'client_id': session.client_id}})
                    else: # notify that user rejected invitation because he's waiting for other invitation
                        self._send(dictdata={'type': GroupInvitationReject.TYPE, 'ack': 0, 'source_id': message.source_id, 'group_id': self.NO_GROUP_ID, 'options': {'type': message.options.type, 'group_id': self.group_id}})
                    break # only one user
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.SERVER_ID, 'group_id': self.NO_GROUP_ID})

    def group_invitation_accept(self, message):
        if (message.sequence != self.last_seq_recv):
            log.info('[Invitation Accept] username={}, group_id={}'.format(self.username, message.options.group_id))
            self.group_id = message.options.group_id
            self.group_type = message.options.type
            self.invitation_timer.cancel()
            if (self.invited_by.creating_group):
                self.invited_by.group_creation_accept(message.options.type, message.options.group_id)
            else:
                print('\033[1mUser {} changed to group {}\033[0m'.format(self.username, self.group_id))
                self._send(dictdata={'type': GroupInvitationAccept.TYPE, 'ack': 0, 'source_id': message.source_id, 'group_id': self.NO_GROUP_ID, 'options': {'type': message.options.type, 'group_id': message.options.group_id, 'client_id': self.client_id}}) # send invitation accept back
            self.invited_by = None
            for session in self.server.session_list:
                if (session != self):
                    session.update_list([self])
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.SERVER_ID, 'group_id': self.NO_GROUP_ID})

    def group_invitation_reject(self, message=None):
        # the session that has sent the invitation (creating group or invited), session in which the timer was expired calls the session that invites
        if (message): # message reception
            if (message.sequence != self.last_seq_recv):
                log.info('[Group Invitation Reject] username={}, group_id={}'.format(self.username, message.options.group_id))
                self.invitation_timer.cancel()
                if (self.invited_by.creating_group):
                    self.invited_by.group_creation_reject()
                else: # inviting
                    self.invited_by._send(dictdata={'type': GroupInvitationReject.TYPE, 'ack': 0, 'source_id': message.source_id, 'group_id': self.NO_GROUP_ID, 'options': {'type': message.options.type, 'group_id': message.options.group_id}}) # notify to the session that invited that the invitation has been rejected
                self.invited_by = None # remove state of invitation
            self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.SERVER_ID, 'group_id': self.NO_GROUP_ID})
        else: # timer expires in session who is being invited (this session)
            # we send rejection anyway (even if it is send when timer expires)
            self.invited_by._send(dictdata={'type': GroupInvitationReject.TYPE, 'ack': 0, 'source_id': self.client_id, 'group_id': self.NO_GROUP_ID, 'options': {'type': self.invited_by.group_type, 'group_id': self.invited_by.group_id}}) # notify to the session that invited that the invitation has been rejected
            self.invited_by = None

    def group_disjoint_request(self, message):
        if (message.sequence != self.last_seq_recv):
            log.info('[Disjoint Request] username={}'.format(self.username))
            print('\033[1mUser {} leaved from group {}\033[0m'.format(self.username, self.group_id))
            old_group_id = self.group_id
            self.group_id = self.PUBLIC_GROUP_ID
            self.group_type = self.PUBLIC_GROUP_TYPE
            # Send update to all users
            for session in self.server.session_list:
                if (session != self):
                    session.update_list([self])
            # Count if there are enough clients in the group
            users_group = 0
            last_session = None
            for session in self.server.session_list:
                if (session.group_id == old_group_id):
                    users_group += 1
                    last_session = session
            if (users_group == 1): # minimum 2 users per group (1 has left so...)
                last_session.group_dissolution() # disolve group
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.SERVER_ID, 'group_id': self.NO_GROUP_ID})

    def group_dissolution(self):
        log.info('[Group Dissolution] username={}'.format(self.username))
        print('\033[1mUser {} requested for resolution in group {}\033[0m'.format(self.username, self.group_id))
        self.group_id = self.PUBLIC_GROUP_ID
        self.group_type = self.PUBLIC_GROUP_TYPE
        self._send(dictdata={'type': GroupDissolution.TYPE, 'ack': 0, 'source_id': self.SERVER_ID, 'group_id': self.group_id})
        # Send update to all users
        for session in self.server.session_list:
            if (session != self):
                session.update_list([self])

    def update_list(self, updated_sessions):
        log.info('[Update List] username={}'.format(self.username))
        users = list()
        for us in updated_sessions:
            item = dict(client_id=us.client_id, group_id=us.group_id, username=us.username, ip_address=us.address[0], port=us.address[1])
            users.append(item)
        self._send(dictdata={'type': UpdateList.TYPE, 'ack': 0, 'source_id': self.SERVER_ID, 'group_id': 0xFF, 'options': {'user_list': users}})

    def update_disconnection(self, old_session):
        log.info('[Update Disconnection] username={}'.format(old_session.username))
        self._send(dictdata={'type': UpdateDisconnection.TYPE, 'ack': 0, 'source_id': self.SERVER_ID, 'group_id': 0xFF, 'options': {'client_id': old_session.client_id}})

    def disconnection_request(self, message):
        if (message.sequence != self.last_seq_recv):
            log.info('[Disconnection] (Requested by user) username={}, id={}'.format(self.username, self.client_id))
            print('\033[1mUser {} disconnected\033[0m'.format(self.username))
            self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.SERVER_ID, 'group_id': self.NO_GROUP_ID})
            # Count if there are enough clients in the group (same as Group Disjoint)
            if (self.group_id != self.PUBLIC_GROUP_ID):
                users_group = 0
                last_session = None
                for session in self.server.session_list:
                    if ((session != self) and (self.group_id == session.group_id)):
                        users_group += 1
                        last_session = session
                if (users_group == 1): # minimum 2 users per group (1 has left so...)
                    last_session.group_dissolution() # disolve group
            # Send update to all users
            for session in self.server.session_list:
                if (session != self):
                    session.update_disconnection(self)
            self.server.session_list.remove(self) # remove itself from the list

    def acknowledgement(self, message):
        #log.debug(self.server.session_list)
        if (message.sequence == self.last_seq_sent): # it can be for connection or any other message
            if (self.state == self.STATE_PENDING_CONN): # Session is created now and all other clients are notified
                for session in self.server.session_list:
                    if (session != self):
                        session.update_list([self])
                log.info('[Connection] username={}, id={}'.format(self.username, self.client_id))
                log.debug(self.server.session_list)

            # Normal behavior -> Stop & Wait (I only wait for one message to be acknowledgement)
            log.debug('[ACK] ACK received')
            self.state = self.STATE_IDLE
            self.timer.cancel() # stop timer
            #log.debug('[STATE_ACK] Stop timer -> {}'.format(message))
            if (len(self.message_queue)): # send first message in queue if exists
                self._send(self.message_queue.pop(0))

    # Private function (send with reliability)
    def _send(self, dictdata, retry=5):
        # When ACK not UDP reliability
        if (dictdata.get('ack') == 0x01):
            self.last_seq_recv = dictdata.get('sequence') # if we send an ACK, we are acknowledging the last sequence
            message = InstantProtocolMessage(dictdata=dictdata)
            log.debug('[---] Sending ACK -> {}'.format(message))
            self.server.sock.sendto(message.serialize(), self.address)
        ## UDP reliability
        # First attempt
        elif (retry == 5):
            # Can we send?
            if ((self.state == self.STATE_IDLE) or (self.state == self.STATE_PENDING_CONN)):
                self.last_seq_sent = 1 - self.last_seq_sent # swap: 0 to 1 and viceversa
                dictdata['sequence'] = self.last_seq_sent # set sequence (different each message)
                message = InstantProtocolMessage(dictdata=dictdata)
                log.debug('[STATE_IDLE] Sending message (retry={}) -> {}'.format(retry, message))
                self.server.sock.sendto(message.serialize(), self.address)
                if (self.state == self.STATE_IDLE):
                    self.state = self.STATE_ACK
                # Timer to resend
                self.timer = threading.Timer(self.RESEND_TIMER, self._send, [dictdata, retry - 1])
                self.timer.start()

            else: # self.state == self.STATE_ACK
                log.debug('[STATE_ACK] Message queued') # don't show the message because it doesn't have sequence yet
                self.message_queue.append(dictdata)

        elif (retry > -1): # next attempts
            message = InstantProtocolMessage(dictdata=dictdata) # dictada has sequence
            log.debug('[STATE_IDLE] Sending message (retry={}) -> {}'.format(retry, message))
            self.server.sock.sendto(message.serialize(), self.address)
            self.timer = threading.Timer(self.RESEND_TIMER, self._send, [dictdata, retry - 1])
            self.timer.start()

        elif (retry == -1): # last attempt expired
            if (self.state != self.STATE_PENDING_CONN): # the user is not connected yet
                for s in self.server.session_list:
                    if (s != self):
                        s.update_disconnection(self)
            log.info('[Disconnection] (Timer expired) username={}, id={}'.format(self.username, self.client_id))
            if (self in self.server.session_list): # sometimes the user is desconnected before but the Threads continue (Disconnection Request)
                self.server.session_list.remove(self) # remove itself from the list

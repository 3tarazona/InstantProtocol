import threading
import logging as log

# Temporal
execfile('InstantProtocol.py')

# Session for each client
class ServerSession(object):
    STATE_IDLE = 0 # ready to send
    STATE_ACK = 1 # waiting for ack
    STATE_PENDING_CONN = 2 # client connection
    RESEND_TIMER = 0.5 # resend in 500ms

    def __init__(self, server, username, client_id, address):
        self.server = server
        self.username = username # asked later
        self.client_id = client_id
        self.group_id = 1 # public by default
        self.group_type = 0 # centralized by default (centralized = 0, decentralized = 1)
        self.address = address
        self.state = self.STATE_PENDING_CONN
        self.last_seq_sent = 0
        self.last_seq_recv = 0
        self.message_queue = list() # saving dictdata so sequence can be changed
        self.timer = None

        # Send message to user -> Connection Accepted (and session created for this user)
        self._send(dictdata={'type': ConnectionAccept.TYPE, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'client_id': self.client_id}})

    def __repr__(self):
        return 'ServerSession(username={}, client_id={}, group_id={}, group_type={}, last_seq_sent={}, last_seq_recv={}, state={}, message_queue={})'.format(
            self.username, self.client_id, self.group_id, self.group_type, self.last_seq_sent, self.last_seq_recv, self.state, self.message_queue)

    def user_list_response(self):
        log.info('[User List] username={}'.format(self.username))
        users = list()
        for user in self.server.session_list:
            item = dict(client_id=user.client_id, group_id=user.group_id, username=user.username, ip_address=user.address[0], port=user.address[1])
            users.append(item)
        self._send(dictdata={'type': UserListResponse.TYPE, 'ack': 0, 'source_id': self.client_id, 'group_id': self.group_id, 'options': {'user_list': users}})

    def data_message(self, message):
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': 0x00, 'group_id': 0x00})
        for session in self.server.session_list:
            if ((session.client_id != self.client_id) and (session.group_id == self.group_id)):
                session._send(dictdata={'type': message.type, 'ack': 0, 'source_id': self.client_id, 'group_id': self.group_id, 'options': {'data_length': message.options.data_length, 'payload': message.options.payload}})
        log.info('[Data message] username={}, payload={}'.format(self.username, message.options.payload))

    def group_creation_request(self):
        pass

    def group_creation_accept(self):
        pass

    def group_creation_reject(self):
        pass

    def group_invitation_request(self):
        pass

    def group_invitation_accept(self):
        pass

    def group_invitation_reject(self):
        pass

    def group_disjoint_request(self):
        pass

    def group_dissolution(self):
        log.info('[Group Dissolution] username={}'.format(self.username))
        self._send(dictdata={'type': GroupDissolution.TYPE, 'ack': 0, 'source_id': 0x00, 'group_id': self.group_id})

    def update_list(self, updated_sessions):
        log.info('[Update List] username={}'.format(self.username))
        users = list()
        for us in updated_sessions:
            item = dict(client_id=us.client_id, group_id=us.group_id, username=us.username, ip_address=us.address[0], port=us.address[1])
            users.append(item)
        self._send(dictdata={'type': UpdateList.TYPE, 'ack': 0, 'source_id': 0x00, 'group_id': 0xFF, 'options': {'user_list': users}})

    def update_disconnection(self, old_session):
        log.info('[Update Disconnection] username={}'.format(self.username))
        self._send(dictdata={'type': UpdateDisconnection.TYPE, 'ack': 0, 'source_id': 0x00, 'group_id': 0xFF, 'options': {'client_id': old_session.client_id}})

    def disconnection_request(self, message):
        log.info('[Disconnection] (Requested by user) username={}, id={}'.format(self.username, self.client_id))
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': 0x00, 'group_id': 0x00})
        for s in self.server.session_list:
            if (s != self):
                s.update_disconnection(self)
        self.server.session_list.remove(self) # remove itself from the list

    def acknowledgement(self, message):
        #log.debug(self.server.session_list)
        if (message.sequence == self.last_seq_sent): # it can be for connection or any other message
            if (self.state == self.STATE_PENDING_CONN): # Session is created now and all other clients are notified
                for s in self.server.session_list:
                    if (s != self):
                        s.update_list([self])
                log.info('[Connection] username={}, id={}'.format(self.username, self.client_id))
                log.debug(self.server.session_list)

            # Normal behavior
            self.state = self.STATE_IDLE
            self.timer.cancel() # stop timer
            #log.debug('[STATE_ACK] Stop timer -> {}'.format(message))
            if (len(self.message_queue)): # send first message in queue if exists
                self._send(self.message_queue.pop(0))

    # Private function (send with reliability)
    def _send(self, dictdata, retry=1):
        # When ACK not UDP reliability
        if (dictdata.get('ack') == 0x01):
            message = InstantProtocolMessage(dictdata=dictdata)
            log.debug('[---] Sending ACK -> {}'.format(message))
            self.server.sock.sendto(message.serialize(), self.address)
        ## UDP reliability
        # First attempt
        elif (retry == 1):
            # Can we send?
            if ((self.state == self.STATE_PENDING_CONN) or (self.state == self.STATE_IDLE)):
                self.last_seq_sent = 1 - self.last_seq_sent # swap: 0 to 1 and viceversa
                dictdata['sequence'] = self.last_seq_sent # set sequence (different each message)
                message = InstantProtocolMessage(dictdata=dictdata)
                log.debug('[STATE_IDLE] Sending message (retry=1) -> {}'.format(message))
                self.server.sock.sendto(message.serialize(), self.address)
                if (self.state == self.STATE_IDLE):
                    self.state = self.STATE_ACK
                # Timer to resend
                self.timer = threading.Timer(self.RESEND_TIMER, self._send, [dictdata, retry - 1])
                self.timer.start()

            else: # self.state == self.STATE_ACK
                log.debug('[STATE_ACK] Message queued') # don't show the message because it doesn't have sequence yet
                self.message_queue.append(dictdata)

        elif (retry == 0): # last attempt
            message = InstantProtocolMessage(dictdata=dictdata) # dictada has sequence
            log.debug('[STATE_IDLE] Sending message (retry=0) -> {}'.format(message))
            self.server.sock.sendto(message.serialize(), self.address)
            self.timer = threading.Timer(self.RESEND_TIMER, self._send, [dictdata, retry - 1])
            self.timer.start()

        elif (retry == -1): # last attempt expired
            if (self.state != self.STATE_PENDING_CONN): # the user is not connected yet
                for s in self.server.session_list:
                    if (s != self):
                        s.update_disconnection(self)
            else:
                log.info('[Disconnection] (Timer expired) username={}, id={}'.format(self.username, self.client_id))

            self.server.session_list.remove(self) # remove itself from the list

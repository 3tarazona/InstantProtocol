import threading
import logging as log

# Temporal
execfile('InstantProtocol.py')

class ServerSession(object):
    STATE_IDLE = 0
    STATE_ACK = 1
    STATE_PENDING_CONN = 2
    RESEND_TIMER = 0.5

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

        # Send message to user
        self._send(dictdata={'type': ConnectionAccept.TYPE, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'client_id': self.client_id}})

    def __repr__(self):
        return 'Session(username={}, client_id={}, group_id={}, group_type={}, last_seq_sent={}, las_seq_recv={}, state={})'.format(
            self.username, self.client_id, self.group_id, self.group_type, self.last_seq_sent, self.last_seq_recv, self.state)

    def user_list_response(self):
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

    def update_list(self, updated_sessions):
        users = list()
        for us in updated_sessions:
            item = dict(client_id=us.client_id, group_id=us.group_id, username=us.username, ip_address=us.address[0], port=us.address[1])
            users.append(item)
        self._send(dictdata={'type': UpdateList.TYPE, 'ack': 0, 'source_id': 0x00, 'group_id': 0xFF, 'options': {'user_list': users}})


    def update_disconnection(self, old_session):
        self._send(dictdata={'type': UpdateDisconnection.TYPE, 'ack': 0, 'source_id': 0x00, 'group_id': 0xFF, 'options': {'client_id': old_session.client_id}})

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
        self._send(dictdata={'type': GroupDissolution.TYPE, 'ack': 0, 'source_id': 0x00, 'group_id': self.group_id})

    def disconnection_request(self, message):
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
                log.info('User logged in [username={} id={}]'.format(self.username, self.client_id))

            # Normal behavior
            self.state = self.STATE_IDLE
            self.timer.cancel() # stop timer
            log.debug('Stopping timer -> ACK received')
            if (len(self.message_queue)):
                self._send(self.message_queue.pop(0))

        log.debug(self.server.session_list)

    # Private function (send with reliability)
    def _send(self, dictdata, retry=1):
        # When ACK not UDP reliability
        if (dictdata.get('ack') == 0x01):
            log.debug('Sending ack')
            message = InstantProtocolMessage(dictdata=dictdata)
            self.server.sock.sendto(message.serialize(), self.address)
        ## UDP reliability
        # First attempt
        elif (retry == 1):
            # Can we send?
            if ((self.state == self.STATE_PENDING_CONN) or (self.state == self.STATE_IDLE)):
                self.last_seq_sent = 1 - self.last_seq_sent # swap: 0 to 1 and viceversa
                dictdata['sequence'] = self.last_seq_sent
                message = InstantProtocolMessage(dictdata=dictdata)
                self.server.sock.sendto(message.serialize(), self.address)
                if (self.state == self.STATE_IDLE):
                    self.state = self.STATE_ACK
                # Timer to resend
                self.timer = threading.Timer(self.RESEND_TIMER, self._send, [dictdata, retry - 1])
                self.timer.start()

                log.debug('Sending message IDLE (retry=1)')
                log.debug(message)

            else: # self.state == self.STATE_ACK
                message = InstantProtocolMessage(dictdata=dictdata)
                self.message_queue.append(dictdata)

                log.debug('Message queued -> STATE_ACK')
                #log.debug(message)

        elif (retry == 0): # last attempt
            message = InstantProtocolMessage(dictdata=dictdata)
            self.server.sock.sendto(message.serialize(), self.address)
            self.timer = threading.Timer(self.RESEND_TIMER, self._send, [dictdata, retry - 1])
            self.timer.start()

            log.debug('Timer expired -> Sending message last time (retry=0)')
            log.debug(message)

        elif (retry == -1): # last attempt expired
            if (self.state != self.STATE_PENDING_CONN): # the user is not connected yet
                for s in self.server.session_list:
                    if (s != self):
                        s.update_disconnection(self)

            log.info('Timer expired -> User {} disconnected'.format(self.username))
            self.server.session_list.remove(self) # remove itself from the list (other users don't know it exists)


            log.debug(self.server.session_list)

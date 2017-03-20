import threading
import logging as log

class ClientSession(object):
    STATE_IDLE = 0 # ready to send
    STATE_ACK = 1 # waiting for ack
    RESEND_TIMER = 0.5

    def __init__(self, client, username, client_id, address):
        self.client = client
        self.username = username
        self.client_id = client_id # self.group_id is not required because session is created in decentralized mode (only users of the same group)
        self.address = address
        self.state = self.STATE_IDLE
        self.last_seq_sent = 0
        self.last_seq_recv = 0
        self.message_queue = list()
        self.timer = None

    def __repr__(self):
        return 'ClientSession(username={}, client_id={}, address={}, group_type={}, last_seq_sent={}, last_seq_recv={}, state={}, message_queue={})'.format(
            self.username, self.client_id, self.address, self.last_seq_sent, self.last_seq_recv, self.state, self.message_queue)

    # only for server (id = 0x00)
    def connection_request(self, username):
        # Only when this session is server
        if ((self.client.client_id == 0x00) and (not self.client.connected)):
            self.client.username = ('{0: <8}'.format(username)).strip() # 8 bytes
            log.debug('[Connection Request] username={}'.format(username))
            self._send(dictdata={'type': ConnectionRequest.TYPE, 'ack': 0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'username': username}})

    # only for server (id = 0x00)
    def connection_accept(self, message):
        if ((self.client_id == 0x00) and (not self.client.connected)):
            self.client.connected = True
            self.client.client_id = message.options.client_id
            self.timer.cancel() # stop timer
            self.state = self.STATE_IDLE
            self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': self.client.group_id})
            log.info('[Connection] username={}, id={}'.format(self.client.username, self.client.client_id))

    # only for server (id = 0x00)
    def connection_reject(self, message):
        if ((self.client_id == 0x00) and (not self.client.connected)):
            self.timer.cancel() # stop timer
            self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': 0x00})
            if (message.options.error == 0):
                log.info('[Connection] (Failed -> maximum reached) username={}'.format(self.username))
            else:
                log.info('[Connection] (Failed -> username already taken) username={}'.format(self.username))

    def user_list_request(self):
        self._send(dictdata={'type': UserListRequest.TYPE, 'ack': 0, 'source_id': self.client.client_id, 'group_id': self.client.group_id})
        log.info('[User List Request] username={}'.format(self.client.username))

    def user_list_response(self, message):
        self.timer.cancel() # stop timer
        self.client.user_list = message.options.user_list
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': self.client.client_id})
        log.info('[User List Response] list={}'.format(self.client.user_list))

    def data_message_send(self, text):
        self._send(dictdata={'type': DataMessage.type, 'ack': 0, 'source_id': self.client.client_id, 'group_id': self.client.group_id})
        log.info('[Data Message] (Message sent) text={}'.format(text))

    def update_list(self, message):
        updated_users = message.options.user_list
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': self.client.group_id})
        log.info('[Update List] list={}'.format(updated_users))
        #for u in self.client.user_list:
            #if ()

    def update_disconnection(self, message):
        deleted_user = message.options.client_id
        self._send(dictdata={'type': message.type, 'sequence': message.sequence, 'ack': 1, 'source_id': self.client.client_id, 'group_id': self.client.group_id})
        log.info('[Update Disconnection] client_id={}'.format(deleted_user))

    def acknowledgement(self, message):
        if (message.sequence == self.last_seq_sent): # it can be for connection or any other message
            # Normal behavior
            self.state = self.STATE_IDLE
            self.timer.cancel() # stop timer
            #log.debug('[STATE_ACK] Stop timer -> {}'.format(message))
            if (len(self.message_queue)): # send first message in queue if exists
                self._send(self.message_queue.pop(0))
                log.debug('[STATE_IDLE] Message dequeued')

    # Private function (send with reliability)
    def _send(self, dictdata, retry=1):
        # When ACK not UDP reliability
        if ((dictdata.get('ack') == 0x01)):
            message = InstantProtocolMessage(dictdata=dictdata)
            self.client.sock.sendto(message.serialize(), self.address)
            log.debug('[---] Sending ACK -> {}'.format(message))
        ## UDP reliability
        # First attempt
        elif (retry == 1):
            # Can we send?
            if (self.state == self.STATE_IDLE):
                self.last_seq_sent = 1 - self.last_seq_sent # swap: 0 to 1 and viceversa
                dictdata['sequence'] = self.last_seq_sent
                message = InstantProtocolMessage(dictdata=dictdata)
                log.debug('[STATE_IDLE] Sending message (retry=1) -> {}'.format(message))
                self.client.sock.sendto(message.serialize(), self.address)
                if (self.state == self.STATE_IDLE):
                    self.state = self.STATE_ACK
                # Timer to resend
                self.timer = threading.Timer(self.RESEND_TIMER, self._send, [dictdata, retry - 1])
                self.timer.start()

            else: # self.state == self.STATE_ACK
                message = InstantProtocolMessage(dictdata=dictdata)
                self.message_queue.append(dictdata)
                log.debug('[STATE_ACK] Message queued') # don't show the message because it doesn't have sequence yet

        elif (retry == 0): # last attempt
            message = InstantProtocolMessage(dictdata=dictdata)
            log.debug('[STATE_IDLE] Sending message (retry=0) -> {}'.format(message))
            self.client.sock.sendto(message.serialize(), self.address)
            self.timer = threading.Timer(self.RESEND_TIMER, self._send, [dictdata, retry - 1])
            self.timer.start()

        elif (retry == -1): # last attempt expired
            log.info('[User unreachable] (Timer expired) username={}'.format(self.username))
            if (self in self.client.users_sessions):
                self.client.users_sessions.remove(self) # remove itself from the list (server will realize by itself)

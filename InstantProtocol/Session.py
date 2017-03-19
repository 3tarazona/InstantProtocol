
class Session(object):
    STATE_IDLE = 0
    STATE_ACK = 1

    def __init__(self, server, username, client_id, address):
        self.server = server
        self.username = username # asked later
        self.client_id = client_id # changed later
        self.group_id = 1 # public by default
        self.group_type = 0 # centralized by default (centralized = 0, decentralized = 1)
        self.address = address
        self.last_seq_sent = 0
        self.last_seq_recv = 0
        self.state = self.STATE_ACK # Waiting for ACK of the connection
        self.message_queue = list()
        self.timer = None

    def __repr__(self):
        return 'Session(username={}, client_id={}, group_id={}, group_type={}, last_seq_sent={}, las_seq_recv={}, state={})'.format(
            self.username, self.client_id, self.group_id, self.group_type, self.last_seq_sent, self.last_seq_recv, self.state)

    def acknowledgement(self, message):
        if (message.sequence == self.last_seq_sent):
            self.state = self.STATE_IDLE

    def user_list(self):
        users = list()
        for user in self.server.session_list:
            item = dict(client_id=user.client_id, group_id=user.group_id, username=user.username, ip_address=user.address[0], port=user.address[1])
            users.append(item)

        self._send({'type': _UserListResponse.TYPE, 'ack': 0, 'source_id': self.client_id, 'group_id': self.group_id, 'options': {'user_list': users}})

    def data_message(self, message):
        #self._send()
        for session in self.server.session_list:
            if ((session.client_id != self.client_id) and (session.group_id == self.group_id)):
                session._send(dictdata={'type': message.type, 'ack': 0, 'source_id': self.client_id, 'group_id': self.group_id, 'options': {'data_length': message.options.data_length, 'payload': message.options.payload}})

    def _send(self, dictdata, retry=1):
        # When ACK not UDP reliable
        if (dictdata.get('ack') == 0x01):
            message = InstantProtocolMessage(dictdata=dictdata)
            self.server.sock.sendto(message.serialize(), self.address)
        # UDP reliable
        elif (retry == -1): #end of session
            pass
            #self.server.update_disconnection(self)
        # First attempt
        elif (retry == 1):
            # Can we send?
            if (self.state == self.STATE_IDLE)):
                self.last_seq_sent = not self.last_seq_sent
                dictdata['sequence'] = self.last_seq_sent
                message = InstantProtocolMessage(dictdata=dictdata)
                self.server.sock.sendto(message.serialize(), self.address)
                self.state = self.STATE_ACK
                # Timer to resend
                self.timer = threading.Timer(10.0, _send, [dictdata, retry - 1])

            else: # self.state == self.STATE_ACK
                message = InstantProtocolMessage(dictdata=dictdata)
                self.message_queue.append(message)
                self.timer = threading.Timer(10.0, _send, [dictdata, retry - 1])

        elif (retry == 0):
            message = InstantProtocolMessage(dictdata=dictdata)
            self.server.sock.sendto(message.serialize(), self.address)

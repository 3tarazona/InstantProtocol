# Server.py
# Copyright (C) 2017
# Jesus Alberto Polo <jesus.pologarcia@imt-atlantique.net>
# Erika Tarazona <erika.tarazona@imt-atlantique.net>

import socket
import sys
import struct
import random
import logging as log
#from InstantProtocol import *
#import SocketError
#import ServerSession
# Temporal
execfile('InstantProtocol.py')
execfile('SocketError.py')
execfile('ServerSession.py')

class Server(object):
    def __init__(self, address=('localhost', 1313), buffer=1024, loss_rate=5):
        self.address = address
        self.pool_client_ids = random.sample(xrange(1, 256), 255) # random client ids
        self.pool_group_ids = random.sample(xrange(2, 256), 254) # random group ids
        self.session_list = list()
        self.sock = SocketError(socket.AF_INET, socket.SOCK_DGRAM, loss_rate) # UDP
        self.sock.bind(address)
        self.buffer = buffer
        ## Run
        #self.run()

    def run(self):
        while True:
            try:
                data, client_address = self.sock.recvfrom(self.buffer)
                message_recv = InstantProtocolMessage(rawdata=data)
                log.debug(message_recv)

                # ACK first because it's more important than type here
                if (message_recv.ack == Acknowledgement.FLAG): # ACK
                    try:
                        self._get_session(message_recv.source_id).acknowledgement(message_recv)
                    except SessionNotFound: # when ConnectionReject we can receive an ACK -> ignore it
                        pass
                elif (message_recv.type == ConnectionRequest.TYPE):
                    # Sending messages directly because session is not created yet
                    new_username = message_recv.options.username
                    # We don't create a session until it's successful
                    if (len(self.pool_client_ids) == 0):
                        log.info('[Connection] (Failed -> maximum reached) {}'.format(new_username))
                        message_reject = InstantProtocolMessage(dictdata={'type': ConnectionReject.TYPE, 'sequence': 0, 'ack': 0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'error': 0}})
                        self.sock.sendto(message_reject.serialize(), client_address)
                    elif (any(s.username == new_username for s in self.session_list)): # username not used
                        log.info('[Connection] (Failed -> username already taken) {}'.format(new_username))
                        message_reject = InstantProtocolMessage(dictdata={'type': ConnectionReject.TYPE, 'sequence': 0, 'ack': 0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'error': 1}})
                        self.sock.sendto(message_reject.serialize(), client_address)
                    else:
                        # Create new session and add it to the list
                        log.info('[Connection] username={}'.format(new_username))
                        new_session = ServerSession(self, new_username, self.pool_client_ids.pop(0), client_address)
                        self.session_list.append(new_session)

                elif (message_recv.type == UserListRequest.TYPE):
                    self._get_session(message_recv.source_id).user_list_response(message_recv)

                elif (message_recv.type == DataMessage.TYPE):
                    self._get_session(message_recv.source_id).data_message(message_recv)

                elif (message_recv.type == GroupCreationRequest.TYPE):
                    self._get_session(message_recv.source_id).group_creation_request(message_recv)

                elif (message_recv.type == GroupInvitationRequest.TYPE):
                    self._get_session(message_recv.source_id).group_invitation_request(message_recv)

                elif (message_recv.type == GroupInvitationAccept.TYPE):
                    self._get_session(message_recv.source_id).group_invitation_accept(message_recv)

                elif (message_recv.type == GroupInvitationReject.TYPE):
                    self._get_session(message_recv.source_id).group_invitation_reject(message_recv)

                elif (message_recv.type == GroupDisjointRequest.TYPE):
                    self._get_session(message_recv.source_id).group_disjoint_request(message_recv)

                elif (message_recv.type == DisconnectionRequest.TYPE):
                    # it's possible to loose an ACK when disconnection (ignore this message because the session isn't longer available)
                    session = self._get_session(message_recv.source_id)
                    if (session):
                        session.disconnection_request(message_recv)

            except KeyboardInterrupt:
                log.info('Closing server...')
                self.sock.close()
                sys.exit(0)

            except SessionNotFound:
                log.error('Session not found, message coming from unexpected source')

    def _get_session(self, source_id):
        for s in self.session_list:
            if (s.client_id == source_id):
                return s
        # Raise exception if not returned value
        raise SessionNotFound

# Execution
if __name__ == '__main__':
    log.basicConfig(format='%(levelname)s: %(message)s', level=log.DEBUG)
    sys.exit(Server(loss_rate=0).run())

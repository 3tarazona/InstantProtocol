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
    def __init__(self, address=('localhost', 1313), buffer=socket.SO_RCVBUF, loss_rate=10):
        self.address = address
        self.pool_client_ids = random.sample(xrange(1, 256), 255) # random client ids
        self.session_list = list()
        self.sock = SocketError(socket.AF_INET, socket.SOCK_DGRAM, loss_rate) # UDP
        self.sock.bind(address)
        self.buffer = buffer
        ## Run
        #self.run()

    def run(self):
        try:
            while True:
                data, client_address = self.sock.recvfrom(1024)
                message_recv = InstantProtocolMessage(rawdata=data)
                log.debug(message_recv)

                # ACK first because it's more important than type here
                if (message_recv.ack == 0x01): # ACK
                    session = self._get_session(message_recv.source_id)
                    if (session): # when ConnectionReject we can receive an ACK -> ignore it
                        session.acknowledgement(message_recv)

                elif (message_recv.type == ConnectionRequest.TYPE):
                    # Sending messages directly because session is not created yet
                    new_username = message_recv.options.username
                    # We don't create a session until it's successful
                    if (len(self.pool_client_ids) == 0):
                        message_reject = InstantProtocolMessage(dictdata={'type': ConnectionReject.TYPE, 'sequence': 0, 'ack': 0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'error': 0}})
                        self.sock.sendto(message_reject.serialize(), client_address)
                        log.info('[Connection] (Failed -> maximum reached) {}'.format(new_username))
                    elif (any(s.username == new_username for s in self.session_list)): # username not used
                        message_reject = InstantProtocolMessage(dictdata={'type': ConnectionReject.TYPE, 'sequence': 0, 'ack': 0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'error': 1}})
                        self.sock.sendto(message_reject.serialize(), client_address)
                        log.info('[Connection] (Failed -> username already taken) {}'.format(new_username))
                    else:
                        # Create new session and add it to the list
                        new_session = ServerSession(self, new_username, self.pool_client_ids.pop(0), client_address)
                        self.session_list.append(new_session)

                elif (message_recv.type == UserListRequest.TYPE):
                    session = self._get_session(message_recv.source_id)
                    session.user_list_response()

                elif (message_recv.type == DataMessage.TYPE):
                    session = self._get_session(message_recv.source_id)
                    session.data_message(message_recv)

                elif (message_recv.type == GroupCreationRequest.TYPE):
                    pass

                elif (message_recv.type == GroupCreationAccept.TYPE):
                    pass

                elif (message_recv.type == GroupCreationReject.TYPE):
                    pass

                elif (message_recv.type == GroupInvitationRequest.TYPE):
                    pass

                elif (message_recv.type == GroupInvitationAccept.TYPE):
                    pass

                elif (message_recv.type == GroupInvitationReject.TYPE):
                    pass

                elif (message_recv.type == GroupDisjointRequest.TYPE):
                    pass

                elif (message_recv.type == DisconnectionRequest.TYPE):
                    session = self._get_session(message_recv.source_id)
                    if (session): # it's possible to loose an ACK when disconnection (ignore this message because the session isn't longer available)
                        session.disconnection_request(message_recv)

                #log.debug(self.session_list)

        except KeyboardInterrupt:
            log.info('Closing server...')
            self.sock.close()
            sys.exit(0)

    def _get_session(self, source_id):
        for s in self.session_list:
            if (s.client_id == source_id):
                return s

# Execution
if __name__ == '__main__':
    log.basicConfig(format='%(levelname)s: %(message)s', level=log.DEBUG)
    sys.exit(Server(loss_rate=0).run())

import socket
import sys
import struct
import logging as log
# Temporal
execfile('InstantProtocol.py')
execfile('Session.py')

class Server(object):
    def __init__(self, address=('localhost', 1313), buffer=1024):
        self.address = address
        self.pool_client_ids = range(1,255) # TODO: random
        self.session_list = list()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
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

                if (message_recv.ack == 0x01):
                    for s in self.session_list:
                        if (s.client_id == message_recv.source_id):
                            s.acknowledgement(message_recv)
                            break

                elif (message_recv.type == _ConnectionRequest.TYPE):
                    # Sending messages directly because session is not created yet
                    new_username = message_recv.options.username
                    if (any(s.username == new_username for s in self.session_list)):
                        self.sock.sendto(InstantProtocolMessage(dictdata={'type': 0x02, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'error': 1}}).serialize(), client_address)
                    elif (len(self.pool_client_ids) == 0):
                        self.sock.sendto(InstantProtocolMessage(dictdata={'type': 0x02, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'error': 0}}).serialize(), client_address)
                    else:
                        # Create new session
                        new_session = Session(self, new_username, self.pool_client_ids.pop(0), client_address)
                        self.session_list.append(new_session)
                        self.sock.sendto(InstantProtocolMessage(dictdata={'type': _ConnectionAccept.TYPE, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'client_id': new_session.client_id}}).serialize(), client_address)
                        log.info('User added')
                        log.debug(self.session_list)

                elif (message_recv.type == _UserListRequest.TYPE):
                    for s in self.session_list:
                        if (s.client_id == message_recv.source_id):
                            s.user_list()
                            break

                elif (message_recv.type == _DataMessage.TYPE):
                    for s in self.session_list:
                        if (s.client_id == message_recv.source_id):
                            s.data_message(message_recv)
                            break

                #log.debug(self.session_list)

        except KeyboardInterrupt:
            log.info('Closing server...')
            self.sock.close()
            sys.exit(0)

    def update_disconnection(self, session):
        for s in self.session_list:
            if (s != session):
                s.send_update_disconnection(session)

        #self.session_list.remove(session)


    def update_users(self, session):
        for s in self.session_list:
            if (s != session):
                s.send_update_users([session])

# Execution
if __name__ == '__main__':
    log.basicConfig(format='%(levelname)s: %(message)s', level=log.DEBUG)
    sys.exit(Server().run())

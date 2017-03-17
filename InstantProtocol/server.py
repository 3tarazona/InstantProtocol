import socket
import sys
import struct
import logging as log
# Temporal
from . import InstantProtocol

class Server(object):
    def __init__(self, address=('localhost', 1313), buffer=1024):
        self.address = address
        self.client_id = 0 # no client id
        self.group_id = 0 # no group
        self.user_list = list()
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
                message_send = InstantProtocolMessage(
                                dictdata={'type': _ConnectionAccept.TYPE, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'client_id': 123}})
                log.debug(message_send)
                self.sock.sendto(message_send.serialize(), client_address)

                data, client_address = self.sock.recvfrom(1024)
                message_recv = InstantProtocolMessage(rawdata=data)
                if (message_recv.type == _UserListRequest.TYPE):
                    message_send = InstantProtocolMessage(dictdata={'type': 0x0E, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {
                    'user_list': [{'client_id': 127, 'group_id': 119, 'username': 'Jesus', 'ip_address': '127.0.0.1', 'port': 1202},
                        {'client_id': 128, 'group_id': 123, 'username': 'Erika', 'ip_address': '127.0.0.1', 'port': 1400}]}})
                    self.sock.sendto(message_send.serialize(), client_address)
        except KeyboardInterrupt:
            log.info('Closing server...')
            self.sock.close()
            sys.exit(0)

# Execution
if __name__ == '__main__':
    log.basicConfig(format='%(levelname)s: %(message)s', level=log.DEBUG)
    sys.exit(Server().run())

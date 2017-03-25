# InstantProtocol.py
# Copyright (C) 2017
# Jesus Alberto Polo <jesus.pologarcia@imt-atlantique.net>
# Erika Tarazona <erika.tarazona@imt-atlantique.net>

import struct
import socket
import sys

# Base object -> it will create any message from application or network
class InstantProtocolMessage(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |
    +-+-+-+-+-+-+-+-+
    """
    HEADER_FORMAT = '>BBBH'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, dictdata=None, rawdata=None):
        if dictdata:
            self.type = dictdata.get('type')
            self.reserved = 0
            self.sequence = dictdata.get('sequence')
            self.ack = dictdata.get('ack')
            self.source_id = dictdata.get('source_id')
            self.group_id = dictdata.get('group_id')
            self.options = None
            # Create different options depending on the type of the message (Factory function could be created...)
            if (self.ack == 1): self.options = Acknowledgement()
            elif (self.type == ConnectionRequest.TYPE): self.options = ConnectionRequest(dictdata=dictdata.get('options'))
            elif (self.type == ConnectionAccept.TYPE): self.options = ConnectionAccept(dictdata=dictdata.get('options'))
            elif (self.type == ConnectionReject.TYPE): self.options = ConnectionReject(dictdata=dictdata.get('options'))
            elif (self.type == UserListRequest.TYPE): self.options = UserListRequest()
            elif (self.type == UserListResponse.TYPE): self.options = UserListResponse(dictdata=dictdata.get('options'))
            elif (self.type == DataMessage.TYPE): self.options = DataMessage(dictdata=dictdata.get('options'))
            elif (self.type == GroupCreationRequest.TYPE): self.options = GroupCreationRequest(dictdata=dictdata.get('options'))
            elif (self.type == GroupCreationAccept.TYPE): self.options = GroupCreationAccept(dictdata=dictdata.get('options'))
            elif (self.type == GroupCreationReject.TYPE): self.options = GroupCreationReject()
            elif (self.type == GroupInvitationRequest.TYPE): self.options = GroupInvitationRequest(dictdata=dictdata.get('options'))
            elif (self.type == GroupInvitationAccept.TYPE): self.options = GroupInvitationAccept(dictdata=dictdata.get('options'))
            elif (self.type == GroupInvitationReject.TYPE): self.options = GroupInvitationReject(dictdata=dictdata.get('options'))
            elif (self.type == GroupDisjointRequest.TYPE): self.options = GroupDisjointRequest()
            elif (self.type == GroupDissolution.TYPE): self.options = GroupDissolution()
            elif (self.type == UpdateList.TYPE): self.options = UpdateList(dictdata=dictdata.get('options'))
            elif (self.type == UpdateDisconnection.TYPE): self.options = UpdateDisconnection(dictdata=dictdata.get('options'))
            elif (self.type == DisconnectionRequest.TYPE): self.options = DisconnectionRequest()
            # Compute header length based on both sizes
            self.header_length = self.HEADER_SIZE + self.options.size()

        elif rawdata:
            raw_header = rawdata[:self.HEADER_SIZE]
            header = struct.unpack(self.HEADER_FORMAT, raw_header)
            self.type = (header[0] & 0xF8) >> 3
            self.reserved = (header[0] & 0x04) >> 2 # reserved
            self.sequence = (header[0] & 0x02) >> 1
            self.ack = header[0] & 0x01
            self.source_id = header[1]
            self.group_id = header[2]
            self.header_length = header[3]
            self.options = None
            # Create different options depending on the type of the message
            if (self.ack == 1): self.options = Acknowledgement()
            elif (self.type == ConnectionRequest.TYPE): self.options = ConnectionRequest(rawdata=rawdata[self.HEADER_SIZE:])
            elif (self.type == ConnectionAccept.TYPE): self.options = ConnectionAccept(rawdata=rawdata[self.HEADER_SIZE:])
            elif (self.type == ConnectionReject.TYPE): self.options = ConnectionReject(rawdata=rawdata[self.HEADER_SIZE:])
            elif (self.type == UserListRequest.TYPE): self.options = UserListRequest()
            elif (self.type == UserListResponse.TYPE): self.options = UserListResponse(rawdata=rawdata[self.HEADER_SIZE:])
            elif (self.type == DataMessage.TYPE): self.options = DataMessage(rawdata=rawdata[self.HEADER_SIZE:])
            elif (self.type == GroupCreationRequest.TYPE): self.options = GroupCreationRequest(rawdata=rawdata[self.HEADER_SIZE:])
            elif (self.type == GroupCreationAccept.TYPE): self.options = GroupCreationAccept(rawdata=rawdata[self.HEADER_SIZE:])
            elif (self.type == GroupCreationReject.TYPE): self.options = GroupCreationReject()
            elif (self.type == GroupInvitationRequest.TYPE): self.options = GroupInvitationRequest(rawdata=rawdata[self.HEADER_SIZE:])
            elif (self.type == GroupInvitationAccept.TYPE): self.options = GroupInvitationAccept(rawdata=rawdata[self.HEADER_SIZE:])
            elif (self.type == GroupInvitationReject.TYPE): self.options = GroupInvitationReject(rawdata=rawdata[self.HEADER_SIZE:])
            elif (self.type == GroupDisjointRequest.TYPE): self.options = GroupDisjointRequest()
            elif (self.type == GroupDissolution.TYPE): self.options = GroupDissolution()
            elif (self.type == UpdateList.TYPE): self.options = UpdateList(rawdata=rawdata[self.HEADER_SIZE:])
            elif (self.type == UpdateDisconnection.TYPE): self.options = UpdateDisconnection(rawdata=rawdata[self.HEADER_SIZE:])
            elif (self.type == DisconnectionRequest.TYPE): self.options = DisconnectionRequest()

        else:
            raise(ValueError)

    def serialize(self):
        first_byte = 0x00
        first_byte |= self.type << 3
        first_byte |= self.reserved << 2 # reserved
        first_byte |= self.sequence << 1
        first_byte |= self.ack
        return '{}{}'.format(struct.pack(self.HEADER_FORMAT, first_byte, self.source_id, self.group_id, self.header_length), self.options.serialize())

    def __repr__(self):
        return 'InstantProtocolMessage(type={}, sequence={}, ack={}, source_id={}, group_id={}, header_length={}, options={})'.format(
                hex(self.type), hex(self.sequence), hex(self.ack), hex(self.source_id), hex(self.group_id), hex(self.header_length), self.options)

# These private objects will handle psudoheaders (also payload when Data Message)
class ConnectionRequest(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |                                               |
    +-+-+-+-+-+-+-+-+                                               +
    |                            Username                           |
    +               +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |
    +-+-+-+-+-+-+-+-+
    """
    TYPE = 0x00
    PSEUDOHEADER_FORMAT = '>8s'
    PSEUDOHEADER_SIZE = struct.calcsize(PSEUDOHEADER_FORMAT)

    def __init__(self, dictdata=None, rawdata=None):
        if dictdata:
            self.username = dictdata.get('username')

        elif rawdata:
            self.username = (struct.unpack(self.PSEUDOHEADER_FORMAT, rawdata)[0]).strip()

        else:
            raise(ValueError)

    def size(self):
        return self.PSEUDOHEADER_SIZE

    def serialize(self):
        normalized_username = '{0: <8}'.format(self.username) # username is always 8 bytes
        return struct.pack(self.PSEUDOHEADER_FORMAT, normalized_username)

    def __repr__(self):
        return '[username={}]'.format(self.username)

class ConnectionAccept(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |   Client ID   |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    """
    TYPE = 0x01
    PSEUDOHEADER_FORMAT = '>B'
    PSEUDOHEADER_SIZE = struct.calcsize(PSEUDOHEADER_FORMAT)

    def __init__(self, dictdata=None, rawdata=None):
        if dictdata:
            self.client_id = dictdata.get('client_id') # int

        elif rawdata:
            self.client_id = struct.unpack(self.PSEUDOHEADER_FORMAT, rawdata)[0]

        else:
            raise(ValueError)

    def size(self):
        return self.PSEUDOHEADER_SIZE

    def serialize(self):
        return struct.pack(self.PSEUDOHEADER_FORMAT, self.client_id)

    def __repr__(self):
        return '[client_id={}]'.format(self.client_id)

class ConnectionReject(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |E|   Padding   |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    """
    TYPE = 0x02
    PSEUDOHEADER_FORMAT = '>B'
    PSEUDOHEADER_SIZE = struct.calcsize(PSEUDOHEADER_FORMAT)

    def __init__(self, dictdata=None, rawdata=None):
        if dictdata:
            self.error = dictdata.get('error')

        elif rawdata:
            self.error = (struct.unpack(self.PSEUDOHEADER_FORMAT, rawdata)[0] & 0x80) >> 7

        else:
            raise(ValueError)

    def size(self):
        return self.PSEUDOHEADER_SIZE

    def serialize(self):
        first_byte = 0x00
        first_byte |= self.error << 7
        return struct.pack(self.PSEUDOHEADER_FORMAT, first_byte)

    def __repr__(self):
        return '[error={}]'.format(self.error)

class UserListRequest(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |
    +-+-+-+-+-+-+-+-+
    """
    TYPE = 0x03
    PSEUDOHEADER_FORMAT = '' # no options
    PSEUDOHEADER_SIZE = struct.calcsize(PSEUDOHEADER_FORMAT)

    def __init__(self):
        pass

    def size(self):
        return self.PSEUDOHEADER_SIZE # 0

    def serialize(self):
        return struct.pack(self.PSEUDOHEADER_FORMAT)

    def __repr__(self):
        return '[]'.format()

class UserListResponse(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |   Client ID   |    Group ID   |               |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+               +
    |                            Username                           |
    +                                                       +-+-+-+-+
    |                                                       |       |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                       IP Address                      |       |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |          Port         |
    +-+-+-+-+-+-+-+-+-+-+-+-+
    """
    TYPE = 0x04
    # Repeated format (per user)
    PSEUDOHEADER_FORMAT_REP = '>BB8sBBBBH' # IP as string of 4 bytes (to split later)
    PSEUDOHEADER_SIZE_REP = struct.calcsize(PSEUDOHEADER_FORMAT_REP)
    """
    user_list': [{'client_id': 123, 'group_id': 234, 'username':'User1', 'ip_address': '127.0.0.1', 'port': 2222}, {...}]
    """
    def __init__(self, dictdata=None, rawdata=None):
        if dictdata:
            self.user_list = dictdata.get('user_list')

        elif rawdata:
            self.user_list = list()
            for i in range(len(rawdata) / self.PSEUDOHEADER_SIZE_REP):
                offset = (i * self.PSEUDOHEADER_SIZE_REP)
                rawclient = struct.unpack(self.PSEUDOHEADER_FORMAT_REP, rawdata[offset:(offset + self.PSEUDOHEADER_SIZE_REP)])
                dictclient = dict(client_id=rawclient[0], group_id=rawclient[1], username=rawclient[2].rstrip('\0'),
                                    ip_address='{}.{}.{}.{}'.format(rawclient[3],rawclient[4],rawclient[5],rawclient[6]), port=rawclient[7])
                self.user_list.append(dictclient)
        else:
            raise(ValueError)

    def size(self):
        return len(self.user_list) * self.PSEUDOHEADER_SIZE_REP

    def serialize(self):
        serialization = ''
        for user in self.user_list:
            ip_bytes = user.get('ip_address').split('.')
            serialization = '{}{}'.format(serialization, struct.pack(self.PSEUDOHEADER_FORMAT_REP, user.get('client_id'), user.get('group_id'),
                                            user.get('username'), int(ip_bytes[0]), int(ip_bytes[1]), int(ip_bytes[2]), int(ip_bytes[3]), user.get('port')))
        return serialization

    def __repr__(self):
        return '[user_list={}]'.format(self.user_list)

class DataMessage(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |          Data Length          |    Payload    |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    """
    TYPE = 0x05
    PSEUDOHEADER_FORMAT = '>H' # Payload is not structured data of this protocol
    PSEUDOHEADER_SIZE = struct.calcsize(PSEUDOHEADER_FORMAT)
    # This message is different because we also save payload (upper layer) because it is the
    # only one which has payload so we save it here for easy coding.

    def __init__(self, dictdata=None, rawdata=None):
        if dictdata:
            self.data_length = dictdata.get('data_length')
            self.payload = dictdata.get('payload')

        elif rawdata:
            self.data_length = struct.unpack(self.PSEUDOHEADER_FORMAT, rawdata[:self.PSEUDOHEADER_SIZE])[0]
            self.payload = rawdata[self.PSEUDOHEADER_SIZE:] # rawdata[self.PSEUDOHEADER_SIZE:(self.PSEUDOHEADER_SIZE + self.data_length)]

        else:
            raise(ValueError)

    def size(self):
        return self.PSEUDOHEADER_SIZE # Size of the header (without payload)

    def serialize(self):
        return '{}{}'.format(struct.pack(self.PSEUDOHEADER_FORMAT, self.data_length), self.payload)

    def __repr__(self):
        return '[data_length={}, payload={}]'.format(self.data_length, self.payload)

class GroupCreationRequest(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |T|   Padding   |   Client ID   |   Client ID   |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    """
    TYPE = 0x06
    PSEUDOHEADER_FORMAT_BASE = '>B' # first byte is readed once
    PSEUDOHEADER_FORMAT_REP = '>B' # repeated format for each user
    PSEUDOHEADER_SIZE_BASE = struct.calcsize(PSEUDOHEADER_FORMAT_BASE)
    PSEUDOHEADER_SIZE_REP = struct.calcsize(PSEUDOHEADER_FORMAT_REP)

    def __init__(self, dictdata=None, rawdata=None):
        if dictdata:
            self.type = dictdata.get('type')
            self.client_ids = dictdata.get('client_ids')

        elif rawdata:
            self.type = (struct.unpack(self.PSEUDOHEADER_FORMAT_BASE, rawdata[:self.PSEUDOHEADER_SIZE_BASE])[0] & 0x80) >> 7
            raw_clients = rawdata[self.PSEUDOHEADER_SIZE_BASE:]
            self.client_ids = list()
            # Get clients from binary data (apply for each client ID)
            for i in range(len(raw_clients) / self.PSEUDOHEADER_SIZE_REP):
                offset = (i * self.PSEUDOHEADER_SIZE_REP)
                self.client_ids.append(struct.unpack(self.PSEUDOHEADER_FORMAT_REP, raw_clients[offset:(offset + self.PSEUDOHEADER_SIZE_REP)])[0])

        else:
            raise(ValueError)

    def size(self):
        return self.PSEUDOHEADER_SIZE_BASE + (len(self.client_ids) * self.PSEUDOHEADER_SIZE_REP)

    def serialize(self):
        first_byte = 0x00
        first_byte |= self.type << 7
        serialization = '{}'.format(struct.pack(self.PSEUDOHEADER_FORMAT_BASE, first_byte))
        # List of users after the type (1 or more users)
        for client_id in self.client_ids:
            serialization = '{}{}'.format(serialization, struct.pack(self.PSEUDOHEADER_FORMAT_REP, client_id)) # equals to serialization += struct.unpack...
        return serialization

    def __repr__(self):
        client_list = ', '.join(str(client) for client in self.client_ids)
        return '[type={}, client_ids={}]'.format(self.type, client_list)

class GroupCreationAccept(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |T|   Padding   |    Group ID   |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    """
    TYPE = 0x07
    PSEUDOHEADER_FORMAT = '>BB'
    PSEUDOHEADER_SIZE = struct.calcsize(PSEUDOHEADER_FORMAT)

    def __init__(self, dictdata=None, rawdata=None):
        if dictdata:
            self.type = dictdata.get('type')
            self.group_id = dictdata.get('group_id')

        elif rawdata:
            pseudoheader = struct.unpack(self.PSEUDOHEADER_FORMAT, rawdata)
            self.type = (pseudoheader[0] & 0x80) >> 7
            self.group_id = pseudoheader[1]

        else:
            raise(ValueError)

    def size(self):
        return self.PSEUDOHEADER_SIZE

    def serialize(self):
        first_byte = 0x00
        first_byte |= self.type << 7
        return struct.pack(self.PSEUDOHEADER_FORMAT, first_byte, self.group_id)

    def __repr__(self):
        return '[type={}, group_id={}]'.format(self.type, self.group_id)

class GroupCreationReject(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |
    +-+-+-+-+-+-+-+-+
    """
    TYPE = 0x08
    PSEUDOHEADER_FORMAT = ''
    PSEUDOHEADER_SIZE = struct.calcsize(PSEUDOHEADER_FORMAT)

    def __init__(self):
        pass

    def size(self):
        return self.PSEUDOHEADER_SIZE

    def serialize(self):
        return struct.pack(self.PSEUDOHEADER_FORMAT)

    def __repr__(self):
        return '[]'.format()

class GroupInvitationRequest(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |T|   Padding   |    Group ID   |   Client ID   |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    """
    TYPE = 0x09
    PSEUDOHEADER_FORMAT = '>BBB'
    PSEUDOHEADER_SIZE = struct.calcsize(PSEUDOHEADER_FORMAT)

    def __init__(self, dictdata=None, rawdata=None):
        if dictdata:
            self.type = dictdata.get('type')
            self.group_id = dictdata.get('group_id')
            self.client_id = dictdata.get('client_id')

        elif rawdata:
            pseudoheader = struct.unpack(self.PSEUDOHEADER_FORMAT, rawdata)
            self.type = (pseudoheader[0] & 0x80) >> 7
            self.group_id = pseudoheader[1]
            self.client_id = pseudoheader[2]

        else:
            raise(ValueError)

    def size(self):
        return self.PSEUDOHEADER_SIZE

    def serialize(self):
        first_byte = 0x00
        first_byte |= self.type << 7
        return struct.pack(self.PSEUDOHEADER_FORMAT, first_byte, self.group_id, self.client_id)

    def __repr__(self):
        return '[type={}, group_id={}, client_id={}]'.format(self.type, self.group_id, self.client_id)

class GroupInvitationAccept(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |T|   Padding   |    Group ID   |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    """
    TYPE = 0x0A
    PSEUDOHEADER_FORMAT = '>BB'
    PSEUDOHEADER_SIZE = struct.calcsize(PSEUDOHEADER_FORMAT)

    def __init__(self, dictdata=None, rawdata=None):
        if dictdata:
            self.type = dictdata.get('type')
            self.group_id = dictdata.get('group_id')

        elif rawdata:
            pseudoheader = struct.unpack(self.PSEUDOHEADER_FORMAT, rawdata)
            self.type = (pseudoheader[0] & 0x80) >> 7
            self.group_id = pseudoheader[1]

        else:
            raise(ValueError)

    def size(self):
        return self.PSEUDOHEADER_SIZE

    def serialize(self):
        first_byte = 0x00
        first_byte |= self.type << 7
        return struct.pack(self.PSEUDOHEADER_FORMAT, first_byte, self.group_id)

    def __repr__(self):
        return '[type={}, group_id={}]'.format(self.type, self.group_id)

class GroupInvitationReject(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |T|   Padding   |    Group ID   |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    """
    TYPE = 0x0B
    PSEUDOHEADER_FORMAT = '>BB'
    PSEUDOHEADER_SIZE = struct.calcsize(PSEUDOHEADER_FORMAT)

    def __init__(self, dictdata=None, rawdata=None):
        if dictdata:
            self.type = dictdata.get('type')
            self.group_id = dictdata.get('group_id')

        elif rawdata:
            pseudoheader = struct.unpack(self.PSEUDOHEADER_FORMAT, rawdata)
            self.type = (pseudoheader[0] & 0x80) >> 7
            self.group_id = pseudoheader[1]

        else:
            raise(ValueError)

    def size(self):
        return self.PSEUDOHEADER_SIZE

    def serialize(self):
        first_byte = 0x00
        first_byte |= self.type << 7
        return struct.pack(self.PSEUDOHEADER_FORMAT, first_byte, self.group_id)

    def __repr__(self):
        return '[type={}, group_id={}]'.format(self.type, self.group_id)

class GroupDisjointRequest(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |
    +-+-+-+-+-+-+-+-+
    """
    TYPE = 0x0C
    PSEUDOHEADER_FORMAT = ''
    PSEUDOHEADER_SIZE = struct.calcsize(PSEUDOHEADER_FORMAT)

    def __init__(self):
        pass

    def size(self):
        return self.PSEUDOHEADER_SIZE

    def serialize(self):
        return struct.pack(self.PSEUDOHEADER_FORMAT)

    def __repr__(self):
        return '[]'.format()

class GroupDissolution(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |
    +-+-+-+-+-+-+-+-+
    """
    TYPE = 0x0D
    PSEUDOHEADER_FORMAT = ''
    PSEUDOHEADER_SIZE = struct.calcsize(PSEUDOHEADER_FORMAT)

    def __init__(self, dictdata=None, rawdata=None):
        pass

    def size(self):
        return self.PSEUDOHEADER_SIZE

    def serialize(self):
        return struct.pack(self.PSEUDOHEADER_FORMAT)

    def __repr__(self):
        return '[]'.format()

class UpdateList(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |   Client ID   |    Group ID   |               |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+               +
    |                            Username                           |
    +                                               +-+-+-+-+-+-+-+-+
    |                                               |               |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                   IP Address                  |      Port     |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |
    +-+-+-+-+-+-+-+-+
    """
    TYPE = 0x0E
    # Repeated format (per user)
    PSEUDOHEADER_FORMAT_REP = '>BB8sBBBBH' # IP as string of 4 bytes (to split later)
    PSEUDOHEADER_SIZE_REP = struct.calcsize(PSEUDOHEADER_FORMAT_REP)

    def __init__(self, dictdata=None, rawdata=None):
        if dictdata:
            self.user_list = dictdata.get('user_list')

        elif rawdata:
            self.user_list = list()
            for i in range(len(rawdata) / self.PSEUDOHEADER_SIZE_REP):
                offset = (i * self.PSEUDOHEADER_SIZE_REP)
                rawclient = struct.unpack(self.PSEUDOHEADER_FORMAT_REP, rawdata[offset:(offset + self.PSEUDOHEADER_SIZE_REP)])
                dictclient = dict(client_id=rawclient[0], group_id=rawclient[1], username=rawclient[2].rstrip('\0'),
                                    ip_address='{}.{}.{}.{}'.format(rawclient[3],rawclient[4],rawclient[5],rawclient[6]), port=rawclient[7])
                self.user_list.append(dictclient)
        else:
            raise(ValueError)

    def size(self):
        return len(self.user_list) * self.PSEUDOHEADER_SIZE_REP

    def serialize(self):
        serialization = ''
        for user in self.user_list:
            ip_bytes = user.get('ip_address').split('.')
            serialization = '{}{}'.format(serialization, struct.pack(self.PSEUDOHEADER_FORMAT_REP, user.get('client_id'), user.get('group_id'),
                                            user.get('username'), int(ip_bytes[0]), int(ip_bytes[1]), int(ip_bytes[2]), int(ip_bytes[3]), user.get('port')))
        return serialization

    def __repr__(self):
        return '[user_list={}]'.format(self.user_list)

class UpdateDisconnection(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |   Client ID   |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    """
    TYPE = 0x0F
    PSEUDOHEADER_FORMAT = '>B'
    PSEUDOHEADER_SIZE = struct.calcsize(PSEUDOHEADER_FORMAT)

    def __init__(self, dictdata=None, rawdata=None):
        if dictdata:
            self.client_id = dictdata.get('client_id')

        elif rawdata:
            self.client_id = struct.unpack(self.PSEUDOHEADER_FORMAT, rawdata)[0]

        else:
            raise(ValueError)

    def size(self):
        return self.PSEUDOHEADER_SIZE

    def serialize(self):
        return struct.pack(self.PSEUDOHEADER_FORMAT, self.client_id)

    def __repr__(self):
        return '[client_id={}]'.format(self.client_id)

class DisconnectionRequest(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |
    +-+-+-+-+-+-+-+-+
    """
    TYPE = 0x10
    PSEUDOHEADER_FORMAT = ''
    PSEUDOHEADER_SIZE = struct.calcsize(PSEUDOHEADER_FORMAT)

    def __init__(self, dictdata=None, rawdata=None):
        pass

    def size(self):
        return self.PSEUDOHEADER_SIZE

    def serialize(self):
        return struct.pack(self.PSEUDOHEADER_FORMAT)

    def __repr__(self):
        return '[]'.format()

class Acknowledgement(object):
    """
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Type  |R|S|A|   Source ID   |    Group ID   | Header Length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               |
    +-+-+-+-+-+-+-+-+
    """
    # TYPE = depends on the message which is being acknowledged
    FLAG = 0x01
    PSEUDOHEADER_FORMAT = ''
    PSEUDOHEADER_SIZE = struct.calcsize(PSEUDOHEADER_FORMAT)

    def __init__(self):
        pass

    def size(self):
        return self.PSEUDOHEADER_SIZE

    def serialize(self):
        return struct.pack(self.PSEUDOHEADER_FORMAT)

    def __repr__(self):
        return '[ack]'.format() # print 'ack' to show that it's a special type

## Testing
#dictdata={'type': 0x00, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'username': 'Jesus'}}
#dictdata={'type': 0x01, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'client_id': 227}}
#dictdata={'type': 0x02, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'error': 1}}
#dictdata={'type': 0x03, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00}
#dictdata={'type': 0x04, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {
#   'user_list': [{'client_id': 127, 'group_id': 119, 'username': 'Jesus', 'ip_address': '127.0.0.1', 'port': 1202},
#       {'client_id': 128, 'group_id': 123, 'username': 'Erika', 'ip_address': '127.0.0.1', 'port': 1400}]}})
#dictdata={'type': 0x05, 'sequence':1, 'ack':0, 'source_id': 22, 'group_id': 25, 'options': {'data_length': len('Testing this amazing protocol'), 'payload': 'Testing this amazing protocol'}}
#dictdata={'type': 0x06, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'type':1, 'client_ids':[1,2,3,4,5]}}
#dictdata={'type': 0x07, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'type': 0, 'group_id': 121}}
#dictdata={'type': 0x08, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00}
#dictdata={'type': 0x09, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'type': 0, 'group_id': 121}}
#dictdata={'type': 0x09, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'type': 0, 'group_id': 121}}
#dictdata={'type': 0x0A, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'type': 0, 'group_id': 121}}
#dictdata={'type': 0x0B, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'type': 0, 'group_id': 121}}
#dictdata={'type': 0x0B, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00}
#dictdata={'type': 0x0C, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00}
#dictdata={'type': 0x0D, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00}
#dictdata={'type': 0x0E, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {
#'user_list': [{'client_id': 127, 'group_id': 119, 'username': 'Jesus', 'ip_address': '127.0.0.1', 'port': 1202},
#    {'client_id': 128, 'group_id': 123, 'username': 'Erika', 'ip_address': '127.0.0.1', 'port': 1400}]}})
#dictdata={'type': 0x0F, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {'client_id': 68}}
#dictdata={'type': 0x10, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00}
#dictdata={'type': 0x10, 'sequence':0, 'ack':1, 'source_id': 0x00, 'group_id': 0x00}

"""
mes = InstantProtocolMessage(dictdata={'type': 0x0E, 'sequence':0, 'ack':0, 'source_id': 0x00, 'group_id': 0x00, 'options': {
    'user_list': [{'client_id': 127, 'group_id': 119, 'username': 'Jesus', 'ip_address': '127.0.0.1', 'port': 1202},
        {'client_id': 128, 'group_id': 123, 'username': 'Erika', 'ip_address': '127.0.0.1', 'port': 1400}]}})
print mes

address = ('localhost', 1212)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
#sock.bind(('localhost', 4242))

sock.sendto(mes.serialize(), address)

data = sock.recv(1024)

mes2 = InstantProtocolMessage(rawdata=data)
print mes2

sock.close()
"""

"""
classes for managing a client connection
"""
from json import dumps as json_dumps
from os import urandom

from .encryption import generate_login_hash, fit_to_secret_length, create_cipher, decode_token_and_secret
from .protocol import PacketBuilder, Packet, HandshakePacket, EncryptionResponsePacket, EncryptionRequestPacket
from ..mojang import has_player_joined


class ClientConnection:
    """
    represents a connected client and its state
    """
    __slots__ = "secret", "token", "cipher", "socket", "username", "uuid", "public_key", "private_key", "encrypted", "connected", "state", "loop"

    DEFAULT_QUERY = {
        "version": {
            "name": "1.16.5",
            "protocol": 754
        },
        "players": {
            "max": 0,
            "online": 0,
            "sample": []
        },
        "description": {
            "text": "Hello world"
        }
    }

    def __init__(self, socket, loop, public_key, private_key):
        self.secret = b""
        self.token = b""
        self.cipher = None
        self.socket = socket
        self.username = ""
        self.uuid = b""
        self.public_key = public_key
        self.private_key = private_key
        self.encrypted = False
        self.connected = False
        self.state = 1
        self.loop = loop

    def send_packet(self, packet):
        """
        sends a packet to the client
        :param packet: the raw data to send
        """
        # encrypt packet if connection is encrypted
        if self.encrypted:
            packet = self.cipher.encrypt(fit_to_secret_length(packet, self.secret))
        self.socket.sendall(packet)

    async def receive_packet(self):
        """
        waits for a packet and parses it
        :return: the parsed Packet instance, or None on error or timeout
        """
        # wait for a packet,
        req = await self.loop.sock_recv(self.socket, 2097151)
        if req:
            # decrypt it,
            if self.encrypted:
                req = self.cipher.decrypt(req)
            # parse it and return it
            return Packet(req)

    def handle_query(self, handshake_packet):
        """
        event that is called when the client requests a server query.
        sends the default query if not overridden.
        :param handshake_packet: the packet that triggered the event
        """
        packet = PacketBuilder(0x00)
        # send back default static query
        packet.add_string(json_dumps(ClientConnection.DEFAULT_QUERY))
        self.send_packet(packet.build())

    def handle_handshake(self, packet):
        """
        handles a handshake packet.
        not safe to override
        :param packet: the Packet instance
        """
        # parse packet as HandshakePacket
        packet = HandshakePacket(packet)
        # sometimes empty packet gets sent, ignore it
        if packet.protocol_version == 0:
            return
        # update state
        self.state = packet.next_state
        # when state is status, send query
        if self.state == 1:
            self.handle_query(packet)

    def handle_ping(self, packet):
        """
        handles a client ping and disconnects the client
        not useful to override.
        :param packet: the packet that requested the ping
        """
        # read junk from packet,
        j = packet.read_long()
        packet = PacketBuilder(0x01)
        # send it back
        packet.add_long(j)
        self.send_packet(packet.build())
        # and disconnect
        self.disconnect()

    def disconnect(self):
        """
        disconnects the client
        """
        self.connected = False

    async def block(self):
        """
        serves this client until disconnected
        """
        self.connected = True
        while self.connected:
            # wait for packet
            packet = await self.receive_packet()
            if not packet:
                continue
            if packet.packet_id == 0x00:
                # status is requested
                if self.state == 1:
                    self.handle_handshake(packet)
                # player tries to login
                elif self.state == 2:
                    self.username = packet.read_string()
                    self.token = urandom(4)
                    enc_req_pack = EncryptionRequestPacket(self.public_key, self.token)
                    self.send_packet(enc_req_pack.build())
            elif packet.packet_id == 0x01:
                # ping packet
                if self.state == 1:
                    self.handle_ping(packet)
                # encryption response, encrypted connection gets established
                elif self.state == 2:
                    await self.handle_encryption_response(packet)
        # close socket when ended
        self.socket.close()

    def send_login_success(self):
        """
        sends a login success packet to the client and upgrades the state
        :return:
        """
        packet = PacketBuilder(0x02)
        packet.add_uuid(self.uuid)
        packet.add_string(self.username)
        self.send_packet(packet.build())
        self.state = 2

    def pre_login(self, uuid, name):
        """
        event handler that is called after the session verification and the encryption has been done
        :param uuid: the uuid of the connected player
        :param name: the name of the connected player
        :return: True, if the login should be proceeded or False to disconnect the player
        """
        return True

    def post_login(self):
        """
        called after the login success packet has been sent
        """
        pass

    def login_error(self):
        """
        called when an error occurred during login
        """
        pass

    async def handle_encryption_response(self, client_packet):
        """
        handles the encryption response packet and enabled encryption and verifies the client session.
        not safe to override.
        :param client_packet: the encryption response packet that got sent by the client
        """
        # parse packet
        encryption_response = EncryptionResponsePacket(client_packet)
        # decode shared secret and control token
        token, self.secret = decode_token_and_secret(self.private_key, encryption_response.token, encryption_response.secret)
        # compare tokens
        assert token == self.token

        self.cipher = create_cipher(self.secret)
        # future packets get encrypted
        self.encrypted = True
        # login hash for verifying session
        login_hash = generate_login_hash(b"", self.secret, self.public_key)
        # request if the player has joined our server
        resp = await has_player_joined(login_hash, self.username)

        if not resp:
            # event when incorrect session
            self.login_error()
            self.disconnect()
            return

        self.username, self.uuid = resp

        # fire event, disconnect when cancelled
        if not self.pre_login(self.uuid, self.username):
            self.disconnect()
            return
        # login success packet
        self.send_login_success()
        # another event
        self.post_login()

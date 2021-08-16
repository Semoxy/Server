"""
abstraction for websocket packet building
"""
from __future__ import annotations

import json
from typing import Any, Dict, TYPE_CHECKING

from bson.objectid import ObjectId

from ..util import serialize_objectids

if TYPE_CHECKING:
    from ..mc.server import MinecraftServer


class BasePacket:
    """
    the packet base class
    this is not a valid packet
    """
    ACTION = "NULL"

    def __init__(self):
        self.json: Dict[str, Any] = {
            "action": self.ACTION,
            "data": {}
        }

    @property
    def data(self):
        """
        the data object on the output json
        """
        return self.json["data"]

    async def send(self, ws):
        """
        sends this packet to the specified client
        """
        await ws.send(json.dumps(self.json, default=serialize_objectids))


class ServerStateChangePacket(BasePacket):
    """
    sent when some properties on a server object change
    """
    ACTION = "SERVER_STATE_CHANGE"

    def __init__(self, server_id: ObjectId, **patch):
        super(ServerStateChangePacket, self).__init__()
        self.data["id"] = server_id
        self.data["patch"] = patch


class ConsoleLinePacket(BasePacket):
    """
    sent when a line is printed to the server stdout or stderr
    """
    ACTION = "CONSOLE_LINE"

    def __init__(self, server_id: ObjectId, message: str):
        super(ConsoleLinePacket, self).__init__()
        self.data["id"] = server_id
        self.data["message"] = message


class MetaMessagePacket(BasePacket):
    """
    contains debug or meta information for client developers
    """
    ACTION = "META_MESSAGE"

    def __init__(self, message: str):
        super(MetaMessagePacket, self).__init__()
        self.data["message"] = message


class ServerAddPacket(BasePacket):
    """
    sent when a new server was created
    """
    ACTION = "SERVER_ADD"

    def __init__(self, server: MinecraftServer):
        super(ServerAddPacket, self).__init__()
        self.json["data"] = server.json()


# TODO: implement addon packets


class ServerDeletePacket(BasePacket):
    """
    sent when a server was removed
    """
    ACTION = "SERVER_DELETE"

    def __init__(self, server_id: ObjectId):
        super(ServerDeletePacket, self).__init__()
        self.data["id"] = server_id


class AuthenticationErrorPacket(MetaMessagePacket):
    """
    sent when there was an error during authentication
    """
    ACTION = "AUTH_ERROR"


class AuthenticationSuccessPacket(BasePacket):
    """
    sent when the client was authorized successfully
    """
    ACTION = "AUTH_SUCCESS"

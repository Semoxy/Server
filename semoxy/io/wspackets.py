from __future__ import annotations

import json
from typing import Any, Dict, TYPE_CHECKING

from bson.objectid import ObjectId

from ..util import serialize_objectids

if TYPE_CHECKING:
    from ..mc.server import MinecraftServer


class BasePacket:
    ACTION = "NULL"

    def __init__(self):
        self.json: Dict[str, Any] = {
            "action": self.ACTION,
            "data": {}
        }

    @property
    def data(self):
        return self.json["data"]

    async def send(self, ws):
        await ws.send(json.dumps(self.json, default=serialize_objectids))


class ServerStateChangePacket(BasePacket):
    ACTION = "SERVER_STATE_CHANGE"

    def __init__(self, server_id: ObjectId, **patch):
        super(ServerStateChangePacket, self).__init__()
        self.data["id"] = server_id
        self.data["patch"] = patch


class ConsoleLinePacket(BasePacket):
    ACTION = "CONSOLE_LINE"

    def __init__(self, server_id: ObjectId, message: str):
        super(ConsoleLinePacket, self).__init__()
        self.data["id"] = server_id
        self.data["message"] = message


class MetaMessagePacket(BasePacket):
    ACTION = "META_MESSAGE"

    def __init__(self, message: str):
        super(MetaMessagePacket, self).__init__()
        self.data["message"] = message


class ServerAddPacket(BasePacket):
    ACTION = "SERVER_ADD"

    def __init__(self, server: MinecraftServer):
        super(ServerAddPacket, self).__init__()
        self.json["data"] = server.json()


# TODO: implement addon packets


class ServerDeletePacket(BasePacket):
    ACTION = "SERVER_DELETE"

    def __init__(self, server_id: ObjectId):
        super(ServerDeletePacket, self).__init__()
        self.data["id"] = server_id


class AuthenticationErrorPacket(MetaMessagePacket):
    ACTION = "AUTH_ERROR"


class AuthenticationSuccessPacket(BasePacket):
    ACTION = "AUTH_SUCCESS"

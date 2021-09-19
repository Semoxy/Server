"""
websocket session and broadcast management
"""
from __future__ import annotations

from typing import List, Set

from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

from ..models.auth import User


class WebsocketConnectionManager:
    """
    class for managing all websocket connections this semoxy instance
    """
    def __init__(self):
        self.connections: List[WebSocketConnection] = []

    async def connected(self, ws, user: User) -> WebSocketConnection:
        """
        registers a websocket to the manager
        :param ws: the websocket to register
        :param user: the user that belongs to the request
        """
        conn = WebSocketConnection(ws, user)
        self.connections.append(conn)
        return conn

    async def disconnected(self, ws):
        """
        unregisters a websocket connection to the server
        :param ws: the websocket to unregister
        """
        if isinstance(ws, WebSocketConnection):
            self.connections.remove(ws)
            return
        for conn in self.connections:
            if conn.ws == ws:
                self.connections.remove(conn)

    async def send(self, msg, *intents):
        """
        broadcasts a message to all connected clients
        :param msg: the message to send
        """
        to_disc = []
        for ws in self.connections:
            try:
                # send when no intents are passed, otherwise OR intents
                send = len(intents) == 0

                for i in intents:
                    if i in ws.intents:
                        send = True
                        break

                if send:
                    await ws.send(msg)
            except (ConnectionClosedOK, ConnectionClosedError):
                to_disc.append(ws)
        for ws in to_disc:
            await self.disconnected(ws)

    async def disconnect_all(self):
        """
        disconnects all connected clients
        """
        for conn in self.connections:
            await conn.close()


class WebSocketConnection:
    """
    Represents a WebSocket connection to a client

    Every Connection has a set of enabled intents.
    Specific events are only sent, when the client has
    enabled the corresponding intents.

    These intents exist:
        stat.614635a7e671a3df0a12154b  - Sends the following events for the server with id "614635a7e671a3df0a12154b"
                                          + STAT_UPDATE
        console.614635a7e671a3df0a12154b - Sends the following events for the server with id "614635a7e671a3df0a12154b"
                                          + CONSOLE_MESSAGE
        console.* - Sends the console events for all servers (mainly for bot users)
        stat.* - Sends the statistics events for all servers (mainly for bot users)

    Events that are always sent for all servers:
        + SERVER_START
        + PLAYER_JOIN
        + PLAYER_LEAVE
        + SERVER_STOP
        + SERVER_EXCEPTION
        + CONSOLE_COMMAND
    """
    def __init__(self, ws, user: User):
        self.ws = ws
        self.user: User = user
        self.intents: Set[str] = set()

    def disable_intent(self, intent: str):
        self.intents.remove(intent)

    def enable_intent(self, intent: str):
        self.intents.add(intent)

    async def send(self, msg):
        """
        sends a message to the client
        :param msg: the message to send
        """
        return await self.ws.send(msg)

    async def close(self):
        """
        closes the websocket connection
        """
        return await self.ws.close()

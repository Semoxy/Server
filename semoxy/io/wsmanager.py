"""
websocket session and broadcast management
"""
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

from ..models.auth import User


class WebsocketConnectionManager:
    """
    class for managing all websocket connections this semoxy instance
    """
    def __init__(self):
        self.connections = []

    async def connected(self, ws, user: User):
        """
        registers a websocket to the manager
        :param ws: the websocket to register
        :param user: the user that belongs to the request
        """
        self.connections.append(WebSocketConnection(ws, user))

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

    async def broadcast(self, msg):
        """
        broadcasts a message to all connected clients
        :param msg: the message to send
        """
        to_disc = []
        for ws in self.connections:
            try:
                await ws.send(msg)
            except (ConnectionClosedOK, ConnectionClosedError):
                to_disc.append(ws)
        for ws in to_disc:
            await self.disconnected(ws)

    async def send(self, msg):
        """
        broadcasts a message to all connected clients
        :param msg: the message to send
        """
        return await self.broadcast(msg)

    async def disconnect_all(self):
        """
        disconnects all connected clients
        """
        for conn in self.connections:
            await conn.close()


class WebSocketConnection:
    """
    represents a connection to a client
    """
    def __init__(self, ws, user: User):
        self.ws = ws
        self.user: User = user

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

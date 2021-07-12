from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

from ..models.auth import User


class WebsocketConnectionManager:
    """
    class for managing all websocket connections to a MinecraftServer
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
        broadcasts a message to all connections
        :param msg: the msg to broadcast
        """
        for ws in self.connections:
            try:
                await ws.send(msg)
            except (ConnectionClosedOK, ConnectionClosedError):
                await self.disconnected(ws)

    async def send(self, msg):
        return await self.broadcast(msg)

    async def disconnect_all(self):
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
        return await self.ws.send(msg)

    async def close(self):
        return await self.ws.close()

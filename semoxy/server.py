"""
the semoxy server main class
"""
import os
import secrets
import socket
import time
from typing import Optional

import aiohttp
import pymongo.errors
from argon2 import PasswordHasher
from motor.core import AgnosticDatabase
from odmantic import AIOEngine
from sanic import Sanic

from .endpoints import account_blueprint, version_blueprint, server_blueprint, misc_blueprint
from .io.config import Config
from .io.mongo import MongoClient
from .io.regexes import Regexes
from .mc.servermanager import ServerManager
from .models.auth import Session, User
from .util import json_response


class Semoxy(Sanic):
    """
    the Sanic server for Semoxy
    """
    __slots__ = "server_manager", "public_ip", "database", "password_hasher", "pepper"

    def __init__(self):
        super().__init__(__name__)
        Config.load(self)
        self.server_manager: ServerManager = ServerManager()
        self.register_routes()
        self.public_ip: str = ""
        self.database: Optional[AgnosticDatabase] = None
        self.password_hasher: PasswordHasher = PasswordHasher()
        self.pepper: bytes = (Config.get_docker_secret("pepper") or Config.PEPPER).encode()
        self.root_user_created: bool = True
        self.root_user_token: Optional[str] = None

    @property
    def data(self) -> AIOEngine:
        """
        shorthand for the odmantic engine
        """
        return self.mongo.odmantic

    def register_routes(self) -> None:
        """
        registers middleware, listeners and routes to sanic
        """
        self.static("static", "static")
        self.blueprint(server_blueprint)
        self.blueprint(account_blueprint)
        self.blueprint(misc_blueprint)
        self.blueprint(version_blueprint)
        self.register_listener(self._before_server_start, "before_server_start")
        self.register_listener(self._after_server_stop, "after_server_stop")
        self.register_middleware(self.set_session_middleware, "request")

    async def _after_server_stop(self, app, loop):
        """
        called when sanic has shutdown
        shuts down all minecraft servers
        """
        await self.server_manager.shutdown_all()

    @staticmethod
    async def check_ip(s):
        """
        converts an ip address or hostname to an numeric IP
        :param s: the ip to convert
        :return: the converted ip
        """
        if not Regexes.IP.match(s):
            s = socket.gethostbyname(s)
        return s

    async def reload_ip(self):
        """
        reloads the public IP of the Semoxy instance host
        """
        if Config.STATIC_IP:
            ip = Config.STATIC_IP
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.ipify.org/") as resp:
                    ip = await resp.text()
        self.public_ip = await Semoxy.check_ip(ip)

    async def _before_server_start(self, app, loop):
        """
        initialises mongo and reloads when the server starts
        """
        self.mongo = MongoClient(loop)
        self.database = self.mongo.semoxy_db
        await self.reload()

    async def check_root_user(self):
        """
        checks if a root user is existing
        if not, it sets up all variables and files to create a root user
        """
        root_user = await self.data.find_one(User, User.isRoot == True)
        if root_user:
            return

        self.root_user_created = False
        print("No root user found, generating secret")
        self.regenerate_root_creation_token()

    def regenerate_root_creation_token(self):
        """
        generates a new root creation token and dumps it into root.txt
        """
        if self.root_user_created:
            return

        self.root_user_token = secrets.token_urlsafe(48)
        with open("root.txt", "w") as f:
            f.write(self.root_user_token)

    async def reload(self):
        """
        reloads the Semoxy instance, the public IP and deletes expired sessions
        """
        await self.reload_ip()
        try:
            # invalidate expired sessions and websocket tickets
            await self.database["session"].delete_many({"expiration": {"$lt": time.time()}})
            await self.database["wsticket"].delete_many({"expiration": {"$lt": time.time()}})
            await self.server_manager.init()
        except pymongo.errors.ServerSelectionTimeoutError:
            self.stop()
            raise ConnectionError("No connection to mongodb could be established. Check your preferences in the config.json and if your mongo server is running!")
        if not Config.DISABLE_ROOT:
            await self.check_root_user()

    async def set_session_middleware(self, req):
        """
        middleware that fetches and sets the session on the request object
        """
        req.ctx.semoxy = self
        sid = req.token
        req.ctx.session = None
        req.ctx.user = None
        if sid:
            session = await self.data.find_one(Session, Session.sid == sid)
            if not session:
                return json_response({"error": "session id not existing", "status": 401}, status=401)
            if not session.is_expired:
                await session.refresh()
                req.ctx.user = session.user
                req.ctx.session = session
            else:
                await session.delete()
                return json_response({"error": "session expired", "status": 401}, status=401)

    def start(self) -> None:
        """
        starts up sanic
        """
        if not os.path.isdir(os.path.join(os.getcwd(), "servers")):
            os.mkdir(os.path.join(os.getcwd(), "servers"))

        self.run(host=os.getenv("BACKEND_HOST") or "localhost", port=os.getenv("BACKEND_PORT") or 5001)

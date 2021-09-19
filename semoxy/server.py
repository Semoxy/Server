"""
the semoxy server main class
"""
import os
import time
from typing import Optional

import pymongo.errors
from argon2 import PasswordHasher
from odmantic import AIOEngine
from sanic import Sanic

from .endpoints import account_blueprint, version_blueprint, server_blueprint, misc_blueprint
from .io.config import Config
from .io.mongo import MongoClient
from .mc.communication import ServerCommunication
from .mc.servermanager import ServerManager
from .models.auth import Session, User
from .util import renew_root_creation_token, get_public_ip, APIError, json_error


class Semoxy(Sanic):
    """
    the Sanic server for Semoxy
    """
    __slots__ = "server_manager", "public_ip", "password_hasher", "pepper"

    def __init__(self):
        super().__init__(__name__)
        Config.load(self)
        self.server_manager: ServerManager = ServerManager()
        self.register_routes()
        self.public_ip: str = ""
        self.password_hasher: PasswordHasher = PasswordHasher()
        self.pepper: bytes = (Config.get_docker_secret("pepper") or Config.PEPPER).encode()
        self.ram_cpu = self.get_total_resource_usage()

    @classmethod
    def get_total_resource_usage(cls):
        ram, cpu = ServerCommunication.get_system_resource_usage()
        server_ram, server_cpu = Config.SEMOXY_INSTANCE.server_manager.get_total_resource_usage()
        return ram + server_ram, cpu + server_cpu

    @property
    def odm(self) -> AIOEngine:
        """
        shorthand for accessing the odmantic engine
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

    async def _before_server_start(self, app, loop):
        """
        initialises mongo and reloads when the server starts
        """
        self.mongo = MongoClient(loop)
        await self.reload()

    async def get_root_user(self) -> Optional[User]:
        """
        :return: the root user of this semoxy instance, or None if none exists
        """
        return await self.odm.find_one(User, User.isRoot == True)

    async def reload(self):
        """
        reloads the Semoxy instance, the public IP and deletes expired sessions
        """
        self.public_ip = await get_public_ip()
        try:
            # remove expired sessions
            await self.mongo.semoxy_db["session"].delete_many({"expiration": {"$lt": time.time()}})
            await self.server_manager.init()
        except pymongo.errors.ServerSelectionTimeoutError:
            self.stop()
            raise ConnectionError("No connection to mongodb could be established. Check your preferences in the config.json and if your mongo server is running!")
        if not Config.DISABLE_ROOT and not await self.get_root_user():
            renew_root_creation_token()

    async def set_session_middleware(self, req):
        """
        middleware that fetches and sets the session on the request object
        """
        req.ctx.semoxy = self
        sid = req.token
        req.ctx.session = None
        req.ctx.user = None
        if sid:
            session = await self.odm.find_one(Session, Session.sid == sid)
            if not session:
                return json_error(APIError.INVALID_SESSION, "the specified session id is not existing", 401)
            if not session.is_expired:
                await session.refresh()
                req.ctx.user = session.user
                req.ctx.session = session
            else:
                await session.delete()
                return json_error(APIError.SESSION_EXPIRED, "your session is expired", 401)

    def start(self) -> None:
        """
        starts up sanic
        """
        server_dir = os.path.join(os.getcwd(), "servers")
        if not os.path.isdir(server_dir):
            os.mkdir(server_dir)

        self.run(host=os.getenv("BACKEND_HOST") or "localhost", port=os.getenv("BACKEND_PORT") or 5001)

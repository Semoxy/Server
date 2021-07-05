from __future__ import annotations

import hashlib
import time
from typing import List, Optional

from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash
from sanic.request import Request

from .base import Model
from ..io.config import Config


class User(Model):
    """
    represents a user that can login to semoxy
    """
    __collection__ = "user"
    __slots__ = "name", "email", "password", "permissions", "salt"

    def __init__(self, doc: dict):
        super(User, self).__init__(doc)
        self.name: str = doc["name"]
        self.email: str = doc["email"]
        self.password: str = doc["password"]
        self.permissions: List[str] = doc["permissions"]
        self.salt: bytes = doc["salt"].encode()

    @classmethod
    async def fetch_by_name(cls, name: str) -> Optional[User]:
        """
        fetches a user with the specified name
        :param name: the name to get the user of
        :return: User if a user was found, None instead
        """
        return await cls.fetch(name=name)

    @classmethod
    async def fetch_by_id(cls, _id: str) -> Optional[User]:
        """
        fetches a user with the specified id
        :param _id: the id to get the user of
        :return: User if a user was found, None instead
        """
        return await cls.fetch(_id=_id)

    @classmethod
    async def fetch_from_session_id(cls, sid: str) -> Optional[User]:
        """
        tries to get the user of a session id
        :param sid: the sid to get the user of
        :return: User if the user was found, else None
        """
        session = await Session.fetch_by_sid(sid)
        if not session:
            return
        return await session.get_user()

    @classmethod
    def hash_password(cls, pwd: str, salt: bytes, pepper: bytes) -> str:
        """
        hashes the password with the current hasher of the semoxy instance
        :param pwd: the actual password
        :param salt: the user-specific salt
        :param pepper: the instance-specific pepper
        :return: the password hash
        """
        return cls.semoxy().password_hasher.hash(salt + pwd.encode() + pepper)

    async def rehash_if_needed(self, spp: bytes):
        """
        rehashes the password, if needed
        :param spp: salt + password + pepper
        """
        if not self.semoxy().password_hasher.check_needs_rehash(self.password):
            return
        new_hash: str = self.semoxy().password_hasher.hash(spp)
        await self.set_attributes(password=new_hash)

    async def check_password(self, pwd: str) -> bool:
        """
        checks a password against the password of the user
        :param pwd: the password to check
        :return: True, if the password is correct. False otherwise.
        """
        spp: bytes = self.salt + pwd.encode() + self.semoxy().pepper
        try:
            self.semoxy().password_hasher.verify(self.password, spp)
            await self.rehash_if_needed(spp)
            return True
        except (VerifyMismatchError, VerificationError, InvalidHash):
            return False

    async def create_session(self) -> Session:
        """
        creates a new session with this user as user
        :return: the new session object
        """
        return await Session.new(sid=await Session.get_unused_token("sid"), expiration=int(time.time() + Config.SESSION_EXPIRATION), userId=self._id)

    async def create_ticket(self, req: Request) -> WebsocketTicket:
        """
        creates a new websocket ticket with the user
        :param req: the request object for calculating BrowserMetrics
        :return: a new WebsocketTicket
        """
        token = WebsocketTicket.get_unused_token("token")
        metrics = BrowserMetrics(req).hash

        ticket = await WebsocketTicket.new(token=token, userId=self._id, expiration=int(time.time() + Config.SESSION_EXPIRATION), browserMetrics=metrics)
        return ticket


class Session(Model):
    """
    represents a login session of a user
    """
    __slots__ = "sid", "userId", "expiration"
    __collection__ = "session"

    def __init__(self, doc):
        super(Session, self).__init__(doc)
        self.sid: str = doc["sid"]
        self.userId: Model.ObjectId = doc["userId"]
        self.expiration: int = doc["expiration"]

    @classmethod
    async def fetch_by_sid(cls, sid: str) -> Session:
        """
        fetches a session with this id
        :param sid: the sid of the session
        :return: Session if the session was found, else None
        """
        return await cls.fetch(sid=sid)

    async def get_user(self) -> User:
        """
        fetches the user of this session
        :return: the User object
        """
        return await User.fetch_by_id(self.userId)

    @property
    def is_expired(self):
        """
        whether this session is expired or not
        """
        return self.expiration < time.time()

    async def logout(self):
        """
        deletes/ invalidates this session
        """
        return await self.delete()

    async def refresh(self):
        """
        refreshes the expiration of this session
        """
        await self.set_attributes(expiration=int(time.time() + Config.SESSION_EXPIRATION))


class WebsocketTicket(Model):
    """
    represents a ticket that can be used to connect to the websocket endpoint
    """
    __slots__ = "token", "userId", "expiration", "browserMetrics"
    __collection__ = "ticket"

    def __init__(self, doc: dict):
        super(WebsocketTicket, self).__init__(doc)
        self.token: str = doc["token"]
        self.userId: Model.ObjectId = doc["userId"]
        self.expiration: int = doc["expiration"]
        self.browserMetrics: str = doc["browserMetrics"]

    @classmethod
    async def fetch_from_token(cls, token: str) -> Optional[WebsocketTicket]:
        """
        fetches a ticket with the specified token
        :return: the WebsocketTicket or None if none found
        """
        return await cls.fetch(token=token)

    async def get_user(self) -> Optional[User]:
        return await User.fetch_by_id(self.userId)

    @property
    def is_expired(self):
        """
        whether this session is expired or not
        """
        return self.expiration < time.time()


class BrowserMetrics:
    """
    class for hashing browser metrics to verify that something has been done in the same browser as before
    """
    __slots__ = "hash"

    def __init__(self, request: Request):
        h = hashlib.sha256()
        h.update(request.ip.encode())
        h.update(request.headers.get("User-Agent") or "UNKNOWN_AGENT")
        self.hash: str = h.hexdigest()

    def __str__(self):
        return self.hash

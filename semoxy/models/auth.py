from __future__ import annotations

from typing import List, Optional
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash

import time
import secrets

from .base import Model
from ..io.config import Config


class User(Model):
    """
    represents a user that can login to semoxy
    """
    __tablename__ = "user"
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
        return await Session.new(sid=await Session.get_new_sid(), expiration=int(time.time() + Config.SESSION_EXPIRATION), userId=self._id)


class Session(Model):
    """
    represents a login session of a user
    """
    __slots__ = "sid", "userId", "expiration"
    __tablename__ = "session"

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

    @classmethod
    async def get_new_sid(cls) -> str:
        """
        Method to make sure that the session id is unique
        :return: a unique session id
        """
        do = True
        sid = None
        while do:
            sid = secrets.token_urlsafe(32)
            do = bool(await cls.collection().find_one({"sid": sid}))
        return sid

    async def refresh(self):
        """
        refreshes the expiration of this session
        """
        await self.set_attributes(expiration=int(time.time() + Config.SESSION_EXPIRATION))

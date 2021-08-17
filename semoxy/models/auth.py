from __future__ import annotations

import secrets
import time
from typing import List, Optional
from odmantic import Model, Reference
from ..io.config import Config
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash


class User(Model):
    class Config:
        collection = "user"

    name: str
    email: Optional[str]
    password: str
    permissions: List[str]
    salt: str
    isRoot: bool = False

    @classmethod
    def hash_password(cls, pwd: str, salt: bytes, pepper: bytes) -> str:
        """
        hashes the password with the current hasher of the semoxy instance
        :param pwd: the actual password
        :param salt: the user-specific salt
        :param pepper: the instance-specific pepper
        :return: the password hash
        """
        return Config.SEMOXY_INSTANCE.password_hasher.hash(salt + pwd.encode() + pepper)

    async def rehash_if_needed(self, spp: bytes):
        """
        rehashes the password, if needed
        :param spp: salt + password + pepper
        """
        if not Config.SEMOXY_INSTANCE.password_hasher.check_needs_rehash(self.password):
            return
        new_hash: str = Config.SEMOXY_INSTANCE.password_hasher.hash(spp)
        self.password = new_hash
        await Config.SEMOXY_INSTANCE.data.save(self)

    async def check_password(self, pwd: str) -> bool:
        """
        checks a password against the password of the user
        :param pwd: the password to check
        :return: True, if the password is correct. False otherwise.
        """
        spp: bytes = self.salt.encode() + pwd.encode() + Config.SEMOXY_INSTANCE.pepper
        try:
            Config.SEMOXY_INSTANCE.password_hasher.verify(self.password, spp)
            await self.rehash_if_needed(spp)
            return True
        except (VerifyMismatchError, VerificationError, InvalidHash):
            return False

    async def new_session(self) -> Session:
        new_session = Session(sid=await Session.generate_sid(), user=self, expiration=int(time.time() + Config.SESSION_EXPIRATION))
        await Config.SEMOXY_INSTANCE.data.save(new_session)
        return new_session


class Session(Model):
    class Config:
        collection = "session"

    sid: str
    user: User = Reference()
    expiration: int

    @classmethod
    async def generate_sid(self) -> str:
        do = True
        sid = None
        while do:
            sid = secrets.token_urlsafe(32)
            do = bool(await Config.SEMOXY_INSTANCE.data.find_one(Session, Session.id == sid))
        return sid

    @property
    def is_expired(self) -> bool:
        """
        whether this session is expired or not
        """
        return self.expiration < time.time()

    async def delete(self):
        await Config.SEMOXY_INSTANCE.data.delete(self)

    async def refresh(self):
        self.expiration = int(time.time() + Config.SESSION_EXPIRATION)
        await Config.SEMOXY_INSTANCE.data.save(self)


"""
class BrowserMetrics:
    ""
    class for hashing browser metrics to verify that something has been done in the same browser as before
    ""
    __slots__ = "hash"

    def __init__(self, request: Request):
        h = hashlib.sha256()
        h.update(request.ip.encode())
        h.update(request.headers.get("User-Agent") or "UNKNOWN_AGENT")
        self.hash: str = h.hexdigest()

    def __str__(self):
        return self.hash
"""
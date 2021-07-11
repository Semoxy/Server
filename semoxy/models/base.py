from __future__ import annotations

import secrets
from typing import Optional, Set, TYPE_CHECKING, Dict

from bson.objectid import ObjectId
from motor.core import AgnosticCollection

if TYPE_CHECKING:
    from .. import Semoxy
from ..io.config import Config


class Model:
    """
    base class for mongodb database models
    """
    __collection__: str = "<invalid>"
    __slots__ = "_id",
    _slots: Dict[object, Set[str]] = {}

    ObjectId = ObjectId

    def __init__(self, doc):
        self._id: ObjectId = doc["_id"]

    @classmethod
    def slots(cls) -> Set[str]:
        """
        gets all attributes of this class
        """
        if cls not in cls._slots.keys():
            cls._slots[cls] = set()
            for cs in [getattr(c, "__slots__", []) for c in cls.__mro__]:
                for s in cs:
                    cls._slots[cls].add(s)
            cls._slots[cls].remove("_id")
        return cls._slots[cls]

    @classmethod
    def collection(cls) -> AgnosticCollection:
        """
        the collection this model refers to
        """
        return Config.SEMOXY_INSTANCE.database[cls.__collection__]

    @classmethod
    async def fetch(cls, **kwargs) -> Optional[Model]:
        """
        fetches a instance of this model depending on the kwargs
        :param kwargs: the keys that have to have the values
        :return: DatabaseModel, if an instance was found, None otherwise
        """
        doc = await cls.collection().find_one(kwargs)
        if not doc:
            return None
        return cls(doc)

    async def set_attributes(self, **kwargs):
        """
        sets the specified attributes on this record
        :param kwargs: the attributes and values to set
        :raises ValueError: when an attribute gets set that is not in __slots__ of this model
        """
        # don't set attributes that are not allowed by the model
        missing: Set[str] = kwargs.keys() - self.slots()
        if missing:
            raise ValueError(f"invalid attributes: {missing}")
        await self.collection().update_one({"_id": self._id}, {"$set": kwargs})

        # update attributes of this Model instance
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def semoxy(cls) -> Semoxy:
        """
        :return: the current semoxy instance
        """
        return Config.SEMOXY_INSTANCE

    @classmethod
    async def new(cls, **kwargs) -> Model:
        """
        creates a new instance of this model
        :param kwargs: the attributes of the new object
        :return: the created instance of the model
        """
        slots = cls.slots()
        missing: Set[str] = slots - kwargs.keys()

        if missing:
            raise ValueError(f"missing attributes: {missing}")

        await cls.collection().insert_one(kwargs)
        return cls(kwargs)

    async def delete(self):
        """
        deletes this instance from the database
        """
        return await self.collection().delete_one({"_id": self._id})

    @classmethod
    async def get_unused_token(cls, key: str, length: int = 32) -> str:
        """
        Method to make sure that the session id is unique
        :return: a unique session id
        """
        do = True
        sid = None
        while do:
            sid = secrets.token_urlsafe(length)
            do = bool(await cls.collection().find_one({key: sid}))
        return sid

    def json(self, include_id=True):
        """
        returns a json representation of this model instance as dict
        :param include_id: whether the ObjectId should be included in the output
        :return: a json representation of this model instance
        """
        out = {slot: getattr(self, slot) for slot in self.slots()}

        if include_id:
            out["id"] = self.id

        return out

    @property
    def id(self):
        """
        the ObjectId of this model instance
        """
        return self._id

    def __str__(self):
        return f"<{self.__class__.__name__} {' '.join([f'{s}={getattr(self, s)}' for s in self.slots()])}>"

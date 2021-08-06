from typing import Optional

from .base import Model


class ServerData(Model):
    """
    represents the data of a minecraft server
    """
    __slots__ = "name", "allocatedRAM", "dataDir", "jarFile", "onlineStatus",\
                "software", "displayName", "port", "addons", "javaVersion", "description"
    __collection__ = "server"

    def __init__(self, doc: dict):
        super(ServerData, self).__init__(doc)
        self.name: str = doc["name"]
        self.allocatedRAM: int = doc["allocatedRAM"]
        self.dataDir: str = doc["dataDir"]
        self.jarFile: str = doc["jarFile"]
        self.onlineStatus: int = doc["onlineStatus"]
        self.software: dict = doc["software"]
        self.displayName: str = doc["displayName"]
        self.port: int = doc["port"]
        self.addons: list = doc["addons"]
        self.javaVersion: str = doc["javaVersion"]
        self.description: Optional[str] = doc.get("description", None)

    @classmethod
    async def fetch_from_id(cls, _id: Model.ObjectId):
        return await cls.fetch(_id=_id)

    async def set_online_status(self, status: int):
        return await self.set_attributes(onlineStatus=status)

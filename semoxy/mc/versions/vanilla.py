import aiohttp

from .base import VersionProvider
from ...io.config import Config


class SnapshotVersionProvider(VersionProvider):
    """
    the version provider for vanilla snapshot servers
    """
    NAME = "snapshot"
    DISPLAY_NAME = "Vanilla Snapshot"
    DESCRIPTION = "Play the experimental development versions of Minecraft"
    IMAGE_URL = "$BASE/static/assets/grass_block_side.png"
    MAJOR_VERSION_NAME = "Game"
    MINOR_VERSION_NAME = "Snapshot"

    def __init__(self):
        self.versions = {}

    async def reload(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(Config.VERSIONS["vanilla"]["getVersions"]) as r:
                resp = await r.json()
        for v in resp["versions"]:
            if v["type"] == "snapshot":
                self.versions[v["id"]] = v["url"]

    async def get_major_versions(self):
        return ["minecraft"]

    async def get_minor_versions(self, major):
        if major != "minecraft":
            return []
        return list(reversed(list(self.versions.keys())))

    async def get_download(self, major, minor):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.versions[minor]) as r:
                resp = await r.json()

        url = resp["downloads"]["server"]["url"]
        return url

    async def has_version(self, major, minor):
        return major == "minecraft" and minor in self.versions.keys()

    async def get_minecraft_version(self, major, minor):
        return minor


class VanillaVersionProvider(SnapshotVersionProvider):
    """
    the version provider for vanilla servers
    """
    NAME = "vanilla"
    DISPLAY_NAME = "Vanilla"
    DESCRIPTION = "The default Minecraft Servers directly from Mojang"
    MAJOR_VERSION_NAME = "Game"
    MINOR_VERSION_NAME = "Minecraft Version"

    async def reload(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(Config.VERSIONS["vanilla"]["getVersions"]) as r:
                resp = await r.json()
        for v in resp["versions"]:
            if v["type"] == "release":
                self.versions[v["id"]] = v["url"]

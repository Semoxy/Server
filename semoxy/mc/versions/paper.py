import aiohttp

from .base import VersionProvider
from ...io.config import Config


class PaperVersionProvider(VersionProvider):
    """
    the version provider for paper servers
    """
    NAME = "paper"
    DISPLAY_NAME = "PaperMC"
    DESCRIPTION = "Paper aims to improve the performance of spigot servers"
    IMAGE_URL = "https://avatars.githubusercontent.com/u/7608950?s=200&v=4"
    MINOR_VERSION_NAME = "Paper Release"

    def __init__(self):
        self.versions = {}

    async def has_version(self, major, minor):
        return major in self.versions.keys() and minor in self.versions[major]

    async def reload(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(Config.VERSIONS["paper"]["getVersions"]) as r:
                resp = await r.json()
            for version in resp["versions"]:
                async with session.get(Config.VERSIONS["paper"]["getBuilds"].format(version=version)) as r:
                    builds = await r.json()
                self.versions[version] = [str(build) for build in builds["builds"]]

    async def get_download(self, major, minor):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    Config.VERSIONS["paper"]["getBuildDownload"].format(version=major, build=minor)) as r:
                resp = await r.json()
            download = resp["downloads"]["application"]["name"]
            return Config.VERSIONS["paper"]["downloadBuild"].format(version=major, build=minor, download=download)

    async def get_major_versions(self):
        return list(self.versions.keys())

    async def get_minor_versions(self, major):
        if major not in self.versions.keys():
            return []
        return self.versions[major]

    async def get_minecraft_version(self, major, minor):
        return major

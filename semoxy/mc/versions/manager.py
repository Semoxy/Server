"""
version management
"""
from typing import Optional

from .base import VersionProvider
from .forge import ForgeVersionProvider
from .paper import PaperVersionProvider
from .vanilla import SnapshotVersionProvider, VanillaVersionProvider


class VersionManager:
    """
    The version manager that keeps track of all version providers
    """
    def __init__(self):
        # register version provider
        self.provider = [
            PaperVersionProvider(),
            ForgeVersionProvider(),
            SnapshotVersionProvider(),
            VanillaVersionProvider()
        ]

    async def reload_all(self):
        """
        reloads all version providers
        """
        for p in self.provider:
            await p.reload()

    async def provider_by_name(self, s) -> Optional[VersionProvider]:
        """
        searches for a version provider by its software name
        :param s: the software name to search for
        :return: the VersionProvider instance if found, else None
        """
        for p in self.provider:
            if p.NAME == s:
                return p
        return None

    async def get_all_major_versions_json(self) -> list:
        """
        bundles all softwares and their major versions into a json object
        """
        out = []
        for v in self.provider:
            out.append({
                "id": v.NAME,
                "majorVersions": await v.get_major_versions(),
                "name": v.DISPLAY_NAME,
                "description": v.DESCRIPTION,
                "image": v.IMAGE_URL,
                "majorVersionName": v.MAJOR_VERSION_NAME,
                "minorVersionName": v.MINOR_VERSION_NAME
            })
        return out

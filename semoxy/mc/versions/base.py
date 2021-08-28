"""
version provider base class
"""
from typing import List


class VersionProvider:
    """
    the base class for a version provider
    A version provider is responsible for delivering and downloading all available versions for a specific server software and its addons
    """
    NAME = "version provider"
    DOWNLOAD_FILE_NAME = "server.jar"
    DISPLAY_NAME = "VersionProvider"
    DESCRIPTION = "base version provider"
    IMAGE_URL = ""
    MAJOR_VERSION_NAME = "Minecraft Version"
    MINOR_VERSION_NAME = "Build"

    async def reload(self) -> None:
        """
        should fetch all versions
        """
        pass

    async def has_version(self, major: str, minor: str) -> bool:
        """
        should check whether the specific version is valid
        :return: True if the version can be downloaded, False if not
        """
        return False

    async def get_download(self, major: str, minor: str) -> str:
        """
        should return the download url for the specified version
        :return: the url which can be used to download the jar for the specified version
        """
        return "//"

    async def post_download(self, directory: str, major: str, minor: str):
        """
        optional cleanup/ file modification/ installation after download
        :param directory: the directory where the jar was downloaded to
        :param major: the installed major version
        :param minor: the installed minor version
        """
        pass

    # TODO: addon stuff
    async def add_addon(self, addon_id, addon_type, addon_version, server_dir):
        # {"filePath": "./plugins/jei.jar", "name": "JEI", "description": "..."}
        return {}

    async def get_major_versions(self) -> List[str]:
        """
        should return all major versions available for this software
        :return: a list major version identifier strings
        """
        return []

    async def get_minor_versions(self, major: str) -> List[str]:
        """
        should return all minor versions for the specified major version
        :return: a list of all minor versions for the major version
        """
        return []

    async def get_minecraft_version(self, major: str, minor: str) -> str:
        """
        should return the minecraft client version of a specific version
        :return: the minecraft version as string. example: "1.17.1"
        """
        return ""

from typing import List


class VersionProvider:
    NAME = "version provider"
    DOWNLOAD_FILE_NAME = "server.jar"

    async def reload(self) -> None:
        pass

    async def has_version(self, major: str, minor: str) -> bool:
        return False

    async def get_download(self, major: str, minor: str) -> str:
        return "//"

    async def post_download(self, directory: str, major: str, minor: str):
        pass

    # TODO: addon stuff
    async def add_addon(self, addon_id, addon_type, addon_version, server_dir):
        # {"filePath": "./plugins/jei.jar", "name": "JEI", "description": "..."}
        return {}

    async def get_major_versions(self):
        return []

    async def get_minor_versions(self, major: str) -> List[str]:
        return []

    async def get_minecraft_version(self, major: str, minor: str) -> str:
        return ""

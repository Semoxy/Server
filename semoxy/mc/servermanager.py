"""
class for managing and caching all minecraft servers
"""
import asyncio
import os
import shutil
import sys
from typing import Optional, List

import aiofiles

from .server import MinecraftServer
from .versions.base import VersionProvider
from .versions.manager import VersionManager
from ..io.config import Config
from ..io.regexes import Regexes
from ..io.wsmanager import WebsocketConnectionManager
from ..io.wspackets import ServerAddPacket, ServerDeletePacket
from ..models.event import ServerStat
from ..models.server import Server, ServerSoftware
from ..util import json_response, download_and_save


class ServerManager:
    """
    class for managing all servers of the semoxy instance
    """
    __slots__ = "mc", "servers", "versions", "connections"

    def __init__(self):
        self.servers: List[MinecraftServer] = []
        self.versions = VersionManager()
        self.connections = WebsocketConnectionManager()

    async def init(self) -> None:
        """
        fetches all servers and adds them to its server list
        """
        self.servers = []
        async for server in Config.SEMOXY_INSTANCE.odm.find(Server):
            s = MinecraftServer(server)
            if s.data.onlineStatus == 2:  # if the server was online, start it
                await s.start()
            elif s.data.onlineStatus != 0:
                await s.set_online_status(0)
            self.servers.append(s)

        await self.versions.reload_all()
        Config.SEMOXY_INSTANCE.loop.create_task(self.server_stat_loop())

    @classmethod
    async def server_running_on(cls, port):
        """
        checks if a server is running on the specified port
        :param port: the port to check
        :return: whether there is a server running or not
        """
        return await Config.SEMOXY_INSTANCE.odm.find_one(Server, (Server.port == port) & (Server.onlineStatus != 0)) is not None

    async def get_server(self, i) -> Optional[MinecraftServer]:
        """
        returns a server for the given id
        :param i: the id of the server
        """
        for server in self.servers:
            if str(server.data.id) == i:
                return server
        return None

    async def delete_server(self, server: MinecraftServer):
        """
        Closes and deletes a server.
        Removes server files and database references
        Broadcasts deletion to clients and unloads the server from server manager
        :param server:
        :return:
        """
        if server not in self.servers:
            raise ValueError("invalid server")

        # stop server when it is online
        if 0 < server.data.onlineStatus < 3:
            stop_event = await server.stop()
            await stop_event.wait()

        # remove server files
        shutil.rmtree(server.data.dataDir, ignore_errors=False)

        # Remove server document
        await Config.SEMOXY_INSTANCE.odm.delete(server.data)

        await ServerDeletePacket(server.id).send(self)
        self.servers.remove(server)

    async def create_server(self, name: str, version_provider: VersionProvider, major_version: str, minor_version: str, ram: int, port: int, java_version: str, description: Optional[str]):
        """
        creates a new server
        :param name: the new servers name
        :param version_provider: the version provider that is used to get the version download link
        :param major_version: major version of server to install
        :param minor_version: minor version of server to install
        :param ram: the ram the server should have, can be changed later
        :param port: the port the server should run on in the future
        :param java_version: the java version that runs the server
        :param description: the optional server description
        :return: sanic json response
        """
        # check if version existing
        if not isinstance(version_provider, VersionProvider):
            return json_response({"error": "Invalid Server", "description": "use /server/versions to view all valid servers and versions", "status": 404}, status=404)
        if not await version_provider.has_version(major_version, minor_version):
            return json_response({"error": "Invalid Version", "description": "use /server/versions to view all valid servers and their versions", "status": 404}, status=404)

        # Check ram
        if ram > Config.MAX_RAM:
            return json_response({"error": "Too Much RAM", "description": "maximal ram is " + str(Config.MAX_RAM), "status": 400, "maxRam": Config.MAX_RAM}, status=400)

        if not isinstance(port, int):
            return json_response({"error": "TypeError", "description": "port has to be int", "status": 400}, status=400)

        if port < 25000 | port > 30000:
            return json_response({"error": "Invalid Port", "description": f"Port range is between 25000 and 30000", "status": 400}, status=400)

        if not Regexes.SERVER_DISPLAY_NAME.match(name):
            return json_response({"error": "Illegal Server Name", "description": f"the server name doesn't match the regex for server names", "status": 400, "regex": Regexes.SERVER_DISPLAY_NAME.pattern}, status=400)

        if java_version not in Config.JAVA["installations"].keys():
            return json_response({"error": "Invalid Java Version", "description": "there is no such java version: " + java_version, "status": 400}, status=400)

        # Lowercase, no special char server name
        display_name = name
        name = ServerManager.format_name(name)

        # check if server with name is existing
        while not await self.is_name_available(name):
            name += "-"

        # generate path name and dir
        dir_ = os.path.join(os.path.join(os.getcwd(), Config.SERVER_DIR), name)
        while os.path.isdir(dir_):
            dir_ += "-server"
        os.mkdir(dir_)

        # Download Server jar
        out_file = version_provider.DOWNLOAD_FILE_NAME
        await download_and_save(await version_provider.get_download(major_version, minor_version), os.path.join(dir_, out_file))
        # save agreed eula
        await ServerManager.save_eula(dir_)

        software = ServerSoftware(
            server=version_provider.NAME,
            majorVersion=major_version,
            minorVersion=minor_version,
            minecraftVersion=await version_provider.get_minecraft_version(major_version, minor_version)
        )

        data = Server(
            name=name,
            allocatedRAM=ram,
            dataDir=dir_,
            jarFile="server.jar",
            onlineStatus=0,
            software=software,
            displayName=display_name,
            port=port,
            addons=[],
            javaVersion=java_version,
            description=str(description) if description is not None else None
        )

        await Config.SEMOXY_INSTANCE.odm.save(data)
        s = MinecraftServer(data)

        try:
            await version_provider.post_download(dir_, major_version, minor_version)
        except Exception as e:
            await Config.SEMOXY_INSTANCE.odm.delete(s.data)
            return json_response({"error": "Error during Server Creation", "description": " ".join(e.args), "status": 500}, status=500)

        self.servers.append(s)

        await ServerAddPacket(s).send(self)
        return json_response({"success": "Server successfully created", "add": {"server": s.json()}})

    @classmethod
    async def is_name_available(cls, name):
        """
        checks whether there is no server with the specified name
        :param name: the name to check
        """
        return await Config.SEMOXY_INSTANCE.odm.find_one(Server, Server.name == name) is None

    @staticmethod
    async def save_eula(path):
        """
        saves a static minecraft eula to the specified folder
        :param path: the directory to save the eula in
        """
        async with aiofiles.open(os.path.join(path, "eula.txt"), mode="w") as f:
            await f.write("eula=true")

    async def send(self, msg):
        """
        broadcasts a message to all connected clients of this semoxy instance
        :param msg: the message to broadcast
        """
        return await self.connections.send(msg)

    async def shutdown_all(self):
        """
        shuts down all servers and blocks until this has happened
        """
        online_servers = [server for server in self.servers if server.data.onlineStatus == 2]
        await asyncio.gather(*[(await server.stop()).wait() for server in online_servers])

    async def report_server_statistics(self) -> None:
        """
        saves all server statistics like online players and ram+cpu usage to the database
        """
        logged_stats = []
        for server in self.servers:
            if not server.running:
                continue
            ram, cpu = None, None
            if sys.platform in ["linux", "linux2"]:
                ram, cpu = server.communication.get_resources()
            player_count = len(server.online_players)

            stat_log = ServerStat(
                server=server.data,
                playerCount=player_count,
                ramUsage=ram,
                cpuUsage=cpu
            )
            logged_stats.append(stat_log)
        await Config.SEMOXY_INSTANCE.odm.save_all(logged_stats)

    async def server_stat_loop(self):
        """
        reports the server statistics in 10 second intervals
        :return:
        """
        while Config.SEMOXY_INSTANCE.is_running:
            await self.report_server_statistics()
            await asyncio.sleep(10)

    @staticmethod
    def format_name(s):
        """
        removes special characters from string
        :param s: string to format
        :return: reformatted string
        """
        s = s.lower().replace(" ", "-")
        o = []
        for e in s:
            if e.isalnum() or (e == "-"):
                o.append(e)
            else:
                o.append("_")
        return "".join(o)

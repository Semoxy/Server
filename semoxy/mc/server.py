"""
class that represents a single minecraft server
"""
import os
import re
import shlex
from asyncio import Event
from typing import Any, Dict, Optional, Set, List

from bson.objectid import ObjectId

from .versions.base import VersionProvider
from ..io.config import Config
from ..io.wspackets import ServerStateChangePacket, EventPacket
from ..mc.communication import ServerCommunication
from ..models.event import ServerEvent, EventType
from ..models.server import Server


class MinecraftServer:
    """
    class that represents a single minecraft server
    """
    __slots__ = "communication", "ram_cpu", "files_to_remove", "_stop_event", "data", "online_players"

    def __init__(self, data: Server):
        self.data: Server = data
        self.communication: Optional[ServerCommunication] = None
        self.files_to_remove = []
        self._stop_event = None
        self.online_players: Set[str] = set()
        self.ram_cpu = None, None

    @property
    def start_command(self) -> List[str]:
        """
        the command that is used to start the server
        """
        args = [Config.JAVA['installations'][self.data.javaVersion]['path']]

        java_args = Config.JAVA['installations'][self.data.javaVersion]['additionalArguments']

        if java_args:
            args.extend(shlex.split(java_args))

        args.append(f"-Xmx{self.data.allocatedRAM}G")
        args.extend(["-jar", self.data.jarFile])
        args.extend(["--port", str(self.data.port)])

        return args

    @property
    def connections(self):
        """
        all connected clients
        """
        return Config.SEMOXY_INSTANCE.server_manager.connections

    @property
    def id(self) -> ObjectId:
        """
        the id of this server
        """
        return self.data.id

    async def set_online_status(self, status) -> None:
        """
        updates the online status of the server in the database and broadcasts the change to the connected sockets
        0 - offline
        1 - starting
        2 - online
        3 - stopping
        :param status: the server status to update
        """
        self.data.onlineStatus = status
        await self.data.save()

        if status == 0:
            await self.create_event(EventType.SERVER_STOP)
        elif status == 1:
            await self.create_event(EventType.SERVER_START)

        await ServerStateChangePacket(self.id, onlineStatus=status).send(self.connections)

    @property
    def running(self) -> bool:
        """
        whether the server process is running or not
        """
        if not self.communication:
            return False
        return self.communication.running

    @property
    def loop(self):
        """
        the sanic server loop
        """
        return Config.SEMOXY_INSTANCE.loop

    async def start(self) -> None:
        """
        starts the server and updates it status
        check if server is not running before calling
        """
        # shell has to be True when running with docker
        self.communication = ServerCommunication(self.loop, self.start_command, self.on_output, self.on_output, self.on_stop, cwd=self.data.dataDir)#, shell=Config.get_docker_secret("mongo_user") is not None)

        await self.set_online_status(1)
        try:
            await self.communication.begin()
            self.ram_cpu = self.communication.get_resource_usage()
        except Exception as e:
            await self.create_event(EventType.SERVER_EXCEPTION, message=str(e))
            await self.set_online_status(0)

    async def stop(self) -> Optional[Event]:
        """
        stops the server
        :return: asyncio.Event if the server is stopping now, otherwise None
        """
        if self.data.onlineStatus in [0, 3]:
            return None
        await self.send_command("stop")
        self._stop_event = Event()
        return self._stop_event

    async def on_stop(self) -> None:
        """
        called on server process end
        sets the server status to offline
        """
        self.communication.running = False
        self.ram_cpu = None, None
        await self.set_online_status(0)

        for f in self.files_to_remove:
            os.remove(f)
        self.files_to_remove = []

        if self._stop_event is not None:
            self._stop_event.set()
            self._stop_event = None

    async def on_output(self, line: str) -> None:
        """
        called when the server prints a new line to its stdout
        used to check for patterns and broadcasting to the connected websockets
        :param line: the line that is printed
        """
        line = line.strip()

        if self.data.onlineStatus == 1:
            # update online status when started
            if re.match(self.data.regexes.start, line):
                await self.set_online_status(2)

        user_join_match = re.match(self.data.regexes.playerJoin, line)
        if user_join_match:
            await self.on_player_join(user_join_match.group(1), user_join_match.group(2))

        user_leave_match = re.match(self.data.regexes.playerLeave, line)
        if user_leave_match:
            await self.on_player_leave(user_leave_match.group(1))

        await self.create_event(EventType.CONSOLE_MESSAGE, message=line)

    async def create_event(self, type_: str, **data) -> None:
        """
        creates a new event for this server and saves it to the database
        :param type_: the EventType
        :param data: the type specific event data
        """
        event = ServerEvent(
            type=type_,
            server=self.data,
            data=data
        )

        await Config.SEMOXY_INSTANCE.odm.save(event)
        intents = []
        if type_ == "CONSOLE_MESSAGE":
            intents.append(f"console.{self.id}")
            intents.append("console.*")

        await EventPacket(event).send(self.connections, *intents)

    async def on_player_join(self, player_name: str, uuid: str) -> None:
        """
        called when a player joins the server
        :param player_name: the name of the player
        :param uuid: the uuid of the player
        """
        await self.create_event(EventType.PLAYER_JOIN, name=player_name, uuid=uuid)
        self.online_players.add(player_name)

    async def on_player_leave(self, player_name: str) -> None:
        """
        called when a player leaves the server
        :param player_name: the name of the player
        """
        await self.create_event(EventType.PLAYER_LEAVE, name=player_name)
        self.online_players.remove(player_name)

    async def send_command(self, cmd: str) -> None:
        """
        prints a command to the server stdin and flushes it
        :param cmd: the command to print
        """

        if cmd.startswith("stop"):
            await self.set_online_status(3)

        await self.communication.write_stdin(cmd)

    def json(self) -> Dict[str, Any]:
        """
        convert the server to a json object
        :return: a json dict
        """

        return {
            **self.data.dict(),
            "supports": Config.VERSIONS[self.data.software.server]["supports"],
            "ramUsage": self.ram_cpu[0],
            "cpuUsage": self.ram_cpu[1],
            "onlinePlayers": self.online_players
        }

    async def get_version_provider(self) -> VersionProvider:
        """
        gets the version provider of this server
        :return: the version provider
        """
        return await Config.SEMOXY_INSTANCE.server_manager.versions.provider_by_name(self.data.software.server)

    async def delete(self):
        """
        deletes this server
        """
        await Config.SEMOXY_INSTANCE.server_manager.delete_server(self)

    async def supports(self, addon_type: str) -> bool:
        """
        checks if the server supports the specified type of addon
        """
        return Config.VERSIONS[self.data.software.server]["supports"][addon_type]

    # TODO: addon stuff
    """
    async def add_addon(self, addon_id, addon_type, addon_version):
        await self.remove_addon(addon_id)
        res = await (await self.get_version_provider()).add_addon(addon_id, addon_type, addon_version, self.data.dataDir)
        if res:
            await AddonUpdatePacket(AddonUpdatePacket.Mode.ADD, res).send(self.connections)
            await self.data.semoxy().database["server"].update_one({"_id": self.data.id}, {"$addToSet": {"addons": res}})
        return res

    async def remove_addon(self, addon_id):
        addon = await self.get_installed_addon(addon_id)
        if addon is None:
            return False
        if self.running:
            self.files_to_remove.append(addon["filePath"])
        else:
            os.remove(addon["filePath"])
        new_addon_list = []
        for ad in self.data.addons:
            if ad["id"] != addon_id:
                new_addon_list.append(ad)
        await AddonUpdatePacket(AddonUpdatePacket.Mode.REMOVE, addon).send(self.connections)
        self.data.semoxy().database["server"].update_one({"_id": self.data.id}, {"$set": {"addons": new_addon_list}})
        return True

    async def get_installed_addon(self, addon_id):
        for ad in self.data.addons:
            if ad["id"] == addon_id:
                return ad
        return None

    async def pack_addons(self, f):
        zipf = zipfile.ZipFile(f, "w")
        for addon in self.data.addons:
            zipf.write(addon["filePath"], os.path.relpath(addon["filePath"], self.data.dataDir))
        zipf.close()
    """

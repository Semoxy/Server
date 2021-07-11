import os
import zipfile
from asyncio import Event
from time import strftime
from typing import Any, Dict, Optional

from ..io.config import Config
from ..io.regexes import Regexes
from ..io.wsmanager import WebsocketConnectionManager
from ..io.wspackets import StateChangePacket, ConsoleMessagePacket, AddonUpdatePacket
from ..mc.communication import ServerCommunication
from ..models.server import ServerData


class MinecraftServer:
    """
    class for representing a single minecraft server
    """
    __slots__ = "connections", "communication", "output", "files_to_remove", "_stop_event", "data"

    CHANGEABLE_FIELDS = {
        "displayName": lambda x: Regexes.SERVER_DISPLAY_NAME.match(x),
        "port": lambda x: isinstance(x, int) and 25000 < x < 30000,
        "allocatedRAM": lambda x: isinstance(x, int) and x <= Config.MAX_RAM,
        "javaVersion": lambda x: x in Config.JAVA["installations"].keys()
    }

    def __init__(self, data: ServerData):
        self.data: ServerData = data
        self.connections = WebsocketConnectionManager()
        self.communication = None
        self.output = []
        self.files_to_remove = []
        self._stop_event = None

    @classmethod
    async def from_id(cls, _id: ServerData.ObjectId):
        data = await ServerData.fetch_from_id(_id)
        return MinecraftServer(data)

    @property
    def start_command(self) -> str:
        return f"{Config.JAVA['installations'][self.data.javaVersion]['path'] + Config.JAVA['installations'][self.data.javaVersion]['additionalArguments']} -Xmx{self.data.allocatedRAM}G -jar {self.data.jarFile} --port {self.data.port}"

    async def update(self, data):
        """
        updates the server instance based on the specified document and broadcasts the change to the clients
        :param data: the attributes to update
        :return:
        """
        await StateChangePacket(**data).send(self.connections)
        await self.data.set_attributes(**data)

    async def set_online_status(self, status) -> None:
        """
        updates the online status of the server in the database and broadcasts the change to the connected sockets
        0 - offline
        1 - starting
        2 - online
        3 - stopping
        :param status: the server status to update
        """
        await self.data.set_online_status(status)
        await StateChangePacket(onlineStatus=status).send(self.connections)

    @property
    def running(self) -> bool:
        """
        whether the server process is running or not.
        """
        if not self.communication:
            return False
        return self.communication.running

    @property
    def loop(self):
        return self.data.semoxy().loop

    async def start(self) -> None:
        """
        starts the server and updates it status
        check if server is not running before calling
        """
        # shell has to be True when running with docker
        self.communication = ServerCommunication(self.loop, self.start_command, self.on_output, self.on_output, self.on_stop, cwd=self.data.dataDir, shell=Config.get_docker_secret("mongo_user") is not None)
        self.output = []
        # Clear console on all clients
        await StateChangePacket(consoleOut=[]).send(self.connections)
        await self.set_online_status(1)
        try:
            await self.communication.begin()
        except Exception as e:
            print("Couldn't find Start Command")
            await ConsoleMessagePacket("Error: " + str(e)).send(self.connections)
            await self.set_online_status(0)

    async def stop(self) -> Optional[Event]:
        """
        stops the server
        check if server is running before calling
        :return:
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
        await self.set_online_status(0)
        for f in self.files_to_remove:
            os.remove(f)
        self.files_to_remove = []
        if self._stop_event is not None:
            self._stop_event.set()
            self._stop_event = None

    async def on_output(self, line) -> None:
        """
        called when the server prints a new line to its stdout
        used to check for patterns and broadcasting to the connected websockets
        :param line: the line that is printed
        """
        self.output.append(line)
        if self.data.onlineStatus == 1:
            if Regexes.DONE.match(line.strip()):
                await self.set_online_status(2)
        await ConsoleMessagePacket(line).send(self.connections)

    async def send_command(self, cmd) -> None:
        """
        prints a command to the server stdin and flushes it
        :param cmd: the command to print
        """
        await ConsoleMessagePacket(f"[{strftime('%H:%M:%S')} MCWEB CONSOLE COMMAND]: {cmd}").send(self.connections)
        if cmd.startswith("stop"):
            await self.set_online_status(3)
        await self.communication.write_stdin(cmd)

    def json(self) -> Dict[str, Any]:
        """
        convert the server to a json object
        :return: a json dict
        """
        return {
            **self.data.json(),
            "supports": Config.VERSIONS[self.data.software["server"]]["supports"],
            "consoleOut": self.output
        }

    async def get_version_provider(self):
        return await self.data.semoxy().server_manager.versions.provider_by_name(self.data.software["server"])

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

    async def supports(self, addon_type):
        return Config.VERSIONS[self.data.software["server"]]["supports"][addon_type]

    async def pack_addons(self, f):
        zipf = zipfile.ZipFile(f, "w")
        for addon in self.data.addons:
            zipf.write(addon["filePath"], os.path.relpath(addon["filePath"], self.data.dataDir))
        zipf.close()

    async def delete(self):
        await self.data.semoxy().server_manager.delete_server(self)

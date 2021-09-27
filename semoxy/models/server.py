
from typing import List, Optional

from odmantic import Model, EmbeddedModel, Field
from pydantic import validator

from . import SemoxyValidationError
from ..io.config import Config
from ..io.regexes import Regexes as SemoxyRegexes


class ServerSoftware(EmbeddedModel):
    server: str
    majorVersion: str
    minorVersion: str
    minecraftVersion: str


class Addon(EmbeddedModel):
    source: str
    type: str
    version: str


class Regexes(EmbeddedModel):

    # message to mark the server as started
    start: str = r'^(\[[0-9]+:[0-9]+:[0-9]+ .*\]: Timings Reset)|(\[[0-9]*:[0-9]*:[0-9]*\] \[Server thread\/INFO\]: Time elapsed: [0-9]* ms)|(\[[0-9]*:[0-9]*:[0-9]*\] \[.*\]: Done \([0-9]*[\.,][0-9]*s\)! For help, type "help"( or "\?")?)$'

    # message to notice a joined player - group(1): player name; group(2): player uuid
    playerJoin: str = r'^\[[0-9]+:[0-9]+:[0-9]+ .*\]: UUID of player (.+) is ([a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89aAbB][a-f0-9]{3}-[a-f0-9]{12})$'

    # message to notice a player leave - group(1): player name; group(2): reason for leave
    playerLeave: str = r'^\[[0-9]+:[0-9]+:[0-9]+ .*\]: (.+) lost connection: (.+)$'

    # regex that is applied to every message on the client to extract important information - group(1): message severity [INFO, WARN, ERROR]; group(2): message content
    consoleMessage: str = r"^\[[0-9]+:[0-9]+:[0-9]+\]\s\[.+\/(.+)\]:\s?(.*)$"


class Server(Model):
    class Config:
        collection = "server"
        anystr_strip_whitespace = True

    name: str
    allocatedRAM: int
    dataDir: str
    jarFile: str
    onlineStatus: int
    software: ServerSoftware
    displayName: str
    port: int
    addons: List[Addon]
    javaVersion: str
    description: Optional[str]
    regexes: Regexes = Field(default=Regexes())

    async def save(self):
        await Config.SEMOXY_INSTANCE.odm.save(self)

    @validator("allocatedRAM")
    def check_max_ram(cls, v):
        """
        makes sure that the ram of this server does not exceed the ram limit
        """
        if v > Config.MAX_RAM:
            raise SemoxyValidationError("allocatedRAM", f"the ram has to be smaller or equal to {Config.MAX_RAM}GB")
        return v

    @validator("name")
    def check_name(cls, v):
        """
        makes sure the server name matches the corresponding regex
        """
        if not SemoxyRegexes.SERVER_NAME.match(v):
            raise SemoxyValidationError("name", "the name doesn't match the requirements")
        return v

    @validator("displayName")
    def check_display_name(cls, v):
        """
        makes sure the server display name matches the corresponding regex
        """
        if not SemoxyRegexes.SERVER_DISPLAY_NAME.match(v):
            raise SemoxyValidationError("displayName", "the displayName doesn't match the requirements")
        return v

    @validator("port")
    def check_port(cls, v):
        """
        makes sure the server port is in the allowed range
        """
        if not (25000 < v < 30000):
            raise SemoxyValidationError("port", "the port isn't in the port range 25000-30000")
        return v

    @validator("javaVersion")
    def check_java_version(cls, v):
        """
        makes sure the java version of this server is valid
        """
        if v not in Config.JAVA["installations"].keys():
            raise SemoxyValidationError("javaVersion", "invalid java version")
        return v

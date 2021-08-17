
from typing import List

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
    start: str = r'^(\[[0-9]+:[0-9]+:[0-9]+ .*\]: Timings Reset)|(\[[0-9]*:[0-9]*:[0-9]*\] \[Server thread\/INFO\]: Time elapsed: [0-9]* ms)|(\[[0-9]*:[0-9]*:[0-9]*\] \[.*\]: Done \([0-9]*[\.,][0-9]*s\)! For help, type "help"( or "\?")?)$'
    playerJoin: str = r'^\[[0-9]+:[0-9]+:[0-9]+ .*\]: UUID of player (.+) is ([a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89aAbB][a-f0-9]{3}-[a-f0-9]{12})$'
    playerLeave: str = r'^\[[0-9]+:[0-9]+:[0-9]+ .*\]: (.+) lost connection: (.+)$'


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
    description: str
    regexes: Regexes = Field(default=Regexes())

    async def save(self):
        await Config.SEMOXY_INSTANCE.data.save(self)

    @validator("allocatedRAM")
    def check_max_ram(cls, v):
        if v > Config.MAX_RAM:
            raise SemoxyValidationError("allocatedRAM", f"the ram has to be smaller or equal to {Config.MAX_RAM}GB")
        return v

    @validator("name")
    def check_name(cls, v):
        if not SemoxyRegexes.SERVER_NAME.match(v):
            raise SemoxyValidationError("name", "the name doesn't match the requirements")
        return v

    @validator("displayName")
    def check_display_name(cls, v):
        if not SemoxyRegexes.SERVER_DISPLAY_NAME.match(v):
            raise SemoxyValidationError("displayName", "the displayName doesn't match the requirements")
        return v

    @validator("port")
    def check_port(cls, v):
        if not (25000 < v < 30000):
            raise SemoxyValidationError("port", "the port isn't in the port range 25000-30000")
        return v

    @validator("javaVersion")
    def check_java_version(cls, v):
        if v not in Config.JAVA["installations"].keys():
            raise SemoxyValidationError("javaVersion", "invalid java version")
        return v


from typing import List

from odmantic import Model, EmbeddedModel, Field
from pydantic import validator

from semoxy.io.config import Config as SemoxyConfig
from semoxy.io.regexes import Regexes
from semoxy.models import SemoxyValidationError


class ServerSoftware(EmbeddedModel):
    server: str
    majorVersion: str
    minorVersion: str
    minecraftVersion: str


class Addon(EmbeddedModel):
    source: str
    type: str
    version: str


class Server(Model):
    class Config:
        collection = "server"
        anystr_strip_whitespace = True

    async def save(self):
        await SemoxyConfig.SEMOXY_INSTANCE.data.save(self)

    @validator("name")
    def check_name(cls, v):
        if not Regexes.SERVER_NAME.match(v):
            raise SemoxyValidationError("name", "the name doesn't match the requirements")
        return v

    @validator("displayName")
    def check_display_name(cls, v):
        if not Regexes.SERVER_DISPLAY_NAME.match(v):
            raise SemoxyValidationError("displayName", "the displayName doesn't match the requirements")
        return v

    @validator("javaVersion")
    def check_java_version(cls, v):
        if v not in SemoxyConfig.JAVA["installations"].keys():
            raise SemoxyValidationError("javaVersion", "invalid java version")
        return v

    name: str
    allocatedRAM: int = Field(le=SemoxyConfig.MAX_RAM)
    dataDir: str
    jarFile: str
    onlineStatus: int = Field(le=3, ge=0)
    software: ServerSoftware
    displayName: str
    port: int = Field(ge=25000, lt=30000)
    addons: List[Addon]
    javaVersion: str
    description: str

from typing import Optional

from odmantic import Model, Reference

from .server import Server


class ServerStat(Model):
    class Config:
        collection = "statistic"
    server: Server = Reference()
    playerCount: int
    ramUsage: Optional[int]
    cpuUsage: Optional[int]


class EventType:
    SERVER_START = "SERVER_START"
    PLAYER_JOIN = "PLAYER_JOIN"
    PLAYER_LEAVE = "PLAYER_LEAVE"
    SERVER_STOP = "SERVER_STOP"
    SERVER_EXCEPTION = "SERVER_EXCEPTION"
    CONSOLE_COMMAND = "CONSOLE_COMMAND"
    CONSOLE_MESSAGE = "CONSOLE_MESSAGE"


class ServerEvent(Model):
    class Config:
        collection = "event"
    type: str
    data: dict
    server: Server = Reference()

from typing import Optional

from odmantic import Model, Reference

from .server import Server


class ServerStat(Model):
    """
    server stats that are saved every 10 seconds for every running server
    """
    class Config:
        collection = "statistic"
    server: Server = Reference()
    playerCount: int
    ramUsage: Optional[int]
    cpuUsage: Optional[int]


class EventType:
    """
    enum for type values for a ServerEvent
    """
    SERVER_START = "SERVER_START"
    PLAYER_JOIN = "PLAYER_JOIN"
    PLAYER_LEAVE = "PLAYER_LEAVE"
    SERVER_STOP = "SERVER_STOP"
    SERVER_EXCEPTION = "SERVER_EXCEPTION"
    CONSOLE_COMMAND = "CONSOLE_COMMAND"
    CONSOLE_MESSAGE = "CONSOLE_MESSAGE"


class ServerEvent(Model):
    """
    an event that occurs on a server like a player join or a console message
    """
    class Config:
        collection = "event"
    type: str
    data: dict
    server: Server = Reference()

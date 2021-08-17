"""
enums for permission flags
"""


class Permission:
    """
    all permission flag
    """
    class Global:
        """
        Enum for all permissions that can be applied unrelated to servers
        """
        CREATE_USER = 1 << 0
        LOGIN = 1 << 1
        CREATE_SERVER = 1 << 2
        DELETE_SERVER = 1 << 3
        GLOBAL_ADMIN = 1 << 4
        MANAGE_USER = 1 << 5

    class Server:
        """
        Enum for all permissions that are related to single servers
        """
        START_SERVER = 1 << 6
        STOP_SERVER = 1 << 7
        VIEW_SERVER = 1 << 8
        VIEW_EVENTS = 1 << 9
        CONSOLE = 1 << 10
        MANAGE_SERVER = 1 << 11
        SERVER_ADMIN = 1 << 12

        ADD_ADDON = 1 << 13
        REMOVE_ADDON = 1 << 14
        DOWNLOAD_ADDONS = 1 << 15
        MANAGE_DSM = 1 << 16
        CREATE_BACKUP = 1 << 17
        LOAD_BACKUP = 1 << 18
        REMOVE_BACKUP = 1 << 19
        CREATE_WORLD = 1 << 20
        CHANGE_WORLD = 1 << 21
        REMOVE_WORLD = 1 << 22

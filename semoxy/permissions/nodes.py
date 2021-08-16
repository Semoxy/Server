class PermissionNode:
    """
    Enum for all permissions
    """
    START_SERVER = 1 << 0
    STOP_SERVER = 1 << 1
    CREATE_USER = 1 << 2
    LOGIN = 1 << 3
    VIEW_SERVER = 1 << 4
    VIEW_EVENTS = 1 << 5
    CONSOLE = 1 << 6
    CREATE_SERVER = 1 << 7
    DELETE_SERVER = 1 << 8
    MANAGE_SERVER = 1 << 9
    ADMIN = 1 << 10

    MANAGE_USER = 1 << 11
    ADD_ADDON = 1 << 12
    REMOVE_ADDON = 1 << 13
    DOWNLOAD_ADDONS = 1 << 14
    MANAGE_DSM = 1 << 15
    CREATE_BACKUP = 1 << 16
    LOAD_BACKUP = 1 << 17
    REMOVE_BACKUP = 1 << 18
    CREATE_WORLD = 1 << 19
    CHANGE_WORLD = 1 << 20
    REMOVE_WORLD = 1 << 21

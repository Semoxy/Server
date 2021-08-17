"""
functions to check whether a user has a specific permission or not
"""
from ..models.auth import User
from ..models.server import Server
from ..io.config import Config


async def recompute_permissions(user: User) -> None:
    """
    recomputes the permissions for this user
    """
    user.permissionsOutdated = False
    await Config.SEMOXY_INSTANCE.data.save(user)


async def has_server_permission(user: User, server: Server, permission: int) -> bool:
    """
    checks whether a user has a specific permission on a server level
    :param user: the user to check the permissions of
    :param server: the server that the user wants to access
    :param permission: the permission that the user has to have
    :return: whether the user has this permission
    """
    if user.permissionsOutdated:
        await recompute_permissions(user)
    return True


async def has_global_permission(user: User, permission: int) -> bool:
    """
    checks whether a user has a specific permission on a global
    :param user: the user to check the permissions of
    :param permission: the permission that the user has to have
    :return: whether the user has this permission
    """
    if user.permissionsOutdated:
        await recompute_permissions(user)
    return True

from functools import wraps
from sanic.request import Request
from sanic.response import HTTPResponse

from .checking import has_global_permission, has_server_permission
from ..util import json_response


def requires_global_permission(permissions: int):
    """
    An endpoint decorator that requires the user to have certain permission to access
    :param permissions: the permission int the user has to match, join PermissionNodes using |
    """
    def decorator(f):
        @wraps(f)
        async def decorated_function(req: Request, *args, **kwargs) -> HTTPResponse:
            if not await has_global_permission(req.ctx.user, permissions):
                return json_response({"error": "No Permission", "description": "You don't have the permission to access this endpoint"}, status=403)

            return await f(req, *args, **kwargs)
        return decorated_function
    return decorator


def requires_server_permission(permissions: int):
    """
    An endpoint decorator that requires the user to have certain server permissions
    has to follow a semoxy.util.server_endpoint() decorator
    :param permissions: the permissions the user has to have on the current server
    """
    def decorator(f):
        @wraps(f)
        async def decorated_function(req: Request, *args, **kwargs) -> HTTPResponse:
            if not await has_server_permission(req.ctx.user, req.ctx.server, permissions):
                return json_response({"error": "No Permission", "description": "You don't have the permission to access this endpoint"}, status=403)

            return await f(req, *args, **kwargs)
        return decorated_function
    return decorator

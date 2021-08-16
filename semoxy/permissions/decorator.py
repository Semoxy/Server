from functools import wraps
from sanic.request import Request
from sanic.response import HTTPResponse


def requires_permission(nodes: int):
    """
    An endpoint decorator that requires the user to have certain permission to access
    :param nodes: the permission int the user has to match, join PermissionNodes using |
    """
    def decorator(f):
        @wraps(f)
        async def decorated_function(req: Request, *args, **kwargs) -> HTTPResponse:
            return await f(req, *args, **kwargs)
        return decorated_function
    return decorator

from __future__ import annotations

import secrets
from functools import wraps
from json import dumps as json_dumps
from os.path import split as split_path
from types import SimpleNamespace
from typing import Union, Tuple, TYPE_CHECKING, Optional
from urllib.parse import urlparse

import aiofiles
import aiohttp
from bson.objectid import ObjectId
from sanic.request import Request
from sanic.response import json, HTTPResponse

from semoxy.io.config import Config

if TYPE_CHECKING:
    from .server import Semoxy
    from .models.auth import User, Session


class SemoxyRequestContext(SimpleNamespace):
    semoxy: Semoxy
    user: Optional[User]
    session: Optional[Session]


class SemoxyRequest(Request):
    ctx: SemoxyRequestContext


def json_response(di: Union[dict, list], **kwargs) -> HTTPResponse:
    """
    generates a json response based on a dict
    translates ObjectIds to str
    :return: the created sanic.response.HTTPResponse
    """
    return json(di, dumps=lambda s: json_dumps(s, default=serialize_objectids), **kwargs)


def serialize_objectids(v):
    """
    stringifies ObjectIds
    function to be passed to json.dumps as default
    """
    # translate ObjectIds
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, set):
        return list(v)
    raise ValueError("value can't be serialized: " + str(v))


def get_path(url) -> Tuple[Union[bytes, str], Union[bytes, str]]:
    """
    extracts and splits the path of a url
    """
    return split_path(urlparse(url).path)


async def download_and_save(url: str, path: str) -> bool:
    """
    downloads a file and saves it to the given path
    :param url: the url to download
    :param path: the path of the output file
    :return: True, if the file was saved successfully
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(path, mode='wb')
                await f.write(await resp.read())
                await f.close()
                return True
    raise FileNotFoundError("file couldn't be saved")


def server_endpoint():
    """
    marks an api endpoint as a server endpoint
    needs <i> parameter in path
    fetches the server for the id and saves it to request.ctx.server for access in the endpoint
    raises json error and cancels response when server couldn't be found
    """
    def decorator(f):
        @wraps(f)
        async def decorated_function(req: Request, *args, **kwargs) -> HTTPResponse:
            if "i" not in kwargs.keys():
                return json_response({"error": "KeyError", "status": 400, "description": "please specify the server id"}, status=404)
            i = kwargs["i"]
            server = await Config.SEMOXY_INSTANCE.server_manager.get_server(i)
            if server is None:
                return json_response({"error": "Not Found", "status": 404, "description": "no server was found for your id"}, status=404)

            req.ctx.server = server
            return await f(req, *args, **kwargs)
        return decorated_function
    return decorator


def requires_server_online(online: bool = True):
    """
    decorator for a @server_endpoint()
    raises json error when the server from the @server_endpoint() hasn't the running state that is specified
    :param online: whether the server has to be online or offline for the request to pass to the handler
    """
    def decorator(f):
        @wraps(f)
        async def decorated_function(req: Request, *args, **kwargs) -> HTTPResponse:
            if online != req.ctx.server.running:
                return json_response({"error": "Invalid State", "status": 423, "description": "this endpoint requires the server to be " + ("online" if online else "offline")},
                                     status=423)
            return await f(req, *args, **kwargs)
        return decorated_function
    return decorator


def requires_post_params(*json_keys: str):
    """
    rejects post requests if they have not the specified json keys in it
    :param json_keys: the json keys that the request has to have for the handler to call
    """
    def decorator(f):
        @wraps(f)
        async def decorated_function(req: Request, *args, **kwargs) -> HTTPResponse:
            for prop in json_keys:
                if prop not in req.json.keys():
                    return json_response({"error": "KeyError", "status": 400, "description": "you need to specify " + prop, "missingField": prop}, status=404)
            return await f(req, *args, **kwargs)
        return decorated_function
    return decorator


def requires_login(logged_in: bool = True):
    """
    requires the user to be logged in to access this endpoint
    :param logged_in: whether the user has to be logged in or has to be not logged in
    """
    def decorator(f):
        @wraps(f)
        async def decorated_function(req: Request, *args, **kwargs) -> HTTPResponse:
            if logged_in and not req.ctx.user:
                return json_response({"error": "Not Logged In", "status": 401,
                                      "description": "you need to be logged in to use this"},
                                     status=401)
            if not logged_in and req.ctx.user:
                return json_response({"error": "Logged In", "status": 401,
                                      "description": "you need to be logged out to use this"},
                                     status=401)
            return await f(req, *args, **kwargs)
        return decorated_function
    return decorator


def catch_keyerrors():
    """
    catches all KeyErrors in the decorated route and cancels request
    """
    def decorator(f):
        @wraps(f)
        async def decorated_function(req: Request, *args, **kwargs) -> HTTPResponse:
            try:
                return await f(req, *args, **kwargs)
            except KeyError:
                return json_response({"error": "KeyError", "description": "there was an error, check your payload"})
        return decorated_function
    return decorator


def renew_root_creation_token() -> None:
    with open("root.txt", "w") as f:
        f.write(secrets.token_urlsafe(48))


def get_root_creation_token() -> str:
    with open("root.txt", "r") as f:
        return f.read()

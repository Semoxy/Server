import os
import shutil
import sys
from typing import Union, Tuple

from .models import WebsocketTicket

if sys.version_info.minor < 7:
    from async_generator import asynccontextmanager
else:
    from contextlib import asynccontextmanager
from functools import wraps
from json import dumps as json_dumps
from os.path import split as split_path
from urllib.parse import urlparse

import aiofiles
import aiohttp
from bson.objectid import ObjectId
from sanic.response import json, redirect, HTTPResponse
from sanic.request import Request


def json_res(di: Union[dict, list], **kwargs) -> HTTPResponse:
    """
    straight wrapper for sanic.response.json
    adds indent to the output json
    :return: the created sanic.response.HTTPResponse
    """
    return json(objid_to_str(di), dumps=lambda s: json_dumps(s, indent=2), **kwargs)


def get_path(url) -> Tuple[Union[bytes, str], Union[bytes, str]]:
    u = urlparse(url)
    return split_path(u.path)


async def download_and_save(url: str, path: str) -> bool:
    """
    downloads a file and saves it to the given path
    :param url: the url to download
    :param path: the path of the output file
    :return: True, if the server was created successfully
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(path, mode='wb')
                await f.write(await resp.read())
                await f.close()
                return True
    raise FileNotFoundError("file couldn't be saved")


def objid_to_str(d: Union[dict, list]) -> Union[dict, list]:
    """
    converts all object id objects in a json response to str
    :param d: element to convert
    :return: converted  dict
    """
    if isinstance(d, dict):
        out = {}
        for k, v in d.items():
            if isinstance(v, dict):
                v = objid_to_str(v)
            elif isinstance(v, ObjectId):
                v = str(v)
            out[k] = v
        return out
    elif isinstance(d, list):
        out = []
        for l in d:
            out.append(objid_to_str(l))
        return out
    return d


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
                return json_res({"error": "KeyError", "status": 400, "description": "please specify the server id"}, status=404)
            i = kwargs["i"]
            server = await req.app.server_manager.get_server(i)
            if server is None:
                return json_res({"error": "Not Found", "status": 404, "description": "no server was found for your id"}, status=404)
            await server.refetch()
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
                return json_res({"error": "Invalid State", "status": 423, "description": "this endpoint requires the server to be " + ("online" if online else "offline")},
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
                    return json_res({"error": "KeyError", "status": 400, "description": "you need to specify " + prop, "missingField": prop}, status=404)
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
                return redirect("/account/login")
            if not logged_in and req.ctx.user:
                return json_res({"error": "Logged In", "status": 401,
                                 "description": "you need to be logged out to use this"},
                                status=401)
            return await f(req, *args, **kwargs)
        return decorated_function
    return decorator


def console_ws():
    """
    verifies tickets for the console websocket endpoint
    """
    def decorator(f):
        @wraps(f)
        async def decorated_function(req, *args, **kwargs):
            ticket_token = req.args.get("ticket")
            if not ticket_token:
                return json_res({"error": "No Ticket Provided", "status": 401, "description": "open a ticket using /account/ticket"}, status=401)

            ticket = await WebsocketTicket.fetch_from_token(ticket_token)

            if ticket.is_expired:
                await ticket.delete()
                return json_res({"error": "Ticket expired", "status": 401, "description": "please open a new ticket"}, status=401)

            if BrowserMetrics(req).hash != ticket.browserMetrics:
                await ticket.delete()
                return json_res({"error": "Access error", "status": 400, "description": "we couldn't verify your browser"}, status=400)

            req.ctx.user = await ticket.get_user()
            if not req.ctx.user:
                await ticket.delete()
                return json_res({"error": "Invalid Ticket", "status": 401, "description": "open a ticket using /account/ticket"}, status=401)

            req.ctx.ticket = ticket

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
            except KeyError as e:
                return json_res({"error": "KeyError", "description": str(e)})
        return decorated_function
    return decorator


class _TmpDir:
    def __init__(self, path: str):
        self._path: str = path

    @property
    def path(self) -> str:
        """
        the base path of the directory
        :return:
        """
        return self._path

    def use_file(self, name: str) -> str:
        """
        returns the path to a file with the specified name in the directory
        """
        return os.path.join(self.path, name)


@asynccontextmanager
async def TempDir(path="."):
    """
    Context Manager for using temporary directory
    :param path: the path of the directory
    """
    d: _TmpDir = _TmpDir(os.path.join(path, "tmp"))
    if not os.path.isdir(d.path):
        os.mkdir(d.path)
    yield d
    shutil.rmtree(d.path)

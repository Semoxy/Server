"""
misc endpoints that effect the entire semoxy instance
"""
import os
from uuid import UUID

from sanic.blueprints import Blueprint
from sanic.response import HTTPResponse, file

from ..io.config import Config
from ..mc.mojang import download_head, get_uuid
from ..util import requires_login, json_response, renew_root_creation_token, json_error, APIError

misc_blueprint = Blueprint("misc")


@misc_blueprint.get("/info")
@requires_login()
async def get_config(_) -> HTTPResponse:
    """
    retrieves the public semoxy config
    """
    return json_response(Config.public_json())


@misc_blueprint.get("/")
async def get_status_information(_):
    """
    returns information about the running semoxy instance
    """
    has_root = bool(await Config.SEMOXY_INSTANCE.get_root_user()) or Config.DISABLE_ROOT

    if not has_root:
        renew_root_creation_token()

    return json_response({
        "software": "Semoxy",
        "repository": "https://github.com/SemoxyMC/Server",
        "version": "0.1",
        "description": "Semoxy is a universal decentralized Minecraft Server Interface for the Web",
        "issueTracker": "https://github.com/SemoxyMC/Server/issues",
        "hasRoot": has_root
    })


@misc_blueprint.get("/playerhead/<uuid:string>")
async def get_player_head(_, uuid: str):
    """
    endpoint for getting the head of a player
    """
    if not os.path.isdir("playerheads"):
        os.mkdir("playerheads")
    head_file = os.path.join("playerheads", uuid + ".png")
    if not os.path.isfile(head_file):
        if not await download_head(UUID(uuid), head_file):
            return json_error(APIError.INVALID_NAME, "this minecraft account does not exist")
    return await file(head_file, mime_type="image/png")


@misc_blueprint.get("/playerhead/name/<name:string>")
async def get_player_head_by_name(req, name: str):
    player_uuid = await get_uuid(name)

    if not player_uuid:
        return json_error(APIError.INVALID_NAME, "invalid player name")

    return await get_player_head(req, str(player_uuid))

"""
misc endpoints that effect the entire semoxy instance
"""
from sanic.blueprints import Blueprint
from sanic.response import HTTPResponse

from ..io.config import Config
from ..util import requires_login, json_response

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
    return json_response({
        "software": "Semoxy",
        "repository": "https://github.com/SemoxyMC/Server",
        "version": "0.1",
        "description": "Semoxy is a universal decentralized Minecraft Server Interface for the Web",
        "issueTracker": "https://github.com/SemoxyMC/Server/issues",
        "hasRoot": Config.SEMOXY_INSTANCE.root_user_created or Config.DISABLE_ROOT
    })

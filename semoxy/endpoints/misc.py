from sanic.blueprints import Blueprint
from sanic.response import HTTPResponse

from ..io.config import Config
from ..util import requires_login, json_response

misc_blueprint = Blueprint("misc")


@misc_blueprint.get("/config")
@requires_login()
async def get_config(_) -> HTTPResponse:
    """
    retrieves the public semoxy config
    """
    return json_response(Config.public_json())

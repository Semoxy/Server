from sanic.blueprints import Blueprint
from sanic.request import Request
from sanic.response import HTTPResponse

from ..io.config import Config
from ..util import requires_login, json_res

misc_blueprint = Blueprint("misc")


@misc_blueprint.get("/config")
@requires_login()
async def get_config(req: Request) -> HTTPResponse:
    return json_res(Config.public_json())

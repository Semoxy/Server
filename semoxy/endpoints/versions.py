from sanic.blueprints import Blueprint

from ..util import requires_login, json_response, json_error, APIError

version_blueprint = Blueprint("versions", url_prefix="versions")


@version_blueprint.get("/")
@requires_login()
async def get_all_versions(req):
    """
    endpoint for getting all major versions that can be installed on a minecraft server
    """
    return json_response(await req.app.server_manager.versions.get_all_major_versions_json())


@version_blueprint.get("/<software:string>/<major_version:string>")
@requires_login()
async def get_minor_versions(req, software, major_version):
    """
    endpoint for getting all minor versions for a specific major version
    """
    prov = await req.app.server_manager.versions.provider_by_name(software)
    if not prov:
        return json_error(APIError.INVALID_VERSION, f"there is no server software with that name: {software}")
    return json_response(await prov.get_minor_versions(major_version))

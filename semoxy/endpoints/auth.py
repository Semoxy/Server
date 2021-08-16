"""
authentication and user related endpoints
"""
from sanic.blueprints import Blueprint

from ..odm.auth import User
from ..io.config import Config
from ..util import json_response, requires_post_params, requires_login


account_blueprint = Blueprint("account", url_prefix="account")


@account_blueprint.post("/login")
@requires_login(False)
@requires_post_params("username", "password")
async def login_post(req):
    """
    post endpoint for logging in a user
    """
    user = await Config.SEMOXY_INSTANCE.data.find_one(User, User.name == req.json["username"])
    if user:
        if await user.check_password(str(req.json["password"])):
            session = await user.new_session()
            return json_response({"success": "logged in successfully", "data": {"sessionId": session.sid}})
    return json_response({"error": "Wrong Credentials", "status": 401, "description": "either username or password are wrong"}, status=401)


@account_blueprint.get("/session")
async def check_session(req):
    """
    returns information about a users session
    """
    out = {"loggedIn": req.ctx.session is not None}
    if req.ctx.session:
        out["expiration"] = req.ctx.session.expiration
        out["userId"] = req.ctx.session.user.id
    return json_response(out)


@account_blueprint.get("/logout")
@requires_login()
async def logout(req):
    """
    get endpoint for logging out a user
    """
    await req.ctx.session.delete()
    return json_response({"success": "logged out successfully", "data": {}})


@account_blueprint.get("/")
@requires_login()
async def fetch_me(req):
    """
    sends information about the current user to the client
    """
    return json_response({"username": req.ctx.user.name, "permissions": req.ctx.user.permissions})

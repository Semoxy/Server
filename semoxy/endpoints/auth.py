"""
authentication and user related endpoints
"""
from sanic.blueprints import Blueprint

from ..io.config import Config
from ..models.auth import User
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
    return json_response({"username": req.ctx.user.name})


@account_blueprint.post("/create-root-user")
@requires_post_params("username", "password", "creationSecret")
async def create_root_user(req):
    if Config.SEMOXY_INSTANCE.root_user_created:
        return json_response({"error": "Already existing", "description": "there is already a root user in this semoxy instance"}, status=400)

    if req.json["creationSecret"] != Config.SEMOXY_INSTANCE.root_user_token:
        Config.SEMOXY_INSTANCE.regenerate_root_creation_token()
        return json_response({"error": "Wrong Token", "description": "the provided token is invalid. regenerating.."}, status=400)

    if await Config.SEMOXY_INSTANCE.data.find_one(User, User.name == req.json["username"]):
        return json_response({"error": "Username in use", "description": "there is already a user with that name"}, status=400)

    salt = User.generate_salt()

    # TODO: check for duplicate usernames
    user = User(
        name=req.json["username"],
        password=User.hash_password(req.json["password"], salt.encode(), Config.SEMOXY_INSTANCE.pepper),
        salt=salt,
        isRoot=True
    )
    await Config.SEMOXY_INSTANCE.data.save(user)
    Config.SEMOXY_INSTANCE.root_user_created = True
    Config.SEMOXY_INSTANCE.root_user_token = ""

    return json_response({
        "success": "created root user"
    })


@account_blueprint.post("/create-user")
@requires_login()
@requires_post_params("username", "password", "email")
async def create_user(req):
    # TODO: implement permission system
    pass

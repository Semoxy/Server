
from typing import List
from odmantic import Model, EmbeddedModel, Field
from pydantic import validator
from .auth import User


class PermissionGroup(Model):
    name: str
    permissions: int
    members: List[User]

import base64
import io
import json
import uuid
from typing import Optional, Tuple

import aiohttp
from PIL import Image


async def has_player_joined(hash_: str, name: str) -> Optional[Tuple[str, uuid.UUID]]:
    """
    verifies the session of a player
    checks if this player has joined the server
    :param hash_: the server hash of the server to check
    :param name: the name of the player to check
    :return: None if the players session is invalid, Tuple[name, uuid] if valid
    """
    async with aiohttp.ClientSession() as s:
        async with s.get(f"https://sessionserver.mojang.com/session/minecraft/hasJoined?username={name}&serverId={hash_}") as req:
            if not req.ok or not req.content:
                return None
            data = await req.json()
    return data["name"], uuid.UUID(data["id"])


async def get_uuid(player_name: str) -> Optional[uuid.UUID]:
    """
    fetches the uuid of a minecraft player
    :param player_name: the player's name
    :return: the UUID if successful, else None
    """
    async with aiohttp.ClientSession() as s:
        async with s.get(f"https://api.mojang.com/users/profiles/minecraft/{player_name}") as req:
            if not req.ok:
                return None
            data = await req.json()
    return uuid.UUID(data["id"])


async def download_head(uuid: uuid.UUID, path: str) -> bool:
    """
    saves the player head of the specified uuid to the specified path
    :param uuid: the uuid to get the head of
    :param path: the path to save the head at
    :return: whether the operation was successful
    """
    async with aiohttp.ClientSession() as s:
        async with s.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{str(uuid)}") as req:
            if not req.ok:
                return False
            skin_url = json.loads(base64.b64decode((await req.json())["properties"][0]["value"].encode()))["textures"]["SKIN"]["url"]
        async with s.get(skin_url) as req:
            skin_data = io.BytesIO(await req.read())
    skin_img: Image.Image = Image.open(skin_data)
    skin_img = skin_img.crop((8, 8, 16, 16))
    skin_img.save(path)
    return True

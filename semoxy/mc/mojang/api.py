from .exceptions import ApiError
from .responses import *


def get_uuid(player_name) -> UUIDResponse:
	"""
	returns the uuid of the player
	:param player_name: the player to find the uuid
	:return: a UUIDResponse containing the uuid
	"""
	resp = rq.get(f"https://api.mojang.com/users/profiles/minecraft/{player_name}")
	if resp.status_code != 200:
		raise ApiError(f"Name {player_name} wasn't found by the API. Status code: {resp.status_code}")
	resp_json = resp.json()
	return UUIDResponse(resp_json["name"], resp_json["id"])


def get_skin_by_uuid(uuid) -> SkinResponse:
	"""
	fetches the skin of a player
	:param uuid: the uuid of the player
	:return: a SkinResponse containing skin information
	"""
	resp = rq.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}")
	
	if resp.status_code != 200:
		raise ApiError(f"Unknown UUID: {uuid}. Status code: {resp.status_code}")
	
	resp_json = resp.json()
	
	return SkinResponse(resp_json)
		

def get_skin_by_name(player_name) -> SkinResponse:
	"""
	fetches the skin by player name
	:param player_name: the player to get the skin of
	:return: a SkinResponse containing skin information
	"""
	uuid = get_uuid(player_name).get_uuid()
	return get_skin_by_uuid(uuid)


def has_player_joined(hash_, name) -> HasPlayerJoinedResponse:
	"""
	checks if a player has joined a server
	:param hash_: the calculated session hash
	:param name: the name of the player
	:return: a HasPlayerJoinedResponse containing the uuid and name of the player if it joined
	"""
	resp = rq.get(f"https://sessionserver.mojang.com/session/minecraft/hasJoined?username={name}&serverId={hash_}")

	if not resp.ok:
		raise ApiError(f"Request Failed. Status: {resp.status_code}")

	if not resp.content:
		return HasPlayerJoinedResponse({})
	resp_json = resp.json()
	return HasPlayerJoinedResponse(resp_json)

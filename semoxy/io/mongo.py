import urllib.parse

import motor.motor_asyncio

from ..io.config import Config


class MongoClient(motor.motor_asyncio.AsyncIOMotorClient):
    def __init__(self, mc, loop):
        username = urllib.parse.quote_plus(Config.get_docker_secret("mongo_user") or Config.MONGO['username'])
        password = urllib.parse.quote_plus(Config.get_docker_secret("mongo_password") or Config.MONGO['password'])
        mongo_address: str = Config.get_docker_secret("mongo_address") or f"{Config.MONGO['host']}:{Config.MONGO['port']}"

        uri = f"mongodb://{username}:{password}@{mongo_address}/semoxy?authSource=admin"

        super(MongoClient, self).__init__(uri, io_loop=loop)
        self.mc = mc
        self.db = self[Config.MONGO["database"]]

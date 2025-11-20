from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os

from .logger import Logger 

class MongoDB:
    def __init__(self, uri=None, db_name="BestImmo"):
        self.uri = uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        self.db_name = db_name
        self.client = None
        self.db = None
        self.logger = Logger('Database')

    def connect(self):
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.client.server_info() 
            self.db = self.client[self.db_name]
            self.logger.success(f"[MongoDB] Connected to {self.uri}, database: {self.db_name}")
        except ConnectionFailure as e:
            self.logger.error(f"[MongoDB] Failed to connect: {e}")
            raise

    def get_collection(self, name):
        if self.db is None:
            self.logger.error("MongoDB not connected. Call connect() first.")
            raise RuntimeError("MongoDB not connected. Call connect() first.")
        return self.db[name]

    def insert_one(self, collection_name, data: dict):
        self.logger.info(f"Inserting one document into collection '{collection_name}'")
        return self.get_collection(collection_name).insert_one(data)

    def find(self, collection_name, query: dict = {}):
        self.logger.info(f"Finding documents in collection '{collection_name}' with query: {query}")
        return self.get_collection(collection_name).find(query)

    def update_one(self, collection_name, query: dict, update: dict):
        self.logger.info(f"Updating one document in collection '{collection_name}' matching {query} with {update}")
        return self.get_collection(collection_name).update_one(query, {"$set": update})

    def delete_one(self, collection_name, query: dict):
        self.logger.info(f"Deleting one document from collection '{collection_name}' matching {query}")
        return self.get_collection(collection_name).delete_one(query)

    def close(self):
        if self.client:
            self.client.close()
            self.logger.info("[MongoDB] Connection closed.")

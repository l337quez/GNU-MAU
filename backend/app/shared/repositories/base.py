from bson.objectid import ObjectId


class BaseRepository:
    def __init__(self, db, collection_name: str):
        self.db = db
        self.collection = db[collection_name]

    def find(self, filter_dict: dict = None) -> list:
        if filter_dict is None:
            filter_dict = {}
        return list(self.collection.find(filter_dict))

    def find_one(self, filter_dict: dict) -> dict | None:
        return self.collection.find_one(filter_dict)

    def find_by_id(self, id_val: str | ObjectId) -> dict | None:
        if isinstance(id_val, str):
            try:
                id_val = ObjectId(id_val)
            except Exception:
                return None
        return self.collection.find_one({"_id": id_val})

    def insert_one(self, document: dict) -> dict:
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def update_one(self, filter_dict: dict, update_dict: dict):
        return self.collection.update_one(filter_dict, update_dict)

    def update_by_id(self, id_val: str | ObjectId, update_dict: dict):
        if isinstance(id_val, str):
            try:
                id_val = ObjectId(id_val)
            except Exception:
                return None
        return self.collection.update_one({"_id": id_val}, update_dict)

    def delete_one(self, filter_dict: dict):
        return self.collection.delete_one(filter_dict)

    def delete_by_id(self, id_val: str | ObjectId):
        if isinstance(id_val, str):
            try:
                id_val = ObjectId(id_val)
            except Exception:
                return None
        return self.collection.delete_one({"_id": id_val})

    def count(self, filter_dict: dict = None) -> int:
        if filter_dict is None:
            filter_dict = {}
        return self.collection.count_documents(filter_dict)

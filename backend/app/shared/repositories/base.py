from bson.objectid import ObjectId


class BaseRepository:
    """
    Base repository for all collections in the database. All queries are compatible with 
    MongoDB. But with if used Mongita not support advanced queries.
    """
    def __init__(self, db, collection_name: str):
        self.db = db
        self.collection = db[collection_name]

    def find(self, filter_dict: dict = None) -> list:
        """
        Return all documents in the collection.
        """
        if filter_dict is None:
            filter_dict = {}
        return list(self.collection.find(filter_dict))

    def find_one(self, filter_dict: dict) -> dict | None:
        """
        Return a single document that matches the filter.
        """
        return self.collection.find_one(filter_dict)

    def find_by_id(self, id_val: str | ObjectId) -> dict | None:
        """
        Return a single document by its ID.
        """
        if isinstance(id_val, str):
            try:
                id_val = ObjectId(id_val)
            except Exception:
                return None
        return self.collection.find_one({"_id": id_val})

    def insert_one(self, document: dict) -> dict:
        """
        Insert a single document into the collection.
        """
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def update_one(self, filter_dict: dict, update_dict: dict):
        """
        Update a single document that matches the filter.
        """
        return self.collection.update_one(filter_dict, update_dict)

    def update_by_id(self, id_val: str | ObjectId, update_dict: dict):
        """
        Update a single document by its ID.
        """
        if isinstance(id_val, str):
            try:
                id_val = ObjectId(id_val)
            except Exception:
                return None
        return self.collection.update_one({"_id": id_val}, update_dict)

    def delete_one(self, filter_dict: dict):
        """
        Delete a single document that matches the filter.
        """
        return self.collection.delete_one(filter_dict)

    def delete_by_id(self, id_val: str | ObjectId):
        """
        Delete a single document by its ID.
        """
        if isinstance(id_val, str):
            try:
                id_val = ObjectId(id_val)
            except Exception:
                return None
        return self.collection.delete_one({"_id": id_val})

    def count(self, filter_dict: dict = None) -> int:
        """
        Count the number of documents in the collection.
        """
        if filter_dict is None:
            filter_dict = {}
        return self.collection.count_documents(filter_dict)

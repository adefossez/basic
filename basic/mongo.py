from bson import objectid

from . import types


class _ObjectId(types.BasicType):
    def __init__(self, *, klass=objectid.ObjectId, **kwargs):
        super(_ObjectId, self).__init__(klass=klass, **kwargs)

    def _from_jsony(self, jsony, source):
        if source is types.JSON:
            return ObjectId(jsony)
        elif source is types.BSON:
            return types.validate_class(jsony, objectid.ObjectId)
        else:
            raise ValueError(f"Unsupported source {source}")

    def _to_jsony(self, value, target):
        if target is types.JSON:
            return str(value)
        elif target is types.BSON:
            return types.validate_class(value, objectid.ObjectId)
        else:
            raise ValueError(f"Unsupported target {target}")


ObjectId = _ObjectId()


class BasicCursor:
    def __init__(self, cursor, type):
        self.__cursor = cursor
        self.__type = type

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        return getattr(self.__cursor, name)

    def __iter__(self):
        for item in self.__cursor:
            yield self.__type.from_bson(item)


class BasicCollection:
    def __init__(self, collection, type):
        self.__collection = collection
        self.__type = type

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        return getattr(self.__collection, name)

    def insert_one(self, document, *args, **kwargs):
        bson_document = self.__type.to_bson(document)
        result = self.__collection.insert_one(bson_document, *args, **kwargs)
        document._id = bson_document["_id"]
        return result

    def insert_many(self, documents, *args, **kwargs):
        bson_documents = [
            self.__type.to_bson(document) for document in documents
        ]
        result = self.__collection.insert_many(bson_documents, *args, **kwargs)
        for document, bson_document in zip(documents, bson_documents):
            document._id = bson_document["_id"]
        return result

    def replace_one(self, filter, replacement, *args, **kwargs):
        return self.__collection.replace_one(filter,
                                             self.__type.to_bson(replacement),
                                             *args, **kwargs)

    def replace_document(self, document, *args, **kwargs):
        return self.replace_one

    def with_options(self, *args, **kwargs):
        collection = self.__collection.with_options(*args, **kwargs)
        return BasicCollection(collection, self.__type)

    def find(self, *args, **kwargs):
        return BasicCursor(
            self.__collection.find(*args, **kwargs), self.__type)

    def find_one(self, *args, **kwargs):
        result = self.__collection.find_one(*args, **kwargs)
        if result is not None:
            result = self.__type.from_bson(result)
        return result

    def refresh(self, documents, projection=None):
        ids_to_documents = {document._id: document for document in documents}
        query = {"_id": {"$in": list(ids_to_documents.keys())}}
        results = self.__collection.find(query, projection=projection)
        for result in results:
            document = ids_to_documents.pop(result["_id"])
            for key, value in result.items():
                type = self.__type.field(key)
                setattr(document, key, type.from_bson(value))
        assert not ids_to_documents

        return documents

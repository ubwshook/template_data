import os
from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

# python3 a_map_poi.py --para=5ee31da5a0a6cd17802a663c

parameter = {"_id": ObjectId("5ee31da5a0a6cd17802a663c"),
             "headersList": ["keyword"],
             "parameterMap": {"keyword": ["大学", "咖啡馆", "日料店"]},
             "spiderId": 0, "templateId": 2}


if __name__ == "__main__":
    os.environ["CRAWLAB_MONGO_HOST"] = "localhost"
    os.environ["CRAWLAB_MONGO_DB"] = "test"
    os.environ["CRAWLAB_MONGO_USERNAME"] = ""
    os.environ["CRAWLAB_MONGO_PASSWORD"] = ""
    os.environ["CRAWLAB_MONGO_AUTHSOURCE"] = "admin"
    os.environ["CRAWLAB_COLLECTION"] = "test"

    os.environ["CRAWLAB_TASK_ID"] = "000000000001"

    mongo = MongoClient(
        host="localhost",
        port=27017,
        username="",
        password="",
        authSource="admin",
    )
    db = mongo.get_database("test")
    col = db.get_collection("parameters")
    try:
        col.insert_one(parameter)
    except DuplicateKeyError:
        print("Parameters already exist.")

    print(os.getenv("CRAWLAB_MONGO_DB"))

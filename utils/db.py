from pymongo import MongoClient
print("Connecting to database...")
client = MongoClient(
    "mongodb+srv://anidl:encodes@cluster0.oobfx33.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)

db = client["anidl"]
filesdb = db["files"]
print("Connected to database...")

client2 = MongoClient(
    "mongodb://admin:secretpassword@mongodxx.ddlserverv1.me.in:27017/"
)

db2 = client2["techzcloud"]
filesdb2 = db2["files"]
print("Connected to database...")

def save_file_in_db(orgname, filename, hash, msg_id=None):
    filesdb.update_one(
        {
            "hash": hash,
            "fid": str(msg_id),
        },
        {"$set": {"filename": filename, "filenamex": orgname, "code": hash, "msg_id": msg_id}},
        upsert=True,
    )


def is_hash_in_db(hash):
    data = filesdb.find_one({"hash": hash})
    if data:
        return data
    else:
        return None
def is_hash_in_db2(hash):
    data = filesdb2.find_one({"hash": hash})
    if data:
        return data
    else:
        return None


def replace_is_hash_in_db(hash, file_name):
    data = filesdb.find_one({"hash": hash})
    if data:
        data["filenamex"] = file_name
        result = filesdb.replace_one({"_id": data["_id"]}, data)
        return data
    else:
        return None

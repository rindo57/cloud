from pymongo import MongoClient
print("Connecting to database...")
client = MongoClient(
    "mongodb+srv://hevc:sucks@cluster0.mdnim6a.mongodb.net/?retryWrites=true&w=majority"
)

db = client["techzcloud"]
filesdb = db["files"]
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


def replace_is_hash_in_db(hash, file_name):
    data = filesdb.find_one({"hash": hash})
    if data:
        fname = data["filenamex"]
        filter = {"filenamex": fname}
        update = {"$set": {"filenamex": file_name}}
        result = filesdb.update_one(filter, update)
        return data
    else:
        return None

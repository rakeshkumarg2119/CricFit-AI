import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "cricfit_ai")

_client = None
_db = None


def get_db():
    """
    Return a MongoDB database handle, or None if unavailable.
    Re-attempts connection on each call if previously failed,
    so a transient outage is recovered automatically.
    """
    global _client, _db

    if _db is not None:
        return _db

    try:
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
        _client.admin.command("ping")       # force-verify the connection
        _db = _client[MONGODB_DATABASE]
        print(f"[INFO] Connected to MongoDB: {MONGODB_URI} / {MONGODB_DATABASE}")
    except Exception as e:
        print(f"[WARN] MongoDB unavailable: {e}")
        _client = None
        _db = None

    return _db


def reset_db():
    """Call this to force a reconnection attempt on the next get_db() call."""
    global _client, _db
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
    _client = None
    _db = None

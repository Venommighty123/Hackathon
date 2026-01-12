import os
from functools import lru_cache
from app_rec.database.base import DatabaseRepository
from app_rec.database.mongo_db import MongoDB
# from app.database.mock_db import MockDB # Keep for backup if needed

@lru_cache()
def get_db() -> DatabaseRepository:
    """
    Initializes the MongoDB connection using the env variable.
    """
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    return MongoDB(mongo_uri)
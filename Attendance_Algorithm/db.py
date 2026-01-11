# db.py
import certifi
from motor.motor_asyncio import AsyncIOMotorClient

ATLAS_URI = "mongodb+srv://mathurkushagra163_db_user:ElTitz0clXuFXUeu@cluster0.1c2z3gd.mongodb.net/?retryWrites=true&w=majority"

ca = certifi.where()

client = AsyncIOMotorClient(
    ATLAS_URI,
    tls=True,
    tlsCAFile=ca
)

db = client["hr_database"]
employees_collection = db["employees_biometrics"]

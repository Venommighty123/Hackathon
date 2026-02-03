import json
import os
from pymongo import MongoClient, errors

# Use your Atlas SRV string here
ATLAS_URI = "mangodb_line"
DB_NAME = "hr_database"
COLLECTION_NAME = "employees_biometrics"

def upload_json_to_mongodb(file_path):
    client = MongoClient(ATLAS_URI, serverSelectionTimeoutMS=5000)
    try:
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        with open(file_path, 'r', encoding='utf-8') as file:
            raw_data = json.load(file)

        # LOGIC: Your JSON uses IDs as KEYS. We must transform this for MongoDB.
        documents = []
        for emp_id, details in raw_data.items():
            # Create a flat document structure
            doc = {
                "emp_id": emp_id,
                "name": details.get("name"),
                "department": details.get("department"),
                "office_lat": details.get("office_lat"),
                "office_lon": details.get("office_lon"),
                "geo_threshold_meters": details.get("geo_threshold_meters"),
                "face_embeddings": details.get("face_embeddings")
            }
            
            # Upsert into MongoDB
            collection.update_one(
                {"emp_id": emp_id},
                {"$set": doc},
                upsert=True
            )
        
        print(f"Successfully synced {len(raw_data)} employees to Atlas.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    path = r"Attendance_Algorithm\data\employees_biometric_with_names.json"
    upload_json_to_mongodb(path)

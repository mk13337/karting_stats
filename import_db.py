import json
from pymongo import MongoClient
from settings_ import MONGO_CONNECT_ST

# Подключение к MongoDB
client = MongoClient(MONGO_CONNECT_ST)
db = client['karting']
heats_collection = db['heats']
users_collection = db['users']

def import_data_if_empty(collection, json_file_path):
    if collection.count_documents({}) == 0:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            collection.insert_many(data)
        print(f"Data imported from {json_file_path} to {collection.name} collection.")
    else:
        print(f"{collection.name} collection already has data.")

def main():
    import_data_if_empty(heats_collection, 'db/karting.heats.json')
    import_data_if_empty(users_collection, 'db/karting.users.json')

if __name__ == "__main__":
    main()

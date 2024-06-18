import json
from pymongo import MongoClient

# Функция для преобразования JSON данных в формат, удобный для MongoDB
def transform_data(data):
    for document in data:
        if '_id' in document and '$oid' in document['_id']:
            document['_id'] = document['_id']['$oid']
        if 'date' in document and '$date' in document['date']:
            document['date'] = document['date']['$date']
        if 'karts' in document:
            for kart in document['karts']:
                if 'pilot_ID' in kart and '$oid' in kart['pilot_ID']:
                    kart['pilot_ID'] = kart['pilot_ID']['$oid']
    return data

# Подключение к MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['karting']
heats_collection = db['heats']
users_collection = db['users']

def import_data_if_empty(collection, json_file_path):
    if collection.count_documents({}) == 0:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            data = transform_data(data)
            collection.insert_many(data)
        print(f"Data imported from {json_file_path} to {collection.name} collection.")
    else:
        print(f"{collection.name} collection already has data.")

def main():
    import_data_if_empty(heats_collection, 'db/karting.heats.json')
    import_data_if_empty(users_collection, 'db/karting.users.json')

if __name__ == "__main__":
    main()

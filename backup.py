import os
import json
from datetime import datetime
from pymongo import MongoClient
from settings_ import MONGO_CONNECT_ST


def create_backup():
    # Подключение к базе данных MongoDB
    client = MongoClient(MONGO_CONNECT_ST)
    db = client['karting']

    # Получение текущей даты для имени папки
    current_date = datetime.now().strftime("%Y%m%d")
    backup_dir = f"backup/{current_date}"

    # Создание директории для бэкапа, если она не существует
    os.makedirs(backup_dir, exist_ok=True)

    # Функция для создания бэкапа коллекции
    def backup_collection(collection_name):
        collection = db[collection_name]
        documents = list(collection.find({}))
        backup_file_path = os.path.join(backup_dir, f"{collection_name}.json")

        with open(backup_file_path, 'w', encoding='utf-8') as file:
            json.dump(documents, file, default=str, ensure_ascii=False, indent=4)

        print(f"Backup for collection '{collection_name}' created at '{backup_file_path}'")

    # Создание бэкапа для каждой коллекции
    collections = db.list_collection_names()
    for collection_name in collections:
        backup_collection(collection_name)

if __name__ == "__main__":
    create_backup()

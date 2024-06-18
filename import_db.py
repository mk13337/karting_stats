import json
import os
from pymongo import MongoClient
from tqdm import tqdm

# Подключение к MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['karting']
heats_collection = db['heats']


file_path = 'db/karting.heats.json'

with open(file_path, 'r', encoding='utf-8') as file:
    heats_data = json.load(file)

print("Импорт данных в базу данных...")
for heat in tqdm(heats_data, desc="Importing heats", unit="heat"):
    heats_collection.insert_one(heat)

print("Импорт завершён.")

from pymongo import MongoClient
from datetime import datetime
from settings_ import MONGO_CONNECT_ST

def fix_dates_in_heats():
    # Подключение к MongoDB
    client = MongoClient(MONGO_CONNECT_ST)
    db = client['karting']
    heats_collection = db['heats']

    # Поиск всех заездов с датой в формате строки
    heats = heats_collection.find({'date': {'$type': 'string'}})

    for heat in heats:
        date_str = heat['date']
        try:
            # Попытка преобразовать строку в datetime
            new_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            try:
                new_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                new_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

        # Обновление записи в базе данных
        heats_collection.update_one({'_id': heat['_id']}, {'$set': {'date': new_date}})
        print(f"Updated heat {heat['heat_id']} date to {new_date}")

# Вызов функции для исправления дат
fix_dates_in_heats()

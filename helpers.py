from pymongo import MongoClient
from datetime import datetime

def get_recent_heats(user_identifier, num_heats):
    # Подключение к MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['karting']
    heats_collection = db['heats']

    # Проверка, является ли идентификатор никнеймом или ID
    if user_identifier.isdigit():
        search_field = "karts.pilot_ID"
    else:
        search_field = "karts.pilot_nickname"

    # Поиск всех заездов пользователя
    heats = heats_collection.find({search_field: user_identifier}).sort("date", -1).limit(num_heats)

    recent_heats = []
    for heat in heats:
        date = heat['date']
        # Преобразование строки в объект datetime, если необходимо
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            except ValueError:
                try:
                    date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")
                except ValueError:
                    date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")

        recent_heats.append({
            'heat_id': heat['heat_id'],
            'name': heat['name'],
            'date': date.strftime("%Y-%m-%d %H:%M:%S")
        })

    return recent_heats

# Пример использования функции
# recent_heats = get_recent_heats('mk', 5)
# print(recent_heats)

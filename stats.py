import matplotlib.pyplot as plt
import numpy as np
from pymongo import MongoClient
from datetime import datetime
import os
from collections import Counter


def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

def make_naive(dt):
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt



def analyze_heat_by_user(heat_id, nickname):
    # Подключение к MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['karting']
    heats_collection = db['heats']

    # Поиск заезда по ID
    heat = heats_collection.find_one({'heat_id': heat_id})

    if not heat:
        return f"No heat found with ID {heat_id}", []

    # Поиск данных пользователя
    user_kart = None
    for kart in heat['karts']:
        if kart['pilot_nickname'] == nickname:
            user_kart = kart
            break

    if not user_kart:
        return f"No data found for user {nickname} in heat {heat_id}", []

    lap_times = [float(time.replace(':', '')) for time in user_kart['lap_times']]
    laps = list(range(1, len(lap_times) + 1))

    # Построение графика зависимости времени круга от номера круга
    plt.figure(figsize=(10, 5))
    plt.plot(laps, lap_times, marker='o', linestyle='-', color='b')
    for i, txt in enumerate(lap_times):
        plt.annotate(f'{txt:.2f}', (laps[i], lap_times[i]), textcoords="offset points", xytext=(0,10), ha='center')
    plt.title(f"Времена круга гонщика {nickname} в заезде {heat['name']}")
    plt.xlabel("Номер круга")
    plt.ylabel("Время круга (сек)")
    plt.grid(True)
    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    output_dir = f"stats/pictures/{nickname}"
    os.makedirs(output_dir, exist_ok=True)
    filepath = f"{output_dir}/{timestamp}_heat_{heat_id}.png"
    plt.savefig(filepath)
    plt.close()
    pictures = [(filepath, f"Времена круга гонщика {nickname} в заезде {heat['name']}")]
    #print(f"Graph saved as {filepath}")

    text = f"Информация по заезду [№{heat_id}](https://timing.batyrshin.name/tracks/narvskaya/heats/{heat_id}) для пилота *{nickname}*\n"

    best_lap_time = min(lap_times)
    text += f"Лучшее время круга: *{best_lap_time:.3f}* сек\n"


    # Расчет среднего времени круга
    mean_lap_time = np.mean(lap_times)
    text += f"Среднее время круга: *{mean_lap_time:.3f}* сек\n"

    # Расчет стабильности (средний разброс времён круга)
    lap_time_std = np.std(lap_times)
    text += f"Разброс времён круга: *{lap_time_std:.3f}* сек\n"

    # Позиция по лучшему времени круга среди остальных
    best_lap_time = min(lap_times)
    best_times = [min([float(time.replace(':', '')) for time in kart['lap_times']]) for kart in heat['karts']]
    position = sorted(best_times).index(best_lap_time) + 1
    text += f"Позиция по лучшему кругу: *{position}* из *{len(best_times)}*"

    return text, pictures




def get_all_weather_conditions():
    # Подключение к MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['karting']
    heats_collection = db['heats']

    # Запрос для получения всех уникальных состояний погоды
    weather_conditions = heats_collection.distinct("weather")

    # Вывод всех возможных состояний погоды
    print("All possible weather conditions:")
    for weather in weather_conditions:
        print(weather)





def analyze_user_heats(user_identifier, num_heats):
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

    # Отбор заездов по условиям
    user_heats = []
    for heat in heats:
        if 'rain' not in heat['weather'].lower():
            user_kart = next((kart for kart in heat['karts'] if kart[search_field.split('.')[1]] == user_identifier), None)
            if user_kart:
                lap_times = [float(time.replace(':', '')) for time in user_kart['lap_times'] if float(time.replace(':', '')) <= 60]
                if len(lap_times) > 0:
                    best_lap_time = min(lap_times)
                    mean_lap_time = np.mean(lap_times)
                    std_lap_time = np.std(lap_times)
                    user_heats.append({
                        'heat_id': heat['heat_id'],
                        'date': heat['date'],
                        'best_lap_time': best_lap_time,
                        'mean_lap_time': mean_lap_time,
                        'std_lap_time': std_lap_time
                    })

    if len(user_heats) < 2:
        return "Not enough heats to analyze.", []
        return "", []

    # Сортировка заездов от старых к новым
    user_heats = sorted(user_heats, key=lambda x: make_naive(
        datetime.fromisoformat(x['date'].replace('Z', '+00:00'))) if isinstance(x['date'], str) else make_naive(
        x['date']))

    # Построение графиков
    heat_numbers = list(range(1, len(user_heats) + 1))
    best_lap_times = [heat['best_lap_time'] for heat in user_heats]
    mean_lap_times = [heat['mean_lap_time'] for heat in user_heats]
    std_lap_times = [heat['std_lap_time'] for heat in user_heats]

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    output_dir = f"stats/pictures/{user_identifier}"
    os.makedirs(output_dir, exist_ok=True)

    pictures = []

    def plot_graph(y_values, y_label, title, filename):
        plt.figure(figsize=(10, 5))
        plt.plot(heat_numbers, y_values, marker='o', linestyle='-', color='b')
        for i, txt in enumerate(y_values):
            plt.annotate(f'{txt:.2f}', (heat_numbers[i], y_values[i]), textcoords="offset points", xytext=(0,10), ha='center')
        plt.title(title)
        plt.xlabel("Heat Number")
        plt.ylabel(y_label)
        plt.grid(True)
        plt.tight_layout()
        filepath = f"{output_dir}/{timestamp}_{filename}.png"
        plt.savefig(filepath)
        plt.close()
        pictures.append((filepath, title))
        #print(f"Graph saved as {filepath}")

    # График лучших времён
    plot_graph(best_lap_times, "Лучшее время круга (сек)",
               f"Лучшие времена круга гонщика {user_identifier}", "best_lap_times")

    # График средних времён
    plot_graph(mean_lap_times, "Среднее время круга (сек)",
               f"Среднее время круга гонщика {user_identifier}", "mean_lap_times")

    # График стандартного отклонения
    plot_graph(std_lap_times, "Стандартное отклонение (сек)",
               f"Стандартное отклонение (показатель стабильности) гонщика {user_identifier}", "std_lap_times")

    # Анализ улучшений/ухудшений
    delta_best_lap_time = (best_lap_times[-1] - best_lap_times[0]) / (len(best_lap_times) - 1)
    delta_mean_lap_time = (mean_lap_times[-1] - mean_lap_times[0]) / (len(mean_lap_times) - 1)
    delta_std_lap_time = (std_lap_times[-1] - std_lap_times[0]) / (len(std_lap_times) - 1)

    improvement_best = "улучшение" if delta_best_lap_time < 0 else "ухудшение"
    improvement_mean = "улучшение" if delta_mean_lap_time < 0 else "ухудшение"
    improvement_std = "улучшение" if delta_std_lap_time < 0 else "ухудшение"

    text = (f"Аналитика для пользователя {user_identifier}.\n"
            f"За последние {len(user_heats)} заездов:\n"
            f"- {improvement_best} лучшего времени составляет {abs(delta_best_lap_time):.3f} секунд за заезд.\n"
            f"- {improvement_mean} среднего времени круга составляет {abs(delta_mean_lap_time):.3f} секунд за заезд.\n"
            f"- {improvement_std} стабильности (стандартного отклонения) составляет {abs(delta_std_lap_time):.3f} секунд за заезд.")

    return text, pictures




def kart_usage_statistics(user_identifier):
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
    heats = heats_collection.find({search_field: user_identifier})

    # Подсчет использования картов
    kart_counter = Counter()
    for heat in heats:
        for kart in heat['karts']:
            if kart[search_field.split('.')[1]] == user_identifier:
                kart_counter[kart['kart_number']] += 1

    # Общий подсчет заездов
    total_heats = sum(kart_counter.values())

    if total_heats == 0:
        return "No heats found for user."

    # Расчет процентов и округление до целого числа
    kart_usage_percentages = {kart: round((count / total_heats) * 100) for kart, count in kart_counter.items()}

    # Группировка картов с идентичным процентом
    grouped_kart_usage = {}
    for kart, percentage in kart_usage_percentages.items():
        if percentage not in grouped_kart_usage:
            grouped_kart_usage[percentage] = []
        grouped_kart_usage[percentage].append(kart)

    # Сортировка по использованию
    sorted_kart_usage = dict(sorted(grouped_kart_usage.items(), key=lambda item: item[0], reverse=True))

    # Вывод статистики
    text = f"Статистика картов гонщика *{user_identifier}*:\n"
    for percentage, karts in sorted_kart_usage.items():
        kart_list = ', '.join(karts)
        if len(karts) == 1:
            text += f"*{percentage}%*: Карт {kart_list}\n"
        else:
            text += f"*{percentage}%*: Карты {kart_list}\n"

    return text


def compare_user_heats(user1_identifier, user2_identifier, num_heats):
    def get_user_heats(user_identifier, num_heats):
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

        # Отбор заездов по условиям
        user_heats = []
        for heat in heats:
            if 'rain' not in heat['weather'].lower():
                user_kart = next((kart for kart in heat['karts'] if kart[search_field.split('.')[1]] == user_identifier), None)
                if user_kart:
                    lap_times = [float(time.replace(':', '')) for time in user_kart['lap_times'] if float(time.replace(':', '')) <= 60]
                    if len(lap_times) > 0:
                        best_lap_time = min(lap_times)
                        mean_lap_time = np.mean(lap_times)
                        std_lap_time = np.std(lap_times)
                        user_heats.append({
                            'heat_id': heat['heat_id'],
                            'date': heat['date'],
                            'best_lap_time': best_lap_time,
                            'mean_lap_time': mean_lap_time,
                            'std_lap_time': std_lap_time
                        })

        if len(user_heats) < 2:
            print(f"Not enough heats to analyze for user {user_identifier}.")
            return []


            # Сортировка заездов от старых к новым
        user_heats = sorted(user_heats, key=lambda x: x['date'])


        return user_heats

    user1_heats = get_user_heats(user1_identifier, num_heats)
    user2_heats = get_user_heats(user2_identifier, num_heats)

    if not user1_heats or not user2_heats:
        return "Not enough heats to analyze for one or both users.", []

    # Объединение и фиксация общих заездов
    combined_heats = []
    user1_index, user2_index = 0, 0

    while user1_index < len(user1_heats) and user2_index < len(user2_heats):
        if user1_heats[user1_index]['date'] == user2_heats[user2_index]['date']:
            combined_heats.append((user1_heats[user1_index], user2_heats[user2_index]))
            user1_index += 1
            user2_index += 1
        elif user1_heats[user1_index]['date'] < user2_heats[user2_index]['date']:
            combined_heats.append((user1_heats[user1_index], None))
            user1_index += 1
        else:
            combined_heats.append((None, user2_heats[user2_index]))
            user2_index += 1

    while user1_index < len(user1_heats):
        combined_heats.append((user1_heats[user1_index], None))
        user1_index += 1

    while user2_index < len(user2_heats):
        combined_heats.append((None, user2_heats[user2_index]))
        user2_index += 1

    def plot_comparison_graph(user1_data, user2_data, y_label, title, filename):
        plt.figure(figsize=(10, 5))
        plt.plot(range(1, len(user1_data) + 1), user1_data, marker='o', linestyle='-', color='b', label=user1_identifier)
        plt.plot(range(1, len(user2_data) + 1), user2_data, marker='o', linestyle='-', color='r', label=user2_identifier)
        for i, txt in enumerate(user1_data):
            if txt is not None:
                plt.annotate(f'{txt:.2f}', (i + 1, user1_data[i]), textcoords="offset points", xytext=(0,10), ha='center', color='b')
        for i, txt in enumerate(user2_data):
            if txt is not None:
                plt.annotate(f'{txt:.2f}', (i + 1, user2_data[i]), textcoords="offset points", xytext=(0,10), ha='center', color='r')
        plt.title(title)
        plt.xlabel("Heat Number")
        plt.ylabel(y_label)
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        filepath = f"{output_dir}/{timestamp}_{filename}.png"
        plt.savefig(filepath)
        plt.close()
        pictures.append((filepath, title))

    # Данные для построения графиков
    user1_best_lap_times = [heat[0]['best_lap_time'] if heat[0] else None for heat in combined_heats]
    user2_best_lap_times = [heat[1]['best_lap_time'] if heat[1] else None for heat in combined_heats]
    user1_mean_lap_times = [heat[0]['mean_lap_time'] if heat[0] else None for heat in combined_heats]
    user2_mean_lap_times = [heat[1]['mean_lap_time'] if heat[1] else None for heat in combined_heats]
    user1_std_lap_times = [heat[0]['std_lap_time'] if heat[0] else None for heat in combined_heats]
    user2_std_lap_times = [heat[1]['std_lap_time'] if heat[1] else None for heat in combined_heats]

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    output_dir = f"stats/pictures/comparison_{user1_identifier}_{user2_identifier}"
    os.makedirs(output_dir, exist_ok=True)

    pictures = []

    # График лучших времён
    plot_comparison_graph(user1_best_lap_times, user2_best_lap_times, "Лучшее время круга (сек)",
                          f"Сравнение лучших времён кругов {user1_identifier} и {user2_identifier}", "best_lap_times")

    # График средних времён
    plot_comparison_graph(user1_mean_lap_times, user2_mean_lap_times, "Среднее время круга (сек)",
                          f"Сравнение средних времён кругов {user1_identifier} и {user2_identifier}", "mean_lap_times")

    # График стандартного отклонения
    plot_comparison_graph(user1_std_lap_times, user2_std_lap_times, "Стандартное отклонение (сек)",
                          f"Сравнение стабильности кругов {user1_identifier} и {user2_identifier}", "std_lap_times")

    text = (f"Сравнение пользователей {user1_identifier} и {user2_identifier}.\n"
            f"На основе последних {num_heats} заездов каждого.")

    return text, pictures




# Пример использования функции
# text, pictures = compare_user_heats('Куксенко', 'Соколик', 100)
# print(text)
# for pic in pictures:
#     print(pic)


# Пример использования функции
# a = kart_usage_statistics('Куксенко')
# print(a)

# a,b = analyze_user_heats('mk', 100)
# print(a)
# print(b)









# Пример использования функции
# text, pictures = analyze_user_heats('mk', 5)
# print(text)
# for pic in pictures:
#     print(pic)





# Пример использования функции
# a,b = analyze_heat_by_user('55334', 'mk')
# print(a)
# print(b)
#get_all_weather_conditions()
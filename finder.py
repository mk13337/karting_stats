import telebot
from pymongo import MongoClient
from stats import analyze_heat_by_user
from settings_ import TELEGRAM_API_TOKEN, MONGO_CONNECT_ST

# Подключение к MongoDB
client = MongoClient(MONGO_CONNECT_ST)
db = client['karting']
heats_collection = db['heats']
users_collection = db['users']

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_API_TOKEN)

def send_message(chat_id, text, pictures):
    bot.send_message(chat_id, text, parse_mode='Markdown', disable_web_page_preview=True)
    for pic in pictures:
        with open(pic[0], 'rb') as photo:
            bot.send_photo(chat_id, photo, caption=pic[1], parse_mode='Markdown')

def notify_users_of_new_heats():
    # Поиск заездов с notified = False
    heats = heats_collection.find({'notified': False})

    for heat in heats:
        heat_id = heat['heat_id']
        heat_name = heat['name']

        # Поиск подписанных пользователей, участвующих в этом заезде
        for kart in heat['karts']:
            pilot_nickname = kart['pilot_nickname']
            user = users_collection.find_one({'karting_nickname_or_id': pilot_nickname, 'subscription': True})

            if user:
                chat_id = user['telegram_id']
                # Отправка уведомления о новом заезде
                bot.send_message(chat_id, f"Обнаружен новый заезд {heat_name}!")

                # Получение и отправка анализа заезда
                text, pictures = analyze_heat_by_user(heat_id, pilot_nickname)
                send_message(chat_id, text, pictures)

        # Обновление статуса заезда на notified = True
        heats_collection.update_one({'heat_id': heat_id}, {'$set': {'notified': True}})

if __name__ == "__main__":
    notify_users_of_new_heats()

import telebot
from pymongo import MongoClient
from telebot import types
from stats import analyze_user_heats, analyze_heat_by_user, kart_usage_statistics, compare_user_heats
from helpers import get_recent_heats
from settings_ import TELEGRAM_API_TOKEN, MONGO_CONNECT_ST


# Подключение к MongoDB
client = MongoClient(MONGO_CONNECT_ST)
db = client['karting']
users_collection = db['users']

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_API_TOKEN)

# Хранилище состояния пользователя
user_states = {}

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_data = users_collection.find_one({'telegram_id': message.chat.id})
    if user_data:
        show_main_menu(message)
    else:
        bot.reply_to(message, "Привет! Пожалуйста, введите свой гоночный никнейм или ID с сайта https://timing.batyrshin.name")
        user_states[message.chat.id] = {'state': 'awaiting_nickname'}

# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_data = users_collection.find_one({'telegram_id': message.chat.id})
    if user_data:
        state = user_states.get(message.chat.id, {}).get('state')
        if state == 'awaiting_other_user':
            handle_other_user(message)
        elif state == 'awaiting_heat_selection':
            handle_heat_selection(message)
        elif state == 'awaiting_kart_user':
            handle_kart_user(message)
        elif state == 'awaiting_first_driver':
            handle_first_driver(message)
        elif state == 'awaiting_second_driver':
            handle_second_driver(message)
        elif state == 'awaiting_new_nickname':
            handle_new_nickname(message)
        elif state == 'awaiting_subscription_change':
            handle_subscription_change(message)
        elif state == 'awaiting_num_heats':
            handle_num_heats(message)
        else:
            handle_main_menu(message)
    else:
        state = user_states.get(message.chat.id, {}).get('state')
        if state == 'awaiting_nickname':
            handle_nickname(message)
        elif state == 'awaiting_subscription':
            handle_subscription(message)

def handle_nickname(message):
    user_identifier = message.text.strip()
    user_states[message.chat.id] = {'state': 'awaiting_subscription', 'nickname': user_identifier}

    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Да', 'Нет')
    bot.send_message(message.chat.id, "Хотите ли вы получать уведомления о новых заездах?", reply_markup=markup)

def handle_subscription(message):
    subscription = message.text.strip().lower() == 'да'
    user_data = {
        'telegram_nickname': message.from_user.username,
        'telegram_id': message.chat.id,
        'karting_nickname_or_id': user_states[message.chat.id]['nickname'],
        'subscription': subscription,
        'num_heats_analyze': 10  # значение по умолчанию
    }
    users_collection.update_one(
        {'telegram_id': message.chat.id},
        {'$set': user_data},
        upsert=True
    )

    bot.reply_to(message, f"Привет, {user_states[message.chat.id]['nickname']}!", reply_markup=get_main_menu_markup())
    user_states[message.chat.id] = {'state': 'main_menu'}

def get_main_menu_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Статистика")
    btn2 = types.KeyboardButton("Настройки")
    markup.add(btn1, btn2)
    return markup

def get_stats_menu_markup():
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("Анализ своих заездов", callback_data="analyze_own_heats")
    btn2 = types.InlineKeyboardButton("Анализ чужих заездов", callback_data="analyze_other_heats")
    btn3 = types.InlineKeyboardButton("Показать заезд", callback_data="show_heat")
    btn4 = types.InlineKeyboardButton("Любимые карты", callback_data="favorite_karts")
    btn5 = types.InlineKeyboardButton("Сравнить двух гонщиков", callback_data="compare_drivers")  # Новая кнопка
    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    markup.add(btn4)
    markup.add(btn5)  # Новая кнопка
    return markup

def get_settings_menu_markup():
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("Привязанный никнейм", callback_data="change_nickname")
    btn2 = types.InlineKeyboardButton("Уведомление о новых заездах", callback_data="change_subscription")
    btn3 = types.InlineKeyboardButton("Количество заездов для анализа", callback_data="change_num_heats")
    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    return markup

def show_main_menu(message):
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=get_main_menu_markup())

def handle_main_menu(message):
    if message.text == "Статистика":
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=get_stats_menu_markup())
    elif message.text == "Настройки":
        bot.send_message(message.chat.id, "Что вы хотите изменить?", reply_markup=get_settings_menu_markup())

def handle_other_user(message):
    other_user_identifier = message.text.strip()
    user_data = users_collection.find_one({'telegram_id': message.chat.id})
    num_heats = user_data.get('num_heats_analyze', 10)
    text, pictures = analyze_user_heats(other_user_identifier, num_heats)
    bot.send_message(message.chat.id, text, parse_mode='Markdown', disable_web_page_preview=True, reply_markup=get_main_menu_markup())
    for pic in pictures:
        with open(pic[0], 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=pic[1], parse_mode='Markdown')
    user_states[message.chat.id] = {'state': 'main_menu'}

@bot.callback_query_handler(func=lambda call: call.data == "analyze_own_heats")
def handle_analyze_own_heats(call):
    user_data = users_collection.find_one({'telegram_id': call.message.chat.id})
    if user_data:
        user_identifier = user_data['karting_nickname_or_id']
        num_heats = user_data.get('num_heats_analyze', 10)
        text, pictures = analyze_user_heats(user_identifier, num_heats)
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown', disable_web_page_preview=True, reply_markup=get_main_menu_markup())
        for pic in pictures:
            with open(pic[0], 'rb') as photo:
                bot.send_photo(call.message.chat.id, photo, caption=pic[1], parse_mode='Markdown')
        user_states[call.message.chat.id] = {'state': 'main_menu'}
    else:
        bot.send_message(call.message.chat.id, "Не удалось найти данные пользователя. Пожалуйста, повторите ввод /start и следуйте инструкциям.")

@bot.callback_query_handler(func=lambda call: call.data == "analyze_other_heats")
def handle_analyze_other_heats(call):
    bot.send_message(call.message.chat.id, "Пожалуйста, введите гоночный никнейм или ID другого пользователя:")
    user_states[call.message.chat.id] = {'state': 'awaiting_other_user'}

@bot.callback_query_handler(func=lambda call: call.data == "show_heat")
def handle_show_heat(call):
    user_data = users_collection.find_one({'telegram_id': call.message.chat.id})
    if user_data:
        user_identifier = user_data['karting_nickname_or_id']
        recent_heats = get_recent_heats(user_identifier, 5)
        if recent_heats:
            markup = types.InlineKeyboardMarkup()
            for heat in recent_heats:
                button_text = f"{heat['name']}, {heat['date']}"
                callback_data = f"show_heat_{heat['heat_id']}"
                markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
            bot.send_message(call.message.chat.id, "Выберете заезд:", reply_markup=markup)
            user_states[call.message.chat.id] = {'state': 'awaiting_heat_selection'}
        else:
            bot.send_message(call.message.chat.id, "Не найдено заездов для отображения.")
    else:
        bot.send_message(call.message.chat.id, "Не удалось найти данные пользователя. Пожалуйста, повторите ввод /start и следуйте инструкциям.")

@bot.callback_query_handler(func=lambda call: call.data == "favorite_karts")
def handle_favorite_karts(call):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("Свою", callback_data="favorite_karts_own")
    btn2 = types.InlineKeyboardButton("Другого пользователя", callback_data="favorite_karts_other")
    markup.add(btn1)
    markup.add(btn2)
    bot.send_message(call.message.chat.id, "Чью статистику вы хотите посмотреть?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "favorite_karts_own")
def handle_favorite_karts_own(call):
    user_data = users_collection.find_one({'telegram_id': call.message.chat.id})
    if user_data:
        user_identifier = user_data['karting_nickname_or_id']
        text = kart_usage_statistics(user_identifier)
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown', disable_web_page_preview=True, reply_markup=get_main_menu_markup())
        user_states[call.message.chat.id] = {'state': 'main_menu'}
    else:
        bot.send_message(call.message.chat.id, "Не удалось найти данные пользователя. Пожалуйста, повторите ввод /start и следуйте инструкциям.")

@bot.callback_query_handler(func=lambda call: call.data == "favorite_karts_other")
def handle_favorite_karts_other(call):
    bot.send_message(call.message.chat.id, "Пожалуйста, введите гоночный никнейм или ID другого пользователя:")
    user_states[call.message.chat.id] = {'state': 'awaiting_kart_user'}

def handle_kart_user(message):
    other_user_identifier = message.text.strip()
    text = kart_usage_statistics(other_user_identifier)
    bot.send_message(message.chat.id, text, parse_mode='Markdown', disable_web_page_preview=True, reply_markup=get_main_menu_markup())
    user_states[message.chat.id] = {'state': 'main_menu'}

@bot.callback_query_handler(func=lambda call: call.data.startswith("show_heat_"))
def handle_heat_selection(call):
    heat_id = call.data.split("_")[2]
    user_data = users_collection.find_one({'telegram_id': call.message.chat.id})
    if user_data:
        nickname = user_data['karting_nickname_or_id']
        text, pictures = analyze_heat_by_user(heat_id, nickname)
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown', disable_web_page_preview=True, reply_markup=get_main_menu_markup())
        for pic in pictures:
            with open(pic[0], 'rb') as photo:
                bot.send_photo(call.message.chat.id, photo, caption=pic[1], parse_mode='Markdown')
        user_states[call.message.chat.id] = {'state': 'main_menu'}
    else:
        bot.send_message(call.message.chat.id, "Не удалось найти данные пользователя. Пожалуйста, повторите ввод /start и следуйте инструкциям.")

@bot.callback_query_handler(func=lambda call: call.data == "compare_drivers")
def handle_compare_drivers(call):
    bot.send_message(call.message.chat.id, "Введите никнейм или ID первого гонщика:")
    user_states[call.message.chat.id] = {'state': 'awaiting_first_driver'}

def handle_first_driver(message):
    first_driver = message.text.strip()
    user_states[message.chat.id] = {'state': 'awaiting_second_driver', 'first_driver': first_driver}
    bot.send_message(message.chat.id, "Введите никнейм или ID второго гонщика:")

def handle_second_driver(message):
    second_driver = message.text.strip()
    first_driver = user_states[message.chat.id]['first_driver']
    user_data = users_collection.find_one({'telegram_id': message.chat.id})
    num_heats = user_data.get('num_heats_analyze', 10)
    text, pictures = compare_user_heats(first_driver, second_driver, num_heats)
    bot.send_message(message.chat.id, text, parse_mode='Markdown', disable_web_page_preview=True, reply_markup=get_main_menu_markup())
    for pic in pictures:
        with open(pic[0], 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=pic[1], parse_mode='Markdown')
    user_states[message.chat.id] = {'state': 'main_menu'}

@bot.callback_query_handler(func=lambda call: call.data == "change_nickname")
def handle_change_nickname(call):
    bot.send_message(call.message.chat.id, "Пожалуйста, введите свой гоночный никнейм или ID с сайта https://timing.batyrshin.name")
    user_states[call.message.chat.id] = {'state': 'awaiting_new_nickname'}

def handle_new_nickname(message):
    new_nickname = message.text.strip()
    user_data = users_collection.find_one({'telegram_id': message.chat.id})
    old_nickname = user_data['karting_nickname_or_id']
    users_collection.update_one(
        {'telegram_id': message.chat.id},
        {'$set': {'karting_nickname_or_id': new_nickname}}
    )
    bot.send_message(message.chat.id, f"Никнейм изменён с {old_nickname} на {new_nickname}", reply_markup=get_main_menu_markup())
    user_states[message.chat.id] = {'state': 'main_menu'}

@bot.callback_query_handler(func=lambda call: call.data == "change_subscription")
def handle_change_subscription(call):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Да', 'Нет')
    bot.send_message(call.message.chat.id, "Хотите ли вы получать уведомления о новых заездах?", reply_markup=markup)
    user_states[call.message.chat.id] = {'state': 'awaiting_subscription_change'}

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get('state') == 'awaiting_subscription_change')
def handle_subscription_change(message):
    subscription = message.text.strip().lower() == 'да'
    users_collection.update_one(
        {'telegram_id': message.chat.id},
        {'$set': {'subscription': subscription}}
    )
    if subscription:
        bot.send_message(message.chat.id, "Теперь вы будете получать сообщения о новых заездах", reply_markup=get_main_menu_markup())
    else:
        bot.send_message(message.chat.id, "Теперь вы не будете получать сообщения о новых заездах", reply_markup=get_main_menu_markup())
    user_states[message.chat.id] = {'state': 'main_menu'}


@bot.callback_query_handler(func=lambda call: call.data == "change_num_heats")
def handle_change_num_heats(call):
    bot.send_message(call.message.chat.id, "Введите количество заездов для анализа")
    user_states[call.message.chat.id] = {'state': 'awaiting_num_heats'}

def handle_num_heats(message):
    try:
        num_heats = int(message.text.strip())
        users_collection.update_one(
            {'telegram_id': message.chat.id},
            {'$set': {'num_heats_analyze': num_heats}}
        )
        bot.send_message(message.chat.id, f"Для анализа будут использоваться {num_heats} заездов", reply_markup=get_main_menu_markup())
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное число")
    user_states[message.chat.id] = {'state': 'main_menu'}

# Запуск бота
bot.polling()

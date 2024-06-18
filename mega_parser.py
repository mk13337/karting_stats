import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime, timedelta


# Функция для получения сегодняшних заездов
def get_today_heats(url):
	response = requests.get(url)
	soup = BeautifulSoup(response.text, 'html.parser')

	today = datetime.now().strftime("%b %d")
	found_today = False

	items = soup.find_all('div', class_='list-group-item')

	heats = []

	for item in items:
		if 'list-group-item-light' in item['class']:
			date_text = item.get_text(strip=True)
			if date_text == today:
				found_today = True
			else:
				found_today = True

		if 'list-group-item-action' in item['class'] and found_today:
			heat_name_tag = item.find('a', class_='text-dark')
			heat_name = heat_name_tag.find('strong').text.strip()
			heat_id = heat_name_tag['href'].split('/')[-1]
			heats.append((heat_name, heat_id))

	return heats


import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime


def parse_heat(heat_id):
	# URL заезда
	url = f"https://timing.batyrshin.name/tracks/narvskaya/heats/{heat_id}"

	# Получение HTML страницы
	response = requests.get(url)
	soup = BeautifulSoup(response.text, 'html.parser')

	# Название и дата заезда
	heat_name = soup.find('title').text.strip()
	date_time = soup.find('small', class_='text-muted').text.strip()

	# Погода во время заезда
	weather_div = soup.find('div', class_='bg-light border-bottom').find_all('div')
	weather = weather_div[0].text.replace('\n', '').strip()

	# Получение имен гонщиков и их ID
	driver_row = soup.find('tr', class_='align-top')
	drivers = []
	pilot_ids = []
	for a in driver_row.find_all('a'):
		drivers.append(a.text)
		pilot_ids.append(a['href'].split('/')[-1])

	# Получение номеров картов
	kart_row = soup.find('th', string='Kart').parent
	karts = [a.find('span').text for a in kart_row.find_all('a')]

	# Получение времени кругов
	lap_times = {driver: [] for driver in drivers}

	rows = soup.find_all('tr')
	for row in rows:
		if row.find('th') and row.find('th').text.isdigit():
			cells = row.find_all('td')
			for i, cell in enumerate(cells):
				time_text = cell.text.split()
				if time_text and time_text[0].replace(':', '', 1).replace('.', '', 1).isdigit():
					lap_times[drivers[i]].append(time_text[0])

	# Подключение к MongoDB
	client = MongoClient('mongodb://localhost:27017/')
	db = client['karting']
	heats_collection = db['heats']

	# Структура данных для записи
	heat_data = {
		'heat_id': heat_id,
		'name': heat_name,
		'date': datetime.strptime(date_time, "%d %b %Y, %H:%M"),
		'weather': weather,
		'notified': False,
		'karts': []
	}

	for driver, pilot_id in zip(drivers, pilot_ids):
		kart_info = {
			'kart_number': karts[drivers.index(driver)],
			'pilot_nickname': driver,
			'pilot_ID': pilot_id,
			'lap_times': lap_times[driver]
		}
		heat_data['karts'].append(kart_info)

	# Запись в базу данных
	heats_collection.insert_one(heat_data)
	print(f"Heat data for {heat_id} has been inserted into the database.")


# Основная логика
url = "https://timing.batyrshin.name/tracks/narvskaya/heats"
today_heats = get_today_heats(url)

# Подключение к MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['karting']
heats_collection = db['heats']

# Проверка наличия заездов в базе данных и вызов функции parse_heat только для новых заездов
for heat_name, heat_id in today_heats:
	# Получение времени начала заезда
	response = requests.get(f"https://timing.batyrshin.name/tracks/narvskaya/heats/{heat_id}")
	soup = BeautifulSoup(response.text, 'html.parser')
	date_time = soup.find('small', class_='text-muted').text.strip()
	start_time = datetime.strptime(date_time, "%d %b %Y, %H:%M")

	# Проверка, прошло ли 15 минут с начала заезда
	if datetime.now() - start_time < timedelta(minutes=15):
		print(f"Heat {heat_id} started less than 15 minutes ago. Skipping...")
		continue

	if not heats_collection.find_one({'heat_id': heat_id}):
		parse_heat(heat_id)
	else:
		print(f"Heat data for {heat_id} already exists in the database.")

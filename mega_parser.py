import aiohttp
import asyncio
from bs4 import BeautifulSoup
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta

async def get_today_heats(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response_text = await response.text()
            soup = BeautifulSoup(response_text, 'html.parser')

            today = datetime.now().strftime("%b %d")
            found_today = True

            items = soup.find_all('div', class_='list-group-item')

            heats = []

            for item in items:
                if 'list-group-item-light' in item['class']:
                    date_text = item.get_text(strip=True)
                    if date_text == today:
                        found_today = True

                if 'list-group-item-action' in item['class'] and found_today:
                    heat_name_tag = item.find('a', class_='text-dark')
                    heat_name = heat_name_tag.find('strong').text.strip()
                    heat_id = heat_name_tag['href'].split('/')[-1]
                    heats.append((heat_name, heat_id))

            return heats

async def parse_heat(session, heat_id, db):
    url = f"https://timing.batyrshin.name/tracks/narvskaya/heats/{heat_id}"

    async with session.get(url) as response:
        response_text = await response.text()
        soup = BeautifulSoup(response_text, 'html.parser')

        heat_name = soup.find('title').text.strip()
        date_time = soup.find('small', class_='text-muted').text.strip()

        weather_div = soup.find('div', class_='bg-light border-bottom').find_all('div')
        weather = weather_div[0].text.replace('\n', '').strip()

        driver_row = soup.find('tr', class_='align-top')
        drivers = []
        pilot_ids = []
        for a in driver_row.find_all('a'):
            drivers.append(a.text)
            pilot_ids.append(a['href'].split('/')[-1])

        kart_row = soup.find('th', string='Kart').parent
        karts = [a.find('span').text for a in kart_row.find_all('a')]

        lap_times = {driver: [] for driver in drivers}

        rows = soup.find_all('tr')
        for row in rows:
            if row.find('th') and row.find('th').text.isdigit():
                cells = row.find_all('td')
                for i, cell in enumerate(cells):
                    time_text = cell.text.split()
                    if time_text and time_text[0].replace(':', '', 1).replace('.', '', 1).isdigit():
                        lap_times[drivers[i]].append(time_text[0])

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

        await db.heats.insert_one(heat_data)
        print(f"Heat data for {heat_id} has been inserted into the database.")

async def main():
    url = "https://timing.batyrshin.name/tracks/narvskaya/heats"
    mongo_uri = 'mongodb://localhost:27017/'
    client = AsyncIOMotorClient(mongo_uri)
    db = client['karting']

    today_heats = await get_today_heats(url)

    # Фильтрация заездов, которых нет в базе данных
    new_heats = []
    for heat_name, heat_id in today_heats:
        if not await db.heats.find_one({'heat_id': heat_id}):
            new_heats.append((heat_name, heat_id))

    async with aiohttp.ClientSession() as session:
        tasks = []
        for heat_name, heat_id in new_heats:
            response = await session.get(f"https://timing.batyrshin.name/tracks/narvskaya/heats/{heat_id}")
            response_text = await response.text()
            soup = BeautifulSoup(response_text, 'html.parser')
            date_time = soup.find('small', class_='text-muted').text.strip()
            start_time = datetime.strptime(date_time, "%d %b %Y, %H:%M")

            if datetime.now() - start_time < timedelta(minutes=-195):
                print(f"Heat {heat_id} started less than 15 minutes ago. Skipping...")
                continue

            tasks.append(parse_heat(session, heat_id, db))

        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())

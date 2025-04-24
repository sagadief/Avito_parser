from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from random import randint

# --- НАСТРОЙКИ ---
START_URL = input("Введи ссылку на Авито:\n")
PAGES = int(input("сколько страниц сканировать \n"))  # сколько страниц сканировать
START_PAGES = int(input("с какой страницы начать \n"))
OUTPUT_FILE = 'avito_ads.xlsx'
ADS_LIMIT = int(input("сколько объявлений максимум обрабатывать\n"))  # сколько объявлений максимум обрабатывать

# --- НАСТРОЙКИ БРАУЗЕРА ---
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(options=options)

ads_data = []

# --- ШАГ 1: Собрать ссылки на объявления ---
ad_links = []

for page in range(START_PAGES, START_PAGES + PAGES + 1):
    url = f"{START_URL}?p={page}"
    print(f"Открываем страницу: {url}")
    driver.get(url)
    time.sleep(randint(4, 8))

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    ads = soup.find_all('a', {'data-marker': 'item-title'})

    for ad in ads:
        href = ad.get('href')
        if href:
            link = 'https://www.avito.ru' + href
            ad_links.append(link)

print(f'Найдено {len(ad_links)} ссылок на объявления.')

# Ограничиваем количество объявлений
ad_links = ad_links[:ADS_LIMIT]
print(f'Будем парсить только {len(ad_links)} объявлений.')

# --- ШАГ 2: Зайти в каждое объявление и собрать данные ---
for link in ad_links:
    print(f"Парсим объявление: {link}")
    
    try:
        driver.get(link)
        WebDriverWait(driver, randint(17, 26)).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-marker="item-view/item-description"]'))
        )
    except Exception as e:
        print(f"Описание не загрузилось для {link}, пробуем собрать без описания...")

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    address_tag = soup.find('span', {'class': 'style-item-address__string-wt61A'})
    address = address_tag.text.strip() if address_tag else None

    description = None
    description_tag = soup.find('div', {'data-marker': 'item-view/item-description'})
    if description_tag:
        description = description_tag.get_text(strip=True)

    kadastr_number = None
    if description:
        match = re.search(r'\b\d{1,2}:\d{1,2}:\d{1,7}:\d{1,9}\b', description)
        if match:
            kadastr_number = match.group(0)

    params_list = soup.find('ul', {'class': 'params-paramsList-_awNW'})
    area = None
    if params_list:
        items = params_list.find_all('li')
        for item in items:
            text = item.get_text(strip=True)
            if text.startswith('Площадь'):
                area = text.replace('Площадь:', '').strip()

    price_tag = soup.find('span', {'itemprop': 'price'})
    price = price_tag.get('content') if price_tag else None

    price_per_m2 = None
    price_per_m2_tag = soup.find('div', {'class': 'styles-item-price-sub-price-A1IZy'})
    if price_per_m2_tag:
        span = price_per_m2_tag.find('span')
        if span:
            price_per_m2 = span.get_text(strip=True)

    # Сохраняем всё что смогли найти
    ads_data.append({
        'Адрес': address,
        'Площадь участка': area,
        'Цена': price,
        'Цена за м²/сотку': price_per_m2,
        'Ссылка': link,
        'Кадастровый номер': kadastr_number
    })

driver.quit()

# --- ШАГ 3: Сохраняем в Excel ---
df = pd.DataFrame(ads_data)
df.to_excel(OUTPUT_FILE, index=False)

print(f'✅ Сохранено {len(df)} объявлений в файл {OUTPUT_FILE}')


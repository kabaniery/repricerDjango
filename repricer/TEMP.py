import time

import requests
from repricer.scripts.LanguageAdapting import generate_ozon_name
from selenium import webdriver


def get_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--enable-javascript")
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    # service = Service('/usr/bin/chromedriver') TODO: вернуть для релиза
    current_driver = webdriver.Chrome(options=chrome_options)
    return current_driver


header = {
    'Client-Id': '1590790',
    'Api-Key': 'f8d5188f-cbcc-4378-b23f-9178b4489ff1'
}
body = {
    'offer_id': '77102'
}
list_body = {
    'filter':
        {
            'visibility': 'VISIBLE'
        },
    'limit': 1000
}
response = requests.post("https://api-seller.ozon.ru/v2/product/list", headers=header, json=list_body)

driver = get_driver()

if response.status_code == 200:
    for item in response.json()['result']['items']:
        body['offer_id'] = item['offer_id']
        item_data = requests.post("https://api-seller.ozon.ru/v2/product/info", headers=header, json=body)
        url = generate_ozon_name(item_data.json()['result']['name'], item_data.json()['result']['sku'])
        print(url)
        driver.get(url)
        time.sleep(2)

# TODO написать автотест для полученного генератора URL

import threading
import time
from decimal import Decimal
from queue import Queue

import requests
import selenium.webdriver

from repricer.scripts.LanguageAdapting import generate_ozon_name
from repricer.models import Client, Product
from repricer.scripts.ozon_finder import SeleniumProcess


class WebManager(threading.Thread):
    @staticmethod
    def generate_data(client: Client):
        header = {
            'Client-Id': client.username,
            'Api-Key': client.api_key
        }
        list_body = {
            'filter':
                {
                    'visibility': 'VISIBLE'
                },
            'limit': 1000
        }
        body = {
            'offer_id': '77102'
        }
        all_data = requests.post("https://api-seller.ozon.ru/v2/product/list", headers=header, json=list_body)
        if all_data.status_code == 200:
            for item in all_data.json()['result']['items']:
                body['offer_id'] = item['offer_id']
                item_data = requests.post("https://api-seller.ozon.ru/v2/product/info", headers=header, json=body)
                if item_data.status_code != 200 or item_data.json().get('result') is None:
                    time.sleep(0.5)
                    item_data = requests.post("https://api-seller.ozon.ru/v2/product/info", headers=header, json=body)
                    if item_data.status_code != 200:
                        print(item_data.text)
                        continue
                json_data = item_data.json()['result']
                product = Product(offer_id=json_data['offer_id'], shop=client, name=json_data['name'], gray_price=int(float(json_data['price'])), price=0)
                yield client, product, generate_ozon_name(json_data['name'], json_data['sku'])


    def __init__(self):
        super().__init__()

    _lock = threading.Lock()

    queue = Queue()
    isActive = False
    driver = None

    @staticmethod
    def check_proc():
        process = SeleniumProcess()
        driver = process.get_driver()
        while True:
            client, product, url = WebManager.queue.get()
            if client is None or product is None or url is None:
                driver.close()
                return
            price = process.find_price(url, driver)
            if price is None:
                # Ошибку логгировать внутри
                continue

            product.price = Decimal(price)
            print("product", product.name, "price", product.price)


    @staticmethod
    def add_to_queue(client: Client, product: Product, url: str):
        with WebManager._lock:
            WebManager.queue.put((client, product, url))
            if WebManager.isActive:
                pass
            else:
                WebManager.isActive = True
                thread = threading.Thread(target=WebManager.check_proc)
                thread.start()

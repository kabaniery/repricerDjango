import multiprocessing
import os
import re
import time
from decimal import Decimal
from queue import Queue

import django
import django.core.signals
import django.db.utils
import requests
from lxml import etree

from scripts.LanguageAdapting import generate_ozon_name
from scripts.ShopInfo import get_code, get_driver


def shutdown():
    if ChromeController.main_activity is not None:
        assert isinstance(ChromeController.main_activity, ChromeController)
        ChromeController.main_activity.turn_off()


class ChromeController(multiprocessing.Process):
    _main_activity = None

    def __new__(cls):
        if ChromeController._main_activity is None:
            cls._main_activity = super(ChromeController, cls).__new__(cls)
        return cls._main_activity

    def __init__(self):
        super().__init__()
        self.queue = Queue()
        self.trigger = multiprocessing.Value('i', 1)

    def turn_off(self):
        self.trigger.value = 0
        self.terminate()

    @staticmethod
    def generate_queue(client):
        django.setup()
        from repricer.models import Product, Client
        assert isinstance(client, Client)
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
            print("Overall size is", len(all_data.json()['result']['items']))
            for item in all_data.json()['result']['items']:
                body['offer_id'] = item['offer_id']
                item_data = requests.post("https://api-seller.ozon.ru/v2/product/info", headers=header, json=body)
                if item_data.status_code != 200 or item_data.json().get('result') is None:
                    time.sleep(0.5)
                    item_data = requests.post("https://api-seller.ozon.ru/v2/product/info", headers=header, json=body)
                    if item_data.status_code != 200:
                        print("Error on request product/info with offerId", body['offer_id'], ". Text:", item_data.text)
                        continue
                json_data = item_data.json()['result']
                product = Product(id=f"{client.username}::{json_data['offer_id']}", offer_id=json_data['offer_id'],
                                  shop=client, name=json_data['name'],
                                  gray_price=int(float(json_data['price'])), price=0)
                ChromeController().queue.put((client, product, generate_ozon_name(json_data['name'], json_data['sku'])))
                print("putted")

    def __del__(self):
        pass

    def find_price(self, url, driver):
        page_source = get_code(driver, url, delay=0.0)
        root = etree.HTML(page_source)
        parent_elements = root.xpath("/html/body/div[1]/div[1]/div[1]/div")
        parent_length = len(parent_elements)
        price_container = None
        if parent_length == 2:
            # Значит товар не доставляется или не найден
            price_container = parent_elements[1].xpath(
                "./div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/span")[0]
        elif parent_length == 6:
            # Значит товар есть
            price_container = \
                parent_elements[3].xpath("./div[3]/div[2]/div[1]/div")[-1].xpath(
                    "./div[1]/div[1]/div[1]/div[1]//span[1]")
            if len(price_container) == 0:
                print(url)
                return
            else:
                price_container = price_container[0]
            if len(price_container) > 0:
                price_container = price_container.xpath(".//span[1]")[0]
        else:
            print("Can't parse page", driver.title)
            return None
        price = re.sub(r'\D', '', price_container.text)
        return price

    def run(self) -> None:
        time.sleep(5)
        if self.driver is None:
            self.driver = get_driver()
        from repricer.models import Product
        it = 0
        mass = list()
        print("Process started")
        while self.trigger.value == 1:
            if self.queue.empty():
                print(self.queue.qsize())
                it = 0
                time.sleep(1)
                continue
            client, product, url = self.queue.get()
            if client is None or product is None or url is None:
                it = 0
                time.sleep(1)
                continue
            if not client.product_blocked:
                continue

            price = self.find_price(url, self.driver)
            if price is None:
                continue
            product.price = Decimal(price)
            print("product", product.name, "price", product.price)
            mass.append(product)
            it += 1
            product.it = it
            if it % 10 == 0:
                try:
                    Product.objects.bulk_create(mass)
                    mass = list()
                except django.db.utils.IntegrityError as e:
                    print("Can't add these products", *mass)
                    print(e)

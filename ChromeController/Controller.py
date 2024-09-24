import multiprocessing
import re
import threading
import time
from decimal import Decimal

import django
from celery.worker.state import requests
from lxml import etree
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

from scripts.ShopInfo import get_driver, get_code

from selenium.webdriver import ChromeOptions, Chrome


def shop_info(current_driver: webdriver.Chrome, result: dict, client_id, shop_url):
    try:
        html = etree.HTML(get_code(current_driver, shop_url))
        parental_object = html.xpath("/html/body/div[1]/div[1]/div[1]/div[@data-widget='shopInShopContainer'][1]/div["
                                     "1]/div[1]/div[1]")[0]
        image_object = parental_object.xpath("./div[1]/div[1]")[0]
        style_value = image_object.get('style')
        background_url = re.search(r'background:url\((.*?)\)', style_value).group(1)
        shop_name = parental_object.xpath("./div[2]/div[1]/span[1]")[0].text
        response = requests.get(background_url)
        filename: str = str(client_id) + "." + background_url.split(".")[-1]
        # Сохранение изображения
        from django.core.files.base import ContentFile
        image_content = ContentFile(response.content, filename)
        result['avatar_path'] = image_content
        result['avatar_name'] = filename
        result['shop_name'] = shop_name
        result['status'] = True
    except Exception as e:
        print(e)
        print(current_driver.title)
        result['status'] = False
        result['message'] = e
    current_driver.close()


class SeleniumManager(multiprocessing.Process):
    def __init__(self, data_queue):
        super().__init__()
        self.driver = None
        self.data_queue = data_queue
        self._lock = threading.Lock()

    def force_push(self, shop_url, client_id, api_key):
        self._lock.acquire()
        result = dict()
        url_thread = threading.Thread(target=shop_info, args=(get_driver(), result, client_id, shop_url))
        url_thread.start()

        headers = {
            'Client-Id': str(client_id),
            'Api-Key': api_key,
        }
        body = {
            'filter': dict(),
            'limit': 1
        }
        response = requests.post("https://api-seller.ozon.ru/v2/product/list", headers=headers, json=body)
        url_thread.join()
        self._lock.release()
        if response.status_code == 200:
            if result['status']:
                return result
        return {'status': False, 'message': 'Неправильные данные аутентификации на странице'}

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

    def run(self):
        from repricer.models import Client, Product
        import django.db.utils

        # Копипаста из Driver
        options = ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=9222")
        from random import randint
        port = randint(9000, 9999)
        options.add_argument(f"--remote-debugging-port={port}")
        options.add_argument("--window-size=1920x1080")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36")
        options.add_argument("--disable-software-rasterizer")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--enable-javascript")

        # service = Service('/usr/bin/chromedriver')
        self.driver = Chrome(options=options)

        mass = list()
        it = 0
        while True:
            try:
                client, product, url = self.data_queue.get(timeout=3)
                if client is None or product is None or url is None:
                    it = 0
                    time.sleep(1)
                    continue
                if not client.product_blocked:
                    continue
                self._lock.acquire()
                price = self.find_price(url, self.driver)
                self._lock.release()
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
            except Exception as e:
                print(e)

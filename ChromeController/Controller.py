import multiprocessing
import re
import threading
import time
from decimal import Decimal

import django
from lxml import etree
from selenium.webdriver.chrome.service import Service

from scripts.ShopInfo import get_driver, get_code

from selenium.webdriver import ChromeOptions, Chrome


class SeleniumManager(multiprocessing.Process):
    def __init__(self, data_queue):
        super().__init__()
        self.data_queue = data_queue

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
        chrome_options = ChromeOptions()
        chrome_options.add_argument("--enable-javascript")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        from random import randint
        port = randint(9000, 9999)
        chrome_options.add_argument(f"--remote-debugging-port={port}")
        chrome_options.add_argument("--window-size=1920x1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # service = Service('/usr/bin/chromedriver')
        driver = Chrome(options=chrome_options)

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

                price = self.find_price(url, driver)
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

import multiprocessing
import re
import threading
import time
from decimal import Decimal

import requests
from django.core.files.base import ContentFile
from lxml import etree
from selenium.webdriver import ChromeOptions, Chrome

import scripts.Driver
from scripts.Driver import get_code


class SeleniumManager(multiprocessing.Process):
    def __init__(self, data_queue, force_queue):
        super().__init__()
        self.driver = None
        self.data_queue = data_queue
        self._lock = threading.Lock()
        self.force_queue = force_queue



    def find_price(self, url, driver):
        page_source = get_code(driver, url, delay=0.0)
        root = etree.HTML(page_source)
        parent_elements = root.xpath("/html/body/div[1]/div[1]/div[1]/div")
        parent_length = len(parent_elements)
        price_container = None
        gray_price = None
        try:
            if parent_length == 2:
                # Значит товар не доставляется или не найден
                price_container = parent_elements[1].xpath(
                    "./div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/span")[0]
            elif parent_length == 6:
                #Элемент с data-widget = webPrice
                element = parent_elements[3].xpath("./div[3]/div[2]/div[1]/div")[-1].xpath(
                    "./div[1]/div[1]/div[1]/div[1]")[0]
                # Значит товар есть
                price_container = \
                    element.xpath(".//span[1]")
                if len(price_container) == 0:
                    print("Error: can't find price on page", url)
                    return None
                else:
                    price_container = price_container[0]
                if len(price_container) > 0:
                    price_container = price_container.xpath(".//span[1]")[0]
                    gray_price_container = element.xpath("./div[1]/div[2]//span[1]")[0]
                    gray_price = re.sub(r'\D', '', gray_price_container.text)
            else:
                print("Can't parse page", driver.title)
                return None
            price = re.sub(r'\D', '', price_container.text)
        except Exception as e:
            print(e)
            with open("1.html", 'w') as file:
                file.write(page_source)
            return None
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
                if not self.force_queue.empty():
                    shop_url, client_id = self.force_queue.get()
                    try:
                        code = get_code(self.driver, shop_url)
                        with open("temp.html", "w") as f:
                            f.write(code)
                        html = etree.HTML(code)
                        parental_object = \
                        html.xpath("/html/body/div[1]/div[1]/div[1]/div[@data-widget='shopInShopContainer'][1]/div["
                                   "1]/div[1]/div[1]")[0]
                        image_object = parental_object.xpath("./div[1]/div[1]")[0]
                        style_value = image_object.get('style')
                        background_url = re.search(r'background:url\((.*?)\)', style_value).group(1)
                        shop_name = parental_object.xpath("./div[2]/div[1]/span[1]")[0].text
                        response = requests.get(background_url)
                        filename: str = str(client_id) + "." + background_url.split(".")[-1]
                        # Сохранение изображения
                        image_content = ContentFile(response.content, filename)
                        client = Client.objects.get(username=client_id)
                        client.shop_name = shop_name
                        client.shop_avatar.save(filename, image_content)
                        client.save()
                    except Exception as e:
                        print(e)
                        print(self.driver.title)
                    continue
                client = None
                product = None
                url = None
                new_price = None
                if not self.data_queue.empty():
                    client, product, url, new_price = self.data_queue.get(timeout=3)
                else:
                    self._lock.acquire()
                    Product.objects.bulk_create(mass)
                    self._lock.release()
                    mass = list()
                    continue
                if client is None or product is None or url is None:
                    it = 0
                    time.sleep(1)
                    continue
                if not client.product_blocked:
                    continue
                if product.offer_id == '797320':
                    print('test2 started')
                gray_price = None
                price = self.find_price(url, self.driver)

                if price is None:
                    continue
                product.price = Decimal(price)
                if gray_price is not None:
                    product.gray_price = Decimal(gray_price)
                else:
                    product.gray_price = price
                if new_price is not None:
                    if abs(float(price) - float(new_price)) > 10:
                        from repricer.views import changing_price
                        changing_price(client, {product.offer_id: [int(float(price)), int(float(new_price))]}, last_time=True)
                    product.save()
                    continue
                mass.append(product)
                it += 1
                scripts.Driver.it = it
                if it % 10 == 0:
                    try:
                        self._lock.acquire()
                        Product.objects.bulk_create(mass)
                        self._lock.release()
                        mass = list()
                    except django.db.utils.IntegrityError as e:
                        print("Can't add these products", *mass)
                        print(e)
            except KeyboardInterrupt as e:
                print(e)

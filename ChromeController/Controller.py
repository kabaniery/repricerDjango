import logging
import multiprocessing
import re
import threading
import time
from decimal import Decimal

import requests
import selenium.common.exceptions as exceptions
from lxml import etree
from selenium.webdriver import ChromeOptions

import scripts.Driver
from scripts.Driver import get_code
from ChromeController.orm.models import Client, Product


class SeleniumManager(multiprocessing.Process):
    lock = multiprocessing.Lock()

    def __init__(self, data_queue, process_it):
        super().__init__()
        self.driver = None
        self.data_queue = data_queue
        self._lock = threading.Lock()
        self.logger = logging.getLogger("parallel_process")
        self.process_it = process_it
        self.last_alive_ping = multiprocessing.Value('d', time.time())

    def products_save(self, products):
        try:
            Product.bulk_create(products)
        except Exception:
            for product in products:
                try:
                    product.save()
                except Exception as e:
                    self.logger.error(f"Can't save product with {e}")

    def find_price(self, url, driver):
        try:
            page_source = get_code(driver, url, delay=0.0)
        except Exception as e:
            self.logger.error(f"Can't get page with exception {e}")
            self.create_driver()
            time.sleep(1)
            page_source = get_code(self.driver, url, delay=0.0)
            self.logger.info("Error complete successfully")
        root = etree.HTML(page_source)
        parent_elements = root.xpath("/html/body/div[1]/div[1]/div[1]/div")
        parent_length = len(parent_elements)
        try:
            if parent_length == 2:
                # Значит товар не доставляется или не найден
                price_container = parent_elements[1].xpath(
                    "./div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/span")[0]
            elif parent_length == 6:
                # Элемент с data-widget = webPrice
                element = parent_elements[3].xpath("./div[3]/div[2]/div[1]/div[1]")[0].xpath(
                    "./div[1]/div[@data-widget='webSale']/div[1]/div[1]")[
                    0]  # Заместо div[2] сделать анализ количества дивов https://www.ozon.ru/product/okulyar-sky-watcher-wa-66-6-mm-1-25-1539568637/
                # Значит товар есть
                price_container = \
                    element.xpath(".//span[1]")
                if len(price_container) == 0:
                    self.logger.error(f"Can't find price on page {url}")
                    return None
                else:
                    price_container = price_container[0]
                if len(price_container) > 0:
                    price_container = price_container.xpath(".//span[1]")[0]
            else:
                self.logger.error(f"Can't find price on page {url}")
                return None
            price = re.sub(r'\D', '', price_container.text)
        except Exception as e:
            self.logger.critical(f"Unexpected error while finding price on page {url} with error {e}")
            with open("broken_page.html", "w") as f:
                f.write(page_source)
            return None
        return price

    def create_driver(self):
        # Копипаста из Driver
        options = ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        from random import randint
        port = randint(9000, 9999)
        options.add_argument(f"--remote-debugging-port={self.process_it + 9000}")
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
        with SeleniumManager.lock:
            # service = Service('/usr/bin/chromedriver')
            self.driver = scripts.Driver.get_driver()

    def run(self):
        self.create_driver()
        self.logger.info(f"Controller {self.process_it} started")
        mass = list()
        it = 0
        client_map: dict[Client] = dict()
        while True:
            try:
                self.last_alive_ping.value = time.time()
                if not self.data_queue.empty():
                    try:
                        command, client_id, data = self.data_queue.get(timeout=3)
                    except Exception:
                        self.logger.info("Empty queue...")
                        time.sleep(3)
                        continue
                else:
                    if len(mass) > 0:
                        print("mass writed")
                        self._lock.acquire()
                        self.products_save(mass)
                        self._lock.release()
                    mass = list()
                    # Прописать освобождение ресурсов
                    time.sleep(10)
                    continue
                if command is None or client_id is None or data is None:
                    time.sleep(1)
                    continue

                if command == 0:
                    code = get_code(self.driver, data)

        self.logger.critical(f"Thread {self.process_it} was stopped")

import asyncio
import datetime
import logging
import multiprocessing
import re
import threading
import time

import requests
from lxml import etree
from selenium.webdriver import ChromeOptions
from sqlalchemy import and_

from ChromeController.helper import changing_price, init_db, execute_async
from ChromeController.orm.AlchemyManager import AlchemyManager
from ChromeController.orm.alchemy_models import Client, Product
from scripts.Driver import get_code, get_driver, get_request
from scripts.LanguageAdapting import generate_ozon_name


class SeleniumManager(threading.Thread):
    lock = threading.Lock()
    iterator = 0

    def __init__(self, data_queue, process_it):
        super().__init__()
        print(f"init started {process_it}")
        self.driver = None

        self.data_queue = data_queue

        self.logger = logging.getLogger("parallel_process")
        self.process_it = process_it
        self.last_alive_ping = multiprocessing.Value('d', time.time())
        self.manager = AlchemyManager()
        print(f"init complete {process_it}")

    def products_save(self, products):
        try:
            self.manager.session.bulk_save_objects(products)
        except Exception:
            for product in products:
                try:
                    self.manager.add(product)
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
                if price_container.get("class") != "om2_27 tsHeadline400Small":
                    print(f"Not ok {url}")
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
            if int(price) > 5000000:
                with open(f"temp/{SeleniumManager.iterator}.html", "w", encoding="utf-8") as f:
                    f.write(page_source)
                    SeleniumManager.iterator += 1
        except Exception as e:
            self.logger.critical(f"Unexpected error while finding price on page {url} with error {e}")
            with open("broken_page.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            return None
        return price

    def create_driver(self):
        with SeleniumManager.lock:
            self.driver = get_driver()

    def run(self):
        print(f"start driver creating for {self.process_it}")
        self.create_driver()
        self.logger.info(f"Controller {self.process_it} started")
        while True:
            self.last_alive_ping.value = time.time()
            if not self.data_queue.empty():
                try:
                    command, client_id, data = self.data_queue.get(timeout=3)
                except Exception:
                    self.logger.info("Empty queue...")
                    time.sleep(3)
                    continue
            else:
                # Прописать освобождение ресурсов
                time.sleep(10)
                continue
            if command is None or client_id is None or data is None:
                time.sleep(1)
                continue
            client = self.manager.session.query(Client).filter(Client.username == client_id).first()
            # client = execute_async(Client.get, username=client_id)
            if command == 0:
                try:
                    code = get_code(self.driver, data)
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
                    # TODO: Сохранение изображения
                    # image_content = ContentFile(response.content, filename)
                    client.shop_name = shop_name
                    # client.shop_avatar.save(filename, image_content)
                    self.manager.session.commit()
                    # execute_async(client.save)
                except Exception as e:
                    self.logger.error(f"Can't process force queue on page {self.driver.current_url}")
            elif command == 1:
                print("queue getted")
                if client.last_product == data:
                    client.product_blocked = False
                    time.sleep(3)
                    self.manager.session.query(Product).filter(Product.to_removal == True).delete(
                        synchronize_session=False)
                    self.manager.session.commit()
                    # execute_async(client.save)
                product = self.manager.session.query(Product).filter(and_(
                    Product.shop == client, Product.offer_id == str(data))).first()
                # product_list = execute_async(Product.filter, shop=client, offer_id=str(data))
                if product is None:
                    headers = {
                        "Client-Id": client.username,
                        "Api-Key": client.api_key
                    }
                    body = {
                        "offer_id": data
                    }
                    response = get_request("https://api-seller.ozon.ru/v2/product/info", headers, body)
                    if response.status_code == 200:
                        product_info = response.json()['result']
                        product = Product(id=f"{client.username}::{data}", shop=client, offer_id=data,
                                          name=product_info['name'], sku=product_info['sku'], price=0,
                                          is_updating=True, to_removal=False,
                                          last_update=datetime.datetime.now(datetime.timezone.utc))
                        self.manager.add(product)
                        # product = execute_async(Product.create, id=f"{client.username}::{data}", shop=client, offer_id=data, name=product_info['name'], sku=product_info['sku'], price=0, is_updating=True)
                    else:
                        self.logger.error(f"Cannot create product: {response.text}")
                product.to_removal = False
                product.is_updating = False
                product.last_update = datetime.datetime.now(datetime.timezone.utc)
                url = generate_ozon_name(product.name, product.sku)

                price = self.find_price(url, self.driver)
                if str(data) == "67882":
                    print(url, price)

                if price is not None:
                    product.price = price
                    product.is_updated = False
                    # TODO: сделать установку цен групповой
                    self.manager.session.commit()
                    # execute_async(product.save)
                    if product.needed_price is not None and 0 < product.needed_price != price:
                        changing_price(client, {product.offer_id: [product.price, product.needed_price]},
                                       self.data_queue,
                                       last_time=True)
                        # execute_async(changing_price, client,
                        #              {product.offer_id: [product.price, product.needed_price]},
                        #              self.data_queue,
                        #              last_time=True)
                else:
                    self.manager.session.commit()
                    # execute_async(product.save)
                    self.logger.error(f"Can't find price for product {url}")

        self.logger.critical(f"Thread {self.process_it} was stopped")

    async def async_body(self):
        await init_db()

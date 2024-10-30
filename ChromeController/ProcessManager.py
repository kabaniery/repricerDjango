import datetime
import json
import logging
import multiprocessing
import time

import redis
from pyvirtualdisplay import Display
from tortoise import Tortoise

from ChromeController.Controller import SeleniumManager
from ChromeController.orm import tortoise_config
from ChromeController.orm.models import Client, Product
from scripts.Driver import get_request
from scripts.LanguageAdapting import generate_ozon_name


def is_old_price_correct(old_price, price):
    if old_price == 0:
        return True
    if price < 400:
        return old_price - price > 20
    elif price < 10000:
        return price / old_price < 0.95
    else:
        return old_price - price > 500


# TODO: перенести в ProcessManager



class Manager(multiprocessing.Process):
    _singleton = None

    def __new__(cls, *args, **kwargs):
        if cls._singleton is None:
            cls._singleton = super(Manager, cls).__new__(cls)
        return cls._singleton


    def __init__(self, count_process: int):
        super().__init__()
        self.putQueue = multiprocessing.Queue()
        self.count = count_process
        self.threads = list()
        self.logger = logging.getLogger("parallel_process")
        self.broker = redis.StrictRedis(host='localhost', port=6379, db=0)
        await Tortoise.init(config=tortoise_config.tortoise_config)

    def __del__(self):
        self.logger.warning("process stopped?")


    # products: {'offer-id': (old_price, new_price, new_gray_price)}
    def changing_price(self, client: Client, products: dict[int, list[int, int]], last_time=False):
        headers = {
            'Client-Id': client.username,
            'Api-Key': client.api_key
        }
        data = {
            'filter': {
                'offer_id': list(products.keys())
            },
            'limit': str(len(products.keys()))
        }
        response = get_request("https://api-seller.ozon.ru/v4/product/info/prices", headers, data)
        if response.status_code == 200:
            prices = list()
            for item in response.json()['result']['items']:
                new_green = int(float(products[item['offer_id']][1]))
                fact_price = int(float(item['price']['price']))
                old_green = int(float(products[item['offer_id']][0]))
                new_price = int(new_green * fact_price / old_green)

                # Дебаг
                if item['offer_id'] == '77103':
                    print('setted price -', new_price)

                if is_old_price_correct(float(item['price']['old_price']), new_price):
                    old_price = item['price']['old_price']
                else:
                    old_price = str(int(float(item['price']['old_price']) * new_price / fact_price))
                actual_data = {
                    'auto_action_enabled': 'UNKNOWN',
                    'currency_code': item['price']['currency_code'],
                    'min_price': str(new_price - 1),
                    'offer_id': item['offer_id'],
                    'old_price': old_price,
                    'price': str(new_price),
                    'price_strategy_enabled': 'UNKNOWN',
                    'product_id': item['product_id']
                }
                prices.append(actual_data)

            new_data = {
                'prices': prices
            }
            response = get_request('https://api-seller.ozon.ru/v1/product/import/prices', headers, new_data)
            if response.status_code == 200:
                if last_time:
                    for key, value in products.items():
                        try:
                            product_list = await Product.filter(shop=client, offer_id=str(key))
                            if len(product_list) > 0:
                                product = product_list[0]
                            else:
                                logging.getLogger("django").error(
                                    f"Can't find product {key} for client {client.username}")
                                continue
                            product.price = value[1]
                            product.save()
                        except Exception:
                            logging.getLogger("django").warning(
                                f"Error reparse for product {key} user {client.username}")
                    return
                for key, value in products.items():
                    self.putQueue.put([1, client.username, key])
            else:
                print("error on edit", response.text)
        else:
            print("error", response.text)


    def selenium_healer(self, process_list: list[SeleniumManager]):
        logger = logging.getLogger("parallel_process")
        while True:
            for index, process in enumerate(process_list):
                if time.time() - process.last_alive_ping.value > 60:
                    logger.warning(f"Process {process.process_it} has been dead. Revive it...")
                    it = process.process_it

                    process.terminate()
                    time.sleep(5)

                    process_list[index] = SeleniumManager(self.putQueue, it)
                    process_list[index].start()
            time.sleep(5)

    def run(self):
        self.logger.info(f"Process started with {self.count} threads")
        display = Display(visible=False, size=(1920, 1080))
        display.start()
        time.sleep(10)

        self.threads = [SeleniumManager(self.putQueue, i) for i in range(self.count)]
        for thread in self.threads:
            thread.start()

        p_reviewer = multiprocessing.Process(target=self.selenium_healer, args=(self.threads,))
        p_reviewer.start()

        while True:
            # Блок с оживлением процессов
            for it, thread in enumerate(self.threads):
                if not thread.is_alive():
                    self.threads[it] = SeleniumManager(self.putQueue, thread.process_it)
                    self.threads[it].start()
                    '''p_reviewer.terminate()
                    display.stop()
                    self.logger.warning("display stopped")
                    for thread in self.threads:
                        if thread.is_alive():
                            thread.terminate()
                    self.logger.critical("Main Process stopped")
                    return'''

            # Блок с считыванием данных
            message = self.broker.rpop("register")
            if message is not None:
                message_split = message.split(";")
                client_id = message_split[0]
                shop_url = message_split[1]
                self.putQueue.put([0, client_id, shop_url])

            message = self.broker.rpop("changer")
            if message is not None:
                message_split = message.split(";;")
                client_id = message_split[0]
                data = json.loads(message_split[1])
                self.changing_price(await Client.get(username=client_id), data)

            message = self.broker.rpop("parser")
            if message is not None:
                client = await Client.get(username=message)
                headers = {
                    "Client-Id": client.username,
                    "Api-Key": client.api_key
                }
                body = {
                    "filter": {
                        'visibility': 'VISIBLE'
                    },
                    "limit": 1000
                }
                result = get_request("https://api-seller.ozon.ru/v2/product/list", headers, body)
                if result.status_code == 200:
                    for item in result.json()['result']['items']:
                        offer_id = item['offer_id']
                        self.putQueue.put([1, client.username, offer_id])

            # Блок автопрогрузки
            clients = await Client.all()
            now = datetime.datetime.now()
            for client in clients:
                assert isinstance(client, Client)
                if (now - client.last_update).total_seconds() > 1800:
                    for product in await Product.filter(shop=client):
                        self.putQueue.put([1, client.username, product.offer_id])


    def put_data(self, data):
        self.putQueue.put(data)

    def add_product(self, username, api_key, offer_id):
        headers = {
            "Client-Id": username,
            'Api-Key': api_key
        }
        body = {
            'offer_id': offer_id
        }
        response = get_request("https://api-seller.ozon.ru/v2/product/info", headers, body)

        if response.status_code != 200 or response.json()['result'] is None:
            time.sleep(0.5)
            item_data = get_request("https://api-seller.ozon.ru/v2/product/info", headers, body)
            if item_data.status_code != 200:
                self.logger.critical(
                    f"Error on request product/info with offerId {body['offer_id']}. Text: {item_data.text}")
                return

        from repricer.models import Client, Product
        client = Client.objects.get(username=username)
        json_data = response.json()['result']
        if not Product.objects.filter(offer_id=json_data['offer_id']).exists():
            product = Product(id=f"{client.username}::{json_data['offer_id']}", offer_id=json_data['offer_id'],
                              shop=client, name=json_data['name'], price=0, is_updating=True)
        else:
            product = Product.objects.get(offer_id=json_data['offer_id'])
            product.to_removal = False
            product.is_updating = True
            product.save()
        self.putQueue.put(
            (client, product, generate_ozon_name(json_data['name'], json_data['sku']), None))

    def correct_product(self, username, api_key, offer_id, new_price):
        headers = {
            "Client-Id": username,
            'Api-Key': api_key
        }
        body = {
            'offer_id': offer_id
        }
        response = get_request("https://api-seller.ozon.ru/v2/product/info", headers, body)
        if response.status_code != 200 or response.json()['result'] is None:
            time.sleep(0.5)
            item_data = get_request("https://api-seller.ozon.ru/v2/product/info", headers, body)
            if item_data.status_code != 200:
                self.logger.critical(
                    f"Error on request correct product/info with offerId {body['offer_id']}. Text: {item_data.text}")
                return
        client = Client.objects.get(username=username)
        json_data = response.json()['result']
        try:
            product = Product.objects.get(shop=client, offer_id=offer_id)
        except Exception as e:
            self.logger.error(f"Can't get product {offer_id} from client {username} with {e}")
            return
        product.is_updating = True
        self.putQueue.put(
            (client, product, generate_ozon_name(json_data['name'], json_data['sku']), new_price))

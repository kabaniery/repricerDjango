import asyncio
import json
import logging
import multiprocessing
import time

import redis
from datetime import datetime, timezone

from tortoise.transactions import in_transaction

from ChromeController.Controller import SeleniumManager
from ChromeController.helper import changing_price, init_db, execute_async
from ChromeController.orm.AlchemyManager import AlchemyManager
from ChromeController.orm.alchemy_models import Client, Product
from scripts.Driver import get_request


async def save_client(client):
    async with in_transaction():
        await client.save()


class Manager(multiprocessing.Process):
    def __init__(self, count_process: int):
        super().__init__()
        self.putQueue = None
        self.count = count_process
        self.threads = list()
        self.logger = logging.getLogger("parallel_process")
        self.broker = None
        self.manager = None

    def __del__(self):
        self.logger.warning("process stopped?")

    def run(self):
        self.manager = AlchemyManager()
        self.putQueue = multiprocessing.Queue()
        self.threads = [SeleniumManager(self.putQueue, i) for i in range(self.count)]
        for thread in self.threads:
            thread.start()

        self.logger.info(f"Process started with {self.count} threads")
        self.broker = redis.StrictRedis(host='localhost', port=6379, db=0)
        # display = Display(visible=False, size=(1920, 1080))
        # display.start()
        it = 0
        while True:
            time.sleep(3)
            print("Ok", it)
            it += 1

            # Блок с считыванием данных
            message = self.broker.rpop("register")
            if message is not None:
                message = message.decode("utf-8")
                message_split = message.split(";")
                client_id = message_split[0]
                shop_url = message_split[1]
                self.putQueue.put([0, client_id, shop_url])

            message = self.broker.rpop("changer")
            if message is not None:
                message = message.decode("utf-8")
                message_split = message.split(";;")
                client_id = message_split[0]
                data = json.loads(message_split[1])
                print(data)
                changing_price(self.manager.session.query(Client).filter(Client.username == client_id).first(), data, self.putQueue)
                # execute_async(changing_price, execute_async(Client.get, username=client_id), data, self.putQueue)

            message = self.broker.rpop("parser")
            if message is not None:
                print("broker getted")
                message = message.decode("utf-8")
                client = self.manager.session.query(Client).filter(Client.username == message).first()
                # client = execute_async(Client.get, username=message)
                assert isinstance(client, Client)
                self.manager.session.query(Product).filter(Product.shop == client).update({Product.to_removal: True})
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
                    last_offer_id = None
                    print(f"queue putting {len(result.json()['result']['items'])}")
                    for item in result.json()['result']['items']:
                        offer_id = item['offer_id']
                        self.putQueue.put([1, client.username, offer_id])
                        last_offer_id = offer_id
                    if last_offer_id is None:
                        client.product_blocked = False
                    else:
                        client.last_product = last_offer_id
                    self.manager.session.commit()

            # Блок автопрогрузки
            clients = self.manager.session.query(Client).all()
            # clients = execute_async(Client.all)
            now = datetime.now(timezone.utc)
            for client in clients:
                assert isinstance(client, Client)
                products = self.manager.session.query(Product).filter(Product.shop == client).all()
                # products = execute_async(Product.filter, shop=client)
                for product in products:
                    if (now - product.last_update).total_seconds() > 1800 and not product.is_updating:
                        # TODO: сделать это массовым
                        product.is_updating = True
                        # execute_async(product.save)
                        self.putQueue.put([1, client.username, product.offer_id])
                self.manager.session.commit()

            # Блок восстановления данных

            now = time.time()
            for index, thread in enumerate(self.threads):
                if now - thread.last_alive_ping.value > 60:
                    try:
                        thread.driver.close()
                    except:
                        pass
                    self.threads[index] = SeleniumManager(self.putQueue, index)
                    self.threads[index].start()
                    self.logger.warning(f"Thread {index} was reload")



    async def async_worker(self):
        await init_db()


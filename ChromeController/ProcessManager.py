import multiprocessing
import time

import django
import requests
from pyvirtualdisplay import Display

import ChromeController.Controller
from ChromeController.Controller import SeleniumManager
from scripts.LanguageAdapting import generate_ozon_name


class Manager(multiprocessing.Process):
    _singleton = None

    @staticmethod
    def shutdown():
        if Manager._singleton is not None:
            singleton = Manager._singleton
            for thread in singleton.threads:
                thread.terminate()


    @staticmethod
    def get_instance():
        return Manager._singleton

    def __new__(cls, *args, **kwargs):
        if cls._singleton is None:
            cls._singleton = super(Manager, cls).__new__(cls)
        return cls._singleton

    def __init__(self, count_process: int, q):
        super().__init__()
        self.putQueue = q
        self.started = False
        self.count = count_process
        self.threads = list()

    def __del__(self):
        print("Manager stopped")

    def run(self):
        self.started = True
        display = Display(visible=False, size=(1920, 1080))
        display.start()
        time.sleep(5)
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repricerDjango.settings')
        django.setup()
        self.threads = [SeleniumManager(self.putQueue) for _ in range(self.count)]
        for thread in self.threads:
            thread.start()

        for thread in self.threads:
            thread.join()
        display.stop()
        print("diplay stopped")

    def push_request(self, shop_url, client_id, api_key):
        assert isinstance(self.threads[0], SeleniumManager)
        return self.threads[0].force_push(shop_url, client_id, api_key)

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
        response = requests.post("https://api-seller.ozon.ru/v2/product/info", headers=headers, json=body)

        if response.status_code != 200 or response.json()['result'] is None:
            time.sleep(0.5)
            item_data = requests.post("https://api-seller.ozon.ru/v2/product/info", headers=headers, json=body)
            if item_data.status_code != 200:
                print("Error on request product/info with offerId", body['offer_id'], ". Text:", item_data.text)
                return

        from repricer.models import Client, Product
        client = Client.objects.get(username=username)
        json_data = response.json()['result']
        product = Product(id=f"{client.username}::{json_data['offer_id']}", offer_id=json_data['offer_id'],
                          shop=client, name=json_data['name'],
                          gray_price=int(float(json_data['price'])), price=0)
        self.putQueue.put(
            (client, product, generate_ozon_name(json_data['name'], json_data['sku'])))

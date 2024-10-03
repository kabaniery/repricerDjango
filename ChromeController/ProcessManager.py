import multiprocessing
import time
from datetime import timezone

import django
import requests
from django.utils import timezone
from pyvirtualdisplay import Display

import ChromeController.Controller
from ChromeController.Controller import SeleniumManager
from repricer.models import Client, Product
from scripts.LanguageAdapting import generate_ozon_name


class Manager(multiprocessing.Process):
    _singleton = None

    @staticmethod
    def shutdown():
        print("shutting down manager")
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
        self.forceQueue = multiprocessing.Manager().Queue()

    def __del__(self):
        print("Manager stopped")

    def run(self):
        self.started = True
        print("main cycle started")
        print(self.count)
        display = Display(visible=False, size=(1920, 1080))
        display.start()
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repricerDjango.settings')
        django.setup()
        self.threads = [SeleniumManager(self.putQueue, self.forceQueue) for _ in range(self.count)]
        for thread in self.threads:
            thread.start()
        while True:
            for thread in self.threads:
                if not thread.is_alive():
                    display.stop()
                    print("display stopped")
                    for thread in self.threads:
                        if thread.is_alive():
                            thread.terminate()
                    return
            ctime = timezone.now()
            clients = Client.objects.all()
            for client in clients:
                if (ctime - client.last_update).total_seconds() > 3600:
                    client.last_update = ctime
                    client.save()
                    products = Product.objects.filter(shop=client)
                    for product in products:
                        if product.needed_price is not None and product.needed_price > 0:
                            self.correct_product(client.username, client.api_key, product.offer_id, product.needed_price)

            time.sleep(120)

    def push_request(self, shop_url, client_id, api_key):
        result = dict()
        headers = {
            'Client-Id': str(client_id),
            'Api-Key': api_key,
        }
        body = {
            'filter': dict(),
            'limit': 1
        }
        response = requests.post("https://api-seller.ozon.ru/v2/product/list", headers=headers, json=body)
        result['status'] = True
        if response.status_code == 200:
            self.forceQueue.put((shop_url, client_id))
            if result['status']:
                return result
        return {'status': False, 'message': 'Неправильные данные аутентификации на странице'}

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
                          gray_price=0, price=0)
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
        product = Product.objects.get(shop=client, offer_id=offer_id)
        self.putQueue.put(
            (client, product, generate_ozon_name(json_data['name'], json_data['sku']), new_price))
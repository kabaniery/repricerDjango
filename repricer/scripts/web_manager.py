import threading
import time
from os import path
from queue import Queue

import requests

from repricer.models import Client, Product
from repricer.scripts.ozon_finder import SeleniumProcess
from repricerDjango.settings import MEDIA_URL, MEDIA_ROOT


class WebManager(threading.Thread):

    def __init__(self):
        super().__init__()

    _lock = threading.Lock()

    queue = Queue()
    isActive = False

    @staticmethod
    def check_proc():
        client = WebManager.queue.get()
        if client is None:
            WebManager.isActive = False
            return

        Product.objects.filter(shop=client).delete()

        # запуск процесса
        stop = False
        proc = SeleniumProcess(client, stop)
        proc.start()

        # Поиск всех данных из API
        header = {
            'Client-Id': client.username,
            'Api-Key': client.api_key
        }
        body = {
            'filter': {
                'visibility': 'VISIBLE'
            },
            'limit': 1000
        }

        response = requests.post("https://api-seller.ozon.ru/v2/product/list", headers=header, json=body)
        if response.status_code == 200:
            for item in response.json()['result']['items']:
                item_info_body = {
                    'offer_id': item['offer_id']
                }
                item_info = requests.post("https://api-seller.ozon.ru/v2/product/info", headers=header,
                                          json=item_info_body)
                if item_info.status_code != 200:
                    time.sleep(2)
                    item_info = requests.post("https://api-seller.ozon.ru/v2/product/info", headers=header,
                                              json=item_info_body)
                if item_info.status_code == 200:
                    new_product = Product(shop=client, offer_id=item_info.json()['result']['offer_id'],
                                          name=item_info.json()['result']['name'], price=0)
                    new_product.save()
                else:
                    # TODO: прописать логирование ошибок
                    pass
        else:
            if response.status_code == 403:
                client.is_active = False

        client.product_blocked = False
        client.save()
        with open(path.join(MEDIA_ROOT, "auto_loaders", str(client.username) + ".txt"), "w", encoding="utf-8") as _:
            pass
        while proc.is_alive:
            with open(path.join(MEDIA_ROOT, "auto_loaders", str(client.username) + ".txt"), "a", encoding="utf-8") as auto_loader:
                if not proc.result_data.empty():
                    product_id, product_name, price = proc.result_data.get()
                    product = Product.objects.filter(shop=client, name=product_name)
                    if len(product) == 0:
                        continue
                    elif len(product) > 1:
                        for i in range(1, len(product)):
                            product[i].delete()
                    product = product[0]
                    product.price = int(price)
                    auto_loader.write(f"{product.offer_id} {product.name} {product.price}\n")
                    product.save()

        if WebManager.queue.empty():
            WebManager.isActive = False
        else:
            thread = threading.Thread(target=WebManager.check_proc)
            thread.start()

        client.product_blocked = False
        client.save()

    @staticmethod
    def add_to_queue(client: Client):
        with WebManager._lock:
            WebManager.queue.put(client)
            if WebManager.isActive:
                pass
            else:
                WebManager.isActive = True
                thread = threading.Thread(target=WebManager.check_proc)
                thread.start()

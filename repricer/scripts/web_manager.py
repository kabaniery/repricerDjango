import threading
import time
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
            'Api-Key': client.password
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

        with open(MEDIA_ROOT + "auto_loaders/" + str(client.username) + ".txt", "w") as _:
            pass
        while proc.is_alive():
            with open(MEDIA_ROOT + "auto_loaders/" + str(client.username) + ".txt", "a") as auto_loader:
                if not proc.result_data.empty():
                    product_id, product_name, price = proc.result_data.get()
                    product = None
                    try:
                        product = Product.objects.get(shop=client, product_name=product_name)
                    except Product.DoesNotExist:
                        continue
                    except Product.MultipleObjectsReturned:
                        finded_products = Product.objects.filter(shop=client, product_name=product_name)
                        for i in range(1, finded_products):
                            finded_products[i].delete()
                        product = finded_products[0]
                    finally:
                        product.price = price
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

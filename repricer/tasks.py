import time

import requests
from celery import shared_task

from repricer.models import Product, Client
from scripts.LanguageAdapting import generate_ozon_name
from repricer.ChromeProcess.ChromeController import ChromeController


@shared_task
def add_product(username, api_key, offer_id):
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

    client = Client.objects.get(username=username)
    json_data = response.json()
    product = Product(id=f"{client.username}::{json_data['offer_id']}", offer_id=json_data['offer_id'],
                      shop=client, name=json_data['name'],
                      gray_price=int(float(json_data['price'])), price=0)
    controller = ChromeController().queue.put(
        (client, product, generate_ozon_name(json_data['name'], json_data['sku'])))

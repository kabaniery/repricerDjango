import asyncio
import logging
import threading
import time

from sqlalchemy import and_
from tortoise import Tortoise

from ChromeController.orm.alchemy_models import Client, Product
from ChromeController.orm.AlchemyManager import AlchemyManager
from scripts.Driver import get_request


def is_old_price_correct(old_price, price):
    if old_price == 0:
        return True
    if price < 400:
        return old_price - price > 20
    elif price < 10000:
        return price / old_price < 0.95
    else:
        return old_price - price > 500


# products: {'offer-id': (old_price, new_price, new_gray_price)}
def changing_price(client: Client, products: dict[int, list[int, int]], put_queue, last_time=False):
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
    add_print = False
    response = get_request("https://api-seller.ozon.ru/v4/product/info/prices", headers, data)
    if response.status_code == 200:
        prices = list()
        for item in response.json()['result']['items']:
            new_green = int(float(products[item['offer_id']][1]))
            fact_price = int(float(item['price']['price']))
            old_green = int(float(products[item['offer_id']][0]))
            new_price = int(new_green * fact_price / old_green)
            if new_price == 0:
                logging.getLogger("parallel_process").error(f"price is 0 for {item['offer_id']}")

            # Дебаг
            if item['offer_id'] == '67727':
                print('setted price -', new_price)
                add_print = True

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
            if float(old_price) != 0 and new_price / float(old_price) < 0.3:
                actual_data['old_price'] = str(int(new_price / 0.7))
            prices.append(actual_data)

        new_data = {
            'prices': prices
        }
        response = get_request('https://api-seller.ozon.ru/v1/product/import/prices', headers, new_data)
        if response.status_code == 200:
            if add_print:
                print(response.text)
            if last_time:
                manager = AlchemyManager()
                for key, value in products.items():
                    try:
                        product = manager.session.query(Product).filter(and_(
                            Product.shop == client, Product.offer_id == str(key))).first()
                        if product is None:
                            logging.getLogger("django").error(
                                f"Can't find product {key} for client {client.username}")
                            continue
                        product.price = value[1]
                    except Exception:
                        logging.getLogger("django").warning(
                            f"Error reparse for product {key} user {client.username}")
                manager.session.commit()
                return
            time.sleep(10)
            for key, value in products.items():
                put_queue.put([1, client.username, key])
        else:
            print("error on edit", response.text)
            for block in prices:
                print(block['min_price'], end="; ")

    else:
        print("error", response.text)


async def init_db():
    await Tortoise.init(db_url='postgres://repricer_manager:repricerpassword@127.0.0.1:5432/repricer',
                        modules={'models': ['ChromeController.orm.models']})


lock = threading.Lock()
loop = asyncio.new_event_loop()


def execute_async(command: callable, *args, **kwargs):
    with lock:
        return loop.run_until_complete(command(*args, **kwargs))

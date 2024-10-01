import re

import requests
from lxml import etree
from pyvirtualdisplay import Display
from selenium import webdriver

from scripts.Driver import get_code, get_driver

def get_products():
    headers = {
        'Client-Id': "1267611",
        'Api-Key': "6607a019-7034-43ed-b75d-c6fa63d066d8"
    }
    data = {
        'filter':
            {
                'visibility': 'VISIBLE'
            },
        'limit': 1000
    }
    response = requests.post("https://api-seller.ozon.ru/v2/product/list", headers=headers, json=data)
    return response.json()['result']

def test_display():
    # Создаем виртуальный дисплей
    display = Display(visible=0, size=(1920, 1080))
    display.start()

    # Настройка драйвера Chrome
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')  # Требуется для работы Chrome в контейнере
    options.add_argument('--disable-dev-shm-usage')  # Уменьшает использование памяти
    driver = webdriver.Chrome(options=options)

    # Пример запроса
    driver.get("https://www.ozon.ru/seller/elektromart-1590790/products/?miniapp=seller_1590790")
    print(driver.title)

    # Закрываем драйвер и виртуальный дисплей
    driver.quit()
    display.stop()


def set_price(articul, price):
    headers = {
        'Client-Id': "1590790",
        'Api-Key': "f8d5188f-cbcc-4378-b23f-9178b4489ff1"
    }
    data = {
        'prices': [
            {
                'offer_id': str(articul),
                'price': str(price),
                'old_price': str(price + 500),
                'min_price': str(price * 0.8),
            }
        ]
    }
    response = requests.post("https://api-seller.ozon.ru/v1/product/import/prices", headers=headers, json=data)
    print(response.text)

def page_parser():
    driver = get_driver()
    url = "https://www.ozon.ru/product/mikroskop-biologicheskiy-mikromed-s-11-var-1m-led-1673842749/"
    page_source = get_code(driver, url, delay=0.0)
    root = etree.HTML(page_source)
    parent_elements = root.xpath("/html/body/div[1]/div[1]/div[1]/div")
    parent_length = len(parent_elements)

    price_container = None
    if parent_length == 2:
        # Значит товар не доставляется или не найден
        price_container = parent_elements[1].xpath(
            "./div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/span")[0]
    elif parent_length == 6:
        # Значит товар есть
        price_container = \
            parent_elements[3].xpath("./div[3]/div[2]/div[1]/div")[-1].xpath(
                "./div[1]/div[1]/div[1]/div[1]//span[1]")
        if len(price_container) == 0:
            print("Error: can't find price on page", url)
            return
        else:
            price_container = price_container[0]
        if len(price_container) > 0:
            element = parent_elements[3].xpath("./div[3]/div[2]/div[1]/div")[-1].xpath(
                "./div[1]/div[1]/div[1]/div[1]")[0]
            print(element.get("class"))
            print(price_container.get("class"))
            price_container = price_container.xpath(".//span[1]")[0]
            gray_price_container = element.xpath("./div[1]/div[2]//span[1]")[0]
            gray_price = re.sub(r'\D', '', gray_price_container.text)
    else:
        print("Can't parse page", driver.title)
        return None
    price = re.sub(r'\D', '', price_container.text)
    return price


if __name__ == '__main__':
    print(get_products())
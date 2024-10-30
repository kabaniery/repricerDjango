import logging
import re
import threading

from django.contrib.sites import requests
from django.core.files.base import ContentFile
from lxml import etree
from selenium import webdriver

from scripts.Driver import get_driver, get_code, get_request


# ВОЗВРАЩАЕТ ДАННЫЕ В UTF-8


def shop_info(current_driver: webdriver.Chrome, result: dict, client_id, shop_url):
    try:
        html = etree.HTML(get_code(current_driver, shop_url))
        parental_object = html.xpath("/html/body/div[1]/div[1]/div[1]/div[@data-widget='shopInShopContainer'][1]/div["
                                     "1]/div[1]/div[1]")[0]
        image_object = parental_object.xpath("./div[1]/div[1]")[0]
        style_value = image_object.get('style')
        background_url = re.search(r'background:url\((.*?)\)', style_value).group(1)
        shop_name = parental_object.xpath("./div[2]/div[1]/span[1]")[0].text
        response = requests.get(background_url)
        filename: str = str(client_id) + "." + background_url.split(".")[-1]
        # Сохранение изображения
        image_content = ContentFile(response.content, filename)
        result['avatar_path'] = image_content
        result['avatar_name'] = filename
        result['shop_name'] = shop_name
        result['status'] = True
    except Exception as e:
        logging.getLogger("django").error(f"Can't parse shop info for shop {current_driver.title} with error {e}")
        result['status'] = False
        result['message'] = e
    current_driver.close()


def check_shop_info(client_id, api_key):
    headers = {
        'Client-Id': str(client_id),
        'Api-Key': api_key,
    }
    body = {
        'filter': dict(),
        'limit': 1
    }
    response = get_request("https://api-seller.ozon.ru/v2/product/list", headers, body)
    if response.status_code == 200:
        return True
    return False

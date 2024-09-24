import re
import threading
import time

from django.contrib.sites import requests
from django.core.files.base import ContentFile
from lxml import etree
from selenium import webdriver
from selenium.webdriver.common.by import By

from scripts.Driver import get_driver


def check_block(driver: webdriver.Chrome):
    if "Antibot Challenge Page" == driver.title:
        time.sleep(4)
    if "Доступ ограничен" == driver.title:
        try:
            elem = driver.find_element(By.TAG_NAME, "html").find_element(By.TAG_NAME, "body").find_element(By.TAG_NAME,
                                                                                                           "div").find_element(
                By.TAG_NAME, "div")
            elem = elem.find_element(By.TAG_NAME, "div").find_elements(By.TAG_NAME, "div")
            elem[2].find_element(By.TAG_NAME, "button").click()
            time.sleep(2)
            return driver.page_source
        except Exception as e:
            print(e)
            print(driver.current_url)
            print(len(driver.current_url.split("/")))
            with open(driver.current_url.split("/")[3]+".html", "w") as file:
                file.write(driver.page_source)
    return None


# ВОЗВРАЩАЕТ ДАННЫЕ В UTF-8
def get_code(driver: webdriver.Chrome, site, delay=2.0, exec_script=None, exec_times=1):
    driver.get(site)

    res = check_block(driver)
    if exec_script is not None:
        time.sleep(delay / 2)
        for i in range(exec_times):
            driver.execute_script(exec_script)
            time.sleep(2)
    else:
        time.sleep(delay)
    if res is not None:
        return res
    return driver.page_source


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
        print(e)
        print(current_driver.title)
        result['status'] = False
        result['message'] = e
    current_driver.close()


def get_shop_infos(client_id, api_key, shop_url):
    result = dict()
    url_thread = threading.Thread(target=shop_info, args=(get_driver(), result, client_id, shop_url))
    url_thread.start()

    headers = {
        'Client-Id': str(client_id),
        'Api-Key': api_key,
    }
    body = {
        'filter': dict(),
        'limit': 1
    }
    response = requests.post("https://api-seller.ozon.ru/v2/product/list", headers=headers, json=body)
    url_thread.join()
    if response.status_code == 200:
        if result['status']:
            return result
    return {'status': False, 'message': 'Неправильные данные аутентификации на странице'}

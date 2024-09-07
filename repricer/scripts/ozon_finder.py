import re
import threading
import time

import requests
from django.core.files.base import ContentFile
from lxml import etree
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By


def check_block(driver: webdriver.Chrome):
    if "Antibot Challenge Page" == driver.title:
        time.sleep(4)
    if "Доступ ограничен" == driver.title:
        elem = driver.find_element(By.TAG_NAME, "html").find_element(By.TAG_NAME, "body").find_element(By.TAG_NAME,
                                                                                                       "div").find_element(
            By.TAG_NAME, "div")
        elem = elem.find_element(By.TAG_NAME, "div").find_elements(By.TAG_NAME, "div")
        elem[2].find_element(By.TAG_NAME, "button").click()
        time.sleep(2)
        return driver.page_source
    return None


def get_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--enable-javascript")
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36")
    chrome_options.add_argument("--disable-software-rasterizer")  # Может надо заменить
    chrome_options.add_argument("--verbose")  # Логи

    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    service = Service('/usr/bin/chromedriver')
    current_driver = webdriver.Chrome(service=service, options=chrome_options)
    return current_driver


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


class SeleniumProcess(threading.Thread):
    QUEUE_COUNT = 1

    @staticmethod
    def get_driver():
        return get_driver()

    def find_price(self, url: str, driver: webdriver.Chrome):
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
                print(url)
                return
            else:
                price_container = price_container[0]
            if len(price_container) > 0:
                price_container = price_container.xpath(".//span[1]")[0]
        else:
            print("Can't parse page", driver.title)
            return None
        price = re.sub(r'\D', '', price_container.text)
        return price

    def run(self):
        pass

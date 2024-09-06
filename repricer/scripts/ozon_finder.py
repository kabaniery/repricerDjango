import argparse
import queue
import re
import threading
import time
from multiprocessing import Process

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from lxml import etree
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

import repricer.models


def check_block(driver: webdriver.Chrome):
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
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    # service = Service('/usr/bin/chromedriver') TODO: вернуть для релиза
    current_driver = webdriver.Chrome(options=chrome_options)
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
    scroll_script = """
    window.scrollBy(0, document.body.scrollHeight);
    """

    def __init__(self, client: repricer.models.Client, stop: bool):
        super().__init__()
        self._method = 0
        self._client = client
        self.result_data = queue.Queue()
        self._stop = stop

    def data_writer(self, q: queue.Queue, driver):
        trigger = True

        while trigger:
            if self._stop:
                return
            for i in range(100):
                if not q.empty():
                    link = q.get()
                    code = get_code(driver, link, delay=0.5)
                    htree = etree.HTML(code)
                    if htree is None:
                        # TODO: тут должен быть лог
                        with open(f"log/{driver.title}.html", "w", encoding="utf-8") as f:
                            f.write(driver.page_source)
                        continue
                    main_info = htree.xpath("/html/body/div[1]/div[1]/div[1]/div[4]")
                    if len(main_info) == 0:
                        # TODO: тут должен быть лог
                        with open(f"log/{driver.title}.html", "w", encoding="utf-8") as f:
                            f.write(driver.page_source)
                        continue
                    else:
                        main_info = main_info[0]
                    product_id = \
                        main_info.xpath("./div[2]/div[1]/div[1]/div[1]/div[2]/button[1]/div[1]")[0].text.split(" ")[1]
                    product_name = main_info.xpath("./div[3]/div[1]/div[1]/div[2]/div[1]/div[1]/h1[1]")[0].text
                    product_name = product_name.replace('\n', '').strip()
                    price = main_info.xpath(
                        "./div[3]/div[2]/div[1]/div[@data-widget='webSale']//span[1]")[0]
                    if len(price.xpath(".//span[1]")) > 0:
                        price = price.xpath(".//span[1]")[0].text
                    else:
                        price = price.text
                    price = int(re.sub(r'\D', '', price))
                    self.result_data.put(item=(product_id, product_name, price))
                    break
                if i == 99:
                    trigger = False
                time.sleep(0.1)
        driver.close()

    def money_parser(self, driver: webdriver.Chrome):
        try:
            driver.get(self._client.shop_address)
            htree = etree.HTML(get_code(driver, self._client.shop_address, delay=2, exec_script=self.scroll_script, exec_times=2))
            parent_layout = htree.xpath("/html/body/div[1]/div[1]/div[1]/div[@data-widget='shopInShopContainer']")[1]
            parent_layout = parent_layout.xpath(".//div[@data-widget='megaPaginator']")[0]
            queues = list()
            for i in range(SeleniumProcess.QUEUE_COUNT):
                queues.append(queue.Queue())

            encounter = 0
            pages = parent_layout.xpath("./div")[1]
            if pages.get("class") != "re3":
                htree = etree.HTML(get_code(driver, self._client.shop_address, delay=4, exec_script=self.scroll_script, exec_times=4))
                parent_layout = htree.xpath("/html/body/div[1]/div[1]/div[1]/div[@data-widget='shopInShopContainer']")[1]
                parent_layout = parent_layout.xpath(".//div[@data-widget='megaPaginator']")[0]
                pages = parent_layout.xpath("./div")[1]
                if pages.get("class") != "re3":
                    print("Error. Can't find pages")

            string = etree.tostring(pages, pretty_print=True, encoding='unicode') #TODO удалить
            pages = pages.xpath("./div[1]/div[1]/div[1]/a")
            if len(pages) == 0:
                pages = ["empty"]
            '''
        threads = list()
        for i in range(SeleniumProcess.QUEUE_COUNT):
            threads.append(threading.Thread(target=self.data_writer, args=(queues[i],)))

        for i in range(SeleniumProcess.QUEUE_COUNT):
            threads[i].start()
            '''
            index = 0
            for i in range(len(pages)):
                if i != 0:
                    htree = etree.HTML(get_code(driver, "https://www.ozon.ru" + pages[i].get("href"), delay=2, exec_script=self.scroll_script, exec_times=2))
                    parent_layout = htree.xpath(
                        "/html/body/div[1]/div[1]/div[1]/div[@data-widget='shopInShopContainer']/div[1]/div[1]/div["
                        "2]/div[3]")[
                        0]
                elements = parent_layout.xpath("./div[1]/div[1]/div[1]/div")
                j = 0
                for element in elements:
                    j += 1
                    link = element.xpath("./div[1]/a[1]")
                    if len(link) == 0:
                        # TODO: прописать лог
                        with open(f"{index}.html", "w", encoding="utf-8") as f:
                            f.write(etree.tostring(element, pretty_print=True, encoding="unicode"))
                            index += 1
                        continue
                    queues[0].put("https://www.ozon.ru" + link[0].get("href"))
                    encounter += 1
            # TODO: Сюда засунуть
            self._client.product_blocked = False
            self._client.save()
            self.data_writer(queues[0], driver)
            #driver.close() TODO: убрать в мультинитевой версии

        except Exception as e:
            print(e)
            self._client.product_blocked = False
            self._client.save()

    def run(self):
        if self._method == 0:
            self.money_parser(driver=get_driver())

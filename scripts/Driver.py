import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By


def get_options():
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
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--enable-javascript")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    return chrome_options


def get_driver():
    # service = Service('/usr/bin/chromedriver')
    current_driver = webdriver.Chrome(options=get_options())
    return current_driver


it = 0


def check_block(driver: webdriver.Chrome):
    if "Antibot Challenge Page" == driver.title:
        time.sleep(4)
    if "Доступ ограничен" == driver.title:
        try:
            elem = driver.find_element(By.TAG_NAME, "html").find_element(By.TAG_NAME, "body").find_element(By.TAG_NAME,
                                                                                                           "div").find_element(
                By.TAG_NAME, "div")
            elem.find_element(By.CLASS_NAME, "rb").click()
            time.sleep(2)
            return driver.page_source
        except Exception as e:
            print(e)
            global it
            it += 1
            with open(f"{it}.html", "w") as file:
                file.write(driver.page_source)
    return None


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

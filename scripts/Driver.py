from selenium import webdriver
from selenium.webdriver.chrome.service import Service


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

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

if __name__ == "__main__":
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")

    service = Service("/usr/bin/chromedriver")

    driver = webdriver.Chrome(options=options, service=service)
    driver.get("https://www.w3.org")
    print(driver.title)
    print(driver.page_source[0:50])

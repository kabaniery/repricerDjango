import time

import undetected_chromedriver as uc

drivers = [uc.Chrome(headless=False, browser_executable_path="C:/Program Files/Google/Chrome Beta/Application/chrome.exe", use_subprocess=False) for _ in range(5)]
for driver in drivers:
    driver.get("https://www.ozon.ru/product/mikroskop-levenhuk-320-base-monokulyarnyy-1241813359/")
    print(driver.title)
time.sleep(5)
with open("1.html", "w", encoding="utf-8") as f:
    f.write(drivers[0].page_source)
for driver in drivers:
    driver.close()

from pyvirtualdisplay import Display
from selenium import webdriver

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
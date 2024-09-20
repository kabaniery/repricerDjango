import time

from scripts.ShopInfo import get_driver

if __name__ == "__main__":
    driver = [get_driver() for _ in range(5)]
    time.sleep(20)

import os
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=chrome_options)

def scrape(url):
    driver = setup_driver()
    try:
        print(f"Testing URL: {url}")
        driver.get(url)
        time.sleep(10)
        
        all_imgs = driver.find_elements(By.TAG_NAME, "img")
        print(f"Found {len(all_imgs)} images on page.")
        for i, img in enumerate(all_imgs):
            src = img.get_attribute('src')
            cls = img.get_attribute('class')
            if src and 'vehicle' in src.lower() or 'car' in src.lower() or 'carscommerce' in src.lower():
                print(f"  Img: {src} | Class: {cls}")
                
    finally:
        driver.quit()

if __name__ == "__main__":
    test_url = "https://www.hollywoodkia.com/inventory/used-2020-bmw-3-series-m340i-rwd-4dr-car-wba5u7c06la232273/"
    scrape(test_url)


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
        time.sleep(5)
        
        # Swiper images
        imgs = driver.find_elements(By.CSS_SELECTOR, ".swiper-slide:not(.swiper-slide-duplicate) img")
        print(f"Found {len(imgs)} swiper images.")
        for i, img in enumerate(imgs[:5]):
            print(f"  Img {i+1}: {img.get_attribute('src')}")
            
        # DataLayer check
        dl = driver.execute_script("return window.dataLayer;")
        if dl:
            print("DataLayer found.")
            for obj in dl:
                if 'ecommerce' in obj:
                    print("Ecommerce data found in DataLayer.")
                    
    finally:
        driver.quit()

if __name__ == "__main__":
    test_url = "https://www.hollywoodkia.com/inventory/used-2020-bmw-3-series-m340i-rwd-4dr-car-wba5u7c06la232273/"
    scrape(test_url)

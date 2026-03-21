import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def main():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    try:
        url = "https://rickcasehonda.com/used-inventory/index.htm"
        print(f"Loading {url}")
        driver.get(url)
        time.sleep(5)  # Wait for page/react/vue to load
        
        items = driver.find_elements(By.CSS_SELECTOR, ".inventoryList > li.item, .srp-vehicle-item, .vehicle-card, .vehicle-item")
        print(f"Found {len(items)} items")
        
        for idx, item in enumerate(items[:2]):
            print(f"--- Item {idx} ---")
            print("Classes:", item.get_attribute('class'))
            
            try: title_el = item.find_element(By.CSS_SELECTOR, ".title, .vehicle-title, h2, h3")
            except: title_el = None
            if title_el:
                print("Title:", title_el.text.strip())
            
            try: link_el = item.find_element(By.CSS_SELECTOR, "a.vehicle-card-link, a.url, a.vehicle-title, a")
            except: link_el = None
            if link_el:
                print("Link:", link_el.get_attribute('href'))
            
            try: vin_el = item.find_element(By.CSS_SELECTOR, "[data-vin]")
            except: vin_el = None
            if vin_el:
                print("VIN attributes:", vin_el.get_attribute('data-vin'))
            
            try: img_el = item.find_element(By.CSS_SELECTOR, "img")
            except: img_el = None
            if img_el:
                print("Img SRC:", img_el.get_attribute('src') or img_el.get_attribute('data-src'))
    finally:
        driver.quit()

if __name__ == "__main__":
    main()

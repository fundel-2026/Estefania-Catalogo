import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def main():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    url = "https://rickcasehonda.com/used/Honda/2025-Honda-CR-V-096aa1f7ac1846b2c5d9aed6cceb069c.htm"
    driver.get(url)
    time.sleep(5)
    try:
        data = driver.execute_script("return DDC.dataLayer;")
        print("KEYS IN DATALAYER:", data.keys() if data else "No dataLayer")
        
        # Dealer.com has an array of objects in DDC.dataLayer or typical dataLayer
        for prop in ['digitalData', 'vehicle', '__PRELOADED_STATE__']:
            try:
                val = driver.execute_script(f"return window.{prop};")
                if val:
                    print(f"FOUND window.{prop}!")
            except: pass
    finally:
        driver.quit()

if __name__ == "__main__":
    main()

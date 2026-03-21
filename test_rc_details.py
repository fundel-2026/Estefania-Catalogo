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
        driver.get(url)
        time.sleep(5)  # Wait for page load
        
        items = driver.find_elements(By.CSS_SELECTOR, ".vehicle-card")
        if items:
            item = items[0]
            with open("test_rc_out.html", "w", encoding="utf-8") as f:
                f.write(item.get_attribute('outerHTML'))
    finally:
        driver.quit()

if __name__ == "__main__":
    main()

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def main():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    url = "https://rickcasehonda.com/used/Honda/2025-Honda-CR-V-096aa1f7ac1846b2c5d9aed6cceb069c.htm"
    driver.get(url)
    time.sleep(5)
    with open("vdp_out.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    driver.quit()

if __name__ == "__main__":
    main()

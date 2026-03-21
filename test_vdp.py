import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def scrape_vdp(driver, vdp_url):
    print(f"   -> Visitando VDP: {vdp_url}")
    data = {
        "trim": "",
        "transmission": "",
        "fuel": "",
        "exterior": "",
        "interior": "",
        "location": "",
        "description": "",
        "all_images": []
    }
    
    try:
        driver.get(vdp_url)
        time.sleep(5)
        
        # 1. Gallery Images
        # Most of these sites use Swiper
        img_elements = driver.find_elements(By.CSS_SELECTOR, ".swiper-slide:not(.swiper-slide-duplicate) img")
        if not img_elements:
            img_elements = driver.find_elements(By.CSS_SELECTOR, ".vdp-gallery img, .gallery-item img, .photos img, .gallery-slides img")
            
        img_urls = []
        for img in img_elements:
            src = img.get_attribute("src") or img.get_attribute("data-src") or img.get_attribute("data-lazy")
            if src and src not in img_urls and "placeholder" not in src.lower():
                img_urls.append(src)
        
        data["all_images"] = img_urls[:20]
        print(f"      Encontradas {len(img_urls)} imágenes.")

        # 2. Metadata (Key-Value pairs)
        items = driver.find_elements(By.CLASS_NAME, "vdp-details__sub-list-item")
        for item in items:
            try:
                label = item.find_element(By.CLASS_NAME, "vdp-details__sub-list-item--label").text.lower()
                value = item.find_element(By.CLASS_NAME, "vdp-details__sub-list-item--value").text.strip()
                if "trans" in label: data["transmission"] = value
                if "ext" in label: data["exterior"] = value
                if "int" in label: data["interior"] = value
                if "fuel" in label or "motor" in label: data["fuel"] = value
                if "trim" in label: data["trim"] = value
            except: pass
            
        # Dealer.com style details
        if not data["transmission"]:
            details = driver.find_elements(By.CSS_SELECTOR, ".vdp-details-basics li")
            for item in details:
                text = item.text
                if ":" in text:
                    label, value = text.split(":", 1)
                    label = label.lower()
                    if "transmission" in label: data["transmission"] = value.strip()
                    if "exterior" in label: data["exterior"] = value.strip()
                    if "interior" in label: data["interior"] = value.strip()
                    if "engine" in label or "fuel" in label: data["fuel"] = value.strip()

        # 3. Trim from Title
        try:
            title = driver.find_element(By.CSS_SELECTOR, "h1, .page-title").text
            if not data["trim"]:
                parts = title.split()
                if len(parts) > 3:
                    data["trim"] = " ".join(parts[3:])
        except: pass

        # 4. Description
        try:
            desc_el = driver.find_element(By.CSS_SELECTOR, "#vehicle-description .description, .vdp-description, [itemprop='description'], .vdp-comments")
            data["description"] = desc_el.text.strip()
        except: pass

        # 5. Location
        try:
            loc_el = driver.find_element(By.CSS_SELECTOR, ".footer-address, .dealer-address, .vdp-location")
            data["location"] = loc_el.text.strip()
        except:
            data["location"] = "Davie, FL"

    except Exception as e:
        print(f"      Error scrapeando VDP: {e}")
        
    for k,v in data.items():
        if k != "all_images":
            print(f"{k}: {v}")
    
    return data

def main():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    url = "https://rickcasehonda.com/used/Honda/2025-Honda-CR-V-096aa1f7ac1846b2c5d9aed6cceb069c.htm"
    # Provide a direct valid URL, but we will test it and see length.
    scrape_vdp(driver, url)
    driver.quit()

if __name__ == "__main__":
    main()

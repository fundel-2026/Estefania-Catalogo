
import os
import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURACIÓN ---
DATA_DIR = "data"
IMAGE_DIR = "images"
INPUT_FILE = os.path.join(DATA_DIR, "vehicles.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "vehicles.json")
JS_OUTPUT_FILE = os.path.join(DATA_DIR, "vehicles.js")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=chrome_options)

def download_image(url, folder, filename):
    if not url: return ""
    try:
        if url.startswith("//"): url = "https:" + url
        # Strip query params for better resolution if needed, but some CDNs need them.
        # For now, let's keep them unless we see issues.
        
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, filename)
            with open(path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            # Return relative path for web use
            return path.replace("\\", "/")
    except Exception as e:
        print(f"      Error descargando {url}: {e}")
    return ""

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
        time.sleep(3)
        
        # Try DDC dataLayer (Dealer.com sites like Rick Case Honda)
        try:
            ddc_vehicles = driver.execute_script("return DDC.dataLayer.vehicles;")
            if ddc_vehicles and len(ddc_vehicles) > 0:
                veh = ddc_vehicles[0]
                data["trim"] = veh.get("trim", "")
                data["transmission"] = veh.get("transmission", "")
                data["fuel"] = veh.get("fuelType", "") or veh.get("engine", "")
                data["exterior"] = veh.get("exteriorColor", "")
                data["interior"] = veh.get("interiorColor", "")
                
                if veh.get("images"):
                    for img in veh["images"]:
                        if img.get("uri"):
                            data["all_images"].append(img["uri"].replace("\\", ""))
        except: pass
        
        if not data["all_images"]:
            # 1. Gallery Images Fallback
            img_elements = driver.find_elements(By.CSS_SELECTOR, ".swiper-slide:not(.swiper-slide-duplicate) img")
            if not img_elements:
                img_elements = driver.find_elements(By.CSS_SELECTOR, ".vdp-gallery img, .gallery-item img")
                
            for img in img_elements:
                src = img.get_attribute("src") or img.get_attribute("data-src")
                if src and src not in data["all_images"] and "placeholder" not in src.lower():
                    data["all_images"].append(src)
            
        data["all_images"] = data["all_images"][:20] 

        if not data["transmission"]:
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
                
            # Toyota style
            if not data["transmission"]:
                summaries = driver.find_elements(By.CSS_SELECTOR, "li, div.detail-item")
                for item in summaries:
                    text = item.text
                    if ":" in text:
                        label, value = text.split(":", 1)
                        label = label.lower()
                        if "transmisión" in label: data["transmission"] = value.strip()
                        if "exterior" in label: data["exterior"] = value.strip()
                        if "interior" in label: data["interior"] = value.strip()
                        if "motor" in label or "combustible" in label: data["fuel"] = value.strip()

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
            desc_el = driver.find_element(By.CSS_SELECTOR, "#vehicle-description .description, .vdp-description, [itemprop='description']")
            data["description"] = desc_el.text.strip()
        except:
            try:
                sections = driver.find_elements(By.XPATH, "//*[contains(text(), 'Descripción') or contains(text(), 'Description')]/following-sibling::div")
                if sections:
                    data["description"] = sections[0].text.strip()
            except: pass

        # 5. Location
        try:
            loc_el = driver.find_element(By.CSS_SELECTOR, ".footer-address, .dealer-address")
            data["location"] = loc_el.text.strip()
        except:
            if "braman" in vdp_url: data["location"] = "Miami, FL"
            elif "toyotaofhollywood" in vdp_url: data["location"] = "Hollywood, FL"
            elif "rickcasehonda" in vdp_url: data["location"] = "Davie, FL"

    except Exception as e:
        print(f"      Error scrapeando VDP: {e}")
        
    return data

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} no existe.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        vehicles = json.load(f)

    print(f"Procesando {len(vehicles)} vehículos...")
    driver = setup_driver()
    
    try:
        for i, v in enumerate(vehicles):
            print(f"[{i+1}/{len(vehicles)}] {v.get('display_name', 'Vehicle')}")
            
            # Use VIN as unique folder
            vin = v.get("vin", f"no_vin_{i}")
            vdp_url = v.get("vdp_url")
            
            if not vdp_url:
                print("   ! No hay VDP URL, saltando.")
                continue
                
            # Scrape deep data
            details = scrape_vdp(driver, vdp_url)
            
            # Update fields
            v["trim"] = details["trim"] or v.get("trim", "")
            v["transmission"] = details["transmission"] or v.get("transmission", "")
            v["fuel"] = details["fuel"] or v.get("engine", "")
            v["exterior"] = details["exterior"] or v.get("ext_color", "")
            v["interior"] = details["interior"] or v.get("int_color", "")
            v["location"] = details["location"] or "Miami, FL"
            v["description"] = details["description"]
            
            # Download images (10-15)
            vin_safe = "".join([c for c in vin if c.isalnum()])
            car_img_dir = os.path.join(IMAGE_DIR, vin_safe)
            
            img_list = []
            for idx, img_url in enumerate(details["all_images"][:15]):
                filename = f"image_{idx+1}.jpg"
                local_path = download_image(img_url, car_img_dir, filename)
                if local_path:
                    img_list.append(local_path)
            
            v["images"] = img_list
            # Keep original local_image for backward compatibility
            if img_list:
                v["local_image"] = img_list[0].replace("/", "\\")
            
            # Save periodically to avoid losing data
            if (i+1) % 5 == 0:
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(vehicles, f, indent=4, ensure_ascii=False)

    finally:
        driver.quit()

    # Final Save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(vehicles, f, indent=4, ensure_ascii=False)
    
    # Update JS
    with open(JS_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"const vehicleData = {json.dumps(vehicles, indent=4, ensure_ascii=False)};")
        
    print("\n¡PROCESO COMPLETADO!")

if __name__ == "__main__":
    main()

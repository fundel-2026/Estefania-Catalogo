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
OUTPUT_FILE = os.path.join(DATA_DIR, "vehicles.json")
JS_OUTPUT_FILE = os.path.join(DATA_DIR, "vehicles.js")

URL_RICKCASE = "https://rickcasehonda.com/used-inventory/index.htm"

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

def download_image(url, filename):
    if not url: return ""
    try:
        if url.startswith("//"):
            url = "https:" + url
            
        # Optional: remove resize parameters for better quality
        if "?" in url:
            url = url.split("?")[0]
            
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            path = os.path.join(IMAGE_DIR, filename)
            with open(path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return f"images/{filename}".replace("/", "\\")
    except Exception as e:
        print(f"Error descargando imagen {url}: {e}")
    return ""

def load_existing_data():
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error cargando datos existentes: {e}")
            return []
    return []

def save_data(data):
    for v in data:
        if v.get("local_image"):
            v["local_image"] = v["local_image"].replace("/", "\\")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    with open(JS_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"const vehicleData = {json.dumps(data, indent=4, ensure_ascii=False)};")
    print(f"Datos guardados en {OUTPUT_FILE} y {JS_OUTPUT_FILE}")

def scrape_rickcase(driver, url, existing_vins):
    print(f"\n--- Scrapeando Rick Case Honda: {url} ---")
    try:
        driver.get(url)
        time.sleep(5)
        
        items = driver.find_elements(By.CSS_SELECTOR, ".vehicle-card")
        print(f"Encontrados {len(items)} vehículos.")
        
        newly_found = []
        for item in items:
            try:
                # VIN
                vin = ""
                try: vin = item.find_element(By.CSS_SELECTOR, "[data-tf-vin]").get_attribute("data-tf-vin")
                except:
                    try: vin = item.find_element(By.CSS_SELECTOR, "[data-vin]").get_attribute("data-vin")
                    except: pass
                
                if not vin or vin in existing_vins:
                    continue
                
                # TITULO
                title = ""
                try: title = item.find_element(By.CSS_SELECTOR, ".vehicle-card-title, h2, h3").text.strip()
                except: pass
                
                parts = title.split()
                year = parts[0] if len(parts) > 0 and parts[0].isdigit() else ""
                make = parts[1] if len(parts) > 1 else ""
                model = parts[2] if len(parts) > 2 else ""

                # PRECIO
                price = ""
                try: price = item.find_element(By.CSS_SELECTOR, ".final-price .price-value").text.replace("$", "").replace(",", "").strip()
                except: pass
                
                # MILES
                mileage = ""
                try: mileage = item.find_element(By.CSS_SELECTOR, ".highlight-badge").text.lower().replace("miles", "").replace(",", "").strip()
                except: pass

                # VDP URL
                vdp_url = ""
                try:
                    link_el = item.find_element(By.CSS_SELECTOR, "a")
                    vdp_url = link_el.get_attribute("href")
                except: pass
                
                # IMAGEN
                img_url = ""
                try:
                    img_el = item.find_element(By.CSS_SELECTOR, "img")
                    img_url = img_el.get_attribute("src") or img_el.get_attribute("data-src")
                except: pass
                
                # DETALLES EXTRA
                engine = ""
                try: engine = item.find_element(By.CSS_SELECTOR, ".engine").text.replace("Engine:", "").strip()
                except: pass
                
                transmission = ""
                try: transmission = item.find_element(By.CSS_SELECTOR, ".transmission").text.replace("Transmission:", "").strip()
                except: pass
                
                ext_color = ""
                try: ext_color = item.find_element(By.CSS_SELECTOR, ".exteriorColor").text.replace("Exterior", "").strip()
                except: pass

                v = {
                    "vin": vin,
                    "year": year,
                    "make": make,
                    "model": model,
                    "price": price,
                    "mileage": mileage,
                    "ext_color": ext_color,
                    "int_color": "",
                    "body_style": "SUV" if "SUV" in title else ("Sedan" if "Sedan" in title else ""),
                    "transmission": transmission,
                    "engine": engine,
                    "vdp_url": vdp_url,
                    "display_name": title.upper(),
                    "image_url": img_url,
                    "local_image": ""
                }
                
                if img_url:
                    v["local_image"] = download_image(img_url, f"{vin}.jpg")
                
                newly_found.append(v)
                existing_vins.add(vin)
                print(f"  [OK] Guardado: {v['display_name']}")
            except Exception as e:
                print(f"Error procesando item: {e}")
                continue
        return newly_found
    except Exception as e:
        print(f"Error en página {url}: {e}")
        return []

def main():
    print("Iniciando proceso de extracción de datos para Rick Case Honda...")
    existing_data = load_existing_data()
    existing_vins = {v['vin'] for v in existing_data if v.get('vin')}
    print(f"Cargados {len(existing_data)} vehículos existentes.")
    
    driver = setup_driver()
    new_vehicles = scrape_rickcase(driver, URL_RICKCASE, existing_vins)
    driver.quit()
    
    if new_vehicles:
        combined_data = existing_data + new_vehicles
        save_data(combined_data)
        print(f"\nPROCESO COMPLETADO.")
        print(f"Se han añadido {len(new_vehicles)} nuevos vehículos.")
    else:
        print("\nNo se encontraron nuevos vehículos que no estuvieran ya en la base de datos.")

if __name__ == "__main__":
    main()

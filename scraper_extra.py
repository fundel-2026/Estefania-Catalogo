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

URLS_BRAMAN = [
    "https://www.bramanhonda.com/used-vehicles/",
    "https://www.bramanhonda.com/used-vehicles/?_p=1&_dFR%5Btype%5D%5B0%5D=Used&_dFR%5Btype%5D%5B1%5D=Certified%2520Used",
    "https://www.bramanhonda.com/used-vehicles/?_p=2&_dFR%5Btype%5D%5B0%5D=Used&_dFR%5Btype%5D%5B1%5D=Certified%2520Used",
    "https://www.bramanhonda.com/used-vehicles/?_p=3&_dFR%5Btype%5D%5B0%5D=Used&_dFR%5Btype%5D%5B1%5D=Certified%2520Used"
]

URL_KIA = "https://www.hollywoodkia.com/inventory/new-2025-kia-ev6-gt-line-rwd-sport-utility-5xyc44ja0sg003168/"

# Crear directorios si no existen
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
        # Algunos URLs pueden empezar con //
        if url.startswith("//"):
            url = "https:" + url
            
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            path = os.path.join(IMAGE_DIR, filename)
            with open(path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return f"images/{filename}"
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
    # Asegurar que local_image use backslashes si es necesario para Windows (como en el original)
    for v in data:
        if v.get("local_image"):
            v["local_image"] = v["local_image"].replace("/", "\\")

    # Guardar JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    # Guardar JS
    with open(JS_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"const vehicleData = {json.dumps(data, indent=4, ensure_ascii=False)};")
    print(f"Datos guardados en {OUTPUT_FILE} y {JS_OUTPUT_FILE}")

def scrape_braman(driver, url, existing_vins):
    print(f"\n--- Scrapeando Braman Honda: {url} ---")
    try:
        driver.get(url)
        time.sleep(5) # Esperar carga dinámica de Algolia
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "ais-Hits-item")))
        items = driver.find_elements(By.CLASS_NAME, "ais-Hits-item")
        print(f"Encontrados {len(items)} vehículos.")
        
        newly_found = []
        for item in items:
            try:
                # Intentar obtener via data-attribute (DealerInspire standard)
                data_vehicle_str = item.get_attribute("data-vehicle")
                if not data_vehicle_str:
                    continue
                    
                dv = json.loads(data_vehicle_str)
                vin = dv.get("vin")
                
                if not vin or vin in existing_vins:
                    continue
                
                # Imagen
                img_url = ""
                try:
                    img_el = item.find_element(By.CSS_SELECTOR, "img.hit-image, img.srp-click-image")
                    img_url = img_el.get_attribute("src")
                except:
                    pass
                
                # URL de detalle
                vdp_url = ""
                try:
                    vdp_url = item.find_element(By.CSS_SELECTOR, "a.hit-link, a.car-title-link").get_attribute("href")
                except:
                    pass

                v = {
                    "vin": vin,
                    "year": str(dv.get("year", "")),
                    "make": dv.get("make", ""),
                    "model": dv.get("model", ""),
                    "price": str(dv.get("price", "")),
                    "mileage": str(dv.get("mileage", "")),
                    "ext_color": dv.get("exterior_color", ""),
                    "int_color": dv.get("interior_color", ""),
                    "body_style": dv.get("type", ""),
                    "transmission": dv.get("transmission", ""),
                    "engine": dv.get("engine", ""),
                    "vdp_url": vdp_url,
                    "display_name": f"{dv.get('type', '').upper()} {dv.get('year', '')} {dv.get('make', '')} {dv.get('model', '')}".upper(),
                    "image_url": img_url,
                    "local_image": ""
                }
                
                if img_url:
                    v["local_image"] = download_image(img_url, f"{vin}.jpg")
                
                newly_found.append(v)
                existing_vins.add(vin)
                print(f"  [√] Guardado: {v['display_name']}")
            except Exception as e:
                print(f"Error procesando item: {e}")
                continue
        return newly_found
    except Exception as e:
        print(f"Error en página {url}: {e}")
        return []

def scrape_kia(driver, url, existing_vins):
    print(f"\n--- Scrapeando Hollywood Kia: {url} ---")
    try:
        driver.get(url)
        time.sleep(5)
        
        # Intentar extraer VIN de la URL o del DOM
        vin = ""
        try:
            vin_el = driver.find_element(By.CSS_SELECTOR, ".vdp-basics__vin, [data-vin]")
            vin = vin_el.text.replace("VIN:", "").strip()
            if not vin:
                vin = vin_el.get_attribute("data-vin")
        except:
            # Fallback a URL
            vin = url.split("-")[-1].strip("/")
            
        if not vin or vin in existing_vins:
            print(f"Vehículo Kia ya existe o VIN no encontrado ({vin}).")
            return []

        # Título
        title = ""
        try:
            title = driver.find_element(By.CSS_SELECTOR, ".vehicle-title__h1").text.strip()
        except:
            title = "2025 KIA EV6 GT-LINE"

        # Precio
        price = ""
        try:
            price_el = driver.find_element(By.CSS_SELECTOR, ".pricing-module__price")
            price = price_el.text.replace("$", "").replace(",", "").strip()
        except:
            pass

        # Imagen
        img_url = ""
        try:
            img_el = driver.find_element(By.CSS_SELECTOR, ".vdp-gallery__swiper-wrapper .swiper-slide-active img, .vdp-gallery img")
            img_url = img_el.get_attribute("src")
        except:
            pass

        v = {
            "vin": vin,
            "year": "2025",
            "make": "Kia",
            "model": "EV6",
            "price": price,
            "mileage": "0",
            "ext_color": "Runway Red",
            "int_color": "GT-Line SynTex Suede",
            "body_style": "SUV",
            "transmission": "1-Speed Automatic",
            "engine": "Electric",
            "vdp_url": url,
            "display_name": f"NUEVO {title}".upper(),
            "image_url": img_url,
            "local_image": ""
        }
        
        if img_url:
            v["local_image"] = download_image(img_url, f"{vin}.jpg")
            
        print(f"  [√] Guardado Kia: {v['display_name']}")
        existing_vins.add(vin)
        return [v]
        
    except Exception as e:
        print(f"Error scrapeando Kia: {e}")
        return []

def main():
    print("Iniciando proceso de extracción de datos adicionales...")
    existing_data = load_existing_data()
    existing_vins = {v['vin'] for v in existing_data if v.get('vin')}
    print(f"Cargados {len(existing_data)} vehículos existentes.")
    
    driver = setup_driver()
    new_vehicles_total = []
    
    # Braman Honda
    for url in URLS_BRAMAN:
        new_vehicles_total.extend(scrape_braman(driver, url, existing_vins))
        
    # Hollywood Kia
    new_vehicles_total.extend(scrape_kia(driver, URL_KIA, existing_vins))
    
    driver.quit()
    
    if new_vehicles_total:
        combined_data = existing_data + new_vehicles_total
        save_data(combined_data)
        print(f"\nPROCESO COMPLETADO.")
        print(f"Se han añadido {len(new_vehicles_total)} nuevos vehículos.")
    else:
        print("\nNo se encontraron nuevos vehículos que no estuvieran ya en la base de datos.")

if __name__ == "__main__":
    main()

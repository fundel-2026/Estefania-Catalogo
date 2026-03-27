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

# URLs proporcionadas por el usuario
URLS = [
    "https://www.toyotaofhollywood.com/used-vehicles/?pg=2",
    "https://www.toyotaofhollywood.com/used-vehicles/?pg=3",
    "https://www.toyotaofhollywood.com/used-vehicles/?pg=4",
    "https://www.toyotaofhollywood.com/used-vehicles/?pg=5"
]

# Crear directorios si no existen
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # Agente de usuario para evitar bloqueos
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    
    return webdriver.Chrome(options=chrome_options)

def download_image(url, vin):
    if not url: return ""
    try:
        if url.startswith("//"):
            url = "https:" + url
        
        # Eliminar parámetros de resize si existen para mejor resolución
        clean_url = url.split("?")[0]
        
        # Carpeta específica para el vehículo
        vehicle_img_dir = os.path.join(IMAGE_DIR, vin)
        os.makedirs(vehicle_img_dir, exist_ok=True)
        
        filename = "image_1.jpg"
        path = os.path.join(vehicle_img_dir, filename)
        
        response = requests.get(clean_url, stream=True, timeout=10)
        if response.status_code == 200:
            with open(path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            # Retornamos en formato compatible con el JS (backslash para windows si es necesario, 
            # pero el scraper original usa forward slash o backslash dependiendo del SO)
            # En la data actual parece que usan: "images\\4T1DAACK3SU555467\\image_1.jpg"
            return f"images\\{vin}\\{filename}"
    except Exception as e:
        print(f"Error descargando imagen {url}: {e}")
    return ""

def load_existing():
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def scrape_batch():
    driver = setup_driver()
    existing_data = load_existing()
    # Usar dict para fácil merge por VIN
    all_vehicles = {v['vin']: v for v in existing_data if v.get('vin')}
    
    print(f"Iniciando extracción de {len(URLS)} páginas...", flush=True)
    print(f"Vehículos actuales: {len(all_vehicles)}", flush=True)

    try:
        for url in URLS:
            print(f"\n--- Scrapeando: {url} ---", flush=True)
            driver.get(url)
            
            # Esperar a que carguen los vehículos (Algolia items)
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "ais-Hits-item"))
                )
            except:
                print(f"Tiempo de espera agotado o no hay vehículos en {url}", flush=True)
                continue
            
            items = driver.find_elements(By.CLASS_NAME, "ais-Hits-item")
            print(f"Encontrados {len(items)} vehículos.", flush=True)
            
            for item in items:
                try:
                    # El elemento .listing contiene los data attributes
                    listing = item.find_element(By.CSS_SELECTOR, "div.listing")
                    vin = listing.get_attribute("data-vehicle-vin")
                    
                    if not vin:
                        continue
                        
                    # Título
                    title_el = item.find_element(By.CSS_SELECTOR, "h2.car-title")
                    display_name = title_el.text.upper()
                    
                    # URL de detalles
                    vdp_url = ""
                    try:
                        vdp_link = title_el.find_element(By.XPATH, "..")
                        vdp_url = vdp_link.get_attribute("href")
                    except: pass

                    # Imagen
                    img_url = ""
                    try:
                        img_el = item.find_element(By.CSS_SELECTOR, "img.srp-click-image")
                        img_url = img_el.get_attribute("src")
                    except: pass

                    vehicle = {
                        "vin": vin,
                        "year": listing.get_attribute("data-vehicle-year"),
                        "make": listing.get_attribute("data-ag-make"),
                        "model": listing.get_attribute("data-ag-model"),
                        "price": listing.get_attribute("data-ag-price"),
                        "mileage": listing.get_attribute("data-vehicle-mileage"),
                        "ext_color": listing.get_attribute("data-ag-ext-color"),
                        "int_color": listing.get_attribute("data-ag-int-color"),
                        "body_style": (listing.get_attribute("data-ag-type") or "Used").capitalize(),
                        "transmission": listing.get_attribute("data-ag-transmission"),
                        "engine": listing.get_attribute("data-ag-engine"),
                        "vdp_url": vdp_url,
                        "display_name": display_name,
                        "image_url": img_url,
                        "local_image": "",
                        "trim": "",
                        "fuel": None,
                        "exterior": ""
                    }
                    
                    # Si el vehículo ya existe, solo descargamos imagen si le falta
                    if vin in all_vehicles:
                        if not all_vehicles[vin].get("local_image"):
                             all_vehicles[vin]["local_image"] = download_image(img_url, vin)
                             print(f"  [-] Actualizada imagen para: {display_name}", flush=True)
                        else:
                             print(f"  [-] Ya existe: {display_name}", flush=True)
                    else:
                        vehicle["local_image"] = download_image(img_url, vin)
                        all_vehicles[vin] = vehicle
                        print(f"  [+] Nuevo: {display_name}", flush=True)
                        
                except Exception as e:
                    print(f"Error procesando un vehículo: {e}", flush=True)
                    continue
            
            # Pequeña pausa entre páginas
            time.sleep(2)
            
    finally:
        driver.quit()
        
    # Guardar resultados
    final_list = list(all_vehicles.values())
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_list, f, indent=4, ensure_ascii=False)
    
    with open(JS_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"const vehicleData = {json.dumps(final_list, indent=4, ensure_ascii=False)};")
        
    print(f"\nPROCESO COMPLETADO.", flush=True)
    print(f"Total de vehículos en base de datos: {len(final_list)}", flush=True)
    print(f"Datos guardados en: {OUTPUT_FILE} y {JS_OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    scrape_batch()

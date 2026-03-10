import os
import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURACIÓN ---
BASE_URL = "https://www.toyotaofhollywood.com/used-vehicles/"
DATA_DIR = "data"
IMAGE_DIR = "images"
OUTPUT_FILE = os.path.join(DATA_DIR, "vehicles.json")
MAX_PAGES = 3  # Cambia a None para extraer todo el inventario

# Crear directorios si no existen
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Ejecutar en segundo plano
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # Agente de usuario para evitar bloqueos básicos
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    
    return webdriver.Chrome(options=chrome_options)

def download_image(url, filename):
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            path = os.path.join(IMAGE_DIR, filename)
            with open(path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return path
    except Exception as e:
        print(f"Error descargando imagen {url}: {e}")
    return None

def scrape_vehicles():
    driver = setup_driver()
    vehicles_data = []
    page = 1
    
    try:
        print(f"Conectando a {BASE_URL}...")
        driver.get(BASE_URL)
        
        while True:
            print(f"--- Extrayendo Página {page} ---")
            
            # Esperar a que los elementos de Algolia se carguen
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "ais-Hits-item"))
                )
            except:
                print("No se encontraron más vehículos o la página tardó mucho en cargar.")
                break
            
            # Obtener todos los items
            items = driver.find_elements(By.CLASS_NAME, "ais-Hits-item")
            print(f"Encontrados {len(items)} vehículos en esta página.")
            
            for item in items:
                try:
                    # Usar los data-attributes del elemento .listing que son más fiables
                    listing = item.find_element(By.CSS_SELECTOR, "div.listing")
                    
                    vehicle = {
                        "vin": listing.get_attribute("data-vehicle-vin"),
                        "year": listing.get_attribute("data-vehicle-year"),
                        "make": listing.get_attribute("data-ag-make"),
                        "model": listing.get_attribute("data-ag-model"),
                        "price": listing.get_attribute("data-ag-price"),
                        "mileage": listing.get_attribute("data-vehicle-mileage"),
                        "ext_color": listing.get_attribute("data-ag-ext-color"),
                        "int_color": listing.get_attribute("data-ag-int-color"),
                        "body_style": listing.get_attribute("data-ag-type"),
                        "transmission": listing.get_attribute("data-ag-transmission"),
                        "engine": listing.get_attribute("data-ag-engine"),
                        "vdp_url": item.find_element(By.CSS_SELECTOR, "h2.car-title").find_element(By.XPATH, "..").get_attribute("href")
                    }
                    
                    # Nombre completo para mostrar
                    title_text = item.find_element(By.CSS_SELECTOR, "h2.car-title").text
                    vehicle["display_name"] = title_text if title_text else f"{vehicle['year']} {vehicle['make']} {vehicle['model']}"
                    
                    # Imagen
                    img_element = item.find_element(By.CSS_SELECTOR, "img.srp-click-image")
                    img_url = img_element.get_attribute("src")
                    
                    # Descargar imagen localmente
                    img_name = f"{vehicle['vin']}.jpg" if vehicle['vin'] else f"img_{len(vehicles_data)}.jpg"
                    local_img_path = download_image(img_url, img_name)
                    
                    vehicle["image_url"] = img_url
                    vehicle["local_image"] = local_img_path if local_img_path else ""
                    
                    vehicles_data.append(vehicle)
                    print(f"  [√] Guardado: {vehicle['display_name']}")
                    
                except Exception as e:
                    print(f"Error procesando un vehículo: {e}")
                    continue
            
            # Paginación
            if MAX_PAGES and page >= MAX_PAGES:
                print("Límite de páginas alcanzado.")
                break
                
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, ".ais-Pagination-item--nextPage a")
                if "disabled" in next_button.get_attribute("class"):
                    print("Última página alcanzada.")
                    break
                
                # Scroll al botón y click
                driver.execute_script("arguments[0].scrollIntoView();", next_button)
                time.sleep(1)
                next_button.click()
                page += 1
                time.sleep(3) # Esperar al renderizado de la siguiente página
            except:
                print("No se encontró botón de 'Siguiente' o error al navegar.")
                break
                
    finally:
        driver.quit()
        
    # Guardar resultados en JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(vehicles_data, f, indent=4, ensure_ascii=False)
    
    # NUEVO: Guardar también en un archivo .js para evitar problemas de CORS/Seguridad en el navegador
    js_output_file = os.path.join(DATA_DIR, "vehicles.js")
    with open(js_output_file, 'w', encoding='utf-8') as f:
        f.write(f"const vehicleData = {json.dumps(vehicles_data, indent=4, ensure_ascii=False)};")
        
    print(f"\nPROCESO COMPLETADO.")
    print(f"Total de vehículos extraídos: {len(vehicles_data)}")
    print(f"Datos guardados en: {OUTPUT_FILE} y {js_output_file}")

if __name__ == "__main__":
    scrape_vehicles()

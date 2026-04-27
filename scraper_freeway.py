
import os
import json
import time
import requests
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN ---
DATA_DIR = "data"
IMAGE_DIR = "images"
OUTPUT_FILE = os.path.join(DATA_DIR, "vehicles.json")
JS_OUTPUT_FILE = os.path.join(DATA_DIR, "vehicles.js")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

def download_image(url, folder, filename):
    if not url: return ""
    try:
        if url.startswith("//"): url = "https:" + url
        response = requests.get(url, stream=True, timeout=15, headers=HEADERS)
        if response.status_code == 200:
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, filename)
            with open(path, 'wb') as f:
                for chunk in response.iter_content(2048):
                    f.write(chunk)
            return path.replace("\\", "/")
    except Exception as e:
        print(f"      Error descargando {url}: {e}")
    return ""

def scrape_vdp(vdp_url):
    print(f"   -> Scraping VDP: {vdp_url}")
    details = {
        "vin": "",
        "ext_color": "",
        "int_color": "",
        "images": [],
        "description": ""
    }
    try:
        response = requests.get(vdp_url, headers=HEADERS, timeout=20)
        if response.status_code != 200:
            return details
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Try technical data list (Structure B)
        data_items = soup.select(".data-list-item")
        for item in data_items:
            text = item.text.strip()
            if "VIN:" in text:
                details["vin"] = text.replace("VIN:", "").strip()
            elif "Exterior Color:" in text:
                details["ext_color"] = text.replace("Exterior Color:", "").strip()
            elif "Interior Color:" in text:
                details["int_color"] = text.replace("Interior Color:", "").strip()

        # 2. Try Table (Structure A) as fallback
        if not details["vin"]:
            vin_el = soup.select_one(".t-value.t-vin")
            if vin_el: details["vin"] = vin_el.text.strip()
        
        if not details["ext_color"] or not details["int_color"]:
            rows = soup.select(".single-car-data tr")
            for row in rows:
                label = row.select_one(".t-label")
                value = row.select_one(".t-value")
                if label and value:
                    l_text = label.text.strip().lower()
                    if "exterior" in l_text: details["ext_color"] = value.text.strip()
                    elif "interior" in l_text: details["int_color"] = value.text.strip()

        # 3. Images
        # Based on subagent and manual check: .stm-single-image img or .swiper-slide img
        img_els = soup.select(".stm-single-image img, .swiper-slide img")
        for img in img_els:
            src = img.get("src") or img.get("data-src") or img.get("srcset")
            if src:
                if "," in src: src = src.split(",")[0].split(" ")[0]
                if src.startswith("//"): src = "https:" + src
                if "placeholder" not in src.lower() and "logo" not in src.lower():
                    details["images"].append(src.split("?")[0])
        
        # Deduplicate images while preserving order
        seen = set()
        details["images"] = [x for x in details["images"] if not (x in seen or seen.add(x))]

        # Description
        desc_el = soup.select_one(".stm-car-listing-data .content, .stm-vehicle-description")
        if desc_el:
            details["description"] = desc_el.text.strip()
            
    except Exception as e:
        print(f"      Error en scrape_vdp: {e}")
    
    return details

def main():
    print("Iniciando scraper de FreewayFLA (Cargo Vans)...")
    
    # Load existing vehicles
    all_vehicles = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                all_vehicles = json.load(f)
        except: pass
    
    existing_vins = {v.get("vin") for v in all_vehicles if v.get("vin")}
    print(f"Cargados {len(all_vehicles)} vehículos existentes.")

    new_vehicles_count = 0
    
    # Iterate pages (1 to 4 based on subagent info)
    for page in range(1, 5):
        url = f"https://freewayfla.com/inventory/page/{page}/?body=cargo"
        print(f"\nProcesando página {page}: {url}")
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
            if response.status_code != 200:
                print(f"   ! Error {response.status_code} al acceder a la página. Saltando.")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            containers = soup.select(".listing-list-loop.stm-listing-directory-list-loop")
            
            if not containers:
                print("   ! No se encontraron vehículos en esta página.")
                break
                
            for container in containers:
                # Extract basic info
                title_el = container.select_one(".title.heading-font a")
                if not title_el: continue
                
                vdp_url = title_el.get("href")
                full_title = title_el.text.strip() # e.g. "RAM ProMaster Cargo Van 2023"
                
                price_el = container.select_one(".sale-price .heading-font") or container.select_one(".regular-price")
                price = ""
                if price_el:
                    price = "".join(filter(str.isdigit, price_el.text))
                
                mileage_el = container.select_one(".mileage .value")
                mileage = mileage_el.text.strip() if mileage_el else ""
                
                year_el = container.select_one(".ca-year .value")
                year = year_el.text.strip() if year_el else ""
                
                # Split title to get Make/Model if possible
                # Title is usually "MAKE MODEL YEAR" or "YEAR MAKE MODEL"
                # Looking at "RAM ProMaster Cargo Van 2023"
                parts = full_title.split()
                # Default values
                make = parts[0] if parts else ""
                model = " ".join(parts[1:]) if len(parts) > 1 else ""
                # Clean year from model if present at the end
                if year and model.endswith(year):
                    model = model[:-len(year)].strip()

                # Scrape detail page
                vdp_details = scrape_vdp(vdp_url)
                vin = vdp_details["vin"]
                
                if not vin:
                    # Fallback VIN from URL if possible
                    # URL usually ends with something like ...cargo-van-3500-.../
                    print(f"   ! No se encontró VIN para {full_title}, saltando.")
                    continue
                
                if vin in existing_vins:
                    print(f"   - {vin} ya existe en el catálogo. Saltando.")
                    continue
                
                # Create vehicle object
                v_type = "USADO"
                vehicle = {
                    "vin": vin,
                    "year": year,
                    "make": make,
                    "model": model,
                    "price": price,
                    "mileage": mileage,
                    "ext_color": vdp_details["ext_color"],
                    "int_color": vdp_details["int_color"],
                    "body_style": "Cargo Van",
                    "transmission": "", # Will fill if possible
                    "engine": "",
                    "vdp_url": vdp_url,
                    "display_name": f"{v_type} {year} {make} {model}".upper(),
                    "image_url": vdp_details["images"][0] if vdp_details["images"] else "",
                    "local_image": "",
                    "trim": "",
                    "fuel": "",
                    "exterior": vdp_details["ext_color"],
                    "interior": vdp_details["int_color"],
                    "location": "Miami, FL", # FreewayFLA locations
                    "description": vdp_details["description"],
                    "images": []
                }
                
                # Download images
                vin_safe = "".join([c for c in vin if c.isalnum()])
                car_img_dir = os.path.join(IMAGE_DIR, vin_safe)
                
                local_images = []
                for idx, img_url in enumerate(vdp_details["images"][:1]): # Limit to 1 image as requested
                    filename = f"image_{idx+1}.jpg"
                    local_path = download_image(img_url, car_img_dir, filename)
                    if local_path:
                        local_images.append(local_path)
                
                if local_images:
                    vehicle["images"] = local_images
                    vehicle["local_image"] = local_images[0].replace("/", "\\")
                
                all_vehicles.append(vehicle)
                existing_vins.add(vin)
                new_vehicles_count += 1
                print(f"   [+] Nuevo añadido: {vehicle['display_name']} ({vin})")

                # Save incremental
                if new_vehicles_count % 5 == 0:
                    save_data(all_vehicles)

        except Exception as e:
            print(f"   ! Error procesando página {page}: {e}")

    # Final save
    save_data(all_vehicles)
    print(f"\nPROCESO COMPLETADO. Se añadieron {new_vehicles_count} nuevos vehículos.")

def save_data(data):
    # Ensure local_image uses backslashes for this specific project convention
    for v in data:
        if v.get("local_image"):
            v["local_image"] = v["local_image"].replace("/", "\\")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    with open(JS_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"const vehicleData = {json.dumps(data, indent=4, ensure_ascii=False)};")

if __name__ == "__main__":
    main()

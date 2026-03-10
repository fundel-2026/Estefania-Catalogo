import os
import json
import requests
import sys
import time

# Forzar salida en UTF-8 para evitar errores de charmap en Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- CONFIGURACIÓN ---
DATA_DIR = "data"
IMAGE_DIR = "images"
OUTPUT_FILE = os.path.join(DATA_DIR, "vehicles.json")
JS_OUTPUT_FILE = os.path.join(DATA_DIR, "vehicles.js")

# Credenciales Algolia extraídas mediantes inspección técnica
BRAMAN_CONFIG = {
    "app_id": "V3ZOVI2QFZ",
    "api_key": "ec7553dd56e6d4c8bb447a0240e7aab3",
    "index": "bramanhondamiami_production_inventory"
}

KIA_CONFIG = {
    "app_id": "2591J46P8G",
    "api_key": "78311e75e16dd6273d6b00cd6c21db3c",
    "index": "hollywoodkia1_production_inventory"
}

# Crear directorios si no existen
os.makedirs(IMAGE_DIR, exist_ok=True)

def download_image(url, filename):
    if not url: return ""
    try:
        # Algunos URLs pueden tener parámetros de resize/crop que fallan en descarga directa
        url = url.split("?")[0]
        if url.startswith("//"):
            url = "https:" + url
            
        max_retries = 3
        for i in range(max_retries):
            try:
                response = requests.get(url, stream=True, timeout=15)
                if response.status_code == 200:
                    path = os.path.join(IMAGE_DIR, filename)
                    with open(path, 'wb') as f:
                        for chunk in response.iter_content(2048):
                            f.write(chunk)
                    return f"images/{filename}"
                time.sleep(1)
            except:
                time.sleep(2)
                continue
    except Exception as e:
        print(f"Error descargando imagen {url}: {e}")
    return ""

def query_algolia(config, params=""):
    url = f"https://{config['app_id']}-dsn.algolia.net/1/indexes/{config['index']}/query"
    headers = {
        "X-Algolia-Application-Id": config['app_id'],
        "X-Algolia-API-Key": config['api_key']
    }
    
    max_retries = 3
    for i in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json={"params": params}, timeout=20)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"    - Reintento {i+1} de API {config['index']} debido a: {e}")
            time.sleep(3)
    return None

def transform_hit(hit, dealer_name):
    # Intentar mapear los campos de Algolia a nuestra estructura base
    vin = hit.get("vin") or hit.get("vehicle_vin")
    if not vin: return None
    
    # Campo de imagen: Algolia puede usar 'thumbnail', 'image_url', 'thumbnail_url' o un array 'images'
    img_url = hit.get("thumbnail") or hit.get("image_url") or hit.get("thumbnail_url")
    if not img_url and hit.get("images"):
        img_url = hit.get("images")[0]
        
    # URL de VDP: 'link', 'url', 'vdp_url'
    vdp_url = hit.get("link") or hit.get("vdp_url") or hit.get("url")
    if vdp_url and vdp_url.startswith("/"):
        base = "https://www.bramanhonda.com" if dealer_name == "Braman" else "https://www.hollywoodkia.com"
        vdp_url = base + vdp_url

    v_type = hit.get("type", hit.get("body", "Used"))
    if not v_type: v_type = "Used"

    v = {
        "vin": vin,
        "year": str(hit.get("year", "")),
        "make": hit.get("make", ""),
        "model": hit.get("model", ""),
        "price": str(hit.get("price") or hit.get("our_price") or hit.get("msrp") or hit.get("sale_price", "")),
        "mileage": str(hit.get("mileage") or hit.get("odometer", "")),
        "ext_color": hit.get("exterior_color", ""),
        "int_color": hit.get("interior_color", ""),
        "body_style": v_type.capitalize(),
        "transmission": hit.get("transmission", ""),
        "engine": hit.get("engine", ""),
        "vdp_url": vdp_url,
        "display_name": f"{v_type.upper()} {hit.get('year', '')} {hit.get('make', '')} {hit.get('model', '')}".upper(),
        "image_url": img_url,
        "local_image": ""
    }
    
    if img_url:
        print(f"    -> Descargando imagen para {vin}...")
        v["local_image"] = download_image(img_url, f"{vin}.jpg")
        
    return v

def main():
    print("Iniciando actualización de inventario (Modo Robusto)...")
    
    # Cargar datos existentes
    all_vehicles = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    if item.get("vin"):
                        all_vehicles[item["vin"]] = item
        except: pass
    
    print(f"Cargados {len(all_vehicles)} vehículos existentes.")
    
    # 1. Braman Honda (Used Vehicles)
    print("\nConsultando Braman Honda...")
    params_braman = "query=&hitsPerPage=30&facetFilters=[\"type:Used\"]"
    res_braman = query_algolia(BRAMAN_CONFIG, params_braman)
    
    if res_braman and "hits" in res_braman:
        for hit in res_braman["hits"]:
            v = transform_hit(hit, "Braman")
            if v:
                if v["vin"] in all_vehicles:
                    if not all_vehicles[v["vin"]].get("local_image"):
                        all_vehicles[v["vin"]].update(v)
                else:
                    all_vehicles[v["vin"]] = v
                    print(f"  [+] Nuevo: {v['display_name']}")

    # 2. Hollywood Kia
    target_vin = "5XYC44JA0SG003168"
    print(f"\nConsultando Kia VIN: {target_vin}...")
    res_kia = query_algolia(KIA_CONFIG, f"query={target_vin}&hitsPerPage=1")
    if res_kia and "hits" in res_kia:
        for hit in res_kia["hits"]:
            v = transform_hit(hit, "Kia")
            if v:
                if v["vin"] in all_vehicles:
                    if not all_vehicles[v["vin"]].get("local_image"):
                        all_vehicles[v["vin"]].update(v)
                else:
                    all_vehicles[v["vin"]] = v
                    print(f"  [+] Kia: {v['display_name']}")

    final_data = list(all_vehicles.values())
    for v in final_data:
        if v.get("local_image"):
            v["local_image"] = v["local_image"].replace("/", "\\")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=4, ensure_ascii=False)
    
    with open(JS_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"const vehicleData = {json.dumps(final_data, indent=4, ensure_ascii=False)};")
            
    print(f"\nPROCESO COMPLETADO EXCELENENTE. Total {len(final_data)} vehículos.")

if __name__ == "__main__":
    main()


import requests
import json

BRAMAN_CONFIG = {
    "app_id": "V3ZOVI2QFZ",
    "api_key": "ec7553dd56e6d4c8bb447a0240e7aab3",
    "index": "bramanhondamiami_production_inventory"
}

def query_algolia(config, params=""):
    url = f"https://{config['app_id']}-dsn.algolia.net/1/indexes/{config['index']}/query"
    headers = {
        "X-Algolia-Application-Id": config['app_id'],
        "X-Algolia-API-Key": config['api_key']
    }
    response = requests.post(url, headers=headers, json={"params": params}, timeout=20)
    return response.json()

res = query_algolia(BRAMAN_CONFIG, "hitsPerPage=1")
if res and "hits" in res:
    hit = res["hits"][0]
    print("ALL KEYS:", hit.keys())
    print("\nIMAGE FIELDS:")
    for k in hit.keys():
        if "image" in k or "thumb" in k or "photo" in k:
            print(f"{k}: {hit[k]}")
    
    print("\nCONTENT FIELDS:")
    for field in ["make", "model", "trim", "year", "price", "mileage", "transmission", "engine", "exterior_color", "interior_color", "description", "body"]:
        print(f"{field}: {hit.get(field)}")

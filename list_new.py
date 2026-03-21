import json
with open('data/vehicles.json', 'r', encoding='utf-8') as f:
    vehicles = json.load(f)
    print("Nuevos vehículos cargados de Rick Case Honda:")
    for v in vehicles:
        if v.get('vdp_url') and 'rickcasehonda' in v['vdp_url']:
            print(f"- {v.get('display_name')} (Precio: ${v.get('price')} | Mileage: {v.get('mileage')})")

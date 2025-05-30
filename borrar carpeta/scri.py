import requests
import urllib3
import base64
import psutil
import re

urllib3.disable_warnings()

# Paso 1: Buscar proceso del cliente y obtener token + puerto
def get_lockfile_data():
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == 'LeagueClientUx.exe':
            path = proc.exe().replace('LeagueClientUx.exe', 'lockfile')
            with open(path, 'r') as f:
                lockfile = f.read()
                parts = lockfile.split(':')
                return {
                    'name': parts[0],
                    'pid': parts[1],
                    'port': parts[2],
                    'password': parts[3],
                    'protocol': parts[4]
                }
    raise Exception("No se encontró el cliente de LoL abierto.")

# Paso 2: Acceder al endpoint de inventario
def get_skins():
    lock = get_lockfile_data()
    port = lock['port']
    password = lock['password']
    token = base64.b64encode(f'riot:{password}'.encode()).decode()
    headers = {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json'
    }
    url = f"https://127.0.0.1:{port}/lol-inventory/v1/inventory"
    response = requests.get(url, headers=headers, verify=False)
    
    if response.status_code != 200:
        raise Exception(f"Error al acceder: {response.status_code} - {response.text}")

    items = response.json()["items"]
    skins = [item for item in items if item["type"] == "CHAMPION_SKIN"]
    
    print("Skins encontradas:")
    for skin in skins:
        print(f"Skin ID: {skin['itemId']}")
    
    return skins

# Ejecutar
get_skins()

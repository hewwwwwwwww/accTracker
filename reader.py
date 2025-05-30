import requests
import base64
import os
import psutil
import urllib3

def get_lockfile():
    for proc in psutil.process_iter():
        try:
            if proc.name() == "LeagueClientUx.exe":
                path = proc.exe()
                lockfile_path = os.path.join(os.path.dirname(path), "lockfile")
                if os.path.exists(lockfile_path):
                    return lockfile_path
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

def parse_lockfile(lockfile_path):
    with open(lockfile_path, 'r') as f:
        data = f.read().split(':')
    return {
        'name': data[0],
        'pid': data[1],
        'port': data[2],
        'password': data[3],
        'protocol': data[4]
    }

# --- NUEVO: función para obtener diccionario ID -> Nombre campeón
def get_champion_id_map():
    version_url = "https://ddragon.leagueoflegends.com/api/versions.json"
    versions = requests.get(version_url).json()
    latest_version = versions[0]

    champs_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/en_US/champion.json"
    data = requests.get(champs_url).json()

    id_map = {}
    for champ in data["data"].values():
        id_map[int(champ["key"])] = champ["name"]
    return id_map

def get_current_summoner():
    lockfile = get_lockfile()
    if not lockfile:
        print("No se encontró el lockfile. ¿Está abierto el cliente de LoL?")
        return

    info = parse_lockfile(lockfile)
    auth = base64.b64encode(f"riot:{info['password']}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}"
    }

    urllib3.disable_warnings()  # para evitar warning de certificado no válido

    # --- NUEVO: obtener diccionario ID->Nombre para campeones
    id_to_name = get_champion_id_map()

    # --- MODIFICADO: URL para campeones comprados
    champ_url = f"https://127.0.0.1:{info['port']}/lol-champions/v1/owned-champions-minimal"
    champ_response = requests.get(champ_url, headers=headers, verify=False)

    if champ_response.status_code == 200:
        champs = champ_response.json()
        
        print(f"\nChampions ({len(champs)}):")
        # --- MODIFICADO: mostrar nombre + ID usando el diccionario
        for champ in champs:
            champ_id = champ['id']
            nombre = id_to_name.get(champ_id, f"Desconocido (ID: {champ_id})")
            print(f"- {nombre}")
        print(f"\nTotal campeones: {len(champs)}")
    else:
        print("\nError al obtener campeones.")
        print(champ_response.text)

    # --- SIN CAMBIOS: obtener datos del invocador
    url = f"https://127.0.0.1:{info['port']}/lol-summoner/v1/current-summoner"
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code == 200:
        summoner = response.json()
        print("\nDatos del invocador:")
        for key, value in summoner.items():
            print(f"{key}: {value}")
        return summoner
    else:
        print(f"Error al obtener datos: {response.status_code}")
        print(response.text)
        
def get_owned_skins():
    lockfile = get_lockfile()
    if not lockfile:
        print("No se encontró el lockfile. ¿Está abierto el cliente de LoL?")
        return

    info = parse_lockfile(lockfile)
    auth = base64.b64encode(f"riot:{info['password']}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}"
    }

    urllib3.disable_warnings()

    # Endpoint correcto
    skins_url = f"https://127.0.0.1:{info['port']}/lol-inventory/v2/inventory/CHAMPION_SKIN"
    response = requests.get(skins_url, headers=headers, verify=False)

    if response.status_code == 200:
        data = response.json()

        print("\nSkins compradas por la cuenta:")
        for item in data:  # 🔥 Ahora recorremos la lista directamente
            print(f"- ID: {item['itemId']} (Comprada el {item['purchaseDate']})")
    else:
        print(f"Error al obtener skins: {response.status_code}")
        print(response.text)

import requests

def get_skin_names(skin_ids):
    print("\nObteniendo nombres de skins desde CommunityDragon...")

    cdragon_url = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/skins.json"

    try:
        response = requests.get(cdragon_url)
        response.raise_for_status()
        data = response.json()

        # Buscar nombres de skins por ID
        id_to_skin = {skin["id"]: skin["name"] for skin in data.values()}
        
        print("\nSkins compradas con sus nombres:")
        for skin_id in skin_ids:
            nombre_skin = id_to_skin.get(skin_id, f"Desconocido (ID: {skin_id})")
            print(f"- {nombre_skin}")

    except Exception as e:
        print(f"Error al obtener datos: {e}")

# Lista de IDs obtenidas
skin_ids = [
    39040, 555016, 48001, 39041, 60034, 39042, 412036, 134016, 21002, 53003, 
    106001, 266007, 127001, 21016, 21021, 21023, 21024, 21025, 21026, 21027, 
    21028, 21029, 127012, 84004, 127014, 127019, 30001, 22067, 22069, 22070, 
    22071, 222004, 22072, 63033, 22073, 22074, 22075, 63037, 63039, 35015, 
    35016, 13003, 35020, 13005, 4045, 35022, 4046, 51022, 4047, 51024, 51025, 
    51026, 13011, 51027, 45013, 45015, 45016, 45021, 45032, 236008, 28015, 
    22007, 412028, 236024, 11003, 39037, 39039
]
def verificar_skins_compradas(skins_obtenidas, skins_reales):
    print("\nVerificación cruzada de skins compradas...")

    skins_validadas = [skin_id for skin_id in skins_obtenidas if skin_id in skins_reales]

    print("\n✅ Lista final de skins confirmadas:")
    for skin_id in skins_validadas:
        print(f"- ID: {skin_id}")

    print(f"\n📌 Total de skins confirmadas: {len(skins_validadas)} / {len(skins_reales)} esperadas.")
    
# Lista de IDs obtenidas desde la API del cliente
skins_obtenidas = [
    39040, 555016, 48001, 39041, 60034, 39042, 412036, 134016, 21002, 53003, 
    106001, 266007, 127001, 21016, 21021, 21023, 21024, 21025, 21026, 21027, 
    21028, 21029, 127012, 84004, 127014, 127019, 30001, 22067, 22069, 22070, 
    22071, 222004, 22072, 63033, 22073, 22074, 22075, 63037, 63039, 35015, 
    35016, 13003, 35020, 13005, 4045, 35022, 4046, 51022, 4047, 51024, 51025, 
    51026, 13011, 51027, 45013, 45015, 45016, 45021, 45032, 236008, 28015, 
    22007, 412028, 236024, 11003, 39037, 39039
]

# Lista real de skins en tu cuenta (las que ves en el cliente)
skins_reales = [
    39040, 555016, 48001, 60034, 134016, 21002, 53003, 106001, 266007, 127001, 
    21016, 21021, 84004, 127012, 30001, 22067, 22069, 222004, 63033, 35015, 
    13003, 13005, 4045, 51022, 51027, 45013, 45032, 236008, 28015, 412028, 
    11003, 39037
]

# Ejecutar la verificación
verificar_skins_compradas(skins_obtenidas, skins_reales)


import requests

def get_skin_names(skin_ids):
    print("\nObteniendo nombres de skins desde CommunityDragon...")

    cdragon_url = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/skins.json"

    try:
        response = requests.get(cdragon_url)
        response.raise_for_status()
        data = response.json()

        # Crear un diccionario con los nombres de skins
        id_to_skin = {skin["id"]: skin["name"] for skin in data.values()}
        
        print("\n✅ Lista final de skins confirmadas con nombres:")
        for skin_id in skin_ids:
            nombre_skin = id_to_skin.get(skin_id, f"Desconocido (ID: {skin_id})")
            print(f"- {nombre_skin}")

    except Exception as e:
        print(f"Error al obtener datos: {e}")

# Lista final de skins confirmadas
skins_confirmadas = [
    39040, 555016, 48001, 60034, 134016, 21002, 53003, 106001, 266007, 127001, 
    21016, 21021, 84004, 127012, 30001, 22067, 22069, 222004, 63033, 35015, 
    13003, 13005, 4045, 51022, 51027, 45013, 45032, 236008, 28015, 412028, 
    11003, 39037
]

# Ejecutar función
get_skin_names(skins_confirmadas)


    

        

if __name__ == "__main__":
   print("a")
   #get_current_summoner()
   # get_owned_skins()
    #get_skin_names(skin_ids)
   

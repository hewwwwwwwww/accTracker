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

if __name__ == "__main__":
    get_current_summoner()

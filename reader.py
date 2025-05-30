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

   # Obtener campeones comprados
    print("campeones comprados:")
    champ_url = f"https://127.0.0.1:{info['port']}/lol-champions/v1/owned-champions-minimal"
    champ_response = requests.get(champ_url, headers=headers, verify=False)
    print("campones comprados : {champ_response}")
    if champ_response.status_code == 200:
        champs = champ_response.json()
        print("\nCampeones comprados:")
        for champ in champs:
            print(f"- ID: {champ['id']}")
    else:
        print("\nError al obtener campeones.")
        print(champ_response.text)



    url = f"https://127.0.0.1:{info['port']}/lol-summoner/v1/current-summoner"
    urllib3.disable_warnings()  # para evitar warning de certificado no válido

    response = requests.get(url, headers=headers, verify=False)
    if response.status_code == 200:
        summoner = response.json()
        print("Datos del invocador:")
        for key, value in summoner.items():
            print(f"{key}: {value}")
        return summoner
    else:
        print(f"Error al obtener datos: {response.status_code}")
        print(response.text)

  

if __name__ == "__main__":
    get_current_summoner()

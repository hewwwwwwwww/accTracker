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
        get_summoner_basic_info()
        get_current_ranked_info()
       # get_champion_and_skin_counts()


        print(f"\nChampions ({len(champs)}):")
        # --- MODIFICADO: mostrar nombre + ID usando el diccionario
        for champ in champs:
            champ_id = champ['id']
            nombre = id_to_name.get(champ_id, f"Desconocido (ID: {champ_id})")
            print(f"- {nombre}")
        
        return len(champs)
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
        

# ... (mantén las demás funciones como antes)

def get_show_skins():
    lockfile = get_lockfile()
    if not lockfile:
        print("❌ No se encontró el lockfile. ¿Está abierto el cliente de LoL?")
        return

    info = parse_lockfile(lockfile)
    auth = base64.b64encode(f"riot:{info['password']}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}"
    }
    urllib3.disable_warnings()

    response = requests.get(f"https://127.0.0.1:{info['port']}/lol-inventory/v2/inventory/CHAMPION_SKIN", headers=headers, verify=False)
    if response.status_code != 200:
        print(f"❌ Error al obtener skins: {response.status_code}")
        return

    skins_data = response.json()
    owned_skin_ids = [skin['itemId'] for skin in skins_data]
    

    #print("\n📦 Obteniendo base de datos de skins desde CommunityDragon...")
    cdragon_url = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/skins.json"

    try:
        cdragon_response = requests.get(cdragon_url)
        cdragon_response.raise_for_status()
        skin_db = cdragon_response.json()
        id_to_name = {skin["id"]: skin["name"] for skin in skin_db.values()}
    except Exception as e:
        print(f"❌ Error al obtener datos de CommunityDragon: {e}")
        return

    
    #para poder sacar la cantidad y mostrarlas en formato correcto
    reconocidas = 0
    reconocidas_str = []  # Lista para almacenar strings con el formato "- Nombre"
    no_reconocidas = []

    for skin_id in owned_skin_ids:
        nombre = id_to_name.get(skin_id)
        if nombre:
            reconocidas_str.append(f"- {nombre}")  # Agrega a la lista formateado
            reconocidas += 1
        else:
            no_reconocidas.append(skin_id)

    # Construir mensaje final
    final_message = f" Skins ({reconocidas}):"
    print("\n" + final_message)
    print("\n".join(reconocidas_str))  # Imprime todas las skins formateadas
    return (reconocidas)

    

    #if no_reconocidas:
       # print(f"⚠️  Skins no reconocidas (posibles IDs especiales o nuevas):") || printf para ver las id no reconocidas
       # for id_ in no_reconocidas:
           # print(f"- ID: {id_}")
       # print(f"Total no reconocidas: {len(no_reconocidas)}")



def get_summoner_basic_info():
    lockfile = get_lockfile()
    if not lockfile:
        print("❌ No se encontró el lockfile. ¿Está abierto el cliente de LoL?")
        return

    info = parse_lockfile(lockfile)
    auth = base64.b64encode(f"riot:{info['password']}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}"
    }
    urllib3.disable_warnings()

    url = f"https://127.0.0.1:{info['port']}/lol-summoner/v1/current-summoner"
    response = requests.get(url, headers=headers, verify=False)

    if response.status_code == 200:
        summoner = response.json()
        nivel = summoner.get('summonerLevel', 'Desconocido')
        game_name = summoner.get('gameName', 'Desconocido')
        tag_line = summoner.get('tagLine', 'Desconocido')

        # Traducción de regiones
        region_map = {
            'la2': 'LAS',
            'la1': 'LAN',
            'br1': 'BR',
            'na1': 'NA',
            'euw1': 'EUW',
            'eun1': 'EUNE',
            'kr': 'KR',
            'jp1': 'JP',
            'ru': 'RU',
            'tr1': 'TR',
            'oc1': 'OCE',
        }

        region_legible = region_map.get(tag_line.lower(), tag_line.upper())

        print(f"🌐 Servidor: {region_legible}")
        print(f"📈 Nivel: {nivel}")

        return {
            'servidor': region_legible,
            'invocador': f"{game_name}#{tag_line.upper()}",
            'nivel': nivel
        }
    else:
        print(f"❌ Error al obtener datos del invocador: {response.status_code}")
        print(response.text)
        return None

def get_current_ranked_info():
    lockfile = get_lockfile()
    if not lockfile:
        print("❌ No se encontró el lockfile. ¿Está abierto el cliente de LoL?")
        return

    info = parse_lockfile(lockfile)
    auth = base64.b64encode(f"riot:{info['password']}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}"
    }
    urllib3.disable_warnings()

    url = f"https://127.0.0.1:{info['port']}/lol-ranked/v1/current-ranked-stats"
    response = requests.get(url, headers=headers, verify=False)

    if response.status_code == 200:
        data = response.json()

        # Filtrar solo SOLOQ
        soloq = next((q for q in data['queues'] if q['queueType'] == 'RANKED_SOLO_5x5'), None)

        if soloq:
            tier = soloq['tier'].capitalize()
            division = soloq['division']
            lp = soloq['leaguePoints']
            wins = soloq['wins']
            losses = soloq['losses']
            total_games = wins + losses
            winrate = round((wins / total_games) * 100, 1) if total_games > 0 else 0.0

            print(f"🎯 Rango actual SoloQ: {tier} {division} - {lp} LP")
            print(f"🏆 Winrate: {winrate}% ({wins}W / {losses}L)")

            return {
                'rango': f"{tier} {division}",
                'lp': lp,
                'winrate': winrate,
                'wins': wins,
                'losses': losses
            }
        else:
            print("⚠️  No hay datos de SoloQ (no ha jugado rankeds esta season).")
            return {
                'rango': 'Unranked',
                'lp': 0,
                'winrate': 0.0,
                'wins': 0,
                'losses': 0
            }

    else:
        print(f"❌ Error al obtener ranked stats: {response.status_code}")
        print(response.text)
        return None

def get_champion_and_skin_counts(total_champions=None, total_skins=None):
    if total_champions is None:
        total_champions = get_current_summoner()
    if total_skins is None:
        total_skins = get_show_skins()

    print(f"🎮 Campeones: {total_champions}")
    print(f"🎨 Skins: {total_skins}")

    return total_champions, total_skins

def get_loot_info():
    lockfile = get_lockfile()
    if not lockfile:
        print("❌ No se encontró el lockfile. ¿Está abierto el cliente de LoL?")
        return

    info = parse_lockfile(lockfile)
    auth = base64.b64encode(f"riot:{info['password']}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}"
    }
    urllib3.disable_warnings()

    url = f"https://127.0.0.1:{info['port']}/lol-loot/v1/player-loot"
    response = requests.get(url, headers=headers, verify=False)

    if response.status_code != 200:
        print(f"❌ Error al obtener botín: {response.status_code}")
        return

    loot = response.json()

    # Contadores
    champ_shards = 0
    skin_shards = 0
    blue_essence = 0
    orange_essence = 0
    hextech_chests = 0
    hextech_keys = 0

    for item in loot:
        loot_id = item.get('lootId', '')
        count = item.get('count', 0)

        if loot_id.startswith("CHAMPION_RENTAL"):
            champ_shards += count
        elif loot_id.startswith("SKIN_RENTAL"):
            skin_shards += count
        elif loot_id == "CURRENCY_champion":
            blue_essence = count
        elif loot_id == "CURRENCY_cosmetic":
            orange_essence = count
        elif loot_id.startswith("CHEST"):
            hextech_chests += count
        elif loot_id.startswith("MATERIAL_key_fragment") or loot_id == "MATERIAL_key":
            hextech_keys += count

    print(f"\n🔹 Fragmentos de campeón: {champ_shards}")
    print(f"🔸 Fragmentos de skin: {skin_shards}")
    print(f"🔵 Esencia azul: {blue_essence}")
    print(f"🟠 Esencia naranja: {orange_essence}")
    print(f"📦 Cofres Hextech: {hextech_chests}")
    print(f"🗝️ Llaves Hextech: {hextech_keys}")

    

        

if __name__ == "__main__":
    total_champions = get_current_summoner()
    total_skins = get_show_skins()
   # get_summoner_basic_info()
    #get_current_ranked_info()
    #get_champion_and_skin_counts(total_champions, total_skins)
    get_loot_info()
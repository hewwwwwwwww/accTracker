import requests
import base64
import os
import psutil
import urllib3
from concurrent.futures import ThreadPoolExecutor

urllib3.disable_warnings()

# =========================
# CACHE GLOBAL
# =========================
CACHE = {
    "champion_map": None,
    "skin_map": None,
    "connection": None
}


# =========================
# BASE
# =========================

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


def get_connection():
    if CACHE["connection"]:
        return CACHE["connection"]

    lockfile = get_lockfile()
    if not lockfile:
        return None, None

    info = parse_lockfile(lockfile)
    auth = base64.b64encode(f"riot:{info['password']}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}

    CACHE["connection"] = (info, headers)
    return info, headers


# =========================
# DATA DRAGON (CACHE)
# =========================

def get_champion_id_map():
    if CACHE["champion_map"]:
        return CACHE["champion_map"]

    versions = requests.get("https://ddragon.leagueoflegends.com/api/versions.json").json()
    latest = versions[0]

    data = requests.get(
        f"https://ddragon.leagueoflegends.com/cdn/{latest}/data/en_US/champion.json"
    ).json()

    CACHE["champion_map"] = {
        int(champ["key"]): champ["name"]
        for champ in data["data"].values()
    }

    return CACHE["champion_map"]


def get_skin_map():
    if CACHE["skin_map"]:
        return CACHE["skin_map"]

    url = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/skins.json"
    data = requests.get(url).json()

    CACHE["skin_map"] = {
        skin["id"]: skin["name"]
        for skin in data.values()
    }

    return CACHE["skin_map"]


# =========================
# CORE
# =========================

def get_current_summoner():
    info, headers = get_connection()
    if not info:
        print("No se encontró el lockfile. ¿Está abierto el cliente de LoL?")
        return

    id_to_name = get_champion_id_map()

    champ_url = f"https://127.0.0.1:{info['port']}/lol-champions/v1/owned-champions-minimal"

    with ThreadPoolExecutor() as executor:
        future_champs = executor.submit(requests.get, champ_url, headers=headers, verify=False)
        future_summoner = executor.submit(get_summoner_basic_info)
        future_ranked = executor.submit(get_current_ranked_info)
        future_skins = executor.submit(get_skins_count)
        future_loot = executor.submit(get_loot_info)

        champ_response = future_champs.result()
        skinz = future_skins.result()

    if champ_response.status_code == 200:
        champs = champ_response.json()

        print("⭐ BUDA  ⭐  BOOST ⭐\n")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━")

        # estos ya imprimieron dentro del thread
        future_summoner.result()
        future_ranked.result()

        print(f"👤 Champions: {len(champs)}")
        print(f"🎨 Skins: {skinz}")

        future_loot.result()

        print("🔄 Can change nickname\n✉️  Can change e-mail\n🔐 Full access\n✅ 0% Ban Chance\n🚀 Instant Delivery")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━")

        print(f"\nChampions ({len(champs)}):")
        for champ in champs:
            champ_id = champ['id']
            nombre = id_to_name.get(champ_id, f"Desconocido (ID: {champ_id})")
            print(f"- {nombre}")

        return len(champs)

    else:
        print("\nError al obtener campeones.")
        print(champ_response.text)


# =========================
# SKINS
# =========================

def get_show_skins():
    info, headers = get_connection()
    if not info:
        print("❌ No se encontró el lockfile. ¿Está abierto el cliente de LoL?")
        return

    response = requests.get(
        f"https://127.0.0.1:{info['port']}/lol-inventory/v2/inventory/CHAMPION_SKIN",
        headers=headers,
        verify=False
    )

    if response.status_code != 200:
        print(f"❌ Error al obtener skins: {response.status_code}")
        return

    skins_data = response.json()
    owned_ids = [s['itemId'] for s in skins_data]

    id_to_name = get_skin_map()

    reconocidas = 0
    reconocidas_str = []

    for sid in owned_ids:
        nombre = id_to_name.get(sid)
        if nombre:
            reconocidas += 1
            reconocidas_str.append(f"- {nombre}")

    print(f"\n Skins ({reconocidas}):")
    print("\n".join(reconocidas_str))

    return reconocidas


def get_skins_count():
    info, headers = get_connection()
    if not info:
        print("❌ No se encontró el lockfile. ¿Está abierto el cliente de LoL?")
        return

    response = requests.get(
        f"https://127.0.0.1:{info['port']}/lol-inventory/v2/inventory/CHAMPION_SKIN",
        headers=headers,
        verify=False
    )

    if response.status_code != 200:
        print(f"❌ Error al obtener skins: {response.status_code}")
        return

    skins_data = response.json()
    owned_ids = [s['itemId'] for s in skins_data]

    id_to_name = get_skin_map()

    return sum(1 for sid in owned_ids if sid in id_to_name)


# =========================
# SUMMONER INFO
# =========================

def get_summoner_basic_info():
    info, headers = get_connection()
    if not info:
        print("❌ No se encontró el lockfile. ¿Está abierto el cliente de LoL?")
        return

    url = f"https://127.0.0.1:{info['port']}/lol-summoner/v1/current-summoner"
    response = requests.get(url, headers=headers, verify=False)

    if response.status_code == 200:
        s = response.json()

        region_map = {
            'la2': 'LAS', 'la1': 'LAN', 'br1': 'BR', 'na1': 'NA',
            'euw1': 'EUW', 'eun1': 'EUNE', 'kr': 'KR', 'jp1': 'JP',
            'ru': 'RU', 'tr1': 'TR', 'oc1': 'OCE'
        }

        region = region_map.get(s.get('tagLine', '').lower(), s.get('tagLine', '').upper())

        print(f"🌐 Server: {region}")
        print(f"📈 Level: {s.get('summonerLevel', 'Desconocido')}")

    else:
        print(f"❌ Error al obtener datos del invocador: {response.status_code}")


# =========================
# RANKED
# =========================

def get_current_ranked_info():
    info, headers = get_connection()
    if not info:
        print("❌ No se encontró el lockfile. ¿Está abierto el cliente de LoL?")
        return

    url = f"https://127.0.0.1:{info['port']}/lol-ranked/v1/current-ranked-stats"
    response = requests.get(url, headers=headers, verify=False)

    if response.status_code == 200:
        data = response.json()
        soloq = next((q for q in data['queues'] if q['queueType'] == 'RANKED_SOLO_5x5'), None)

        if soloq:
            wins = soloq['wins']
            losses = soloq['losses']
            total = wins + losses
            winrate = round((wins / total) * 100, 1) if total > 0 else 0.0

            print(f"🎯 Rank(Soloq): {soloq['tier'].capitalize()} {soloq['division']} - {soloq['leaguePoints']} LP")
            print(f"📊 Winrate: {winrate}% ({wins}W / {losses}L)")
        else:
            print("⚠️  No hay datos de SoloQ.")


# =========================
# LOOT
# =========================

def get_loot_info():
    info, headers = get_connection()
    if not info:
        print("❌ No se encontró el lockfile. ¿Está abierto el cliente de LoL?")
        return

    url = f"https://127.0.0.1:{info['port']}/lol-loot/v1/player-loot"
    response = requests.get(url, headers=headers, verify=False)

    if response.status_code != 200:
        print(f"❌ Error al obtener botín: {response.status_code}")
        return

    loot = response.json()

    blue = orange = chests = keys = 0

    for item in loot:
        lid = item.get('lootId', '')
        count = item.get('count', 0)

        if lid == "CURRENCY_champion":
            blue = count
        elif lid == "CURRENCY_cosmetic":
            orange = count
        elif lid.startswith("CHEST"):
            chests += count
        elif lid.startswith("MATERIAL_key"):
            keys += count

    if blue > 499:
        print(f"🔵 Blue essence: {blue}")
    if orange > 499:
        print(f"🟠 Orange essence: {orange}")
    if chests > 0:
        print(f"📦 Hextech chests: {chests}")
    if keys > 0:
        print(f"🗝️ Hextech keys: {keys}")

    return loot


# =========================
# SHARDS (SIN CAMBIOS)
# =========================

def get_champion_skins_shards_list():
    lockfile = get_lockfile()
    if not lockfile:
        print("❌ No se encontró el lockfile. ¿Está abierto el cliente de LoL?")
        return None, None

    info = parse_lockfile(lockfile)

    auth = base64.b64encode(f"riot:{info['password']}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}

    url = f"https://127.0.0.1:{info['port']}/lol-loot/v1/player-loot"

    try:
        response = requests.get(url, headers=headers, verify=False)
    except Exception as e:
        print("❌ Error en la petición:", e)
        return None, None

    if response.status_code != 200:
        print(f"❌ Error al obtener botín: {response.status_code}")
        return None, None

    loot = response.json()

    champion_shards = []
    skin_shards = []

    for item in loot:
        loot_id = item.get('lootId', '')
        desc = item.get('itemDesc', '').strip()
        count = item.get('count', 0)

        if not desc or count <= 0:
            continue

        # 🔥 CAMBIO IMPORTANTE: incluir shards reales + rental
        if loot_id.startswith("CHAMPION"):
            for _ in range(count):
                champion_shards.append(desc)

        elif loot_id.startswith("CHAMPION_SKIN"):
            for _ in range(count):
                skin_shards.append(desc)

    champ_str = f"Champions Shards ({len(champion_shards)}):\n" + ''.join(f"-{c}\n" for c in champion_shards)
    skin_str = f"Skin Shards ({len(skin_shards)}):\n" + ''.join(f"-{s}\n" for s in skin_shards)

    return champ_str.strip(), skin_str.strip()



# =========================
# MAIN
# =========================

if __name__ == "__main__":
    get_current_summoner()
    get_show_skins()

    champ_shard_list, skin_shard_list = get_champion_skins_shards_list()

    if champ_shard_list and champ_shard_list.count("-") != 0:
        print("\n")
        print(champ_shard_list)

    if skin_shard_list and skin_shard_list.count("-") != 0:
        print("\n")
        print(skin_shard_list)



        
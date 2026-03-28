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

    champ_perm = {}
    champ_temp = {}

    skin_perm = {}
    skin_temp = {}

    for item in loot:
        loot_id = item.get('lootId', '')
        desc = item.get('itemDesc', '').strip()
        count = item.get('count', 0)

        if not desc or count <= 0:
            continue

        # CHAMPIONS
        if loot_id.startswith("CHAMPION_") and not loot_id.startswith("CHAMPION_SKIN"):
            if loot_id.startswith("CHAMPION_RENTAL"):
                champ_temp[desc] = champ_temp.get(desc, 0) + count
            else:
                champ_perm[desc] = champ_perm.get(desc, 0) + count

        # SKINS
        elif loot_id.startswith("CHAMPION_SKIN"):
            if loot_id.startswith("CHAMPION_SKIN_RENTAL"):
                skin_temp[desc] = skin_temp.get(desc, 0) + count
            else:
                skin_perm[desc] = skin_perm.get(desc, 0) + count

    # =========================
    # SORTING
    # =========================

    # Champions permanentes → alfabético
    champ_perm_sorted = sorted(champ_perm.items(), key=lambda x: x[0].lower())

    # Champions temporales → cantidad DESC, luego nombre
    champ_temp_sorted = sorted(
        champ_temp.items(),
        key=lambda x: (-x[1], x[0].lower())
    )

    # Skins permanentes → alfabético
    skin_perm_sorted = sorted(skin_perm.items(), key=lambda x: x[0].lower())

    # Skins temporales → alfabético
    skin_temp_sorted = sorted(skin_temp.items(), key=lambda x: x[0].lower())

    # =========================
    # FORMAT
    # =========================

    champ_lines = []

    for name, count in champ_perm_sorted:
        suffix = " (permanent)"
        if count > 1:
            suffix += f" (x{count})"
        champ_lines.append(f"-{name}{suffix}")

    for name, count in champ_temp_sorted:
        suffix = f" (x{count})" if count > 1 else ""
        champ_lines.append(f"-{name}{suffix}")

    skin_lines = []

    for name, count in skin_perm_sorted:
        suffix = " (permanent)"
        if count > 1:
            suffix += f" (x{count})"
        skin_lines.append(f"-{name}{suffix}")

    for name, count in skin_temp_sorted:
        suffix = f" (x{count})" if count > 1 else ""
        skin_lines.append(f"-{name}{suffix}")

    champ_str = f"Champions Shards ({len(champ_lines)}):\n" + "\n".join(champ_lines)
    skin_str = f"Skin Shards ({len(skin_lines)}):\n" + "\n".join(skin_lines)

    return champ_str.strip(), skin_str.strip()


from concurrent.futures import ThreadPoolExecutor, as_completed

def delete_all_friends():
    info, headers = get_connection()
    if not info:
        return

    url = f"https://127.0.0.1:{info['port']}/lol-chat/v1/friends"
    response = requests.get(url, headers=headers, verify=False)

    if response.status_code != 200:
        return

    friends = response.json()

    if not friends:
        return


    def delete_friend(puuid):
        try:
            delete_url = f"https://127.0.0.1:{info['port']}/lol-chat/v1/friends/{puuid}"
            requests.delete(delete_url, headers=headers, verify=False)
        except:
            pass  # no queremos romper por uno que falle

    # ⚡ THREADS
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(delete_friend, f.get("puuid"))
            for f in friends if f.get("puuid")
        ]

        # opcional: esperar a que todos terminen
        for _ in as_completed(futures):
            pass


def get_seller_name():
    return "⭐ BUDA  ⭐  BOOST ⭐"


def get_server_region():
    info, headers = get_connection()
    if not info:
        return "Desconocido"

    try:
        url = f"https://127.0.0.1:{info['port']}/lol-platform-config/v1/namespaces"
        response = requests.get(url, headers=headers, verify=False)

        if response.status_code != 200:
            return "Desconocido"

        data = response.json()

        region_raw = data.get("LoginDataPacket", {}).get("platformId", "").lower()

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
            'oc1': 'OCE'
        }

        if region_raw:
            return region_map.get(region_raw, region_raw.upper())

        return "Desconocido"

    except Exception as e:
        print("❌ Error obteniendo región:", e)
        return "Desconocido"
    
def get_summoner_level():
    info, headers = get_connection()
    if not info:
        return None

    try:
        url = f"https://127.0.0.1:{info['port']}/lol-summoner/v1/current-summoner"
        response = requests.get(url, headers=headers, verify=False)

        if response.status_code != 200:
            return None

        data = response.json()
        return data.get("summonerLevel")

    except Exception as e:
        print("❌ Error obteniendo nivel:", e)
        return None
    
    
def get_rank_info():
    info, headers = get_connection()
    if not info:
        return "Unranked"

    url = f"https://127.0.0.1:{info['port']}/lol-ranked/v1/current-ranked-stats"

    try:
        response = requests.get(url, headers=headers, verify=False)
    except:
        return "Unranked"

    if response.status_code != 200:
        return "Unranked"

    data = response.json()

    soloq = next(
        (q for q in data.get('queues', []) if q.get('queueType') == 'RANKED_SOLO_5x5'),
        None
    )

    if not soloq:
        return "Unranked"

    # 🔥 Si está en placements → no mostrar rank
    if soloq.get("type") == "placements":
        return "Unranked"

    tier = soloq.get("tier", "Unknown").capitalize()
    division = soloq.get("division", "")
    lp = soloq.get("leaguePoints", 0)

    return f"{tier} {division} - {lp} LP"


def get_placements_info():
    info, headers = get_connection()
    if not info:
        return None

    url = f"https://127.0.0.1:{info['port']}/lol-ranked/v1/current-ranked-stats"

    try:
        response = requests.get(url, headers=headers, verify=False)
    except:
        return None

    if response.status_code != 200:
        return None

    data = response.json()

    soloq = next(
        (q for q in data.get('queues', []) if q.get('queueType') == 'RANKED_SOLO_5x5'),
        None
    )

    if not soloq:
        return None

    # 🔥 Solo si está en placements
    if soloq.get("type") == "placements":
        played = soloq.get("played", 0)
        return f"📊 {played} Placements played"

    return None

def get_champions_count():
    info, headers = get_connection()
    if not info:
        return None

    url = f"https://127.0.0.1:{info['port']}/lol-champions/v1/owned-champions-minimal"

    try:
        response = requests.get(url, headers=headers, verify=False)
    except:
        return None

    if response.status_code != 200:
        return None

    champs = response.json()
    return len(champs)

def get_skins_count():
    info, headers = get_connection()
    if not info:
        return None

    url = f"https://127.0.0.1:{info['port']}/lol-inventory/v2/inventory/CHAMPION_SKIN"

    try:
        response = requests.get(url, headers=headers, verify=False)
    except:
        return None

    if response.status_code != 200:
        return None

    skins_data = response.json()
    owned_ids = [s['itemId'] for s in skins_data]

    id_to_name = get_skin_map()

    return sum(1 for sid in owned_ids if sid in id_to_name)


def get_blue_essence():
    info, headers = get_connection()
    if not info:
        return None

    url = f"https://127.0.0.1:{info['port']}/lol-loot/v1/player-loot"

    try:
        response = requests.get(url, headers=headers, verify=False)
    except:
        return None

    if response.status_code != 200:
        return None

    loot = response.json()

    for item in loot:
        if item.get('lootId') == "CURRENCY_champion":
            return item.get('count', 0)

    return 0

def get_orange_essence():
    info, headers = get_connection()
    if not info:
        return None

    url = f"https://127.0.0.1:{info['port']}/lol-loot/v1/player-loot"

    try:
        response = requests.get(url, headers=headers, verify=False)
    except:
        return None

    if response.status_code != 200:
        return None

    loot = response.json()

    for item in loot:
        if item.get('lootId') == "CURRENCY_cosmetic":
            return item.get('count', 0)

    return 0

def get_hextech_chests():
    info, headers = get_connection()
    if not info:
        return None

    url = f"https://127.0.0.1:{info['port']}/lol-loot/v1/player-loot"

    try:
        response = requests.get(url, headers=headers, verify=False)
    except:
        return None

    if response.status_code != 200:
        return None

    loot = response.json()

    chests = 0

    for item in loot:
        loot_id = item.get('lootId', '')
        if loot_id.startswith("CHEST"):
            chests += item.get('count', 0)

    return chests

def get_hextech_keys():
    info, headers = get_connection()
    if not info:
        return None

    url = f"https://127.0.0.1:{info['port']}/lol-loot/v1/player-loot"

    try:
        response = requests.get(url, headers=headers, verify=False)
    except:
        return None

    if response.status_code != 200:
        return None

    loot = response.json()

    keys = 0

    for item in loot:
        loot_id = item.get('lootId', '')
        if loot_id.startswith("MATERIAL_key"):
            keys += item.get('count', 0)

    return keys

def get_refunds_remaining():
    info, headers = get_connection()
    if not info:
        return None

    url = f"https://127.0.0.1:{info['port']}/lol-store/v1/refund-inventory"

    try:
        response = requests.get(url, headers=headers, verify=False)
    except:
        return None

    if response.status_code != 200:
        return None

    data = response.json()
    return data.get("refundCredits", 0)

def can_change_name():
    info, headers = get_connection()
    if not info:
        return None

    url = f"https://127.0.0.1:{info['port']}/lol-summoner/v1/name-change"

    try:
        response = requests.get(url, headers=headers, verify=False)
    except:
        return None

    if response.status_code != 200:
        return None

    data = response.json()

    return data.get("canChangeSummonerName", False)


def get_champions_list():
    info, headers = get_connection()
    if not info:
        return None

    url = f"https://127.0.0.1:{info['port']}/lol-champions/v1/owned-champions-minimal"

    try:
        response = requests.get(url, headers=headers, verify=False)
    except:
        return None

    if response.status_code != 200:
        return None

    champs = response.json()
    id_to_name = get_champion_id_map()

    names = []
    for champ in champs:
        champ_id = champ['id']
        nombre = id_to_name.get(champ_id, f"Desconocido (ID: {champ_id})")
        names.append(nombre)

    return sorted(names)

def set_status_message(message):
    info, headers = get_connection()
    if not info:
        return False

    url = f"https://127.0.0.1:{info['port']}/lol-chat/v1/me"

    payload = {
        "statusMessage": message
    }

    try:
        response = requests.put(url, json=payload, headers=headers, verify=False)
        return response.status_code == 200
    except:
        return False

def generate_title(
    server,
    rank,
    level,
    skins,
    lp_per_win,
    champions
):
    parts = []

    # 🔹 SERVER
    parts.append(f"【{server}】")

    # 🔹 RANK
    parts.append(f"✔️ {rank}")

    # 🔹 SKINS
    if skins and skins > 20:
        parts.append(f"✔️ +{skins} SKINS")

    # 🔹 LP/WIN
    if lp_per_win and lp_per_win > 30:
        parts.append(f"✔️ +{lp_per_win} LP/WIN")

    # 🔹 SEASON (fijo)
    parts.append("✔️ SEASON 16")

    # 🔹 CHAMPIONS
    if champions and champions > 70:
        parts.append(f"✔️ {champions} Champions")

    # 🔹 LEVEL
    if level and level > 70:
        parts.append(f"✔️ {level} LVL")

    # 🔹 HANDLEVELED
    if level and level < 90:
        parts.append("✔️ HANDLVL")

    # 🔹 FINAL FIJO
    parts.append("✔️ FULL ACCESS")
    parts.append("✔️ INSTANT DELIVERY")

    # 🔥 JOIN
    return " | ".join(parts)


def generate_title_v2(
    server,
    rank,
    level,
    skins,
    skin_shards,
    lp_per_win,
    champions,
    blue_essence,
    orange_essence
):
    parts = []

    # 🔹 SIEMPRE
    parts.append(f"【{server}】")
    parts.append(f"✔️ {rank}")

    # 🔹 SKIN SHARDS
    if skin_shards and skin_shards > 15:
        parts.append(f"✔️ {skin_shards} Skin Shards")

    # 🔹 LP/WIN
    if lp_per_win and lp_per_win >= 30:
        parts.append(f"✔️ +{lp_per_win} LP/WIN")

    # 🔹 SKINS
    if skins and skins > 30:
        parts.append(f"✔️ +{skins} Skins")

    # 🔹 SEASON (SIEMPRE)
    parts.append("✔️ SEASON 16")

    # 🔹 LEVEL
    if level and level > 70:
        parts.append(f"✔️ {level} LVL")

    # 🔹 BLUE ESSENCE
    if blue_essence and blue_essence > 5000:
        parts.append(f"✔️ {blue_essence} BE")

    # 🔹 ORANGE ESSENCE
    if orange_essence and orange_essence > 5000:
        parts.append(f"✔️ {orange_essence} OE")

    # 🔹 CHAMPIONS
    if champions and champions > 45:
        parts.append(f"✔️ {champions} Champions")

    # 🔥 ARMADO FINAL
    title_main = " | ".join(parts)

    # 🔻 SUFIJO FIJO
    suffix = "|✔️HANDLVL|✔️FRESH ACC|✔️0% BAN CHANCE|✔️FULL ACCESS|✔️INSTANT DELIVERY"

    return f"{title_main} {suffix}"

def estimate_lp_per_win(wins, losses, level):
    if not wins or not losses:
        return None

    total = wins + losses
    if total == 0:
        return None

    winrate = wins / total

    if winrate >= 0.65:
        return 30
    elif winrate >= 0.55:
        return 25
    elif winrate >= 0.50:
        return 22
    else:
        return None

def get_rank_wins_losses():
    info, headers = get_connection()
    if not info:
        return None, None

    url = f"https://127.0.0.1:{info['port']}/lol-ranked/v1/current-ranked-stats"

    try:
        response = requests.get(url, headers=headers, verify=False)
    except:
        return None, None

    if response.status_code != 200:
        return None, None

    data = response.json()

    soloq = next(
        (q for q in data.get('queues', []) if q.get('queueType') == 'RANKED_SOLO_5x5'),
        None
    )

    if not soloq:
        return None, None

    # 🔥 si está en placements → no hay wins/losses reales
    if soloq.get("type") == "placements":
        return None, None

    return soloq.get("wins"), soloq.get("losses")


############################
#PRINTER
############################
def print_summary(seller_name, server_region, summoner_level, rank_info, placements, champions_count, skins_count, blue_essence, orange_essence, chests_count, keys_count, refunds_remaining, can_change_name):
    print(seller_name)
    print("━━━━━━━━━━━━━━━━━━━━━━━━━")
    if server_region != "Desconocido":
        print(f"🌐 Server: {server_region}")
    if summoner_level is not None:
        print(f"📈 Level: {summoner_level}")
    print(f"🎯Rank(Soloq): {rank_info}")
    if placements is not None:
        print(f"📊 Placements: {placements}")
    if champions_count is not None:
        print(f"👤 Champions: {champions_count}")
    if skins_count is not None:
        print(f"🎨 Skins: {skins_count}")
    if blue_essence is not None and blue_essence > 499:
        print(f"🔵 Blue Essence: {blue_essence}")
    if orange_essence is not None and orange_essence > 499:
        print(f"🟠 Orange Essence: {orange_essence}")
    if chests_count is not None:
        print(f"📦 Hextech Chests: {chests_count}")
    if keys_count is not None:
        print(f"🗝️ Hextech Keys: {keys_count}")
    if refunds_remaining is not None:
        print(f"🔙 Refunds Remaining: {refunds_remaining}")
    if can_change_name is not None and can_change_name:
        print("🔄 Can change nickname")
    print("✉️  Can change e-mail\n🔐 Full access\n✅ 0% Ban Chance\n🚀 Instant Delivery")


# =========================
# MAIN
# =========================

from concurrent.futures import ThreadPoolExecutor

if __name__ == "__main__":

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            "seller": executor.submit(get_seller_name),
            "server": executor.submit(get_server_region),
            "level": executor.submit(get_summoner_level),
            "rank": executor.submit(get_rank_info),
            "placements": executor.submit(get_placements_info),
            "champions_count": executor.submit(get_champions_count),
            "skins_count": executor.submit(get_skins_count),
            "blue_essence": executor.submit(get_blue_essence),
            "orange_essence": executor.submit(get_orange_essence),
            "chests_count": executor.submit(get_hextech_chests),
            "keys_count": executor.submit(get_hextech_keys),
            "refunds_remaining": executor.submit(get_refunds_remaining),
            "can_change": executor.submit(can_change_name),
            "champions_list": executor.submit(get_champions_list),
        }

        # 🔥 Resolver resultados
        seller = futures["seller"].result()
        server = futures["server"].result()
        level = futures["level"].result()
        rank = futures["rank"].result()
        placements = futures["placements"].result()
        champions_count = futures["champions_count"].result()
        skins_count = futures["skins_count"].result()
        blue_essence = futures["blue_essence"].result()
        orange_essence = futures["orange_essence"].result()
        chests_count = futures["chests_count"].result()
        keys_count = futures["keys_count"].result()
        refunds_remaining = futures["refunds_remaining"].result()
        can_change = futures["can_change"].result()
        champions_list = futures["champions_list"].result()

    # ✅ Print ordenado
    print_summary(
        seller,
        server,
        level,
        rank,
        placements,
        champions_count,
        skins_count,
        blue_essence,
        orange_essence,
        chests_count,
        keys_count,
        refunds_remaining,
        can_change
    )

    # 🔹 Acción aparte (mejor fuera de threads)
    delete_all_friends()

    # 🔹 Lista de champions
    if champions_list:
        print(f"\nChampions ({len(champions_list)}):")
        for champ in champions_list:
            print(f"- {champ}")

    # 🔹 Shards (podés paralelizar esto también si querés)
    champ_shard_list, skin_shard_list = get_champion_skins_shards_list()

    if champ_shard_list and champ_shard_list.count("-") != 0:
        print("\n")
        print(champ_shard_list)

    if skin_shard_list and skin_shard_list.count("-") != 0:
        print("\n")
        print(skin_shard_list)
        
    set_status_message(
        "⭐ BUDA BOOST ⭐ | Unranked | 30K BE | Full Access"
    )

    win, losses = get_rank_wins_losses()
    lp_per_win = estimate_lp_per_win(win, losses, level) if win and losses else None

    # title = generate_title(
    #     server=server,
    #     rank=rank,
    #     level=level,
    #     skins=skins_count,
    #     lp_per_win=lp_per_win,
    #     champions=champions_count
    # )
    # print("\nGenerated Title:")
    # print(title)

    title = generate_title_v2(
        server=server,
        rank=rank,
        level=level,
        skins=skins_count,
        skin_shards=len(skin_shard_list.splitlines()) if skin_shard_list else 0,
        lp_per_win=lp_per_win,
        champions=champions_count,
        blue_essence=blue_essence,
        orange_essence=orange_essence
    )
    print("\nGenerated Title:")
    print(title)



        
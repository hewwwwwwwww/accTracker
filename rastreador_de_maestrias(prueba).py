import requests

API_KEY = "TU_API_KEY_ACÁ"
SUMMONER_NAME = "TU_NOMBRE_DE_INVOCADOR"
REGION = "la1"  # o br1, na1, etc.

# Paso 1: Obtener datos del invocador
summoner_url = f"https://{REGION}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{SUMMONER_NAME}"
headers = {"X-Riot-Token": API_KEY}
response = requests.get(summoner_url, headers=headers)
summoner_data = response.json()
summoner_id = summoner_data["id"]

# Paso 2: Obtener maestrías
mastery_url = f"https://{REGION}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-summoner/{summoner_id}"
response = requests.get(mastery_url, headers=headers)
mastery_data = response.json()

# Paso 3: Obtener lista de campeones desde Data Dragon
champ_list_url = "https://ddragon.leagueoflegends.com/cdn/14.10.1/data/en_US/champion.json"
champ_data = requests.get(champ_list_url).json()
id_to_name = {int(data["key"]): name for name, data in champ_data["data"].items()}

# Paso 4: Guardar en archivo
with open("campeones_con_maestria.txt", "w", encoding="utf-8") as file:
    for champ in mastery_data:
        champ_id = champ["championId"]
        champ_name = id_to_name.get(champ_id, f"ID {champ_id}")
        puntos = champ["championPoints"]
        file.write(f"{champ_name} - {puntos} puntos\n")

print("✅ Archivo creado: campeones_con_maestria.txt")

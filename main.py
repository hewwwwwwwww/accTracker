import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

from clases.listing import Listing
from diccionarios.servers import SERVERS_URLS
from diccionarios.ranks import RANKS_URL
import db_manager


def server_url_by_key(server_key):
    return SERVERS_URLS.get(server_key, "")


def rank_url_by_key(rank_key):
    return RANKS_URL.get(rank_key, "")


def add_price_sorting_to_url(url):
    if "?" in url:
        return url + "&offerSortingCriterion=Price&isAscending=true"
    else:
        return url + "?offerSortingCriterion=Price&isAscending=true"


def build_url(server_key=None, rank_key=None):
    base_url = "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0"
    parts = []
    server_url = server_url_by_key(server_key)
    rank_url = rank_url_by_key(rank_key)
    if server_url:
        parts.append(server_url.split('?')[1])
    if rank_url:
        parts.append(rank_url.split('?')[1])
    if parts:
        url = base_url + "?" + "&".join(parts)
    else:
        url = base_url
    url = add_price_sorting_to_url(url)
    return url


def get_prices_eldorado(server=None, rank=None):
    print("Starting scraping...")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    edge_driver_path = 'C:/drivers/msedgedriver.exe'
    service = Service(executable_path=edge_driver_path)
    driver = webdriver.Edge(service=service, options=options)

    url = build_url(server_key=server, rank_key=rank)
    print(f"Navigating to URL: {url}")
    driver.get(url)
    # time.sleep(5)sleep comentado

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.offer-item"))
        )
    except Exception as e:
        print("Failed to load account list\n", e)
        driver.quit()
        return []

    offers = driver.find_elements(By.CSS_SELECTOR, "a.offer-item")
    print(f"Number of accounts found: {len(offers)}")

    listings = []

    for i, offer in enumerate(offers):
        try:
            print(f"\n--- Processing listing #{i+1} ---")
            title_element = offer.find_element(By.CLASS_NAME, "offer-title")
            price_element = offer.find_element(By.CLASS_NAME, "font-size-18")
            title = title_element.text
            price = price_element.text
            url = offer.get_attribute("href")

            print(f"Title found: '{title}'")
            print(f"Raw price: '{price}'")
            print(f"URL found: '{url}'")

            price_num = float(price.replace("$", "").strip())
            print(f"Converted price to float: {price_num}")

            listing = Listing(title, price_num)
            listing.url = url  # agregamos el atributo url al objeto Listing
            listings.append(listing)
        except Exception as e:
            print(f"Error extracting account: {e}")
            continue

    driver.quit()
    print(f"\nValid listings obtained: {len(listings)}")
    return listings


def filter_viable_accounts(listings, max_diff_percent):
    if len(listings) < 2:
        return listings

    viable_accounts = [listings[0], listings[1]]
    base_price = listings[0].price

    for listing in listings[2:]:
        current_diff = ((listing.price - base_price) / base_price) * 100
        if current_diff > max_diff_percent:
            print(f"\n❌ Limit of {max_diff_percent}% reached with '{listing.title}' (${listing.price})")
            break
        viable_accounts.append(listing)

    print("\n✅ Viable accounts found:")
    for account in viable_accounts:
        print(account)

    return viable_accounts


def filter_below_average(viable_accounts, below_percent):
    if not viable_accounts:
        return []

    avg_price = sum(acc.price for acc in viable_accounts) / len(viable_accounts)
    # El umbral es el precio promedio menos el porcentaje below_percent
    threshold = avg_price * (1 - below_percent / 100)

    # Filtramos las cuentas cuyo precio sea menor o igual al umbral calculado
    filtered_accounts = [acc for acc in viable_accounts if acc.price <= threshold]

    print(f"\nAverage price: ${avg_price:.2f}")
    print(f"Filtering accounts that are at least {below_percent}% cheaper than average (<= ${threshold:.2f}):")
    for acc in filtered_accounts:
        print(acc)

    return filtered_accounts


def send_discord_message(webhook_url, message):
    data = {
        "content": message
    }
    try:
        response = requests.post(webhook_url, json=data)
        if response.status_code == 204:
            print("Mensaje enviado correctamente a Discord.")
        else:
            print(f"Error enviando mensaje a Discord: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Excepción enviando mensaje a Discord: {e}")


def process_accounts(server, rank, max_diff_percent, below_percent, discord_webhook_url):
    listings = get_prices_eldorado(server=server, rank=rank)
    viable_accounts = filter_viable_accounts(listings, max_diff_percent=max_diff_percent)
    filtered_accounts = filter_below_average(viable_accounts, below_percent=below_percent)

    for account in filtered_accounts:
        if not db_manager.account_exists(account.url):
            message = (
                f"Cuenta viable para control:\n"
                f"Titulo: {account.title}\n"
                f"Precio: ${account.price}\n"
                f"Link: {account.url}"
            )
            send_discord_message(discord_webhook_url, message)
            db_manager.add_account(account.url)



if __name__ == "__main__":

    db_manager.init_db()
    
    DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1378220604058112081/F67MNaoZOF0R5Vxl6NlMmHCLUEm5fTKwBgvJkTEZjP2Lhima8IgSi96Bu_VSa4rsh4oz"

    # Defino listas de servidores y rangos para iterar
    servers = ["na", "las", "lan", "euw", "eune", "br"]
    ranks = ["iron", "bronze", "silver", "gold", "platinum", "emerald", "diamond+"]

    while True:
        # Bucle que reemplaza todas las llamadas repetidas a process_accounts
        for server in servers:
            for rank in ranks:
                # Llamada a process_accounts con cada combinación de servidor y rango
                process_accounts(server=server, rank=rank, max_diff_percent=35, below_percent=20, discord_webhook_url=DISCORD_WEBHOOK_URL)

        print("✅ Ciclo terminado. Esperando 30 minutos para el siguiente...\n")

        # Aquí podés poner el sleep que quieras, por ejemplo 30 minutos:
        # time.sleep(60 * 30)
        # Por ahora lo dejás comentado o con el valor que prefieras
        time.sleep(60 * 5)  # Esto es 6 segundos, solo para prueba

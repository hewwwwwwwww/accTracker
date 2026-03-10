import requests
import re
import statistics
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
from utilidades.monedas.conversor import convertir_ars_a_usd, obtener_cotizacion


# ---------------------------------------
# URL BUILDING
# ---------------------------------------

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

    return add_price_sorting_to_url(url)


# ---------------------------------------
# SCRAPER
# ---------------------------------------

def extract_price_from_text(text):

    match = re.search(r"ARS\s?([\d,]+\.\d+)", text)

    if match:
        return match.group(1)

    return None


def get_prices_eldorado(driver, server=None, rank=None):

    print("\nStarting scraping...")

    url = build_url(server_key=server, rank_key=rank)

    print(f"Navigating to URL: {url}")

    driver.get(url)

    try:

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "a[href*='league-of-legends-account']")
            )
        )

        time.sleep(2)

        offers = driver.find_elements(
            By.CSS_SELECTOR,
            "a[href*='league-of-legends-account']"
        )

    except Exception as e:

        print("Failed to load account list", e)

        return []

    print(f"Listings detected: {len(offers)}")

    listings = []

    cotizacion = obtener_cotizacion()

    for i, offer in enumerate(offers):

        try:

            print(f"\n--- Processing listing #{i+1} ---")

            full_text = offer.text

            print("Element text preview:")
            print(full_text[:200])

            title = full_text.split("\n")[0]

            price_text = None

            spans = offer.find_elements(By.TAG_NAME, "span")

            for s in spans:
                if "ARS" in s.text or "$" in s.text:
                    price_text = s.text
                    break

            if not price_text:

                extracted = extract_price_from_text(full_text)

                if extracted:
                    price_text = "ARS" + extracted

            if not price_text:

                print("Price not found. Skipping listing.")
                continue

            print(f"Raw price: {price_text}")

            price_clean = (
                price_text
                .replace("ARS", "")
                .replace("$", "")
                .replace(",", "")
                .strip()
            )

            price_usd = convertir_ars_a_usd(float(price_clean), cotizacion)

            link = offer.get_attribute("href")

            listing = Listing(title, price_usd)

            listing.url = link

            listings.append(listing)

        except Exception as e:

            print("Listing parse error:", e)

            continue

    print(f"\nValid listings obtained: {len(listings)}")

    return listings


# ---------------------------------------
# NUEVO: ELIMINAR DUPLICADOS
# ---------------------------------------

def remove_duplicates(listings):

    seen = set()

    unique = []

    for listing in listings:

        signature = f"{listing.title}_{listing.price}"

        if signature in seen:
            continue

        seen.add(signature)

        unique.append(listing)

    print(f"Listings after duplicate removal: {len(unique)}")

    return unique


# ---------------------------------------
# FILTROS
# ---------------------------------------

def filter_viable_accounts(listings, max_diff_percent):

    if len(listings) < 2:
        return listings

    viable_accounts = [listings[0]]

    base_price = listings[0].price

    for listing in listings[1:]:

        current_diff = ((listing.price - base_price) / base_price) * 100

        if current_diff > max_diff_percent:

            print(f"\nLimit of {max_diff_percent}% reached")

            break

        viable_accounts.append(listing)

    return viable_accounts


def filter_below_average(viable_accounts, below_percent):

    if not viable_accounts:
        return []

    avg_price = sum(acc.price for acc in viable_accounts) / len(viable_accounts)

    threshold = avg_price * (1 - below_percent / 100)

    filtered_accounts = [
        acc for acc in viable_accounts
        if acc.price <= threshold
    ]

    print(f"\nAverage price: ${avg_price:.2f}")

    return filtered_accounts


# ---------------------------------------
# NUEVO: DETECTAR SNIPES
# ---------------------------------------

def detect_snipes(listings):

    if len(listings) < 3:
        return []

    prices = [l.price for l in listings]

    avg = statistics.mean(prices)

    snipes = []

    for listing in listings:

        if listing.price <= avg * 0.7:

            print("\n🚨 SNIPER DETECTADO 🚨")
            print(listing.title, listing.price)

            snipes.append(listing)

    return snipes


# ---------------------------------------
# DISCORD
# ---------------------------------------

def send_discord_message(webhook_url, message):

    if not webhook_url or "http" not in webhook_url:
        print("Discord webhook not configured. Skipping message.")
        return

    try:

        response = requests.post(webhook_url, json={"content": message})

        if response.status_code == 204:
            print("Mensaje enviado correctamente a Discord.")
        else:
            print("Discord response:", response.status_code, response.text)

    except Exception as e:

        print("Discord error:", e)


# ---------------------------------------
# PROCESS
# ---------------------------------------

def process_accounts(driver, server, rank, max_diff_percent, below_percent, discord_webhook_url):

    listings = get_prices_eldorado(driver, server, rank)

    listings = remove_duplicates(listings)

    viable_accounts = filter_viable_accounts(listings, max_diff_percent)

    filtered_accounts = filter_below_average(viable_accounts, below_percent)

    snipes = detect_snipes(listings)

    for account in filtered_accounts + snipes:

        if not db_manager.account_exists(account.url):

            message = (
                f"Cuenta detectada:\n"
                f"Titulo: {account.title}\n"
                f"Precio: ${account.price:.2f}\n"
                f"Link: {account.url}"
            )

            send_discord_message(discord_webhook_url, message)

            db_manager.add_account(account.url)


# ---------------------------------------
# MAIN
# ---------------------------------------

if __name__ == "__main__":

    db_manager.init_db()

    DISCORD_WEBHOOK_URL = ""

    servers = ["na"]
    ranks = ["iron", "bronze", "silver"]

    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")

    edge_driver_path = 'C:/drivers/msedgedriver.exe'

    service = Service(executable_path=edge_driver_path)

    driver = webdriver.Edge(service=service, options=options)

    while True:

        for server in servers:

            for rank in ranks:

                try:

                    process_accounts(
                        driver,
                        server,
                        rank,
                        35,
                        20,
                        DISCORD_WEBHOOK_URL
                    )

                except Exception as e:

                    print(f"Error procesando {server}-{rank}: {e}")

                time.sleep(10)

        print("Ciclo terminado. Esperando 10 minutos.")

        time.sleep(600)
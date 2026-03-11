import requests
import os
from dotenv import load_dotenv
load_dotenv()
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
# HELPERS
# ---------------------------------------

def extract_sales(text):

    match = re.search(r"\(([\d,]+)\)", text)

    if match:
        return int(match.group(1).replace(",", ""))

    return 0


def extract_skins(text):

    match = re.search(r"(\d+)\s*Skins", text)

    if match:
        return int(match.group(1))

    match_range = re.search(r"(\d+)-(\d+)\s*Skins", text)

    if match_range:
        return int(match_range.group(2))

    return 0


def extract_price_from_text(text):

    match = re.search(r"ARS\s?([\d,]+\.\d+)", text)

    if match:
        return match.group(1)

    return None


# ---------------------------------------
# SCRAPER
# ---------------------------------------

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

    for offer in offers:

        try:

            full_text = offer.text

            if len(full_text.strip()) < 20:
                continue

            lines = full_text.split("\n")

            if len(lines) < 7:
                continue

            title = lines[4]
            seller = lines[5]
            rating_line = lines[6]

            sales = extract_sales(rating_line)

            skins = extract_skins(full_text)

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
                continue

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
            listing.seller = seller
            listing.sales = sales
            listing.skins = skins

            listings.append(listing)

        except Exception:
            continue

    print(f"\nValid listings obtained: {len(listings)}")

    return listings


# ---------------------------------------
# DUPLICATES
# ---------------------------------------

def remove_duplicates(listings):

    seen = set()
    unique = []

    for listing in listings:

        signature = listing.url

        if signature in seen:
            continue

        seen.add(signature)
        unique.append(listing)

    print(f"Listings after duplicate removal: {len(unique)}")

    return unique


# ---------------------------------------
# OPPORTUNITY DETECTION
# ---------------------------------------

def detect_opportunities(listings):

    if len(listings) < 3:
        return []

    prices = [l.price for l in listings]

    avg = statistics.mean(prices)

    opportunities = []

    print("\nMarket scan:")

    for listing in listings:

        print(
            f"${listing.price:.2f} | {listing.skins} skins | "
            f"{listing.seller} ({listing.sales} sales)"
        )

        reasons = []

        if listing.price < avg * 0.6:
            reasons.append("🔥 MUY BARATA")

        if listing.sales < 50:
            reasons.append("🆕 VENDEDOR NUEVO")

        if listing.sales < 500:
            reasons.append("📉 VENDEDOR PEQUEÑO")

        if listing.skins > 40 and listing.price < avg:
            reasons.append("🎁 MUCHAS SKINS BARATO")

        if reasons:

            print("OPPORTUNITY →", " | ".join(reasons))

            listing.reasons = reasons

            opportunities.append(listing)

    return opportunities


# ---------------------------------------
# DISCORD
# ---------------------------------------

def send_discord_message(webhook_url, message):

    if not webhook_url or "http" not in webhook_url:
        print("Discord webhook not configured.")
        return

    try:

        response = requests.post(webhook_url, json={"content": message})

        if response.status_code == 204:
            print("Mensaje enviado a Discord")

    except Exception as e:

        print("Discord error:", e)


# ---------------------------------------
# PROCESS
# ---------------------------------------

def process_accounts(driver, server, rank, discord_webhook_url):

    listings = get_prices_eldorado(driver, server, rank)

    listings = remove_duplicates(listings)

    opportunities = detect_opportunities(listings)

    for acc in opportunities:

        if not db_manager.account_exists(acc.url):

            reasons = " | ".join(acc.reasons)

            message = (
                f"🚨 OPORTUNIDAD DETECTADA 🚨\n\n"
                f"{reasons}\n\n"
                f"Titulo: {acc.title}\n"
                f"Seller: {acc.seller} ({acc.sales} ventas)\n"
                f"Skins: {acc.skins}\n"
                f"Precio: ${acc.price:.2f}\n"
                f"{acc.url}"
            )

            send_discord_message(discord_webhook_url, message)

            db_manager.add_account(acc.url)


# ---------------------------------------
# MAIN
# ---------------------------------------

if __name__ == "__main__":

    db_manager.init_db()

    DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

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
                        DISCORD_WEBHOOK_URL
                    )

                except Exception as e:

                    print(f"Error procesando {server}-{rank}: {e}")

                time.sleep(10)

        print("\nCiclo terminado. Esperando 10 minutos.")

        time.sleep(600)
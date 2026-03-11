import requests
import os
from dotenv import load_dotenv
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

load_dotenv()

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
        parts.append(server_url.split("?")[1])

    if rank_url:
        parts.append(rank_url.split("?")[1])

    if parts:
        url = base_url + "?" + "&".join(parts)
    else:
        url = base_url

    return add_price_sorting_to_url(url)

# ---------------------------------------
# HELPERS
# ---------------------------------------

def extract_sales(text):
    """
    Eldorado format example:
    97.1% (34)

    We only want the number inside parentheses.
    """
    match = re.search(r"\((\d+)\)", text.replace(",", ""))
    if match:
        return int(match.group(1))
    return 0


def extract_skins(text):

    match = re.search(r"(\d+)-(\d+)\s*skins?", text, re.IGNORECASE)
    if match:
        return int(match.group(2))

    match2 = re.search(r"(\d+)\s*skins?", text, re.IGNORECASE)
    if match2:
        return int(match2.group(1))

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
                print(f"[SKIP] Listing muy corto: {full_text[:30]}...")
                continue

            print("\nRAW LISTING TEXT:\n")
            print(full_text)

            lines = full_text.split("\n")

            seller = "Unknown"
            rank_name = "Unknown"
            title = "Unknown"
            sales = extract_sales(full_text)
            skins = extract_skins(full_text)

            if len(lines) >= 7:

                rank_name = lines[2]
                title = lines[4]
                seller = lines[5]

            elif len(lines) >= 5:

                title = lines[0]
                seller = lines[1]
                rank_name = lines[2]

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
                print("[SKIP] No price detected")
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
            listing.rank = rank_name

            listings.append(listing)

        except Exception as e:

            print("[ERROR PARSING LISTING]:", e)

            continue

    print(f"\nValid listings obtained: {len(listings)}")

    return listings


# ---------------------------------------
# DUPLICATE FILTER
# ---------------------------------------

def remove_duplicates(listings):

    seen = set()

    unique = []

    for listing in listings:

        if listing.url in seen:
            continue

        seen.add(listing.url)

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

        score = 0

        reasons = []

        if listing.price < avg * 0.6:
            score += 5
            reasons.append("🔥 MUY BARATA")

        if listing.sales < 50:
            score += 3
            reasons.append("🆕 VENDEDOR NUEVO")

        elif listing.sales < 500:
            score += 1
            reasons.append("📉 VENDEDOR PEQUEÑO")

        if listing.skins > 40 and listing.price < avg:
            score += 2
            reasons.append("🎁 MUCHAS SKINS BARATO")

        listing.score = score
        listing.reasons = reasons

        print(
            f"Score {score} | ${listing.price:.2f} | {listing.rank} | "
            f"{listing.skins} skins | {listing.seller} ({listing.sales})"
        )

        print(listing.url)

        if reasons:
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
                f"Rank: {acc.rank}\n"
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

    edge_driver_path = "C:/drivers/msedgedriver.exe"

    service = Service(executable_path=edge_driver_path)

    driver = webdriver.Edge(service=service, options=options)

    while True:

        for server in servers:

            for rank in ranks:

                try:

                    process_accounts(driver, server, rank, DISCORD_WEBHOOK_URL)

                except Exception as e:

                    print(f"Error procesando {server}-{rank}: {e}")

                time.sleep(10)

        print("\nCiclo terminado. Esperando 10 minutos.")

        time.sleep(600)
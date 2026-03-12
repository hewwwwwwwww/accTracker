import os
import time
import re

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utilidades.monedas.conversor import convertir_ars_a_usd, obtener_cotizacion
from diccionarios.servers import SERVERS_URLS
from diccionarios.ranks import RANKS_URL


market_lows = {}


# -----------------------------
# URL BUILDER
# -----------------------------

def build_url(server_key=None, rank_key=None):

    base_url = "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0"

    params = []

    if server_key and server_key in SERVERS_URLS:
        params.append(SERVERS_URLS[server_key].split("?")[1])

    if rank_key and rank_key in RANKS_URL:
        params.append(RANKS_URL[rank_key].split("?")[1])

    params.append("offerSortingCriterion=Price")
    params.append("isAscending=true")

    return base_url + "?" + "&".join(params)


# -----------------------------
# PRICE PARSER
# -----------------------------

def extract_price(text):

    match = re.search(r"ARS\s?([\d,]+\.\d+)", text)

    if match:
        return float(match.group(1).replace(",", ""))

    return None


# -----------------------------
# SCRAPER
# -----------------------------

def scrape_listings(driver, server, rank):

    url = build_url(server, rank)

    print(f"\nNavigating to {url}")

    driver.get(url)

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

    print("Listings detected:", len(offers))

    listings = []

    cotizacion = obtener_cotizacion()

    for offer in offers:

        try:

            text = offer.text

            if len(text) < 20:
                continue

            lines = text.split("\n")

            rank_name = "Unknown"

            if len(lines) >= 3:
                rank_name = lines[2]

            price_ars = extract_price(text)

            if not price_ars:
                continue

            price_usd = convertir_ars_a_usd(price_ars, cotizacion)

            url = offer.get_attribute("href")

            listings.append({
                "server": server.upper(),
                "rank": rank_name,
                "price": price_usd,
                "url": url
            })

        except Exception:
            continue

    return listings


# -----------------------------
# REMOVE DUPLICATES
# -----------------------------

def remove_duplicates(listings):

    seen = set()

    unique = []

    for l in listings:

        if l["url"] in seen:
            continue

        seen.add(l["url"])

        unique.append(l)

    return unique


# -----------------------------
# MARKET LOW DETECTOR
# -----------------------------

def check_market_lows(listings):

    global market_lows

    for l in listings:

        rank = l["rank"]
        price = l["price"]

        if rank not in market_lows:

            market_lows[rank] = price
            continue

        if price < market_lows[rank]:

            print("\n🔥 NEW MARKET LOW DETECTED")

            print(
                f"{l['server']} - {rank} - ${price:.2f}"
            )

            print(
                f"Previous low: ${market_lows[rank]:.2f}"
            )

            print(l["url"])

            market_lows[rank] = price


# -----------------------------
# OUTPUT
# -----------------------------

def print_listings(listings):

    for l in listings:

        print(
            f"{l['server']} - {l['rank']} - ${l['price']:.2f}"
        )

        print(l["url"])


# -----------------------------
# MAIN LOOP
# -----------------------------

if __name__ == "__main__":

    servers = ["na"]

    ranks = [
        "iron",
        "bronze",
        "silver"
    ]

    options = Options()

    options.add_argument("--disable-blink-features=AutomationControlled")

    service = Service("C:/drivers/msedgedriver.exe")

    driver = webdriver.Edge(service=service, options=options)

    while True:

        all_listings = []

        for server in servers:

            for rank in ranks:

                try:

                    listings = scrape_listings(driver, server, rank)

                    all_listings.extend(listings)

                except Exception as e:

                    print("Error:", e)

                time.sleep(5)

        all_listings = remove_duplicates(all_listings)

        print("\nListings found:", len(all_listings))

        check_market_lows(all_listings)

        print_listings(all_listings)

        print("\nCycle finished. Waiting 10 minutes.")

        time.sleep(600)
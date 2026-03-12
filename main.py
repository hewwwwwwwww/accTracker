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

    patterns = [
        r"ARS\s?([\d,]+\.\d+)",
        r"USD\s?([\d,]+\.\d+)",
        r"US\$\s?([\d,]+\.\d+)",
        r"\$([\d,]+\.\d+)"
    ]

    for p in patterns:

        match = re.search(p, text)

        if match:
            return float(match.group(1).replace(",", "")), p

    return None, None


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

            price, pattern = extract_price(text)

            if not price:
                continue

            if pattern.startswith("ARS"):
                price_usd = convertir_ars_a_usd(price, cotizacion)
            else:
                price_usd = price

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
# GROUP BY RANK
# -----------------------------

def group_by_rank(listings):

    grouped = {}

    for l in listings:

        rank = l["rank"]

        if rank not in grouped:
            grouped[rank] = []

        grouped[rank].append(l)

    return grouped


# -----------------------------
# MARKET ANALYSIS
# -----------------------------

def analyze_market(rank, listings):

    if not listings:
        return

    listings = sorted(listings, key=lambda x: x["price"])

    scanned = []
    prices = []

    for l in listings:

        price = l["price"]

        if prices:

            avg = sum(prices) / len(prices)

            if price > avg * 1.45:
                print("\nMarket range exceeded. Stopping scan.")
                break

        scanned.append(l)
        prices.append(price)

    if not scanned:
        return

    avg_price = sum(prices) / len(prices)

    print(f"\n--- MARKET DEBUG ({rank}) ---")

    for l in scanned:

        print(
            f"{l['server']} | {rank} | ${l['price']:.2f}"
        )

        print(l["url"])

    print("\nAverage price:", round(avg_price, 2))

    first = scanned[0]

    if first["price"] < avg_price * 0.55:

        print("\n🚨 OPPORTUNITY DETECTED")

        print(
            f"{first['server']} | {rank} | ${first['price']:.2f}"
        )

        print("Market average:", round(avg_price, 2))

        print(first["url"])


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

        grouped = group_by_rank(all_listings)

        for rank, listings in grouped.items():

            analyze_market(rank, listings)

        print("\nCycle finished. Waiting 10 minutes.")

        time.sleep(600)
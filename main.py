import time
import re

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utilidades.monedas.conversor import convertir_ars_a_usd, obtener_cotizacion


# -----------------------------
# TARGET URLS
# -----------------------------

TARGET_URLS = {

    # -------- LAN --------

    ("LAN", "unranked"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=unranked&sortBy=price&sortOrder=asc",

    ("LAN", "iron"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=iron&sortBy=price&sortOrder=asc",

    ("LAN", "bronze"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=bronze&sortBy=price&sortOrder=asc",

    ("LAN", "silver"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=silver&sortBy=price&sortOrder=asc",

    ("LAN", "gold"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=gold&sortBy=price&sortOrder=asc",

    ("LAN", "platinum"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=platinum&sortBy=price&sortOrder=asc",

    ("LAN", "diamond"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=diamond&sortBy=price&sortOrder=asc",

    ("LAN", "emerald"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=emerald&sortBy=price&sortOrder=asc",


    # -------- LAS --------

    ("LAS", "unranked"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20South&lol-current-rank=unranked&sortBy=price&sortOrder=asc",

    ("LAS", "iron"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20South&lol-current-rank=iron&sortBy=price&sortOrder=asc",

    ("LAS", "bronze"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20South&lol-current-rank=bronze&sortBy=price&sortOrder=asc",

    ("LAS", "silver"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20South&lol-current-rank=silver&sortBy=price&sortOrder=asc",

    ("LAS", "gold"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20South&lol-current-rank=gold&sortBy=price&sortOrder=asc",

    ("LAS", "platinum"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20South&lol-current-rank=platinum&sortBy=price&sortOrder=asc",

    ("LAS", "diamond"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20South&lol-current-rank=diamond&sortBy=price&sortOrder=asc",

    ("LAS", "emerald"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20South&lol-current-rank=emerald&sortBy=price&sortOrder=asc"
}


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

def scrape_listings(driver, server, rank, url):

    print(f"\nNavigating to {server} | {rank.upper()} market")
    print(url)

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

            price, pattern = extract_price(text)

            if not price:
                continue

            if pattern.startswith("ARS"):
                price_usd = convertir_ars_a_usd(price, cotizacion)
            else:
                price_usd = price

            listing_url = offer.get_attribute("href")

            listings.append({
                "server": server,
                "rank": rank,
                "price": price_usd,
                "url": listing_url
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
# MARKET ANALYSIS
# -----------------------------

def analyze_market(server, rank, listings):

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

    print(f"\n--- MARKET DEBUG ({server} {rank.upper()}) ---")

    for l in scanned:

        print(f"{server} | {rank} | ${l['price']:.2f}")
        print(l["url"])

    print("\nAverage price:", round(avg_price, 2))

    first = scanned[0]

    if first["price"] < avg_price * 0.55:

        print("\n🚨 OPPORTUNITY DETECTED")

        print(f"{server} | {rank} | ${first['price']:.2f}")
        print("Market average:", round(avg_price, 2))
        print(first["url"])


# -----------------------------
# MAIN LOOP
# -----------------------------

if __name__ == "__main__":

    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")

    service = Service("C:/drivers/msedgedriver.exe")

    driver = webdriver.Edge(service=service, options=options)

    while True:

        for (server, rank), url in TARGET_URLS.items():

            try:

                listings = scrape_listings(driver, server, rank, url)

                listings = remove_duplicates(listings)

                analyze_market(server, rank, listings)

            except Exception as e:

                print("Error:", e)

            time.sleep(5)

        print("\nCycle finished. Waiting 10 minutes.")

        time.sleep(600)
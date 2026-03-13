import time
import re
import json
import os

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utilidades.monedas.conversor import convertir_ars_a_usd, obtener_cotizacion


DB_FILE = "seen_listings.json"

MIN_SCORE = 35
ALERT_COOLDOWN = 86400


def load_seen_listings():

    if not os.path.exists(DB_FILE):
        return {}

    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_seen_listings():

    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(seen_listings, f, indent=2)
    except Exception as e:
        print("DB save error:", e)


seen_listings = load_seen_listings()


TARGET_URLS = {

("LAN","unranked"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=unranked&sortBy=price&sortOrder=asc",
("LAN","iron"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=iron&sortBy=price&sortOrder=asc",
("LAN","bronze"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=bronze&sortBy=price&sortOrder=asc",
("LAN","silver"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=silver&sortBy=price&sortOrder=asc",
("LAN","gold"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=gold&sortBy=price&sortOrder=asc",
("LAN","platinum"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=platinum&sortBy=price&sortOrder=asc",
("LAN","diamond"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=diamond&sortBy=price&sortOrder=asc",
("LAN","emerald"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=emerald&sortBy=price&sortOrder=asc",

("LAS","unranked"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20South&lol-current-rank=unranked&sortBy=price&sortOrder=asc",
("LAS","iron"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20South&lol-current-rank=iron&sortBy=price&sortOrder=asc",
("LAS","bronze"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20South&lol-current-rank=bronze&sortBy=price&sortOrder=asc",
("LAS","silver"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20South&lol-current-rank=silver&sortBy=price&sortOrder=asc",
("LAS","gold"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20South&lol-current-rank=gold&sortBy=price&sortOrder=asc",
("LAS","platinum"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20South&lol-current-rank=platinum&sortBy=price&sortOrder=asc",
("LAS","diamond"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20South&lol-current-rank=diamond&sortBy=price&sortOrder=asc",
("LAS","emerald"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20South&lol-current-rank=emerald&sortBy=price&sortOrder=asc"
}


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


def scrape_listings(driver, server, rank, url):

    print(f"\nNavigating to {server} | {rank.upper()} market")

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
                price = convertir_ars_a_usd(price, cotizacion)

            listings.append({
                "server": server,
                "rank": rank,
                "price": price,
                "url": offer.get_attribute("href")
            })

        except:
            continue

    return listings


def analyze_market(server, rank, listings):

    listings = sorted(listings, key=lambda x: x["price"])

    prices = []

    for l in listings:

        price = l["price"]

        if prices:

            avg = sum(prices) / len(prices)

            if price > avg * 1.45:
                break

        prices.append(price)

    if not prices:
        return

    avg_price = sum(prices) / len(prices)

    cheapest = listings[0]

    cheapest_score = (1 - cheapest["price"] / avg_price) * 100

    print("\nBest price in market:")
    print(f"{server} | {rank}")
    print(f"${cheapest['price']:.2f}")
    print("Score:", round(cheapest_score,2), "%")

    if cheapest_score < MIN_SCORE:
        diff = MIN_SCORE - cheapest_score
        print("Missing for opportunity:", round(diff,2), "%")
        print("URL:", cheapest["url"])

    for listing in listings[:5]:

        price = listing["price"]

        score = (1 - price / avg_price) * 100

        url = listing["url"]

        if url not in seen_listings:
            seen_listings[url] = 0

        now = time.time()
        last_alert = seen_listings[url]

        if score >= MIN_SCORE and (now - last_alert) > ALERT_COOLDOWN:

            print("\n🚀 SNIPING OPPORTUNITY")
            print(f"{server} | {rank} | ${price:.2f}")
            print("Score:", round(score,2), "% below market")
            print(url)

            seen_listings[url] = now
            save_seen_listings()


if __name__ == "__main__":

    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--log-level=3")

    service = Service("C:/drivers/msedgedriver.exe")

    driver = webdriver.Edge(service=service, options=options)

    print("Loaded listings in DB:", len(seen_listings))

    while True:

        for (server, rank), url in TARGET_URLS.items():

            try:

                listings = scrape_listings(driver, server, rank, url)

                analyze_market(server, rank, listings)

            except Exception as e:

                print("Error:", e)

            time.sleep(4)

        print("\nCycle finished. Waiting 60 seconds.")

        time.sleep(60)
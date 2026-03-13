import time
import re
import json
import os
import requests
from statistics import median
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utilidades.monedas.conversor import convertir_ars_a_usd, obtener_cotizacion

load_dotenv()

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")

DB_FILE = "seen_listings.json"
MIN_SCORE = 35
ALERT_COOLDOWN = 86400
CYCLE_WAIT = 30
BUDABOOST_NAME = "Budaboost"

MARKET_SAMPLE_SIZE = 10

DEBUG = True


def send_discord_alert(server, rank, price, score, url, note=""):

    if not DISCORD_WEBHOOK:
        print("⚠️ Discord webhook not configured")
        return

    try:

        message = {
            "content": f"""🚀 **SNIPING OPPORTUNITY**
Server: {server}
Rank: {rank}
Price: ${price:.2f}
Score: {score:.2f}% below market
{note}
{url}"""
        }

        print("📤 Sending Discord alert...")
        requests.post(DISCORD_WEBHOOK, json=message, timeout=10)

    except Exception as e:
        print("Discord notification error:", e)


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


def dynamic_market_filter(prices):

    """
    Construye el mercado usando media incremental
    y corta cuando aparece un precio > 200% de la media
    """

    market = []
    running_sum = 0

    for price in prices:

        if not market:
            market.append(price)
            running_sum += price
            continue

        mean = running_sum / len(market)

        if price > mean * 2:
            if DEBUG:
                print(f"⚠️ Dynamic cutoff triggered at ${price:.2f}")
            break

        market.append(price)
        running_sum += price

    return market


def trim_outliers(prices):

    """
    Elimina extremos (primer y último elemento)
    si hay suficientes datos
    """

    if len(prices) <= 3:
        return prices

    return prices[1:-1]


TARGET_URLS = {
    # LAN URLs
    ("LAN","unranked"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=unranked&sortBy=price&sortOrder=asc",
    ("LAN","iron"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=iron&sortBy=price&sortOrder=asc",
    ("LAN","bronze"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=bronze&sortBy=price&sortOrder=asc",
    ("LAN","silver"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=silver&sortBy=price&sortOrder=asc",
    ("LAN","gold"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=gold&sortBy=price&sortOrder=asc",
    ("LAN","platinum"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=platinum&sortBy=price&sortOrder=asc",
    ("LAN","diamond"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=diamond&sortBy=price&sortOrder=asc",
    ("LAN","emerald"): "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0?pageSize=24&te_v0=Latin%20America%20North&lol-current-rank=emerald&sortBy=price&sortOrder=asc",
    # LAS URLs
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
            value = float(match.group(1).replace(",", ""))
            return value, p

    return None, None


def scrape_listings(driver, server, rank, url):

    print("\n==============================")
    print(f"🔎 Navigating to {server} | {rank.upper()} market")
    print("==============================")

    driver.get(url)

    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "a[href*='league-of-legends-account']")
        )
    )

    time.sleep(2)

    offers = driver.find_elements(By.CSS_SELECTOR, "a[href*='league-of-legends-account']")
    print("Listings detected:", len(offers))

    listings = []

    cotizacion = obtener_cotizacion()
    print("💱 Current ARS/USD rate:", cotizacion)

    for i, offer in enumerate(offers, start=1):

        try:

            text = offer.text

            price, pattern = extract_price(text)

            if not price:
                continue

            if pattern.startswith("ARS"):
                price = convertir_ars_a_usd(price, cotizacion)

            if DEBUG:
                print(f"Listing #{i} | ${price:.2f}")

            note = ""

            if BUDABOOST_NAME.lower() in text.lower():
                note = "💡 Esta oferta pertenece a Budaboost"

            url = offer.get_attribute("href")

            listings.append({
                "server": server,
                "rank": rank,
                "price": price,
                "url": url,
                "note": note
            })

        except Exception as e:
            print("Error processing offer:", e)

    return listings


def analyze_market(server, rank, listings):

    print("\n📊 MARKET ANALYSIS")
    print(f"{server} | {rank}")

    if not listings:
        print("No valid listings")
        return

    market_sample = listings[:MARKET_SAMPLE_SIZE]
    prices = [l["price"] for l in market_sample]

    print("\nInitial market sample:")
    for p in prices:
        print("-", round(p,2))

    dynamic_market = dynamic_market_filter(prices)

    print("\nAfter dynamic cutoff:")
    for p in dynamic_market:
        print("-", round(p,2))

    trimmed_market = trim_outliers(dynamic_market)

    print("\nAfter outlier trimming:")
    for p in trimmed_market:
        print("-", round(p,2))

    if not trimmed_market:
        print("Not enough data after filtering")
        return

    median_price = median(trimmed_market)

    print("\nFinal median market price:", round(median_price,2))

    best_listing = min(market_sample, key=lambda x: x["price"])

    price = best_listing["price"]
    url = best_listing["url"]
    note = best_listing["note"]

    score = (1 - price / median_price) * 100
    remaining = max(0, MIN_SCORE - score)

    now = time.time()

    last_alert = seen_listings.get(url, 0)

    is_opportunity = score >= MIN_SCORE
    on_cooldown = (now - last_alert) <= ALERT_COOLDOWN

    status = ""

    if is_opportunity:
        status = "OPPORTUNITY (cooldown)" if on_cooldown else "OPPORTUNITY"

    print("\nFINAL RESULT")
    print(f"{server} | {rank} | ${price:.2f} | {round(score,2)}% | Remaining: {round(remaining,2)}% | {status}")

    if is_opportunity and not on_cooldown and BUDABOOST_NAME.lower() not in note.lower():

        print("✅ Sending alert")

        send_discord_alert(server, rank, price, score, url, note)

        seen_listings[url] = now
        save_seen_listings()

    else:

        print("🚫 Alert not sent")


if __name__ == "__main__":

    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--log-level=3")

    service = Service("C:/drivers/msedgedriver.exe")

    driver = webdriver.Edge(service=service, options=options)

    print("Loaded listings in DB:", len(seen_listings))

    try:

        while True:

            for (server, rank), url in TARGET_URLS.items():

                try:

                    listings = scrape_listings(driver, server, rank, url)
                    analyze_market(server, rank, listings)

                except Exception as e:
                    print("Error:", e)

                time.sleep(4)

            print(f"\nCycle finished. Waiting {CYCLE_WAIT} seconds.")

            time.sleep(CYCLE_WAIT)

    except KeyboardInterrupt:
        print("Exiting...")
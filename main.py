from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

from clases.listing import Publicacion
from diccionarios.servers import SERVERS_URLS
from diccionarios.ranks import RANKS_URL


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
    time.sleep(5)

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

            print(f"Title found: '{title}'")
            print(f"Raw price: '{price}'")

            price_num = float(price.replace("$", "").strip())
            print(f"Converted price to float: {price_num}")

            listing = Listing(title, price_num)
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


if __name__ == "__main__":
    listings = get_prices_eldorado(server="na", rank="emerald")
    viable_accounts = filter_viable_accounts(listings, max_diff_percent=35)

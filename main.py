from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

from diccionarios.servers import SERVERS_URLS
from diccionarios.ranks import RANKS_URL
from clases.publicacion import Publicacion  # Importamos la clase

def url_por_servidor(servidor_key):
    return SERVERS_URLS.get(servidor_key, "")

def url_por_rango(rango_key):
    return RANKS_URL.get(rango_key, "")

def agregar_orden_precio(url):
    if "?" in url:
        return url + "&offerSortingCriterion=Price&isAscending=true"
    else:
        return url + "?offerSortingCriterion=Price&isAscending=true"

def armar_url(servidor_key=None, rango_key=None):
    url_base = "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0"
    partes = []
    servidor_url = url_por_servidor(servidor_key)
    rango_url = url_por_rango(rango_key)
    if servidor_url:
        partes.append(servidor_url.split('?')[1])
    if rango_url:
        partes.append(rango_url.split('?')[1])
    if partes:
        url = url_base + "?" + "&".join(partes)
    else:
        url = url_base
    url = agregar_orden_precio(url)
    return url

def obtain_prices_eldorado_sel(servidor=None, rango=None):
    print("Iniciando scraping...")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    edge_driver_path = 'C:/drivers/msedgedriver.exe'
    service = Service(executable_path=edge_driver_path)
    driver = webdriver.Edge(service=service, options=options)

    url = armar_url(servidor_key=servidor, rango_key=rango)
    print(f"Navegando a URL: {url}")
    driver.get(url)
    time.sleep(5)

    with open("debug_output.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)

    time.sleep(10)

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.offer-item"))
        )
    except Exception as e:
        print("No se pudo cargar la lista de cuentas\n", e)
        driver.quit()
        return []

    offers = driver.find_elements(By.CSS_SELECTOR, "a.offer-item")
    print(f"Cantidad de cuentas encontradas: {len(offers)}")

    publicaciones = []

    for i, offer in enumerate(offers, start=1):
        try:
            print(f"\n--- Procesando publicación #{i} ---")
            title_element = offer.find_element(By.CLASS_NAME, "offer-title")
            price_element = offer.find_element(By.CLASS_NAME, "font-size-18")
            title = title_element.text
            price = price_element.text
            print(f"Título encontrado: '{title}'")
            print(f"Precio raw: '{price}'")

            price_num = float(price.replace("$", "").strip())
            print(f"Precio convertido a número: {price_num}")

            publicacion = Publicacion(title=title, precio=price_num)
            publicaciones.append(publicacion)

        except Exception as e:
            print(f"⚠️ Error extrayendo cuenta: {e}")
            continue

    driver.quit()
    print(f"\nPublicaciones válidas obtenidas: {len(publicaciones)}")
    return publicaciones

if __name__ == "__main__":
    cuentas = obtain_prices_eldorado_sel(servidor="na", rango="emerald")
    print(f"Publicaciones obtenidas: {len(cuentas)}")
    for p in cuentas:
        print(p)

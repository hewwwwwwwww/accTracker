from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

from servers import SERVERS_URLS
from ranks import RANKS_URL  # asumo que haces otro archivo con los rangos

def url_por_servidor(servidor_key):
    """Devuelve el fragmento de URL para el servidor"""
    return SERVERS_URLS.get(servidor_key, "")

def url_por_rango(rango_key):
    """Devuelve el fragmento de URL para el rango"""
    return RANKS_URLS.get(rango_key, "")

def agregar_orden_precio(url):
    """Agrega el ordenamiento de precio ascendente a la URL"""
    if "?" in url:
        return url + "&offerSortingCriterion=Price&isAscending=true"
    else:
        return url + "?offerSortingCriterion=Price&isAscending=true"

def armar_url(servidor_key=None, rango_key=None):
    """Arma la URL completa combinando servidor, rango y ordenamiento"""
    url_base = "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0"
    
    partes = []
    servidor_url = url_por_servidor(servidor_key)
    rango_url = url_por_rango(rango_key)
    
    # Extraemos parámetros si existen
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


def obtain_prices_eldorado_sel(price_max, servidor=None, rango=None):
    print("estoy escribiendo en el repositorio?")
    print("que significa repositorio ? nunca lei la definicion")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    edge_driver_path = 'C:/drivers/msedgedriver.exe'  # Ajusta esta ruta si usas otra
    service = Service(executable_path=edge_driver_path)
    driver = webdriver.Edge(service=service, options=options)

    url = armar_url(servidor_key=servidor, rango_key=rango)
    print(f"Navegando a URL: {url}")
    driver.get(url)
    time.sleep(5)

    print(driver.page_source)
    with open("debug_output.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)

    time.sleep(10)

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.offer-item"))
        )
    except Exception as e:
        print("No se pudo cargar la lista de cuentas\n")
        driver.quit()
        return

    offers = driver.find_elements(By.CSS_SELECTOR, "a.offer-item")
    print(f"Cantidad de cuentas encontradas: {len(offers)}")

    for offer in offers:
        try:
            title = offer.find_element(By.CLASS_NAME, "offer-title").text
            price = offer.find_element(By.CLASS_NAME, "font-size-18").text
            price_num = float(price.replace("$", "").strip())

            if price_num <= price_max:
                print(f"Titulo: {title}")
                print(f"Precio: {price}")
                print("-" * 40)
        except Exception as e:
            print("No se pudo extraer una cuenta")
            continue

    driver.quit()


if __name__ == "__main__":
    # Ejemplo: buscar en Latinoamerica Sur, rango silver y precio máximo 5
    obtain_prices_eldorado_sel(5, servidor="las", rango="silver")

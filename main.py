from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

from diccionarios import SERVERS_URLS
from diccionarios import RANKS_URL  # asumo que haces otro archivo con los rangos

def url_por_servidor(servidor_key):
    """Devuelve el fragmento de URL para el servidor"""
    return SERVERS_URLS.get(servidor_key, "")

def url_por_rango(rango_key):
    """Devuelve el fragmento de URL para el rango"""
    return RANKS_URL.get(rango_key, "")

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

    # Guardamos el código fuente en archivo para debug pero no imprimimos en consola
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
        return

    offers = driver.find_elements(By.CSS_SELECTOR, "a.offer-item")
    print(f"Cantidad de cuentas encontradas: {len(offers)}")

    for offer in offers:
     try:
        title_element = offer.find_element(By.CLASS_NAME, "offer-title")
        price_element = offer.find_element(By.CLASS_NAME, "font-size-18")
        title = title_element.text
        price = price_element.text
        print(f"DEBUG: Encontrado título '{title}', precio raw '{price}'")
        
        # Intentamos convertir a float:
        price_num = float(price.replace("$", "").strip())
        print(f"DEBUG: Precio numérico: {price_num}")
        
        if price_num <= price_max:
            print(f"Titulo: {title}")
            print(f"Precio: {price}")
            print("-" * 40)
        else:
            print(f"DEBUG: Precio {price_num} mayor que límite {price_max}")
            
     except Exception as e:
          print(f"Error extrayendo cuenta: {e}")
          continue


    driver.quit()


if __name__ == "__main__":
    # Ejemplo: buscar en NA, rango emerald y precio máximo 5
    obtain_prices_eldorado_sel(5, servidor="na", rango="emerald")


from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time



def obtain_prices_eldorado_sel(price_max):   
#url de la pagina
 
     print("aaaaurita")
     print("prueba de github")
     print("estoy escribiendo en el repositorio?")
     print("que significa repositorio ? nunca lei la definicion")
     options = webdriver.ChromeOptions()
     options.add_argument("--headless")
     options.add_argument("--disable-gpu")
     options.add_argument("--window-size=1920,1080")
     
     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
     
     url = "https://www.eldorado.gg/league-of-legends-accounts-for-sale/a/17-1-0"
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
    obtain_prices_eldorado_sel(5)



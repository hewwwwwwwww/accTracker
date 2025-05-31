from selenium import webdriver
from selenium.webdriver.edge.service import Service

# Ruta donde está msedgedriver.exe
edge_driver_path = 'C:/drivers/msedgedriver.exe'

# Configuramos el servicio con el driver
service = Service(executable_path=edge_driver_path)

# Creamos la instancia de Edge con ese servicio
driver = webdriver.Edge(service=service)

# Abrimos Google y mostramos el título de la página
driver.get('https://www.google.com')
print(driver.title)

# Cerramos el navegador
driver.quit()

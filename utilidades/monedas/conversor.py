import requests

def convertir_ars_a_usd(monto_ars, cotizacion):
    """
    Convierte un monto en ARS a USD usando la cotización proporcionada.
    Args:
        monto_ars (float): Monto en ARS a convertir.
        cotizacion (float): Cotización del dólar (ARS por USD).
    Returns:
        float: Monto convertido en USD.
    """
    if cotizacion <= 0:
        raise ValueError("La cotización debe ser mayor que cero.")
    monto_usd = monto_ars / cotizacion
    return round(monto_usd, 2)

def obtener_cotizacion(tipo="blue"):
    """
    Consulta la cotización del dólar (por defecto 'blue') y devuelve el valor de venta.
    """
    url = "https://api.bluelytics.com.ar/v2/latest"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        cotizacion = data.get(tipo, {}).get("value_sell")
        if cotizacion is None:
            raise ValueError(f"No se encontró la cotización '{tipo}' en la respuesta.")
        return cotizacion
    except Exception as err:
        print("Error al consultar la API:", err)
        return None

def mostrar_cotizaciones():
    """
    Muestra por consola las cotizaciones oficiales y blue.
    """
    url = "https://api.bluelytics.com.ar/v2/latest"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        print("Cotizaciones del dólar (ARS):")
        for tipo in ["oficial", "blue"]:
            info = data.get(tipo, {})
            nombre = info.get("nombre", tipo)
            venta = info.get("value_sell")
            compra = info.get("value_buy")
            promedio = info.get("value_avg")
            print(f"- {nombre}: Compra = {compra}, Venta = {venta}, Promedio = {promedio}")
    except Exception as err:
        print("Error al consultar la API:", err)


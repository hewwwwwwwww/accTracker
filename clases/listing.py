class Listing:
    def __init__(self, title, price):
        self.title = title
        self.price = price

    def __repr__(self):
        return f"Listing(title='{self.title}', price={self.price})"


def filter_below_average(viable_accounts, below_percent):
    """
    Filtra las cuentas cuyo precio es al menos below_percent % menor que el precio promedio.

    :param viable_accounts: lista de objetos Listing con atributo price
    :param below_percent: porcentaje para definir el umbral de precio mínimo, por ejemplo 20 significa 20% más barato que el promedio
    :return: lista de cuentas filtradas
    """
    if not viable_accounts:
        return []

    avg_price = sum(acc.price for acc in viable_accounts) / len(viable_accounts)
    # El umbral es el precio promedio menos el porcentaje below_percent
    threshold = avg_price * (1 - below_percent / 100)

    # Filtramos las cuentas cuyo precio sea menor o igual al umbral calculado
    filtered_accounts = [acc for acc in viable_accounts if acc.price <= threshold]

    print(f"\nAverage price: ${avg_price:.2f}")
    print(f"Filtering accounts that are at least {below_percent}% cheaper than average (<= ${threshold:.2f}):")
    for acc in filtered_accounts:
        print(acc)

    return filtered_accounts


# Ejemplo de cuentas dummy para testear función
dummy_accounts = [
    Listing("Cuenta 1", 100),
    Listing("Cuenta 2", 150),
    Listing("Cuenta 3", 200),
    Listing("Cuenta 4", 250),
    Listing("Cuenta 5", 300)
]

print("Ejemplo con filtro del 20%:")
filtered_20 = filter_below_average(dummy_accounts, below_percent=20)

print("\nEjemplo con filtro del 30%:")
filtered_30 = filter_below_average(dummy_accounts, below_percent=30)

print("\nEjemplo con filtro del 10%:")
filtered_10 = filter_below_average(dummy_accounts, below_percent=10)



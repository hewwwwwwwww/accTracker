# publicacion.py

class Listing:
    def __init__(self, title, price):
        self.title = title
        self.price = price

    def __repr__(self):
        return f"Listing(title='{self.title}', price={self.price})"

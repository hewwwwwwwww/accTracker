# publicacion.py

class Publicacion:
    def __init__(self, title, price):
        self.title = title
        self.price = price

    def __repr__(self):
        return f"Publicacion(title='{self.title}', price={self.price})"

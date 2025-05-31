# publicacion.py

class Publicacion:
    def __init__(self, titulo, precio):
        self.titulo = titulo
        self.precio = precio

    def __repr__(self):
        return f"Publicacion(titulo='{self.titulo}', precio={self.precio})"

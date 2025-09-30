from . import db

class Cliente(db.Model):
    __tablename__ = "clientes"

    id_cliente = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    direccion = db.Column(db.String(200))
    telefono = db.Column(db.String(50))
    email = db.Column(db.String(120))
    esActivo = db.Column(db.Boolean, default=True)
    facturas = db.relationship("Factura", back_populates="cliente")

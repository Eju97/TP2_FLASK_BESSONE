from . import db
from datetime import datetime

class Factura(db.Model):
    __tablename__ = "facturas"

    id_factura = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey("clientes.id_cliente"), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    total = db.Column(db.Float, default=0.0)
    observaciones = db.Column(db.Text, nullable=True)
    cliente = db.relationship("Cliente", back_populates="facturas")
    detalles = db.relationship("DetalleFactura", backref="factura", lazy=True)
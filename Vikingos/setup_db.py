from flask import Flask
from flask_login import  UserMixin
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/gestion_ventas'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------- TABLAS ---------------- #

class Rol(db.Model):
    __tablename__ = 'rol'
    id_rol = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_rol = db.Column(db.String(255), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    estado = db.Column(db.String(20), default='activo')
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    usuarios = db.relationship('Usuario', back_populates='rol')
    permisos = db.relationship('RolPermiso', back_populates='rol')


class Permiso(db.Model):
    __tablename__ = 'permiso'
    id_permiso = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_permiso = db.Column(db.String(255), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    estado = db.Column(db.String(20), default='activo')
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    roles = db.relationship('RolPermiso', back_populates='permiso')


class RolPermiso(db.Model):
    __tablename__ = 'rol_permiso'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_rol = db.Column(db.Integer, db.ForeignKey('rol.id_rol'))
    id_permiso = db.Column(db.Integer, db.ForeignKey('permiso.id_permiso'))
    estado = db.Column(db.String(20), default='activo')
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    rol = db.relationship('Rol', back_populates='permisos')
    permiso = db.relationship('Permiso', back_populates='roles')


class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuario'
    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    correo = db.Column(db.String(255), unique=True, nullable=False)
    contrasena = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(20), default='activo')
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    id_rol = db.Column(db.Integer, db.ForeignKey('rol.id_rol'))

    rol = db.relationship('Rol', back_populates='usuarios')
    ventas = db.relationship('Venta', back_populates='usuario')

    @property
    def id(self):
        return self.id_usuario

class Cliente(db.Model):
    __tablename__ = 'cliente'
    id_cliente = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cedula = db.Column(db.String(20), unique=True, nullable=False)
    nombre_completo = db.Column(db.String(255), nullable=False)
    correo = db.Column(db.String(255), unique=True, nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    estado = db.Column(db.String(20), default='activo')
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    ventas = db.relationship('Venta', back_populates='cliente')
    historial = db.relationship('HistorialCliente', back_populates='cliente')


class Producto(db.Model):
    __tablename__ = 'producto'
    id_producto = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    fecha_ingreso = db.Column(db.Date)
    estado = db.Column(db.String(20), default='activo')
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    detalles_venta = db.relationship('DetalleVenta', back_populates='producto')


class Venta(db.Model):
    __tablename__ = 'venta'
    id_venta = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cedula = db.Column(db.String(20), db.ForeignKey('cliente.cedula'))
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'))
    total = db.Column(db.Float)
    total_con_descuento = db.Column(db.Float)
    estado = db.Column(db.String(20), default='activo')
    fecha_venta = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    cliente = db.relationship('Cliente', back_populates='ventas')
    usuario = db.relationship('Usuario', back_populates='ventas')
    detalles = db.relationship('DetalleVenta', back_populates='venta')
    pagos = db.relationship('Pago', back_populates='venta')
    factura = db.relationship('Factura', back_populates='venta', uselist=False)
    historial = db.relationship('HistorialCliente', back_populates='venta')


class DetalleVenta(db.Model):
    __tablename__ = 'detalle_venta'
    id_detalle = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_venta = db.Column(db.Integer, db.ForeignKey('venta.id_venta'))
    id_producto = db.Column(db.Integer, db.ForeignKey('producto.id_producto'))
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    descuento_porcentaje = db.Column(db.Float, default=0.00)
    subtotal = db.Column(db.Float)
    estado = db.Column(db.String(20), default='activo')
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    venta = db.relationship('Venta', back_populates='detalles')
    producto = db.relationship('Producto', back_populates='detalles_venta')


class Pago(db.Model):
    __tablename__ = 'pago'
    id_pago = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_venta = db.Column(db.Integer, db.ForeignKey('venta.id_venta'))
    metodo_pago = db.Column(db.String(50), nullable=False)
    estado = db.Column(db.String(20), default='activo')
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    venta = db.relationship('Venta', back_populates='pagos')


class Factura(db.Model):
    __tablename__ = 'factura'
    id_factura = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_venta = db.Column(db.Integer, db.ForeignKey('venta.id_venta'))
    numero_factura = db.Column(db.String(50), unique=True)
    archivo_pdf = db.Column(db.String(255))
    fecha_emision = db.Column(db.Date, default=datetime.utcnow)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    venta = db.relationship('Venta', back_populates='factura')


class HistorialCliente(db.Model):
    __tablename__ = 'historial_cliente'
    id_historial = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cedula = db.Column(db.String(20), db.ForeignKey('cliente.cedula'))
    id_venta = db.Column(db.Integer, db.ForeignKey('venta.id_venta'))
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    cliente = db.relationship('Cliente', back_populates='historial')
    venta = db.relationship('Venta', back_populates='historial')

# ---------------- EJECUTAR CREACIÓN ---------------- #

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("✅ Tablas creadas correctamente en MySQL")

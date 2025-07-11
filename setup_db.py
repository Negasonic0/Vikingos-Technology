from flask import Flask
from flask_login import  UserMixin
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from werkzeug.security import  generate_password_hash

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://avnadmin:AVNS_oRi9rK7mgp8Ar0zG6kc@gestion-ventas-cristiandacalop-2298.e.aivencloud.com:11514/defaultdb'
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


class Producto(db.Model):
    __tablename__ = 'producto'
    id_producto = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(255), nullable=False)
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

class Contactanos(db.Model):
    __tablename__ = 'contactanos'
    id_contactanos = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(50), nullable=False)
    correo = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    asunto = db.Column(db.String(255), nullable=False)
    mensaje = db.Column(db.String(10000), nullable=False)
    

def registros():
    if Rol.query.first():
        print ("los registros ya fueron insertados bro :P")
        return
    try:
        # Roles
        rol_admin = Rol(nombre_rol='Administrador', descripcion='Administra el sistema')
        rol_vendedor = Rol(nombre_rol='Vendedor', descripcion='Gestiona las ventas')
        db.session.add_all([rol_admin, rol_vendedor])

        # Permisos
        permiso_prod = Permiso(nombre_permiso='Gestionar productos', descripcion='Permite crear, editar y eliminar productos')
        permiso_ventas = Permiso(nombre_permiso='Gestionar ventas', descripcion='Permite registrar ventas y ver historial')
        db.session.add_all([permiso_prod, permiso_ventas])

        db.session.flush()  # guarda temporalmente para obtener los IDs

        # RolPermiso (relaciones)
        db.session.add_all([
            RolPermiso(id_rol=rol_admin.id_rol, id_permiso=permiso_prod.id_permiso),
            RolPermiso(id_rol=rol_admin.id_rol, id_permiso=permiso_ventas.id_permiso),
            RolPermiso(id_rol=rol_vendedor.id_rol, id_permiso=permiso_ventas.id_permiso)
        ])

        # Usuarios
        usuario1 = Usuario(nombre='Juan Pérez', correo='juan@ventas.com', contrasena=generate_password_hash('123456'), id_rol=rol_vendedor.id_rol)
        usuario2 = Usuario(nombre='Admin User', correo='admin@ventas.com', contrasena=generate_password_hash('admin123'), id_rol=rol_admin.id_rol)
        db.session.add_all([usuario1, usuario2])

        # Clientes
        cliente1 = Cliente(cedula='1044217661', nombre_completo='Carlos Ramírez', correo='carlos@gmail.com', telefono='3001234567')
        cliente2 = Cliente(cedula='1053727441', nombre_completo='Laura Torres', correo='laura@hotmail.com', telefono='3019876543')
        db.session.add_all([cliente1, cliente2])

        # Productos
        productos = [
            Producto(nombre='Garmin Instinct 2', descripcion='Reloj GPS multideporte con sensores inteligentes.', precio=1450000, stock=10,image='https://garminb2cco.vtexassets.com/arquivos/ids/159955/753759280345_1.png?v=637995419605400000', fecha_ingreso=date(2025, 4, 10)),
            Producto(nombre='Garmin inReach Mini 2', descripcion='Dispositivo de comunicación satelital con GPS.', precio=1900000, stock=5, image='https://res.garmin.com/en/products/010-02602-00/g/37968-4-061c5b23-a943-41e1-b1c3-447e3feb42c6.jpg', fecha_ingreso=date(2025, 4, 12)),
            Producto(nombre='Fenix PD36R Pro', descripcion='Linterna táctica recargable con luz LED de alto rendimiento.', precio=580000, stock=20,image='https://m.media-amazon.com/images/I/61zZ0oyDDWL._AC_SL1000_.jpg', fecha_ingreso=date(2025, 4, 11)),
            Producto(nombre='SteriPEN Ultra', descripcion='Purificador de agua UV portátil con batería recargable.', precio=400000, stock=15,image='https://keniaoutdoor.com/3375-large_default/purificador-steripen-ultra.jpg', fecha_ingreso=date(2025, 4, 9)),
            Producto(nombre='Leatherman Tread Tempo', descripcion='Multiherramienta inteligente con reloj analógico.', precio=1200000, stock=8, image='https://m.media-amazon.com/images/I/51xxynX6K7L._AC_UY900_.jpg', fecha_ingreso=date(2025, 4, 8)),
            Producto(nombre='Mechanix Wear M-Pact', descripcion='Guantes tácticos con protección contra impactos y palma reforzada.', precio=240000, stock=25,image='https://images-na.ssl-images-amazon.com/images/I/91muyxCFrqL._AC_UL210_SR210,210_.jpg', fecha_ingreso=date(2025, 4, 13)),
            Producto(nombre='Salomon Quest 4 GTX', descripcion='Botas impermeables de alta montaña con soporte de tobillo.', precio=890000, stock=12,image='https://m.media-amazon.com/images/I/61pthCIw3OL.jpg', fecha_ingreso=date(2025, 4, 14)),
            Producto(nombre='Maxpedition Falcon-II Backpack', descripcion='Mochila táctica 25L con sistema MOLLE y compartimentos múltiples.', precio=720000, stock=10,image='https://m.media-amazon.com/images/I/71kastbJg7L._AC_SL1000_.jpg', fecha_ingreso=date(2025, 4, 15)),
            Producto(nombre='Anker PowerCore Solar 20000', descripcion='Batería solar resistente al agua con linterna incorporada.', precio=330000, stock=18,image='https://m.media-amazon.com/images/I/815LQj109zL.jpg', fecha_ingreso=date(2025, 4, 16)),
            Producto(nombre='Peltor Tactical 100 (3M)', descripcion='Auriculares con cancelación activa de ruido y amplificación ambiental.', precio=510000, stock=7, image='https://http2.mlstatic.com/D_NQ_NP_930320-MLU73413469297_122023-O.webp',fecha_ingreso=date(2025, 4, 17))
        ]
        db.session.add_all(productos)

        db.session.flush()

        # Venta
        venta1 = Venta(
            cedula='1044217661',
            id_usuario=usuario2.id_usuario,
            total=2030000,
            total_con_descuento=1930000
        )
        db.session.add(venta1)
        db.session.flush()

        # Detalles de la venta
        detalle1 = DetalleVenta(id_venta=venta1.id_venta, id_producto=productos[0].id_producto, cantidad=1,
                                precio_unitario=1450000, descuento_porcentaje=5.0, subtotal=1377500)
        detalle2 = DetalleVenta(id_venta=venta1.id_venta, id_producto=productos[2].id_producto, cantidad=1,
                                precio_unitario=580000, descuento_porcentaje=5.0, subtotal=551000)
        db.session.add_all([detalle1, detalle2])

        # Pago
        pago1 = Pago(id_venta=venta1.id_venta, metodo_pago='tarjeta')
        db.session.add(pago1)

        # Factura
        factura1 = Factura(id_venta=venta1.id_venta, numero_factura='FACT-001', archivo_pdf='facturas/factura_001.pdf')
        db.session.add(factura1)

        
        db.session.commit()
        print("✅ Datos insertados correctamente.")
    except Exception as e:
        db.session.rollback()
        print("❌ Error:", e)

# ---------------- EJECUTAR CREACIÓN ---------------- #

# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#         registros()
#     print("✅ Tablas creadas correctamente en MySQL")

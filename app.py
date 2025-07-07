from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session, make_response
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
import os, json
from datetime import timedelta, datetime # Importar timedelta para la duración de la sesión
from werkzeug.security import check_password_hash, generate_password_hash
from setup_db import db, Usuario, Rol, Permiso, RolPermiso, Cliente, Producto, Venta, DetalleVenta, Pago, Factura, Contactanos
from generador_pdf import generar_factura_pdf, generar_historial_cliente_pdf, enviar_pdf_por_correo, proteger_pdf

app = Flask(__name__)
app.secret_key = 'w3r1T3$T@claveS3cr3ta2025'  # Necesaria para sesiones y flash
PEDEEFES_DIR = os.path.join(app.root_path, 'static', 'pdfs')
os.makedirs(PEDEEFES_DIR, exist_ok=True)

# *** CONFIGURACIÓN PARA SESIONES PERMANENTES ***
# Establece la duración de la sesión permanente (ej. 31 días).
# Si el usuario cierra el navegador y vuelve antes de este tiempo, la sesión se mantendrá.
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)

# *** CORRECCIÓN: Usar 'mysql+pymysql' para el controlador PyMySQL ***
# El dialecto 'pymql' no es reconocido por SQLAlchemy para MySQL.
# Asegúrate de haber instalado 'pymysql' con 'pip install pymysql'.
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://avnadmin:AVNS_oRi9rK7mgp8Ar0zG6kc@gestion-ventas-cristiandacalop-2298.e.aivencloud.com:11514/defaultdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Filtro de Jinja2 para formatear valores como moneda
@app.template_filter('currency_format')
def currency_format_filter(value):
    """
    Formatea un valor numérico como moneda con signo $, separador de miles (punto) y sin decimales.
    Ejemplo: 1234567.89 -> $1.234.567
    """
    try:
        # Convertir a float por si el valor viene como string u otro tipo
        numeric_value = float(value)
        # Formatear el número con separador de miles (coma por defecto en algunas locales) y sin decimales.
        # Luego, reemplazar la coma por un punto para el separador de miles.
        formatted_value = f"{numeric_value:,.0f}".replace(",", ".")
        return f"${formatted_value}"
    except (ValueError, TypeError):
        # Si el valor no es un número válido, devuelve el valor original o un valor predeterminado (ej. "$0")
        return value

# Funcion para historial cliente que busca el historial y lo devuelve para ser puesto en la tabla 
def obtener_historial_por_cedula(cedula):
    cliente = Cliente.query.filter_by(cedula=cedula).first()
    if not cliente:
        return None, None

    pagina = request.args.get('pagina', 1, type=int)

    # Consulta paginada de ventas
    ventas_paginadas = Venta.query.filter_by(cedula=cliente.cedula)\
        .order_by(Venta.fecha_venta.desc())\
        .paginate(page=pagina, per_page=7, error_out=False)

    # Para cada venta de la página, busca sus detalles y productos
    items = []
    for venta in ventas_paginadas.items:
        detalles = DetalleVenta.query.filter_by(id_venta=venta.id_venta).all()
        for detalle in detalles:
            producto = Producto.query.get(detalle.id_producto)
            if producto:
                items.append({
                    'id_venta': venta.id_venta,
                    'fecha': venta.fecha_venta,
                    'producto': producto.nombre,
                    'cantidad': detalle.cantidad,
                    'precio_unitario': detalle.precio_unitario,
                    'subtotal': detalle.subtotal,
                    'total': venta.total_con_descuento
                })

    # Simula paginación sobre los detalles
    class Pagination:
        def __init__(self, items, page, per_page, total, pages, has_prev, has_next, prev_num, next_num):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = pages
            self.has_prev = has_prev
            self.has_next = has_next
            self.prev_num = prev_num
            self.next_num = next_num

    paginated_historial = Pagination(
        items,
        ventas_paginadas.page,
        ventas_paginadas.per_page,
        ventas_paginadas.total,
        ventas_paginadas.pages,
        ventas_paginadas.has_prev,
        ventas_paginadas.has_next,
        ventas_paginadas.prev_num,
        ventas_paginadas.next_num
    )
    return cliente, paginated_historial
def nocache(view):
    @wraps(view)
    def no_cache_view(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        #borrar todo lo que esta en session
        return response
    return no_cache_view


# Config de login para Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'Login' # Define la vista de login si el usuario no está autenticado

login_manager.login_view = 'Login'
login_manager.login_message = "Debes iniciar sesión para acceder a esta página."
login_manager.login_message_category = "danger"

# Cargar usuario por ID para Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Ruta principal
@app.route('/', methods=['GET', 'POST'])
def Menu():
    return render_template('main.html', usuario=current_user)

# Ruta Login
@app.route('/login', methods=['GET', 'POST'])
def Login():
    if current_user.is_authenticated:
        return redirect(url_for('Menu'))
    if 'intentos_login' not in session:
        session['intentos_login'] = 0
    if 'ultimo_intento' not in session:
        session['ultimo_intento'] = datetime.now().replace(tzinfo=None).isoformat()

    TIEMPO_BLOQUEO = 30  # minutos, SI SE QUEIRE DESACTIVAR RAPIDO PONERLO EN 0.1
    INTENTOS_MAXIMOS = 3

    if request.method == 'POST':
        correo = request.form['correo']
        contrasena = request.form['contraseña']
        usuario = Usuario.query.filter_by(correo=correo).first()

        ahora = datetime.now()
        ultimo_intento_raw = session.get('ultimo_intento', datetime.now().isoformat())
        if not isinstance(ultimo_intento_raw, str):
            ultimo_intento_raw = ultimo_intento_raw.isoformat()
        ultimo_intento = datetime.fromisoformat(ultimo_intento_raw)
        if ultimo_intento.tzinfo is not None:
            ultimo_intento = ultimo_intento.replace(tzinfo=None)

        # Verificar si está bloqueado
        if session['intentos_login'] >= INTENTOS_MAXIMOS:
            tiempo_espera = ultimo_intento + timedelta(minutes=TIEMPO_BLOQUEO)
            if ahora < tiempo_espera:
                flash(f"Demasiados intentos fallidos. Intenta nuevamente en unos {TIEMPO_BLOQUEO} minutos.", "danger")
                return redirect(url_for('Login'))
            else:
                session['intentos_login'] = 0  # Reinicia intentos si ya pasó el tiempo

        if not usuario or usuario.estado == "inactivo" or not check_password_hash(usuario.contrasena, contrasena):
            session['intentos_login'] += 1
            session['ultimo_intento'] = ahora.replace(tzinfo=None).isoformat()
            if not usuario or usuario.estado == "inactivo":
                flash("Correo o contraseña incorrectos", "danger")
            else:
                flash("Correo o contraseña incorrectos", "danger")
            return redirect(url_for('Login'))

        # Si el login es exitoso
        session.permanent = True
        login_user(usuario, remember=True)
        session['intentos_login'] = 0
        session['ultimo_intento'] = datetime.now().isoformat()
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        else:
            return redirect(url_for('Menu'))

    return render_template('login.html')

@app.route('/carrito', methods=['GET', 'POST'])
@login_required
@nocache
def Carrito():
    if current_user.estado == "inactivo":
        flash("Tu cuenta está inactiva. Por favor, contacta al administrador.", "danger")
        return redirect(url_for('Menu'))
    productos = Producto.query.all()  # Obtener todos los productos
    return render_template('carrito.html', usuario=current_user, productos=productos)
@app.route('/registrar_venta', methods=['GET', 'POST'])
@login_required
@nocache
def Resventa():
    if current_user.estado == "inactivo":
        flash("Tu cuenta está inactiva. Por favor, contacta al administrador.", "danger")
        return redirect(url_for('Menu'))
    if request.method == 'POST':
        accion = request.form.get('accion')
        if accion == 'generar_pdf':
            try:
                cedula = request.form.get('cedula')
                cliente = Cliente.query.filter_by(cedula=cedula).first()
                if not cliente:
                    flash("Cliente no encontrado", "danger")
                    return redirect(url_for('Resventa'))
                if cliente.estado == 'inactivo':
                    flash("El cliente está inactivo", "danger")
                    return redirect(url_for('Resventa'))
                metodo_pago = request.form.get('metodo_pago')
                descuento = float(request.form.get('descuento'))
                if descuento < 0 or descuento > 100:
                    flash("El descuento debe estar entre 0 y 100", "danger")
                    return redirect(url_for('Resventa'))
                productos_json = request.form.get('productos')

                if not productos_json:
                    print("No se recibieron productos para registrar la venta.")
                    return redirect(url_for('Resventa'))

                productos = json.loads(productos_json)

                if not productos or not cedula:
                    flash("Faltan datos para procesar la venta", "danger")
                    return redirect(url_for('resventa'))
                print("productos: ", productos)

                total = 0
                subtotal = 0

                # Calculamos total y subtotal
                for p in productos:
                    sub = p['precio'] * p['cantidad']
                    subtotal += sub
                total = subtotal * (1 - descuento / 100)

                venta = Venta(
                    cedula=cedula,
                    id_usuario=current_user.id_usuario,
                    total=subtotal,
                    total_con_descuento=total
                )
                db.session.add(venta)
                db.session.flush()  # Obtenemos ID de venta generado

                for p in productos:
                    # Obtener el producto de la base de datos
                    producto = Producto.query.filter_by(id_producto=p['id']).first()
                    if producto.estado == 'inactivo':
                        flash(f"El producto {producto.nombre} esta inactivo", "danger")
                        return redirect(url_for("Resventa"))
                    
                    if producto and producto.stock >= p['cantidad']:
                        # Crear el detalle de la venta
                        detalle = DetalleVenta(
                            id_venta=venta.id_venta,
                            id_producto=p['id'],
                            cantidad=p['cantidad'],
                            precio_unitario=p['precio'],
                            descuento_porcentaje=descuento,
                            subtotal=p['precio'] * p['cantidad'] * (1 - descuento / 100)
                        )

                        # Restar del stock
                        producto.stock -= p['cantidad']

                        if producto.stock <= 0:
                            producto.stock = 0
                            producto.estado = 'inactivo'

                        # Agregar el detalle a la sesión
                        db.session.add(detalle)
                    else:
                        flash(f"Stock insuficiente para el producto{producto.nombre}", "danger")
                        return redirect(url_for("Resventa"))  # Ajusta esto según tu ruta

                # Creamos pago
                pago = Pago(
                    id_venta=venta.id_venta,
                    metodo_pago=metodo_pago
                )
                db.session.add(pago)

                # Generar PDF
                nombre_pdf = f"factura_{venta.id_venta}.pdf"
                ruta_pdf = os.path.join(PEDEEFES_DIR, nombre_pdf)
                generar_factura_pdf(venta.id_venta, ruta_pdf, current_user.nombre)
                archivo_pdf = f"/static/pdfs/{nombre_pdf}"

                # Creamos factura
                factura = Factura(
                    id_venta=venta.id_venta,
                    numero_factura=f"FACT-{venta.id_venta}",
                    archivo_pdf=ruta_pdf
                )
                db.session.add(factura)

                db.session.commit()
                session['cedula_factura'] = cedula
                flash("Venta registrada correctamente", "success")
                #odtener el carrito de la sesión
                carrito = session.get('carrito', [])
                # vaciar el carrito
                session.pop('carrito', None)  # Elimina el carrito de la sesión
                return render_template('venta.html', usuario=current_user, archivo_pdf=archivo_pdf, cliente=cliente)
            except Exception as e:
                db.session.rollback()
                print(f"Error al registrar venta: {e}")
                flash(f"Error al registrar venta: {e}", "danger")
        elif accion == 'enviar_pdf':
            cedula = session.get('cedula_factura')
            destinatario = request.form.get('email')
            if not destinatario:
                flash("Por favor, ingresa un correo electrónico", "danger")
                return redirect(url_for('Resventa'))
            cliente = Cliente.query.filter_by(cedula=cedula).first()
            venta = Venta.query.filter_by(cedula=cedula).order_by(Venta.fecha_venta.desc()).first()
            asunto = f"Factura de compra VIKINGO Technology"   
            mensaje = f"Compra hecha por {cliente.nombre_completo} el {venta.fecha_venta}. La contraseñapara aceder el PDF es la cédula del cliente."
            
            # Generar PDF
            nombre_pdf = f"factura_{venta.id_venta}.pdf"
            ruta_pdf = os.path.join(PEDEEFES_DIR, nombre_pdf)
            ruta_pdf_protegida = os.path.join(PEDEEFES_DIR, f"{nombre_pdf}_protegido.pdf")
            archivo_pdf = f"pdfs/{nombre_pdf}"
            if not os.path.exists(ruta_pdf):
                flash("El archivo PDF no existe.", "danger")
                return redirect(url_for('historial_clientes'))
            proteger_pdf(ruta_pdf, ruta_pdf_protegida, cedula)
            try:
                enviar_pdf_por_correo(destinatario, asunto, mensaje, ruta_pdf_protegida)
                flash("Correo enviado correctamente.", "success")
            except Exception as e:
                flash(f"Error al enviar correo: {e}", "danger")

            # Renderiza el template pasando archivo_pdf para mantener el botón de descarga
            return render_template('venta.html', usuario=current_user ,archivo_pdf=archivo_pdf, cliente=cliente)
        else:
            flash("accion no reconocida", "danger")
    return render_template('venta.html', usuario=current_user)

# Rutas de gestión de usuarios, clientes, productos, informes y contacto
@app.route('/usuarios', methods=['GET' ,'POST'])
@login_required
@nocache
def gestionar_usuarios():
    if current_user.estado == "inactivo":
        flash("Tu cuenta está inactiva. Por favor, contacta al administrador.", "danger")
        return redirect(url_for('Menu'))
    if current_user.id_rol != 1:
        flash("No tienes permiso para acceder a esta página", "danger")
        return redirect(url_for('Menu'))
    if request.method == 'POST':
        print("---- FORM DATA ----")
        for key in request.form:
            print(f"{key}: {request.form[key]}")
        print("-------------------")
        accion = request.form.get('accion')
        if accion == 'insertar':
            usuario = request.form['nombre']
            correo = request.form['correo']
            contrasena = request.form['contrasena']
            confirmar = request.form['confirmar']
            rol = request.form['id_rol']
            
            usuario_correo = Usuario.query.filter_by(correo=correo).first()
            if usuario_correo:
                flash("El correo ya está registrado", "danger")
                return redirect(url_for('gestionar_usuarios'))
            usuario_nombre = Usuario.query.filter_by(nombre=usuario).first()
            if usuario_nombre:
                flash("El nombre ya está registrado", "danger")
                return redirect(url_for('gestionar_usuarios'))
            if contrasena == confirmar:
                contrasena_hash = generate_password_hash(contrasena, method='pbkdf2:sha256')
                new_usuario = Usuario(nombre=usuario, correo=correo, contrasena=contrasena_hash, id_rol=rol)
                db.session.add(new_usuario)
                db.session.commit()
                flash("Usuario insertado correctamente", "success")
                return redirect(url_for('gestionar_usuarios'))
            else:
                flash("Las contraseñas no coinciden", "danger")
        elif accion == 'actualizar':
            id_usuario = request.form.get('usuario_seleccionado')
            usuario = Usuario.query.get(id_usuario)
            if usuario:
                nuevo_nombre = request.form.get('nombre')
                nuevo_correo = request.form.get('correo')
                nueva_contrasena = request.form.get('contrasena')
                confirmar = request.form.get('confirmar')
                if usuario.id_usuario == current_user.id_usuario:
                    flash("No puedes quitarle el admin a tu propio usuario desde aquí", "danger")
                    nuevo_rol = usuario.id_rol
                else:
                    nuevo_rol = request.form.get('id_rol')

                usuario.nombre = nuevo_nombre
                usuario.correo = nuevo_correo
                usuario.id_rol = nuevo_rol
                if nueva_contrasena or confirmar:
                    if nueva_contrasena == confirmar:
                        usuario.contrasena = generate_password_hash(nueva_contrasena, method='pbkdf2:sha256')
                    else:
                        flash("Las contraseñas no coinciden", "danger")
                        return redirect(url_for('gestionar_usuarios'))
                db.session.commit()
                flash("Usuario actualizado correctamente", "success")
                return redirect(url_for('gestionar_usuarios'))        
            else:        
                flash("Usuario no encontrado", "danger")
        elif accion == 'desactivar':
            id_usuario = request.form.get('usuario_seleccionado')
            usuario = Usuario.query.get(id_usuario)
            if usuario:
                if usuario.id_usuario == current_user.id_usuario:
                    flash("No puedes desactivar tu propio usuario", "danger")
                    return redirect(url_for('gestionar_usuarios'))
                usuario.estado = "inactivo"
                db.session.commit()
                flash("Usuario desactivado correctamente", "success")
                return redirect(url_for('gestionar_usuarios'))
            else:
                flash("Usuario no encontrado", "danger")
        elif accion == 'activar':
            id_usuario = request.form.get('usuario_seleccionado')
            usuario = Usuario.query.get(id_usuario)
            if usuario:
                usuario.estado = "activo"
                db.session.commit()
                flash("Usuario activado correctamente", "success")
                return redirect(url_for('gestionar_usuarios'))
            else:
                flash("Usuario no encontrado", "danger")
        else:
            flash("Accion no reconocida", "danger")
    pagina = request.args.get('pagina', 1, type=int)
    buscar = request.args.get('buscar', '').strip()
    estado = request.args.get('estado', '').strip()

    query = Usuario.query

    if buscar:
        query = query.filter(Usuario.nombre.ilike(f'%{buscar}%'))
    if estado:
        query = query.filter_by(estado=estado)

    usuarios = query.order_by(Usuario.id_usuario.desc()).paginate(page=pagina, per_page=10)
    return render_template ('usuarios.html', usuarios=usuarios)

@app.route('/clientes', methods=['GET' ,'POST'])
@login_required
@nocache
def gestionar_clientes():
    if current_user.estado == "inactivo":
        flash("Tu cuenta está inactiva. Por favor, contacta al administrador.", "danger")
        return redirect(url_for('Menu'))
    if request.method == 'POST':
        print("---- FORM DATA ----")
        for key in request.form:
            print(f"{key}: {request.form[key]}")
        print("-------------------")
        accion = request.form.get('accion')
        if accion == 'insertar':
            cedula = request.form['cedula']
            nombre_completo = request.form['nombre']    
            correo = request.form['correo']
            telefono = request.form['telefono']
            
            cliente_existente = Cliente.query.filter_by(cedula=cedula).first()
            if cliente_existente:
                flash("Esta cedula ya está registrada", "danger")
                return redirect(url_for('gestionar_clientes'))
            correo_existente = Cliente.query.filter_by(correo=correo).first()
            if correo_existente:
                flash("Este correo ya está registrado", "danger")
                return redirect(url_for('gestionar_clientes'))

            new_cliente = Cliente(cedula=cedula, nombre_completo=nombre_completo, correo=correo, telefono=telefono)
            db.session.add(new_cliente)
            db.session.commit()
            flash("Cliente insertado correctamente", "success")
            return redirect(url_for('gestionar_clientes'))

        elif accion == 'actualizar':
            id_cliente = request.form.get('cliente_seleccionado')
            cliente = Cliente.query.get(id_cliente)
            if cliente:
                nuevo_nombre = request.form.get('nombre')
                nuevo_correo = request.form.get('correo')
                nuevo_telefono = request.form.get('telefono')
                if not nuevo_correo or not nuevo_nombre or not nuevo_telefono:
                    flash("Todos los campos son obligatorios", "danger")
                    return redirect(url_for('gestionar_clientes'))
                correo_existente = Cliente.query.filter_by(correo=nuevo_correo).first()
                if correo_existente:
                    flash("Este correo ya está registrado", "danger")
                    return redirect(url_for('gestionar_clientes'))
                cliente.nombre_completo = nuevo_nombre
                cliente.correo = nuevo_correo
                cliente.telefono = nuevo_telefono

                db.session.commit()
                flash("Cliente actualizado correctamente", "success")
                return redirect(url_for('gestionar_clientes'))        
            else:        
                flash("Cliente no encontrado", "danger")
        elif accion == 'desactivar':
            id_cliente = request.form.get('cliente_seleccionado')
            cliente = Cliente.query.get(id_cliente)
            if cliente:
                cliente.estado = "inactivo"
                db.session.commit()
                flash("Cliente desactivado correctamente", "success")
                return redirect(url_for('gestionar_clientes'))
            else:
                flash("Cliente no encontrado", "danger")
        elif accion == 'activar':
            id_cliente = request.form.get('cliente_seleccionado')
            cliente = Cliente.query.get(id_cliente)
            if cliente:
                cliente.estado = "activo"
                db.session.commit()
                flash("Cliente activado correctamente", "success")
                return redirect(url_for('gestionar_clientes'))
            else:
                flash("Cliente no encontrado", "danger")
            
        else:
            flash("Accion no reconocida", "danger")
    pagina = request.args.get('pagina', 1, type=int)
    buscar = request.args.get('buscar', '').strip()
    estado = request.args.get('estado', '').strip()

    query = Cliente.query

    if buscar:
        query = query.filter(or_(
            Cliente.nombre_completo.ilike(f'%{buscar}%'),
            Cliente.cedula.ilike(f'%{buscar}%')
        ))
    if estado:
        query = query.filter_by(estado=estado)

    clientes = query.order_by(Cliente.id_cliente.desc()).paginate(page=pagina, per_page=10)

    return render_template('clientes.html', clientes=clientes, usuario=current_user)

@app.route('/productos', methods=['GET' ,'POST'])
@login_required
@nocache
def gestionar_productos():
    if current_user.estado == "inactivo":
        flash("Tu cuenta está inactiva. Por favor, contacta al administrador.", "danger")
        return redirect(url_for('Menu'))
    if current_user.id_rol != 1:  # Verificar si el usuario tiene rol de administrador
        flash("No tienes permiso para acceder a esta página", "danger")
        return redirect(url_for('Menu'))  # Redirigir al menú si no es administrador
    if request.method == 'POST':
        print("---- FORM DATA ----")
        for key in request.form:
            print(f"{key}: {request.form[key]}")
        print("-------------------")
        accion = request.form.get('accion')
        if accion == 'insertar':
            descripcion = request.form['descripcion']
            nombre = request.form['nombre']
            imagen = request.form['image']
            precio = request.form['precio']
            cantidad = request.form['stock']
            fecha = request.form['fecha_ingreso']
            
            producto_existente = Producto.query.filter_by(nombre=nombre).first()
            if producto_existente:
                flash("Este producto ya está registrado", "danger")
                return redirect(url_for('gestionar_productos'))
            if imagen:
                new_producto = Producto(nombre=nombre, descripcion=descripcion, image=imagen, stock=cantidad, precio=precio, fecha_ingreso=fecha)
            else:
                new_producto = Producto(nombre=nombre, descripcion=descripcion, stock=cantidad, precio=precio, fecha_ingreso=fecha)
            db.session.add(new_producto)
            db.session.commit()
            flash("Producto insertado correctamente", "success")
            return redirect(url_for('gestionar_productos'))

        elif accion == 'actualizar':
            id_producto = request.form.get('producto_seleccionado')
            producto = Producto.query.get(id_producto)
            if producto:
                nuevo_nombre = request.form.get('nombre')
                nueva_descripcion = request.form.get('descripcion')
                nueva_imagen = request.form.get('image')
                nuevo_precio = request.form.get('precio')
                nuevo_cantidad = request.form.get('stock')
                nueva_fecha = request.form.get('fecha_ingreso')
                if not nuevo_nombre or not nueva_descripcion or not nuevo_precio or not nuevo_cantidad or not nueva_fecha:
                    flash("Todos los campos son obligatorios", "danger")
                    return redirect(url_for('gestionar_productos'))
                producto.nombre = nuevo_nombre
                producto.descripcion = nueva_descripcion
                producto.precio = nuevo_precio
                producto.stock = int(nuevo_cantidad)
                producto.fecha_ingreso = nueva_fecha
                if nueva_imagen:
                    producto.image = nueva_imagen
                else:
                    pass
                if producto.stock > 0:
                    producto.estado = 'activo'
                else:
                    producto.estado = 'inactivo'
                db.session.commit()
                flash("Producto actualizado correctamente", "success")
                return redirect(url_for('gestionar_productos'))        
            else:        
                flash("Producto no encontrado", "danger")
        elif accion == 'desactivar':
            id_producto = request.form.get('producto_seleccionado')
            producto = Producto.query.get(id_producto)
            if producto:
                producto.estado = "inactivo"
                db.session.commit()
                flash("Producto eliminado correctamente", "success")
                return redirect(url_for('gestionar_productos'))
            else:
                flash("Producto no encontrado", "danger")
        elif accion == 'activar':
            id_producto = request.form.get('producto_seleccionado')
            producto = Producto.query.get(id_producto)
            if producto:
                if producto.stock > 0:
                    producto.estado = "activo"
                    db.session.commit()
                    flash("Producto activado correctamente", "success")
                    return redirect(url_for('gestionar_productos'))
                else:
                    flash("No se puede activar un producto que no tiene cantidad", "danger")
            else:
                flash("Producto no encontrado", "danger")
        else:
            flash("Accion no reconocida", "danger")
    pagina = request.args.get('pagina', 1, type=int)
    buscar = request.args.get('buscar', '').strip()
    estado = request.args.get('estado', '').strip()

    query = Producto.query

    if buscar:
        query = query.filter(or_(
            Producto.nombre.ilike(f'%{buscar}%'),
            Producto.descripcion.ilike(f'%{buscar}%')
        ))
    if estado:
        query = query.filter_by(estado=estado)
        

    productos = query.order_by(Producto.id_producto.desc()).paginate(page=pagina, per_page=10)
    return render_template ('productos.html', productos=productos)

@app.route('/informes', methods=['GET', 'POST'])
@login_required
@nocache
def informes():
    if current_user.estado == "inactivo":
        flash("Tu cuenta está inactiva. Por favor, contacta al administrador.", "danger")
        return redirect(url_for('Menu'))
    if current_user.id_rol != 1:  # Verificar si el usuario tiene rol de administrador
        flash("No tienes permiso para acceder a esta página", "danger")
        return redirect(url_for('Menu'))  # Redirigir al menú si no es administrador
    return render_template('informes.html', usuario=current_user)

@app.route('/historial', methods=['GET', 'POST'])
@login_required
@nocache
def historial_clientes():
    if current_user.estado == "inactivo":
        flash("Tu cuenta está inactiva. Por favor, contacta al administrador.", "danger")
        return redirect(url_for('Menu'))
    if current_user.id_rol != 1:
        flash("No tienes permiso para acceder a esta página", "danger")
        return redirect(url_for('Menu'))

    cliente = None
    historial = []

    if request.method == 'POST':
        accion = request.form.get('accion')
        

        if accion == 'buscar':
            cedula = request.form.get('cedula')

            if not cedula:
                flash("Por favor, ingresa una cédula", "danger")
                return redirect(url_for('historial_clientes'))
            cliente, historial = obtener_historial_por_cedula(cedula)
            if not cliente:
                flash("Cliente no encontrado", "danger")
                return redirect(url_for('historial_clientes'))

            session['cedula_historial'] = cedula
            return render_template('historialcliente.html', cliente=cliente, historial=historial)

        elif accion == 'generar_pdf':
            cedula = session.get('cedula_historial')
            cliente, historial = obtener_historial_por_cedula(cedula)
            if not cliente:
                flash("Cliente no encontrado", "danger")
                return redirect(url_for('historial_clientes'))

            nombre_pdf = f"Historial_{cliente.nombre_completo}.pdf"
            ruta_pdf = os.path.join(PEDEEFES_DIR, nombre_pdf)
            generar_historial_cliente_pdf(cedula, ruta_pdf)
            archivo_pdf = f"pdfs/{nombre_pdf}"
            
            flash(f"PDF generado correctamente", "success")
            session['cedula_historial'] = cedula
            return render_template('historialcliente.html', archivo_pdf=archivo_pdf, cliente=cliente, historial=historial)

        elif accion == 'enviar_pdf':
            destinatario = request.form.get('email')
            if not destinatario:
                flash("Por favor, ingresa un correo electrónico", "danger")
                return redirect(url_for('historial_clientes'))
            cedula = request.form.get('cedula') or session.get('cedula_historial')
            cliente, historial = obtener_historial_por_cedula(cedula)
            asunto = f"Historial de Compras de {cliente.nombre_completo}"   
            mensaje = f"Adjunto el historial de compras de {cliente.nombre_completo}. /n La contraseña para abrir el PDF es la cédula del cliente."
            cedula = session.get('cedula_historial')
            
            nombre_pdf = f"Historial_{cliente.nombre_completo}.pdf"
            ruta_pdf = os.path.join(PEDEEFES_DIR, nombre_pdf)
            ruta_pdf_protegida = os.path.join(PEDEEFES_DIR, f"{nombre_pdf}_protegido.pdf")
            archivo_pdf = f"pdfs/{nombre_pdf}"
            if not os.path.exists(ruta_pdf):
                flash("El archivo PDF no existe.", "danger")
                return redirect(url_for('historial_clientes'))
            proteger_pdf(ruta_pdf, ruta_pdf_protegida, cedula)  # Proteger el PDF antes de enviarlo
            
            try:
                enviar_pdf_por_correo(destinatario, asunto, mensaje, ruta_pdf_protegida)
                flash("Correo enviado correctamente.", "success")
            except Exception as e:
                flash(f"Error al enviar correo: {e}", "danger")

            # Renderiza el template pasando archivo_pdf para mantener el botón de descarga
            return render_template('historialcliente.html', archivo_pdf=archivo_pdf, cliente=cliente, historial=historial)
    # Si se vuelve por GET, se intenta recuperar la última cédula usada
    cedula_guardada = session.get('cedula_historial')
    if cedula_guardada:
        cliente, historial = obtener_historial_por_cedula(cedula_guardada)
    pagina = request.args.get('pagina', 1, type=int)


    return render_template('historialcliente.html', usuario=current_user, cliente=cliente, historial=historial)
@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    if request.method == 'POST':
        data = request.get_json()
        
        nombre = data.get('name')
        correo = data.get('email')
        telefono = data.get('phone')
        asunto = data.get('subject')
        mensaje = data.get('message')
        
        #enviar al correo de la compañia el mensaje       
        destinario = "vikingotic@gmail.com"
        # Armar cuerpo del mensaje con los datos del formulario
        cuerpo = f"""
        📬 Nuevo mensaje desde el formulario de contacto:

        🧑 Nombre: {nombre}
        📧 Correo: {correo}
        📞 Teléfono: {telefono}
        📝 Asunto: {asunto}

        💬 Mensaje:
        {mensaje}
        """
        enviar_pdf_por_correo(destinatario=destinario, asunto=asunto, cuerpo=cuerpo, archivo_pdf="nohay")
        
        new_contacto = Contactanos(nombre=nombre, correo= correo, telefono= telefono, asunto= asunto, mensaje = mensaje)
        db.session.add(new_contacto)
        db.session.commit()
        
        return jsonify({'status': 'ok'})
    
    return render_template('contacto.html', usuario=current_user)

# Logout
@app.route('/logout')
@login_required
@nocache
def Logout():
    logout_user()
    session.clear()
    return redirect(url_for('Login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

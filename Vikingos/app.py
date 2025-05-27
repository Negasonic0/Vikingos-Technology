from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from setup_db import db, Usuario, Rol, Permiso, RolPermiso, Cliente, Producto, Venta, DetalleVenta, Pago, Factura, HistorialCliente, Contactanos
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = 'clave-secreta'  # Necesaria para sesiones y flash

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/gestion_ventas'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


# Config de login
login_manager = LoginManager(app)
login_manager.login_view = 'Login'

# Cargar usuario por ID
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Ruta Login
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def Login():
    if request.method == 'POST':
        correo = request.form['correo']
        contrasena = request.form['contraseña']

        usuario = Usuario.query.filter_by(correo=correo).first()
        if usuario and check_password_hash(usuario.contrasena, contrasena):
            login_user(usuario)
            return redirect(url_for('Menu'))
        else:
            flash("Correo o contrasena incorrectos", "error")
            return redirect(url_for('Login'))
    return render_template('login.html')

# Ruta protegida
@app.route('/menu')
@login_required
def Menu():
    return render_template('menu.html', usuario=current_user)

@app.route('/usuarios', methods=['POST'])
@login_required
def gestionar_usuarios():
    accion = request.form;['accion']
    if accion == 'insertar':
        usuario = request.form['usuario']
        correo = request.form['correo']
        contrasena = request.form['contraseña']
        confirmar = request.form['confirmar']
        rol = request.form['rol']
        if contrasena == confirmar:
            contrasena_hash = generate_password_hash(contrasena)
            new_usuario = Usuario(nombre=usuario, correo=correo, contrasena=contrasena_hash, id_rol=rol)
            db.session.add(new_usuario)
            db.session.commit()
        else:
            flash("Las contraseñas no coinciden", "error")
    elif accion == 'actualizar':
        return 
    elif accion == 'borrar':
        return
    else:
        flash("Accion no reconocida", "error")
    usuarios = Usuario.query.all()
    return render_template ('usuarios.html', usuarios=usuarios)

@app.route('/reguser', methods=['GET', 'POST'])
@login_required
def Reguser():
    if request.method == 'POST':
        usuario = request.form['usuario']
        correo = request.form['correo']
        contrasena = request.form['contraseña']
        confirmar = request.form['confirmar']
        rol = request.form['rol']
        if contrasena == confirmar:
            contrasena_hash = generate_password_hash(contrasena)
            new_usuario = Usuario(nombre=usuario, correo=correo, contrasena=contrasena_hash, id_rol=rol)
            db.session.add(new_usuario)
            db.session.commit()
        else:
            flash("Las contraseñas no coinciden", "error")
        
    return render_template('reguser.html', usuario=current_user)
@app.route('/contacto', methods=['GET', 'POST'])
@login_required
def contacto():
    if request.method == 'POST':
        data = request.get_json()
        
        nombre = data.get('name')
        correo = data.get('email')
        telefono = data.get('phone')
        asunto = data.get('subject')
        mensaje = data.get('message')
        
        new_contacto = Contactanos(nombre=nombre, correo= correo, telefono= telefono, asunto= asunto, mensaje = mensaje)
        db.session.add(new_contacto)
        db.session.commit()
        
        return jsonify({'status': 'ok'})
    
    return render_template('contacto.html', usuario=current_user)

# Logout
@app.route('/logout')
@login_required
def Logout():
    logout_user()
    return redirect(url_for('Login'))

if __name__ == '__main__':
    app.run(debug=True, port=5004)
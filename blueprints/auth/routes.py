from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
import mysql.connector

auth_bp = Blueprint('auth', __name__)

# --------------------------------------
# RUTA: Registro de Usuario (/registrarse)
# --------------------------------------
@auth_bp.route('/registrarse', methods=['GET', 'POST'])
def registrarse():
    conexion = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="gestussg"
    )
    cursor = conexion.cursor(dictionary=True)

    if request.method == 'POST':
        nombre_completo = request.form['nombre_completo']
        correo = request.form['correo']
        usuario = request.form['usuario']
        contraseña = generate_password_hash(request.form['contraseña'])
        nit_empresa = request.form['nit_empresa']
        rol_id = request.form['rol_id']

        # Verificar si ya existe el usuario o el correo
        cursor.execute("SELECT * FROM usuarios WHERE correo = %s OR usuario = %s", (correo, usuario))
        existente = cursor.fetchone()

        if existente:
            flash("Este usuario ya fue registrado anteriormente.", "error")
            return redirect(url_for('auth.registrarse'))

        # Si no existe, lo insertamos
        cursor.execute("""
            INSERT INTO usuarios (nombre_completo, correo, usuario, contraseña, estado, nit_empresa, rol_id)
            VALUES (%s, %s, %s, %s, 'Activo', %s, %s)
        """, (nombre_completo, correo, usuario, contraseña, nit_empresa, rol_id))
        conexion.commit()

        flash("Usuario registrado exitosamente.", "success")
        return redirect(url_for('auth.registrarse'))

    # Si es GET, cargamos roles y empresas
    cursor.execute("SELECT id, nombre FROM roles")
    roles = cursor.fetchall()
    cursor.execute("SELECT nit_empresa, nombre FROM empresas")
    empresas = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template('register.html', roles=roles, empresas=empresas)


# --------------------------------------
# RUTA: Inicio de sesión (/iniciar-sesion)
# --------------------------------------
@auth_bp.route('/iniciar-sesion', methods=['GET', 'POST'])
def iniciar_sesion():
    if request.method == 'POST':
        nit_empresa = request.form['nit_empresa']
        usuario = request.form['usuario']
        contraseña = request.form['contraseña']

        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="gestussg"
        )
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT * FROM usuarios 
            WHERE usuario = %s AND nit_empresa = %s
        """, (usuario, nit_empresa))
        user = cursor.fetchone()

        if user and user['contraseña'] == contraseña:  # 👈 ojo: aquí luego cambiamos a check_password_hash
            session['usuario_id'] = user['id']
            session['usuario'] = user['usuario']
            session['nit_empresa'] = user['nit_empresa']
            flash("Inicio de sesión exitoso.")
            cursor.close()
            conexion.close()
            return redirect(url_for('auth.dashboard'))
        else:
            flash('Credenciales incorrectas o usuario inactivo', 'error')

        cursor.close()
        conexion.close()

    return render_template('login.html')


# --------------------------------------
# RUTA: Dashboard principal (/dashboard)
# --------------------------------------
@auth_bp.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.iniciar_sesion'))

    conexion = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="",
        database="gestussg"
    )
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    cursor.execute("SELECT nit_empresa, nombre FROM empresas WHERE estado = 'Activa'")
    empresas = cursor.fetchall()

    nit_seleccionado = request.args.get('nit_empresa')

    cursor.execute("SELECT COUNT(*) AS total_empresas FROM empresas WHERE estado = 'Activa'")
    total_empresas = cursor.fetchone()['total_empresas']

    cursor.execute("SELECT COUNT(*) AS total_evaluaciones FROM evaluaciones")
    total_evaluaciones = cursor.fetchone()['total_evaluaciones']

    if nit_seleccionado:
        cursor.execute("SELECT COUNT(*) AS total_capacitaciones FROM capacitaciones WHERE nit_empresa = %s", (nit_seleccionado,))
    else:
        cursor.execute("SELECT COUNT(*) AS total_capacitaciones FROM capacitaciones")
    total_capacitaciones = cursor.fetchone()['total_capacitaciones']

    if nit_seleccionado:
        cursor.execute("""
            SELECT i.tipo, COUNT(*) AS cantidad
            FROM incidentes i
            JOIN empresas e ON i.nit_empresa = e.nit_empresa
            WHERE e.estado = 'Activa'
            GROUP BY i.tipo
        """)
    else:
        cursor.execute("SELECT tipo, COUNT(*) AS cantidad FROM incidentes GROUP BY tipo")
    incidentes_por_tipo = cursor.fetchall()

    if nit_seleccionado:
        cursor.execute("""
            SELECT d.estado, COUNT(*) AS cantidad
            FROM documentos_empresa d
            JOIN empresas e ON d.nit_empresa = e.nit_empresa
            WHERE e.estado = 'Activa'
            GROUP BY d.estado
        """)
    else:
        cursor.execute("SELECT estado, COUNT(*) AS cantidad FROM documentos_empresa GROUP BY estado")
    documentos_por_estado = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        'dashboard.html',
        usuario_actual=usuario,
        total_empresas=total_empresas,
        total_evaluaciones=total_evaluaciones,
        total_capacitaciones=total_capacitaciones,
        incidentes_por_tipo=incidentes_por_tipo,
        documentos_por_estado=documentos_por_estado,
        empresas=empresas,
        nit_seleccionado=nit_seleccionado
    )

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
import mysql.connector
from extensions import get_db

recuperacion_bp = Blueprint('recuperacion', __name__)

# --------------------------------------
# RUTA: Recuperar contraseña
# --------------------------------------
@recuperacion_bp.route('/recuperar_contraseña', methods=['GET', 'POST'])
def recuperar_contraseña():
    conexion = get_db()
    cursor = conexion.cursor(dictionary=True)

    if request.method == "POST":
        # Obtener datos del formulario
        nit = request.form["nit_empresa"]
        correo = request.form["correo"]

        # Verificamos si el usuario existe
        cursor.execute(
            "SELECT * FROM usuarios WHERE correo = %s AND nit_empresa = %s",
            (correo, nit)
        )
        usuario = cursor.fetchone()

        if usuario:
            # Insertamos la solicitud de recuperación
            sql = """
                INSERT INTO recuperacion_contraseña (nit_empresa, correo, fecha_solicitud, estado)
                VALUES (%s, %s, NOW(), 'Pendiente')
            """
            cursor.execute(sql, (nit, correo))
            conexion.commit()

            flash("Se ha enviado la solicitud al admin, pronto serás notificado", "success")
        else:
            flash("No se encontró un usuario con ese NIT y correo", "danger")

        return redirect(url_for("recuperacion.recuperar_contraseña"))

    cursor.close()
    return render_template("recuperar_contraseña.html")


# --------------------------------------
# RUTA: Solicitud contraseña Admin
# --------------------------------------
@recuperacion_bp.route('/solicitudes_contrasena', methods=['GET', 'POST'])
def solicitudes_contrasena():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.iniciar_sesion'))

    conexion = get_db()
    cursor = conexion.cursor(dictionary=True)

    # Obtener datos del usuario actual
    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    # Verificar si es administrador
    if usuario['rol'] != 'Administrador':
        cursor.close()
        return "Acceso denegado", 403

    # Procesar formulario POST
    if request.method == 'POST':
        solicitud_id = request.form.get('solicitud_id')
        nueva_contrasena = request.form.get('nueva_contrasena')

        cursor.execute("SELECT correo FROM recuperacion_contraseña WHERE id = %s", (solicitud_id,))
        solicitud = cursor.fetchone()

        if solicitud:
            correo = solicitud['correo']
            hashed_password = generate_password_hash(nueva_contrasena)

            # Actualizar la contraseña del usuario
            cursor.execute("UPDATE usuarios SET contraseña = %s WHERE correo = %s", (hashed_password, correo))

            # Marcar la solicitud como 'Atendida'
            cursor.execute("UPDATE recuperacion_contraseña SET estado = 'Atendida' WHERE id = %s", (solicitud_id,))
            conexion.commit()

    # Obtener todas las solicitudes pendientes
    cursor.execute("SELECT * FROM recuperacion_contraseña WHERE estado = 'Pendiente'")
    solicitudes = cursor.fetchall()

    cursor.close()
    return render_template('solicitudes_contrasena.html', solicitudes=solicitudes, usuario_actual=usuario)

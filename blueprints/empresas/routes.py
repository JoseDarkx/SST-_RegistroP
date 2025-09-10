
import os
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, jsonify, send_from_directory, abort
)
from werkzeug.utils import secure_filename
import mysql.connector
from extensions import get_db

empresas_bp = Blueprint('empresas', __name__, url_prefix='/empresas')

UPLOAD_CERT_FOLDER = 'uploads/certificados'
os.makedirs(UPLOAD_CERT_FOLDER, exist_ok=True)

# ------------------------------
# Ruta: Listar empresas
# ------------------------------
@empresas_bp.route('/')
def listar_empresas():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.iniciar_sesion'))

    empresas_list = []
    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        buscar_nombre = request.args.get('nombre', '')
        buscar_nit = request.args.get('nit', '')
        filtrar_estado = request.args.get('estado', '')

        query = """
            SELECT nit_empresa, nombre, estado, certificado_representacion
            FROM empresas
            WHERE 1=1
        """
        params = []

        if buscar_nombre:
            query += " AND nombre LIKE %s"
            params.append(f"%{buscar_nombre}%")

        if buscar_nit:
            query += " AND nit_empresa LIKE %s"
            params.append(f"%{buscar_nit}%")

        if filtrar_estado and filtrar_estado != 'Todos los estados':
            query += " AND estado = %s"
            params.append(filtrar_estado)

        query += " ORDER BY nombre"
        cursor.execute(query, params)
        empresas_list = cursor.fetchall()

    except mysql.connector.Error as e:
        print(f"Error al consultar empresas: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()

    return render_template(
        'empresas.html',
        empresas=empresas_list,
        buscar_nombre=buscar_nombre,
        buscar_nit=buscar_nit,
        filtrar_estado=filtrar_estado
    )


# ------------------------------
# Ruta: Cambiar estado empresa
# ------------------------------
@empresas_bp.route('/cambiar_estado', methods=['POST'])
def cambiar_estado_empresa():
    data = request.get_json()
    nit = data.get('nit')
    nuevo_estado = data.get('estado')

    try:
        connection = get_db()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE empresas SET estado = %s WHERE nit_empresa = %s",
            (nuevo_estado, nit)
        )
        connection.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error al cambiar estado: {e}")
        return {"success": False}
    finally:
        if 'cursor' in locals():
            cursor.close()


# ------------------------------
# Ruta: Editar empresa
# ------------------------------
@empresas_bp.route('/editar/<nit>', methods=['GET', 'POST'])
def editar_empresa(nit):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.iniciar_sesion'))

    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        nombre = request.form['nombre']
        archivo = request.files.get('certificado')

        certificado_url = None
        if archivo and archivo.filename:
            nombre_seguro = secure_filename(archivo.filename)
            ruta_archivo = os.path.join(UPLOAD_CERT_FOLDER, f"{nit}_{nombre_seguro}")
            archivo.save(ruta_archivo)

            certificado_url = f"{nit}_{nombre_seguro}"

            cursor.execute("""
                UPDATE empresas 
                SET nombre = %s, certificado_representacion = %s
                WHERE nit_empresa = %s
            """, (nombre, certificado_url, nit))
        else:
            cursor.execute("""
                UPDATE empresas 
                SET nombre = %s
                WHERE nit_empresa = %s
            """, (nombre, nit))

        connection.commit()
        flash("Empresa actualizada correctamente", "success")
        cursor.close()
        return redirect(url_for('empresas.listar_empresas'))

    # -------------------------------
    # GET: cargar datos de la empresa
    # -------------------------------
    cursor.execute("SELECT * FROM empresas WHERE nit_empresa = %s", (nit,))
    empresa = cursor.fetchone()
    cursor.close()

    if empresa:
        return render_template('editar_empresa.html', empresa=empresa)
    else:
        flash("Empresa no encontrada", "error")
        return redirect(url_for('empresas.listar_empresas'))


# ------------------------------
# Ruta: Ver certificados
# ------------------------------
@empresas_bp.route('/certificados/<nombre_archivo>')
def ver_certificado(nombre_archivo):
    carpeta = os.path.join(os.getcwd(), 'uploads', 'certificados')
    ruta = os.path.join(carpeta, nombre_archivo)

    if not os.path.exists(ruta):
        abort(404, description="Archivo no encontrado.")

    extension = nombre_archivo.rsplit('.', 1)[-1].lower()

    if extension == 'pdf':
        return send_from_directory(carpeta, nombre_archivo)
    else:
        return send_from_directory(carpeta, nombre_archivo, as_attachment=True)

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from werkzeug.utils import secure_filename
import os
import mysql.connector
from datetime import datetime

documentos_bp = Blueprint('documentos', __name__)



# Configuración de archivos permitidos
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png'}
UPLOAD_FOLDER = 'uploads/documentos'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------------------
# Ruta: Listado de Documentos
# ------------------------------
@documentos_bp.route('/documentacion')
def documentacion():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))  # 👈 ajustado a blueprint auth
    
    try:
        buscar_nombre = request.args.get('nombre', '').strip()
        buscar_nit = request.args.get('nit', '').strip()
        filtrar_estado = request.args.get('estado', '')
        filtrar_formato = request.args.get('formato', '')

        connection = mysql.connector.connect(
            host='localhost',
            database='gestusSG',
            user='root',
            password=""
        )
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT d.*, e.nombre as nombre_empresa,
                   DATE_FORMAT(d.fecha_vencimiento, '%%d/%%m/%%Y') as fecha_vencimiento_formateada
            FROM documentos_empresa d
            JOIN empresas e ON d.nit_empresa = e.nit_empresa
            WHERE 1=1
        """
        params = []

        if buscar_nombre:
            query += " AND d.nombre LIKE %s"
            params.append(f"%{buscar_nombre}%")

        if buscar_nit:
            query += " AND d.nit_empresa LIKE %s"
            params.append(f"%{buscar_nit}%")

        if filtrar_estado:
            query += " AND d.estado = %s"
            params.append(filtrar_estado)

        if filtrar_formato:
            query += " AND d.formato = %s"
            params.append(filtrar_formato)

        query += " ORDER BY d.fecha_vencimiento DESC, d.id DESC"

        cursor.execute(query, params)
        documentos = cursor.fetchall()

        hoy = datetime.now().date()
        for doc in documentos:
            if doc['fecha_vencimiento']:
                dias_restantes = (doc['fecha_vencimiento'] - hoy).days
                doc['vencido'] = dias_restantes < 0
                doc['proximo_vencer'] = 0 <= dias_restantes <= 30
                doc['dias_restantes'] = dias_restantes

        return render_template('documentacion.html',
                               documentos=documentos,
                               buscar_nombre=buscar_nombre,
                               buscar_nit=buscar_nit,
                               filtrar_estado=filtrar_estado,
                               filtrar_formato=filtrar_formato)

    except mysql.connector.Error as e:
        print(f"Error en documentacion: {e}")
        flash('Error al cargar la documentación', 'error')
        return render_template('documentacion.html', documentos=[])
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

# ------------------------------
# Rutas CRUD
# ------------------------------
@documentos_bp.route('/agregar_documento')
def agregar_documento():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='gestusSG',
            user='root',
            password=""
        )
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT nit_empresa, nombre FROM empresas WHERE estado = 'Activa' ORDER BY nombre")
        empresas = cursor.fetchall()

        cursor.execute("SELECT id, nombre FROM formatos_globales ORDER BY nombre")
        formatos_globales = cursor.fetchall()

        return render_template('agregar_documento.html',
                               empresas=empresas,
                               formatos_globales=formatos_globales)

    except mysql.connector.Error as e:
        print(f"Error en agregar_documento: {e}")
        flash('Error al cargar datos del formulario', 'error')
        return redirect(url_for('documentos.documentacion'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()


@documentos_bp.route('/guardar_documento', methods=['POST'])
def guardar_documento():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        nit_empresa = request.form.get('nit_empresa', '').strip()
        nombre = request.form.get('nombre', '').strip()
        if not nit_empresa or not nombre:
            flash('Empresa y nombre del documento son obligatorios', 'error')
            return redirect(url_for('documentos.agregar_documento'))

        archivo = request.files.get('archivo')
        archivo_url = None

        if archivo and archivo.filename:
            if not allowed_file(archivo.filename):
                flash('Tipo de archivo no permitido', 'error')
                return redirect(url_for('documentos.agregar_documento'))

            filename = secure_filename(archivo.filename)
            unique_name = f"{nit_empresa}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            archivo_url = os.path.join(UPLOAD_FOLDER, unique_name)
            archivo.save(archivo_url)

        connection = mysql.connector.connect(
            host='localhost',
            database='gestusSG',
            user='root',
            password=""
        )
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO documentos_empresa (
                nit_empresa, formato_id, nombre, 
                archivo_url, fecha_vencimiento, 
                estado, formato
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            nit_empresa,
            request.form.get('formato_id') or None,
            nombre,
            archivo_url,
            request.form.get('fecha_vencimiento') or None,
            request.form.get('estado', 'Sin Diligenciar'),
            request.form.get('formato_archivo', 'PDF')
        ))

        connection.commit()
        flash('Documento guardado exitosamente', 'success')
        return redirect(url_for('documentos.documentacion'))

    except Exception as e:
        print(f"Error en guardar_documento: {e}")
        flash('Error interno al guardar el documento', 'error')
        return redirect(url_for('documentos.agregar_documento'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()


# ------------------------------
# RUTA: Editar Documento
# ------------------------------
@documentos_bp.route('/editar/<int:documento_id>')
def editar_documento(documento_id):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.iniciar_sesion'))

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT d.*, e.nombre as nombre_empresa
            FROM documentos_empresa d
            JOIN empresas e ON d.nit_empresa = e.nit_empresa
            WHERE d.id = %s
        """, (documento_id,))
        documento = cursor.fetchone()

        if not documento:
            flash('Documento no encontrado', 'error')
            return redirect(url_for('documentos.documentacion'))

        cursor.execute("SELECT nit_empresa, nombre FROM empresas WHERE estado = 'Activa' ORDER BY nombre")
        empresas = cursor.fetchall()

        cursor.execute("SELECT id, nombre FROM formatos_globales ORDER BY nombre")
        formatos_globales = cursor.fetchall()

        return render_template('editar_documento.html',
                               documento=documento,
                               empresas=empresas,
                               formatos_globales=formatos_globales)

    except mysql.connector.Error as e:
        print(f"Error en editar_documento: {e}")
        flash('Error al cargar documento', 'error')
        return redirect(url_for('documentos.documentacion'))
    finally:
        if 'cursor' in locals():
            cursor.close()

# ------------------------------
# RUTA: Actualizar Documento
# ------------------------------
@documentos_bp.route('/actualizar/<int:documento_id>', methods=['POST'])
def actualizar_documento(documento_id):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.iniciar_sesion'))

    try:
        nit_empresa = request.form.get('nit_empresa', '').strip()
        nombre = request.form.get('nombre', '').strip()
        if not nit_empresa or not nombre:
            flash('Empresa y nombre del documento son obligatorios', 'error')
            return redirect(url_for('documentacion.editar_documento', documento_id=documento_id))

        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        archivo = request.files.get('archivo')
        archivo_url = None

        if archivo and archivo.filename:
            if not allowed_file(archivo.filename):
                flash('Tipo de archivo no permitido', 'error')
                return redirect(url_for('documentacion.editar_documento', documento_id=documento_id))

            filename = secure_filename(archivo.filename)
            unique_name = f"{nit_empresa}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            archivo_url = os.path.join(UPLOAD_FOLDER, unique_name)
            archivo.save(archivo_url)

            cursor.execute("SELECT archivo_url FROM documentos_empresa WHERE id = %s", (documento_id,))
            archivo_anterior = cursor.fetchone()['archivo_url']
        else:
            archivo_anterior = None

        if archivo_url:
            query = """
                UPDATE documentos_empresa 
                SET nit_empresa = %s, formato_id = %s, nombre = %s,
                    archivo_url = %s, fecha_vencimiento = %s,
                    estado = %s, formato = %s
                WHERE id = %s
            """
            params = (
                nit_empresa,
                request.form.get('formato_id') or None,
                nombre,
                archivo_url,
                request.form.get('fecha_vencimiento') or None,
                request.form.get('estado', 'Sin Diligenciar'),
                request.form.get('formato_archivo', 'PDF'),
                documento_id
            )
        else:
            query = """
                UPDATE documentos_empresa 
                SET nit_empresa = %s, formato_id = %s, nombre = %s,
                    fecha_vencimiento = %s, estado = %s, formato = %s
                WHERE id = %s
            """
            params = (
                nit_empresa,
                request.form.get('formato_id') or None,
                nombre,
                request.form.get('fecha_vencimiento') or None,
                request.form.get('estado', 'Sin Diligenciar'),
                request.form.get('formato_archivo', 'PDF'),
                documento_id
            )

        cursor.execute(query, params)
        connection.commit()

        if archivo_url and archivo_anterior and os.path.exists(archivo_anterior):
            try:
                os.remove(archivo_anterior)
            except Exception as e:
                print(f"Error al eliminar archivo anterior: {e}")

        flash('Documento actualizado exitosamente', 'success')
        return redirect(url_for('documentos.documentacion'))

    except mysql.connector.Error as e:
        print(f"Error en actualizar_documento: {e}")
        flash('Error al actualizar documento', 'error')
        return redirect(url_for('documentacion.editar_documento', documento_id=documento_id))
    finally:
        if 'cursor' in locals():
            cursor.close()

# ------------------------------
# RUTA: Eliminar Documento
# ------------------------------
@documentos_bp.route('/eliminar/<int:documento_id>', methods=['POST'])
def eliminar_documento(documento_id):
    if 'usuario_id' not in session:
        return jsonify({'success': False, 'message': 'No autorizado'}), 401

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT archivo_url FROM documentos_empresa WHERE id = %s", (documento_id,))
        documento = cursor.fetchone()

        if not documento:
            return jsonify({'success': False, 'message': 'Documento no encontrado'}), 404

        cursor.execute("DELETE FROM documentos_empresa WHERE id = %s", (documento_id,))
        connection.commit()

        if documento['archivo_url'] and os.path.exists(documento['archivo_url']):
            try:
                os.remove(documento['archivo_url'])
            except Exception as e:
                print(f"Error al eliminar archivo: {e}")

        return jsonify({'success': True, 'message': 'Documento eliminado correctamente'})

    except mysql.connector.Error as e:
        print(f"Error en eliminar_documento: {e}")
        return jsonify({'success': False, 'message': 'Error en la base de datos'}), 500
    except Exception as e:
        print(f"Error inesperado en eliminar_documento: {e}")
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()

# ------------------------------
# RUTA: Descargar Documento
# ------------------------------
@documentos_bp.route('/descargar/<int:documento_id>')
def descargar_documento(documento_id):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.iniciar_sesion'))

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT archivo_url, nombre FROM documentos_empresa WHERE id = %s", (documento_id,))
        documento = cursor.fetchone()

        if not documento or not documento['archivo_url']:
            flash('Archivo no encontrado', 'error')
            return redirect(url_for('documentos.documentacion'))

        if not os.path.exists(documento['archivo_url']):
            flash('El archivo físico no existe', 'error')
            return redirect(url_for('documentos.documentacion'))

        return send_file(
            documento['archivo_url'],
            as_attachment=True,
            download_name=f"{documento['nombre']}.{documento['archivo_url'].split('.')[-1]}"
        )

    except mysql.connector.Error as e:
        print(f"Error en descargar_documento: {e}")
        flash('Error al descargar documento', 'error')
        return redirect(url_for('documentos.documentacion'))
    except Exception as e:
        print(f"Error inesperado en descargar_documento: {e}")
        flash('Error interno del servidor', 'error')
        return redirect(url_for('documentos.documentacion'))
    finally:
        if 'cursor' in locals():
            cursor.close()



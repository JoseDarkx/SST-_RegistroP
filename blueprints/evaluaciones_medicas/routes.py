import os
import mysql.connector
from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from flask import Blueprint

evaluaciones_medicas_bp = Blueprint(
    'evaluaciones_medicas', __name__, url_prefix='/evaluaciones_medicas'
)


# ===============================
# LISTAR EVALUACIONES MÉDICAS
# ===============================
@evaluaciones_medicas_bp.route('/evaluaciones_medicas', methods=['GET'])
def evaluaciones_medicas():
    if 'usuario' not in session:
        return redirect(url_for('auth.iniciar_sesion'))

    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)

    filtro_id = request.args.get('id', '').strip()
    nombre = request.args.get('nombre', '').strip()
    nit_empresa = request.args.get('nit_empresa', '').strip()

    query = """
        SELECT em.*, p.nombre_completo, p.documento_identidad, e.nombre AS empresa
        FROM evaluaciones_medicas em
        JOIN personal p ON em.personal_id = p.id
        JOIN empresas e ON em.nit_empresa = e.nit_empresa
        WHERE 1=1
    """
    params = []

    if filtro_id:
        query += " AND em.id = %s"
        params.append(filtro_id)

    if nombre:
        query += " AND em.medico_examinador LIKE %s"
        params.append(f"%{nombre}%")

    if nit_empresa:
        query += " AND em.nit_empresa = %s"
        params.append(nit_empresa)

    cursor.execute(query, params)
    evaluaciones = cursor.fetchall()

    cursor.execute("SELECT nit_empresa, nombre FROM empresas")
    empresas = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        'evaluaciones_medicas.html',
        evaluaciones=evaluaciones,
        empresas=empresas,
        filtro_id=filtro_id,
        filtro_nombre=nombre,
        filtro_empresa=nit_empresa
    )


# ===============================
# AGREGAR EVALUACIÓN MÉDICA
# ===============================
@evaluaciones_medicas_bp.route('/agregar_evaluaciones', methods=['GET', 'POST'])
def agregar_evaluaciones():
    if 'usuario' not in session:
        return redirect(url_for('auth.iniciar_sesion'))

    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
    SELECT p.id, p.nombre_completo, p.documento_identidad, e.nombre AS empresa, p.nit_empresa
    FROM personal p
    JOIN empresas e ON p.nit_empresa = e.nit_empresa
    WHERE 1=1  -- Se eliminó el filtro de estado
""")
    personal = cursor.fetchall()

    if request.method == 'POST':
        try:
            personal_id = int(request.form['personal_id'])
            nit_empresa = request.form['nit_empresa']
            fecha = request.form['fecha']
            tipo_evaluacion = request.form['tipo_evaluacion']
            medico_examinador = request.form['medico_examinador']
            restricciones = request.form['restricciones']
            observaciones = request.form['observaciones']
            recomendaciones = request.form['recomendaciones']

            archivo = request.files.get('archivo')
            archivo_url = None

            if archivo and archivo.filename != '':
                nombre_archivo = secure_filename(archivo.filename)
                carpeta_destino = os.path.join('static', 'uploads', 'archivos_evaluaciones')

                if not os.path.exists(carpeta_destino):
                    os.makedirs(carpeta_destino)

                ruta_archivo = os.path.join(carpeta_destino, nombre_archivo)
                archivo.save(ruta_archivo)

                archivo_url = f"uploads/archivos_evaluaciones/{nombre_archivo}"

            cursor.execute("""
                INSERT INTO evaluaciones_medicas (
                    personal_id, nit_empresa, fecha, tipo_evaluacion, medico_examinador,
                    archivo_url, restricciones, observaciones, recomendaciones
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                personal_id, nit_empresa, fecha, tipo_evaluacion, medico_examinador,
                archivo_url, restricciones, observaciones, recomendaciones
            ))

            conexion.commit()
            flash('Evaluación médica agregada correctamente', 'success')
            return redirect(url_for('evaluaciones_medicas.evaluaciones_medicas'))

        except Exception as e:
            flash(f'Error al guardar la evaluación: {str(e)}', 'danger')

    cursor.close()
    conexion.close()
    return render_template('agregar_evaluaciones.html', personal=personal)


# ===============================
# VER EVALUACIÓN MÉDICA
# ===============================
@evaluaciones_medicas_bp.route('/ver_evaluaciones/<int:evaluacion_id>')
def ver_evaluacion_medica(evaluacion_id):
    if 'usuario' not in session:
        return redirect(url_for('auth.iniciar_sesion'))

    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT em.*, p.nombre_completo, p.documento_identidad, e.nombre AS nombre_empresa
        FROM evaluaciones_medicas em
        JOIN personal p ON em.personal_id = p.id
        JOIN empresas e ON em.nit_empresa = e.nit_empresa
        WHERE em.id = %s
    """, (evaluacion_id,))
    
    evaluacion = cursor.fetchone()

    cursor.close()
    conexion.close()

    if not evaluacion:
        flash("Evaluación no encontrada", "warning")
        return redirect(url_for('evaluaciones_medicas.evaluaciones_medicas'))

    return render_template('ver_evaluaciones.html', evaluacion=evaluacion)


# ===============================
# EDITAR EVALUACIÓN MÉDICA
# ===============================
@evaluaciones_medicas_bp.route('/editar_evaluaciones/<int:evaluacion_id>', methods=['GET', 'POST'])
def editar_evaluaciones(evaluacion_id):
    if 'usuario' not in session:
        return redirect(url_for('auth.iniciar_sesion'))

    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT em.*, p.nombre_completo, p.documento_identidad, e.nombre AS empresa
        FROM evaluaciones_medicas em
        JOIN personal p ON em.personal_id = p.id
        JOIN empresas e ON p.nit_empresa = e.nit_empresa
        WHERE em.id = %s
    """, (evaluacion_id,))
    evaluacion = cursor.fetchone()

    if not evaluacion:
        flash("Evaluación no encontrada", "danger")
        return redirect(url_for('evaluaciones_medicas.evaluaciones_medicas'))

    if request.method == 'POST':
        fecha = request.form['fecha']
        tipo_evaluacion = request.form['tipo_evaluacion']
        medico_examinador = request.form['medico_examinador']
        restricciones = request.form['restricciones']
        observaciones = request.form['observaciones']
        recomendaciones = request.form['recomendaciones']

        archivo = request.files.get('archivo')
        archivo_url = evaluacion['archivo_url']

        if archivo and archivo.filename != '':
            nombre_archivo = secure_filename(archivo.filename)
            ruta_archivo = os.path.join('static/uploads/archivos_evaluaciones', nombre_archivo)
            archivo.save(ruta_archivo)
            archivo_url = f"uploads/archivos_evaluaciones/{nombre_archivo}"

        cursor.execute("""
            UPDATE evaluaciones_medicas
            SET fecha=%s, tipo_evaluacion=%s, medico_examinador=%s, archivo_url=%s,
                restricciones=%s, observaciones=%s, recomendaciones=%s
            WHERE id = %s
        """, (
            fecha, tipo_evaluacion, medico_examinador, archivo_url,
            restricciones, observaciones, recomendaciones, evaluacion_id
        ))
        conexion.commit()
        flash('Evaluación actualizada correctamente', 'success')
        return redirect(url_for('evaluaciones_medicas.evaluaciones_medicas'))

    cursor.close()
    conexion.close()
    return render_template('editar_evaluacion.html', evaluacion=evaluacion)

@evaluaciones_medicas_bp.route('/editar_evaluacion/<int:evaluacion_id>', methods=['GET', 'POST'])
def editar_evaluacion(evaluacion_id):
    """Redirigir desde la ruta singular a la plural"""
    if request.method == 'POST':
        return editar_evaluaciones(evaluacion_id)
    else:
        return redirect(url_for('evaluaciones_medicas.editar_evaluaciones', evaluacion_id=evaluacion_id))


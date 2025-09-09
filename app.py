# Importación de librerías necesarias
from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import mysql.connector  # Para conectar con MySQL
from werkzeug.security import generate_password_hash  # Para encriptar contraseñas

# Inicialización de la app Flask
app = Flask(__name__)
app.secret_key = 'clave_secreta'  # Clave para firmar sesiones (debe ser más segura en producción)
app.debug = True


# ------------------------------------
# CONEXIÓN GLOBAL A LA BASE DE DATOS
# ------------------------------------
conexion = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  # sin contraseña
    database="gestussg"
)
cursor = conexion.cursor(dictionary=True)  # Diccionario para obtener los resultados como claves-valor

# --------------------------------------
# RUTA: Registro de Usuario (/registrarse)
# --------------------------------------
@app.route('/registrarse', methods=['GET', 'POST'])
def registrarse():
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
            flash("Este usuario ya fue registrado anteriormente.", "error")  # Categoría 'error'
            return redirect(url_for('registrarse'))

        # Si no existe, lo insertamos
        cursor.execute("""
            INSERT INTO usuarios (nombre_completo, correo, usuario, contraseña, estado, nit_empresa, rol_id)
            VALUES (%s, %s, %s, %s, 'Activo', %s, %s)
        """, (nombre_completo, correo, usuario, contraseña, nit_empresa, rol_id))
        conexion.commit()

        flash("Usuario registrado exitosamente.", "success")  # Categoría 'success'
        return redirect(url_for('registrarse'))

    # Si es GET, cargamos roles y empresas para mostrar en el formulario
    cursor.execute("SELECT id, nombre FROM roles")
    roles = cursor.fetchall()
    cursor.execute("SELECT nit_empresa, nombre FROM empresas")
    empresas = cursor.fetchall()
    return render_template('register.html', roles=roles, empresas=empresas)


# --------------------------------------
# RUTA: Inicio de sesión (/iniciar-sesion)
# --------------------------------------
@app.route('/iniciar-sesion', methods=['GET', 'POST'])
def iniciar_sesion():
    if request.method == 'POST':
        # Capturar credenciales
        nit_empresa = request.form['nit_empresa']
        usuario = request.form['usuario']
        contraseña = request.form['contraseña']

        # Conexión y cursor
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="gestussg"
        )
        cursor = conexion.cursor(dictionary=True)

        # Buscar el usuario
        cursor.execute("""
            SELECT * FROM usuarios 
            WHERE usuario = %s AND nit_empresa = %s
        """, (usuario, nit_empresa))
        user = cursor.fetchone()

        # Validar usuario y contraseña
        if user and user['contraseña'] == contraseña:
            session['usuario_id'] = user['id']
            session['usuario'] = user['usuario']
            session['nit_empresa'] = user['nit_empresa']
            flash("Inicio de sesión exitoso.")
            cursor.close()
            conexion.close()
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciales incorrectas o usuario inactivo', 'error')

        cursor.close()
        conexion.close()

    return render_template('login.html')

# --------------------------------------
# RUTA: Dashboard principal (/dashboard)
# --------------------------------------
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))

    # Conexión a la base de datos
    conexion = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="",
        database="gestussg"
    )
    cursor = conexion.cursor(dictionary=True)

    # ==============================
    # Obtener datos del usuario actual
    # ==============================
    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    # ==============================
    # Obtener solo las empresas activas para el selector
    # ==============================
    cursor.execute("SELECT nit_empresa, nombre FROM empresas WHERE estado = 'Activa'")
    empresas = cursor.fetchall()

    # ==============================
    # Leer el NIT seleccionado desde el formulario (GET)
    # ==============================
    nit_seleccionado = request.args.get('nit_empresa')

    # ==============================
    # Contar solo  empresas activas (no depende de filtro)
    # ==============================
    cursor.execute("SELECT COUNT(*) AS total_empresas FROM empresas WHERE estado = 'Activa'")
    total_empresas = cursor.fetchone()['total_empresas']

    # ==============================
    # Contar evaluaciones activas (se cuentan todas porque no tienen nit_empresa)
    # ==============================
    cursor.execute("SELECT COUNT(*) AS total_evaluaciones FROM evaluaciones")
    total_evaluaciones = cursor.fetchone()['total_evaluaciones']

    # ==============================
    # Contar capacitaciones (con o sin filtro por empresa)
    # ==============================
    if nit_seleccionado:
        cursor.execute("SELECT COUNT(*) AS total_capacitaciones FROM capacitaciones WHERE nit_empresa = %s", (nit_seleccionado,))
    else:
        cursor.execute("SELECT COUNT(*) AS total_capacitaciones FROM capacitaciones")
    total_capacitaciones = cursor.fetchone()['total_capacitaciones']

    # ==============================
    # Gráfico: Incidentes por tipo (con filtro si hay nit_empresa)
    # ==============================
    if nit_seleccionado:
        cursor.execute("""
            SELECT i.tipo, COUNT(*) AS cantidad
            FROM incidentes i
            JOIN empresas e ON i.nit_empresa = e.nit_empresa
            WHERE e.estado = 'Activa'
            GROUP BY i.tipo
                """)
    else:
        cursor.execute("""
            SELECT tipo, COUNT(*) AS cantidad
            FROM incidentes
            GROUP BY tipo
        """)
    incidentes_por_tipo = cursor.fetchall()

    # ==============================
    # Gráfico: Estado de documentos (con filtro si hay nit_empresa)
    # ==============================
    if nit_seleccionado:
        cursor.execute("""
            SELECT d.estado, COUNT(*) AS cantidad
            FROM documentos_empresa d
            JOIN empresas e ON d.nit_empresa = e.nit_empresa
            WHERE e.estado = 'Activa'
            GROUP BY d.estado
        """)
    else:
        cursor.execute("""
            SELECT estado, COUNT(*) AS cantidad
            FROM documentos_empresa
            GROUP BY estado
        """)
    documentos_por_estado = cursor.fetchall()

    # ==============================
    # Cerrar conexión
    # ==============================
    cursor.close()
    conexion.close()

    # ==============================
    # Renderizar la plantilla con todos los datos
    # ==============================
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


   # ====================================
# SECCIÓN: EVALUACIONES MÉDICAS
# ====================================
@app.route('/evaluaciones_medicas', methods=['GET'])
def evaluaciones_medicas():
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    # Conexión a la base de datos
    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)

    # Obtener filtros del formulario (si los hay)
    filtro_id = request.args.get('id', '').strip()
    nombre = request.args.get('nombre', '').strip()
    nit_empresa = request.args.get('nit_empresa', '').strip()

    # Consulta SQL base
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

    # Obtener todas las empresas activas para el filtro
    cursor.execute("SELECT nit_empresa, nombre FROM empresas")
    empresas = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template('evaluaciones_medicas.html',
                           evaluaciones=evaluaciones,
                           empresas=empresas,
                           filtro_id=filtro_id,
                           filtro_nombre=nombre,
                           filtro_empresa=nit_empresa)


# --------------------------------------
# RUTA: Agregar Evaluación Médica
# --------------------------------------
@app.route('/agregar_evaluaciones', methods=['GET', 'POST'])
def agregar_evaluaciones():
    # Verificar si el usuario está logueado
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    # Conexión a la base de datos
    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)

    # Obtener lista de personal con su empresa
    cursor.execute("""
        SELECT p.id, p.nombre_completo, p.documento_identidad, e.nombre AS empresa, p.nit_empresa
        FROM personal p
        JOIN empresas e ON p.nit_empresa = e.nit_empresa
        WHERE p.estado = 'Activo'
    """)
    personal = cursor.fetchall()

    # Procesar formulario si se envió por POST
    if request.method == 'POST':
        try:

            # Obtener datos del formulario
            personal_id = int(request.form['personal_id'])
            nit_empresa = request.form['nit_empresa']
            fecha = request.form['fecha']
            tipo_evaluacion = request.form['tipo_evaluacion']
            medico_examinador = request.form['medico_examinador']
            restricciones = request.form['restricciones']
            observaciones = request.form['observaciones']
            recomendaciones = request.form['recomendaciones']


            # Procesar archivo adjunto si se sube
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

            # Insertar evaluación médica
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
            return redirect(url_for('evaluaciones_medicas'))

        except Exception as e:
            flash(f'Error al guardar la evaluación: {str(e)}', 'danger')


    # Cerrar conexión a la base de datos
    cursor.close()
    conexion.close()

    # Renderizar formulario HTML
    return render_template('agregar_evaluaciones.html', personal=personal)


# --------------------------------------
# RUTA: Ver Evaluacion Medica
# --------------------------------------
@app.route('/ver_evaluaciones/<int:evaluacion_id>')
def ver_evaluacion_medica(evaluacion_id):
    # Verifica si el usuario ha iniciado sesión
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    # Conexión a la base de datos
    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)

    # Consulta para obtener los datos de la evaluación médica junto con información del personal y la empresa
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
        return redirect(url_for('evaluaciones_medicas'))

    # Renderiza la plantilla con los datos obtenidos
    return render_template('ver_evaluaciones.html', evaluacion=evaluacion)

# --------------------------------------
# RUTA: Editar Evalucion Medica
# --------------------------------------

@app.route('/editar_evaluaciones/<int:evaluacion_id>', methods=['GET', 'POST'])
def editar_evaluaciones(evaluacion_id):
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)

    # Obtener datos de la evaluación médica
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
        return redirect(url_for('evaluaciones_medicas'))

    if request.method == 'POST':
        fecha = request.form['fecha']
        tipo_evaluacion = request.form['tipo_evaluacion']
        medico_examinador = request.form['medico_examinador']
        restricciones = request.form['restricciones']
        observaciones = request.form['observaciones']
        recomendaciones = request.form['recomendaciones']

        archivo = request.files.get('archivo')
        archivo_url = evaluacion['archivo_url']  # mantener archivo actual si no se sube uno nuevo

        if archivo and archivo.filename != '':
            nombre_archivo = secure_filename(archivo.filename)
            ruta_archivo = os.path.join('static/uploads/archivos_evaluaciones', nombre_archivo)
            archivo.save(ruta_archivo)
            archivo_url = ruta_archivo

        # Actualizar datos
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
        return redirect(url_for('evaluaciones_medicas'))

    cursor.close()
    conexion.close()
    return render_template('editar_evaluaciones.html', evaluacion=evaluacion)


# --------------------------------------
# RUTA: Gestion De EPP
# --------------------------------------
@app.route('/control_epp')
def control_epp():
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    # Conectar a la base de datos
    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)
    # ==============================
    # Obtener datos del usuario actual
    # ==============================
    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    # Consulta: Obtener todos los EPP asignados con info del personal y del EPP
    cursor.execute("""
    SELECT ea.id, ea.personal_id, ea.fecha_entrega, ea.estado, ea.observaciones, ea.firmado,
        p.nombre_completo AS nombre_personal,
        e.nombre AS nombre_epp
    FROM epp_asignados ea
    JOIN personal p ON ea.personal_id = p.id
    JOIN epp e ON ea.epp_id = e.id
    """)

    epp_asignados = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template('control_epp.html', usuario_actual=usuario, epp_asignados=epp_asignados)

# --------------------------------------
# RUTA: asignar EPP
# --------------------------------------
@app.route('/asignar_epp', methods=['GET', 'POST'])
def asignar_epp():
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)
    # ==============================
    # Obtener datos del usuario actual
    # ==============================
    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    # Obtener trabajadores con su información
    cursor.execute("""
        SELECT p.id, p.nombre_completo, p.cargo, e.nombre AS empresa
        FROM personal p
        JOIN empresas e ON p.nit_empresa = e.nit_empresa
        WHERE p.estado = 'Activo'
    """)
    personal = cursor.fetchall()

    # Obtener EPP con su información
    cursor.execute("""
        SELECT id, nombre, tipo_proteccion
        FROM epp
    """)
    epps = cursor.fetchall()
    

    if request.method == 'POST':
        try:
            personal_id = int(request.form['personal_id'])
            epp_id = int(request.form['epp_id'])
            fecha_entrega = request.form['fecha_entrega']
            estado = request.form['estado']
            observaciones = request.form.get('observaciones', '')
            firmado = 1 if 'firmado' in request.form else 0

            # Insertar en epp_asignados
            cursor.execute("""
                INSERT INTO epp_asignados (
                    epp_id, personal_id, fecha_entrega,
                    estado, observaciones, firmado
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                epp_id, personal_id, fecha_entrega,
                estado, observaciones, firmado
            ))

            conexion.commit()
            flash('EPP asignado correctamente.', 'success')
            return redirect(url_for('control_epp'))

        except Exception as e:
            flash("No se logró agregar la evaluación", "danger")

    cursor.close()
    conexion.close()

    return render_template('asignar_epp.html', usuario_actual=usuario, personal=personal, epps=epps)


# --------------------------------------
# RUTA: reporte EPP
# --------------------------------------
@app.route('/reporte_general_epp', methods=['GET', 'POST'])
def reporte_general_epp():
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    # Conectar a la base de datos
    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)
    # ==============================
    # Obtener datos del usuario actual
    # ==============================
    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    # Obtener parámetros del formulario de búsqueda
    tipo_epp = request.args.get('tipoEpp')
    nivel_riesgo = request.args.get('nivelRiesgo')  # Si tienes este campo en tu tabla
    fecha_inicio = request.args.get('fechaInicio')
    fecha_fin = request.args.get('fechaFin')

    # Construir condiciones dinámicas para los filtros
    condiciones = []
    parametros = []

    if tipo_epp and tipo_epp != "Todos":
        condiciones.append("e.nombre = %s")
        parametros.append(tipo_epp)

    if fecha_inicio:
        condiciones.append("ea.fecha_entrega >= %s")
        parametros.append(fecha_inicio)

    if fecha_fin:
        condiciones.append("ea.fecha_entrega <= %s")
        parametros.append(fecha_fin)

    where_clause = "WHERE " + " AND ".join(condiciones) if condiciones else ""

    # Consulta principal: contar EPP asignados
    query = f"""
        SELECT COUNT(DISTINCT ea.personal_id) AS trabajadores,
               COUNT(*) AS epp_asignados,
               SUM(CASE WHEN e.fecha_vencimiento >= CURDATE() THEN 1 ELSE 0 END) AS vigentes,
               SUM(CASE WHEN e.fecha_vencimiento BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) AS proximos_vencer,
               SUM(CASE WHEN e.fecha_vencimiento < CURDATE() THEN 1 ELSE 0 END) AS vencidos
        FROM epp_asignados ea
        JOIN epp e ON ea.epp_id = e.id
        {where_clause}
    """

    cursor.execute(query, parametros)
    resultado = cursor.fetchone()

    # Lógica de estado general
    estado = "OK"
    if resultado["vencidos"] > 5:
        estado = "Crítico"
    elif resultado["proximos_vencer"] > 5:
        estado = "Atención"

    # Armar diccionario con los datos
    resumen = {
        "trabajadores": resultado["trabajadores"],
        "epp_asignados": resultado["epp_asignados"],
        "vigentes": resultado["vigentes"],
        "proximos_vencer": resultado["proximos_vencer"],
        "vencidos": resultado["vencidos"],
        "estado": estado
    }

    cursor.close()
    conexion.close()

    # Renderizar plantilla con los datos
    return render_template('reporte_general_epp.html', usuario_actual=usuario, resumen=resumen)



# --------------------------------------
# RUTA: ver EPP
# --------------------------------------
@app.route('/ver_epp_asignado/<int:personal_id>')
def ver_epp_asignado(personal_id):
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)
    # ==============================
    # Obtener datos del usuario actual
    # ==============================
    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    # Obtener datos del trabajador
    cursor.execute("""
        SELECT nombre_completo, cargo, estado
        FROM personal
        WHERE id = %s
    """, (personal_id,))
    trabajador = cursor.fetchone()

    # Historial de entregas de EPP
    cursor.execute("""
        SELECT ea.fecha_entrega, e.nombre AS nombre_epp, e.normativa_cumplida AS modelo,
               e.fecha_vencimiento, 'Juan López' AS responsable
        FROM epp_asignados ea
        JOIN epp e ON ea.epp_id = e.id
        WHERE ea.personal_id = %s
        ORDER BY ea.fecha_entrega DESC
    """, (personal_id,))
    entregas = cursor.fetchall()

    # Historial de novedades (si tienes tabla)
    # Puedes personalizar esto si tienes una tabla de novedades de EPP
    cursor.execute("""
        SELECT '2025-03-12' AS fecha, e.nombre AS tipo_epp, 'Dañado' AS motivo,
               p.nombre_completo AS entidad, 'Aprobado' AS estado
        FROM epp_asignados ea
        JOIN epp e ON ea.epp_id = e.id
        JOIN personal p ON ea.personal_id = p.id
        WHERE ea.personal_id = %s
        LIMIT 2
    """, (personal_id,))
    novedades = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        'ver_epp_asignado.html',
        usuario_actual=usuario,
        trabajador=trabajador,
        entregas=entregas,
        novedades=novedades
    )


# --------------------------------------
# RUTA: editar EPP
# --------------------------------------
@app.route('/editar_epp_asignado/<int:asignacion_id>', methods=['GET', 'POST'])
def editar_epp_asignado(asignacion_id):
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)
    # ==============================
    # Obtener datos del usuario actual
    # ==============================
    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    if request.method == 'POST':
        epp_id = int(request.form['epp_id'])  # nuevo campo que llega desde el formulario
        fecha_entrega = request.form['fecha_entrega']
        estado = request.form['estado']
        observaciones = request.form['observaciones']
        firmado = True if request.form.get('firmado') == '1' else False

        cursor.execute("""
            UPDATE epp_asignados
            SET epp_id = %s, fecha_entrega = %s, estado = %s, observaciones = %s, firmado = %s
            WHERE id = %s
        """, (epp_id, fecha_entrega, estado, observaciones, firmado, asignacion_id))
        conexion.commit()
        cursor.close()
        conexion.close()

        flash('Asignación actualizada correctamente', 'success')
        return redirect(url_for('control_epp'))

    # Obtener datos de la asignación actual
    cursor.execute("""
        SELECT ea.*, p.nombre_completo AS nombre_personal
        FROM epp_asignados ea
        JOIN personal p ON ea.personal_id = p.id
        WHERE ea.id = %s
    """, (asignacion_id,))
    asignacion = cursor.fetchone()

    # Obtener lista de EPP para mostrar en el select
    cursor.execute("""
        SELECT id, nombre, tipo_proteccion, stock
        FROM epp
        ORDER BY nombre ASC
    """)
    lista_epp = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template('editar_epp_asignado.html',
                           usuario_actual=usuario,
                           asignacion=asignacion,
                           lista_epp=lista_epp)

# --------------------------------------
# RUTA: inventario EPP
# --------------------------------------
@app.route('/ver_inventario')
def ver_inventario():
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    # Conectar a la base de datos
    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)
    # ==============================
    # Obtener datos del usuario actual
    # ==============================
    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    # Obtener todos los EPP
    cursor.execute("SELECT * FROM epp")
    epps = cursor.fetchall()

    # Indicador: Total de EPP
    total_epp = len(epps)

    # Indicador: Stock bajo (vida útil < 120 días)
    cursor.execute("""
        SELECT COUNT(*) AS stock_bajo
        FROM epp
        WHERE DATEDIFF(fecha_vencimiento, CURDATE()) <= 120
    """)
    stock_bajo = cursor.fetchone()['stock_bajo']

    # Indicador: EPP Agotados (vida útil vencida)
    cursor.execute("""
        SELECT COUNT(*) AS agotados
        FROM epp
        WHERE fecha_vencimiento < CURDATE()
    """)
    agotados = cursor.fetchone()['agotados']

    # Indicador: EPP entregados este mes
    cursor.execute("""
        SELECT COUNT(*) AS entregados_mes
        FROM epp_asignados
        WHERE MONTH(fecha_entrega) = MONTH(CURDATE())
          AND YEAR(fecha_entrega) = YEAR(CURDATE())
    """)
    entregados_mes = cursor.fetchone()['entregados_mes']

    cursor.close()
    conexion.close()

    return render_template('ver_inventario.html',
        usuario_actual=usuario,
        epps=epps,
        total_epp=total_epp,
        stock_bajo=stock_bajo,
        agotados=agotados,
        entregados_mes=entregados_mes)
# --------------------------------------
# RUTA: inventario EPP/agregar
# --------------------------------------
@app.route('/agregar_epp', methods=['GET', 'POST'])
def agregar_epp():
    # Verifica si el usuario ha iniciado sesión
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))
    
    # ==============================
    # Obtener datos del usuario actual
    # ==============================
    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)  # opcional: dictionary=True para obtener dict en vez de tuplas

    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    # Cerramos cursor temporal
    cursor.close()
    conexion.close()

    if request.method == 'POST':
        try:
            # Obtener los datos del formulario
            nombre = request.form['nombre']
            tipo_proteccion = request.form['tipo_proteccion']
            normativa_cumplida = request.form['normativa_cumplida']
            proveedor = request.form['proveedor']
            vida_util_dias = int(request.form['vida_util_dias'])
            fecha_vencimiento = request.form['fecha_vencimiento']
            stock = int(request.form['stock'])

            # Conexión a la base de datos
            conexion = mysql.connector.connect(
                host='localhost',
                user='root',
                password='',
                database='gestusSG'
            )
            cursor = conexion.cursor()

            # Insertar nuevo EPP
            cursor.execute("""
                INSERT INTO epp (
                    nombre, tipo_proteccion, normativa_cumplida,
                    proveedor, vida_util_dias, fecha_vencimiento, stock
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                nombre, tipo_proteccion, normativa_cumplida,
                proveedor, vida_util_dias, fecha_vencimiento, stock
            ))

            conexion.commit()
            cursor.close()
            conexion.close()

            flash('Elemento de EPP agregado correctamente.', 'success')
            return redirect(url_for('inventario_epp'))

        except Exception as e:
            flash(f'Error al agregar EPP: {str(e)}', 'danger')

    # GET: Renderizar formulario vacío
    return render_template('agregar_epp.html', usuario_actual=usuario)



# --------------------------------------
# RUTA: inventario EPP/editar
# --------------------------------------
# Ruta para editar EPP (muestra formulario de edición)
@app.route('/editar_epp/<int:epp_id>', methods=['GET', 'POST'])
def editar_epp(epp_id):
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)
    # ==============================
    # Obtener datos del usuario actual
    # ==============================
    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    if request.method == 'POST':
        # Obtener datos del formulario y actualizar
        nombre = request.form['nombre']
        tipo_proteccion = request.form['tipo_proteccion']
        normativa_cumplida = request.form['normativa_cumplida']
        proveedor = request.form['proveedor']
        vida_util_dias = request.form['vida_util_dias']
        fecha_vencimiento = request.form['fecha_vencimiento']

        cursor.execute("""
            UPDATE epp
            SET nombre=%s, tipo_proteccion=%s, normativa_cumplida=%s, proveedor=%s,
                vida_util_dias=%s, fecha_vencimiento=%s
            WHERE id=%s
        """, (nombre, tipo_proteccion, normativa_cumplida, proveedor, vida_util_dias, fecha_vencimiento, epp_id))
        conexion.commit()
        flash("EPP actualizado correctamente", "success")
        return redirect(url_for('inventario_epp'))

    # Mostrar formulario con datos existentes
    cursor.execute("SELECT * FROM epp WHERE id = %s", (epp_id,))
    epp = cursor.fetchone()

    cursor.close()
    conexion.close()

    if not epp:
        flash("Elemento EPP no encontrado", "warning")
        return redirect(url_for('inventario_epp'))

    return render_template('editar_epp.html', usuario_actual=usuario, epp=epp)
# --------------------------------------
# RUTA: inventario EPP/eliminar
# --------------------------------------

# Ruta para eliminar EPP
@app.route('/eliminar_epp/<int:epp_id>')
def eliminar_epp(epp_id):
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="",
        database='gestusSG'
    )
    cursor = conexion.cursor()

    cursor.execute("DELETE FROM epp WHERE id = %s", (epp_id,))
    conexion.commit()

    cursor.close()
    conexion.close()

    flash("EPP eliminado correctamente", "success")
    return redirect(url_for('inventario_epp'))




# --------------------------------------
# RUTA: Recuperar contraseña
# --------------------------------------
@app.route('/recuperar_contraseña', methods=['GET', 'POST'])
def recuperar_contraseña():
    if request.method == "POST":
        # Obtener datos del formulario
        nit = request.form["nit_empresa"]
        correo = request.form["correo"]

        # Verificamos si el usuario existe
        cursor.execute("SELECT * FROM usuarios WHERE correo = %s AND nit_empresa = %s", (correo, nit))
        usuario = cursor.fetchone()

        if usuario:
            print("Usuario encontrado:", usuario)  # DEBUG

            # Insertamos la solicitud de recuperación
            sql = """
                INSERT INTO recuperacion_contraseña (nit_empresa, correo, fecha_solicitud, estado)
                VALUES (%s, %s, NOW(), 'Pendiente')
            """
            cursor.execute(sql, (nit, correo))
            conexion.commit()
            print("Solicitud guardada")  # DEBUG

            flash("Se ha enviado la solicitud al admin, pronto seras notificado", "success")
        else:
            print("Usuario NO encontrado")  # DEBUG
            flash("No se encontró un usuario con ese NIT y correo", "danger")

        return redirect(url_for("recuperar_contraseña"))

    return render_template("recuperar_contraseña.html")



# --------------------------------------
# RUTA: Solicitud contrseña Admin
# --------------------------------------
@app.route('/solicitudes_contrasena', methods=['GET', 'POST'])
def solicitudes_contrasena():
    # Redirigir si el usuario no ha iniciado sesión
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))

    # Conexión a la base de datos
    conexion = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="",
        database="gestussg"
    )
    cursor = conexion.cursor(dictionary=True)

    # ============================
    # Obtener datos del usuario actual
    # ============================
    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    # ============================
    # Verificar si es administrador
    # ============================
    if usuario['rol'] != 'Administrador':
        cursor.close()
        conexion.close()
        return "Acceso denegado", 403

    # ============================
    # Procesar formulario POST
    # ============================
    if request.method == 'POST':
        solicitud_id = request.form.get('solicitud_id')
        nueva_contrasena = request.form.get('nueva_contrasena')

        # Buscar el correo de la solicitud
        cursor.execute("SELECT correo FROM recuperacion_contraseña WHERE id = %s", (solicitud_id,))
        solicitud = cursor.fetchone()

        if solicitud:
            correo = solicitud['correo']

            # Generar hash de la nueva contraseña
            hashed_password = generate_password_hash(nueva_contrasena)

            # Actualizar la contraseña del usuario
            cursor.execute("UPDATE usuarios SET contraseña = %s WHERE correo = %s", (hashed_password, correo))

            # Marcar la solicitud como 'Atendida'
            cursor.execute("UPDATE recuperacion_contraseña SET estado = 'Atendida' WHERE id = %s", (solicitud_id,))

            # Guardar cambios
            conexion.commit()

    # ============================
    # Obtener todas las solicitudes pendientes
    # ============================
    cursor.execute("SELECT * FROM recuperacion_contraseña WHERE estado = 'Pendiente'")
    solicitudes = cursor.fetchall()

    # Cerrar conexión
    cursor.close()
    conexion.close()

    # Renderizar plantilla HTML con las solicitudes y datos del usuario
    return render_template('solicitudes_contrasena.html', solicitudes=solicitudes, usuario_actual=usuario)



# ---------------------------
# Ruta principal (Página de inicio)
# ---------------------------
@app.route('/')
def index():
    return render_template('index.html')

#------------------------------
# Ruta documentacion
#------------------------------

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from werkzeug.utils import secure_filename
import os
import mysql.connector
from datetime import datetime

# Configuración de archivos permitidos
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png'}
UPLOAD_FOLDER = 'uploads/documentos'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --------------------------------------
# RUTAS DE DOCUMENTACIÓN MEJORADAS
# --------------------------------------

@app.route('/documentacion')
def documentacion():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    try:
        # Obtener parámetros de búsqueda
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
        
        # Consulta optimizada con JOIN y filtros
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
        
        # Calcular estado de vencimiento
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

@app.route('/agregar_documento')
def agregar_documento():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
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
        return redirect(url_for('documentacion'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

@app.route('/guardar_documento', methods=['POST'])
def guardar_documento():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    try:
        # Validar campos obligatorios
        nit_empresa = request.form.get('nit_empresa', '').strip()
        nombre = request.form.get('nombre', '').strip()
        if not nit_empresa or not nombre:
            flash('Empresa y nombre del documento son obligatorios', 'error')
            return redirect(url_for('agregar_documento'))
        
        # Procesar archivo
        archivo = request.files.get('archivo')
        archivo_url = None
        
        if archivo and archivo.filename:
            if not allowed_file(archivo.filename):
                flash('Tipo de archivo no permitido', 'error')
                return redirect(url_for('agregar_documento'))
            
            filename = secure_filename(archivo.filename)
            unique_name = f"{nit_empresa}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            archivo_url = os.path.join(UPLOAD_FOLDER, unique_name)
            archivo.save(archivo_url)
        
        # Insertar en base de datos
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
        return redirect(url_for('documentacion'))
        
    except mysql.connector.Error as e:
        print(f"Error en guardar_documento: {e}")
        flash('Error al guardar el documento', 'error')
        return redirect(url_for('agregar_documento'))
    except Exception as e:
        print(f"Error inesperado en guardar_documento: {e}")
        flash('Error interno del servidor', 'error')
        return redirect(url_for('agregar_documento'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

@app.route('/editar_documento/<int:documento_id>')
def editar_documento(documento_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='gestusSG',
            user='root',
            password=""
        )
        cursor = connection.cursor(dictionary=True)
        
        # Obtener documento con JOIN para nombre de empresa
        cursor.execute("""
            SELECT d.*, e.nombre as nombre_empresa
            FROM documentos_empresa d
            JOIN empresas e ON d.nit_empresa = e.nit_empresa
            WHERE d.id = %s
        """, (documento_id,))
        documento = cursor.fetchone()
        
        if not documento:
            flash('Documento no encontrado', 'error')
            return redirect(url_for('documentacion'))
        
        # Obtener datos para selects
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
        return redirect(url_for('documentacion'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

@app.route('/actualizar_documento/<int:documento_id>', methods=['POST'])
def actualizar_documento(documento_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    try:
        # Validar campos obligatorios
        nit_empresa = request.form.get('nit_empresa', '').strip()
        nombre = request.form.get('nombre', '').strip()
        if not nit_empresa or not nombre:
            flash('Empresa y nombre del documento son obligatorios', 'error')
            return redirect(url_for('editar_documento', documento_id=documento_id))
        
        connection = mysql.connector.connect(
            host='localhost',
            database='gestusSG',
            user='root',
            password=""
        )
        cursor = connection.cursor(dictionary=True)
        
        # Procesar archivo si se subió uno nuevo
        archivo = request.files.get('archivo')
        archivo_url = None
        
        if archivo and archivo.filename:
            if not allowed_file(archivo.filename):
                flash('Tipo de archivo no permitido', 'error')
                return redirect(url_for('editar_documento', documento_id=documento_id))
            
            filename = secure_filename(archivo.filename)
            unique_name = f"{nit_empresa}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            archivo_url = os.path.join(UPLOAD_FOLDER, unique_name)
            archivo.save(archivo_url)
            
            # Obtener archivo anterior para eliminarlo después
            cursor.execute("SELECT archivo_url FROM documentos_empresa WHERE id = %s", (documento_id,))
            archivo_anterior = cursor.fetchone()['archivo_url']
        
        # Construir query de actualización
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
        
        # Eliminar archivo anterior si se subió uno nuevo
        if archivo_url and archivo_anterior and os.path.exists(archivo_anterior):
            try:
                os.remove(archivo_anterior)
            except Exception as e:
                print(f"Error al eliminar archivo anterior: {e}")
        
        flash('Documento actualizado exitosamente', 'success')
        return redirect(url_for('documentacion'))
        
    except mysql.connector.Error as e:
        print(f"Error en actualizar_documento: {e}")
        flash('Error al actualizar documento', 'error')
        return redirect(url_for('editar_documento', documento_id=documento_id))
    except Exception as e:
        print(f"Error inesperado en actualizar_documento: {e}")
        flash('Error interno del servidor', 'error')
        return redirect(url_for('editar_documento', documento_id=documento_id))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

@app.route('/eliminar_documento/<int:documento_id>', methods=['POST'])
def eliminar_documento(documento_id):
    if 'usuario' not in session:
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='gestusSG',
            user='root',
            password=""
        )
        cursor = connection.cursor(dictionary=True)
        
        # Obtener archivo para eliminarlo después
        cursor.execute("SELECT archivo_url FROM documentos_empresa WHERE id = %s", (documento_id,))
        documento = cursor.fetchone()
        
        if not documento:
            return jsonify({'success': False, 'message': 'Documento no encontrado'}), 404
        
        # Eliminar de la base de datos
        cursor.execute("DELETE FROM documentos_empresa WHERE id = %s", (documento_id,))
        connection.commit()
        
        # Eliminar archivo físico si existe
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
        if 'connection' in locals():
            connection.close()

@app.route('/descargar_documento/<int:documento_id>')
def descargar_documento(documento_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='gestusSG',
            user='root',
            password=""
        )
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT archivo_url, nombre FROM documentos_empresa WHERE id = %s", (documento_id,))
        documento = cursor.fetchone()
        
        if not documento or not documento['archivo_url']:
            flash('Archivo no encontrado', 'error')
            return redirect(url_for('documentacion'))
        
        if not os.path.exists(documento['archivo_url']):
            flash('El archivo físico no existe', 'error')
            return redirect(url_for('documentacion'))
        
        return send_file(
            documento['archivo_url'],
            as_attachment=True,
            download_name=f"{documento['nombre']}.{documento['archivo_url'].split('.')[-1]}"
        )
        
    except mysql.connector.Error as e:
        print(f"Error en descargar_documento: {e}")
        flash('Error al descargar documento', 'error')
        return redirect(url_for('documentacion'))
    except Exception as e:
        print(f"Error inesperado en descargar_documento: {e}")
        flash('Error interno del servidor', 'error')
        return redirect(url_for('documentacion'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()
            
            

#------------------------------
# Ruta empresas
#------------------------------

@app.route('/empresas')
def empresas():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    empresas_list = []
    
    try:
        # Conectar directamente a la base de datos
        connection = mysql.connector.connect(
            host='localhost',  # Cambia por tu host
            database='gestusSG',
            user='root',  # Cambia por tu usuario
            password=""  # Cambia por tu contraseña
        )
        
        cursor = connection.cursor(dictionary=True)
        
        # Obtener parámetros de búsqueda y filtrado
        buscar_nombre = request.args.get('nombre', '')
        buscar_nit = request.args.get('nit', '')
        filtrar_estado = request.args.get('estado', '')
        
        # Construir la consulta SQL dinámicamente
        query = "SELECT nit_empresa, nombre, estado, certificado_representacion FROM empresas WHERE 1=1"
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
        if 'connection' in locals():
            connection.close()
    
    return render_template('empresas.html', 
                            empresas=empresas_list,
                            buscar_nombre=buscar_nombre,
                            buscar_nit=buscar_nit,
                            filtrar_estado=filtrar_estado)


#------------------------------
# Ruta cambiar estado de  empresa
#------------------------------

@app.route('/cambiar_estado_empresa', methods=['POST'])
def cambiar_estado_empresa():
    # Lógica para cambiar estado
    data = request.get_json()
    nit = data.get('nit')
    nuevo_estado = data.get('estado')
    
    try:
        # Conectar directamente a la base de datos
        connection = mysql.connector.connect(
            host='localhost',  # Cambia por tu host
            database='gestusSG',
            user='root',  # Cambia por tu usuario
            password=""  # Cambia por tu contraseña
        )
        cursor = connection.cursor()
        cursor.execute("UPDATE empresas SET estado = %s WHERE nit_empresa = %s", (nuevo_estado, nit))
        connection.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error al cambiar estado: {e}")
        return {"success": False}
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'connection' in locals(): connection.close()
    
#------------------------------
# Ruta editar empresa
#------------------------------

import os
from werkzeug.utils import secure_filename

UPLOAD_CERT_FOLDER = 'uploads/certificados'
os.makedirs(UPLOAD_CERT_FOLDER, exist_ok=True)

@app.route('/editar_empresa/<nit>', methods=['GET', 'POST'])
def editar_empresa(nit):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    connection = mysql.connector.connect(
        host='localhost',
        database='gestusSG',
        user='root',
        password=""
    )
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
        connection.close()
        return redirect(url_for('empresas'))

    # -------------------------------
    # GET: cargar datos de la empresa
    # -------------------------------
    cursor.execute("SELECT * FROM empresas WHERE nit_empresa = %s", (nit,))
    empresa = cursor.fetchone()
    cursor.close()
    connection.close()

    if empresa:
        return render_template('editar_empresa.html', empresa=empresa)
    else:
        flash("Empresa no encontrada", "error")
        return redirect(url_for('empresas'))


#------------------------------
# Ruta ver certificados de  empresa
#------------------------------
import os
from flask import send_from_directory, abort

@app.route('/certificados/<nombre_archivo>')
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
    

# Agregar estas rutas al archivo principal de Flask

#------------------------------
# RUTAS PARA CAPACITACIONES
#------------------------------

@app.route('/capacitaciones')
def capacitaciones():
    """Mostrar listado de capacitaciones con evaluaciones"""
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))
    
    try:
        # Conectar a la base de datos
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="gestussg"
        )
        cursor = connection.cursor(dictionary=True)
        
        # Obtener capacitaciones con nombre de empresa
        cursor.execute("""
            SELECT c.*, e.nombre as nombre_empresa
            FROM capacitaciones c
            JOIN empresas e ON c.nit_empresa = e.nit_empresa
            ORDER BY c.fecha DESC
        """)
        capacitaciones_list = cursor.fetchall()
        
        # Obtener empresas activas para el formulario
        cursor.execute("""
            SELECT nit_empresa, nombre 
            FROM empresas 
            WHERE estado = 'Activa' 
            ORDER BY nombre
        """)
        empresas = cursor.fetchall()
        
        # Obtener evaluaciones de capacitación
        cursor.execute("""
            SELECT * FROM evaluaciones_capacitacion
            ORDER BY participante
        """)
        evaluaciones = cursor.fetchall()
        
        return render_template('capacitaciones.html', 
                             capacitaciones=capacitaciones_list,
                             empresas=empresas,
                             evaluaciones=evaluaciones)
        
    except mysql.connector.Error as e:
        print(f"Error en capacitaciones: {e}")
        flash('Error al cargar las capacitaciones', 'error')
        return render_template('capacitaciones.html', 
                             capacitaciones=[], empresas=[], evaluaciones=[])
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()


@app.route('/crear_capacitacion', methods=['POST'])
def crear_capacitacion():
    """Crear nueva capacitación"""
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))
    
    try:
        # Obtener datos del formulario
        nit_empresa = request.form['empresa']
        fecha = request.form['fecha']
        responsable = request.form['responsable']
        estado = request.form['estado']
        
        # Validar campos obligatorios
        if not nit_empresa or not fecha or not responsable:
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('capacitaciones'))
        
        # Conectar a la base de datos
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="gestussg"
        )
        cursor = connection.cursor()
        
        # Insertar nueva capacitación
        cursor.execute("""
            INSERT INTO capacitaciones (nit_empresa, fecha, responsable, estado, fecha_creacion)
            VALUES (%s, %s, %s, %s, NOW())
        """, (nit_empresa, fecha, responsable, estado))
        
        connection.commit()
        flash('Capacitación creada exitosamente', 'success')
        
    except mysql.connector.Error as e:
        print(f"Error al crear capacitación: {e}")
        flash('Error al crear la capacitación', 'error')
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()
    
    return redirect(url_for('capacitaciones'))


@app.route('/editar_capacitacion/<int:capacitacion_id>', methods=['GET', 'POST'])
def editar_capacitacion(capacitacion_id):
    """Editar capacitación existente"""
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))
    
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="gestussg"
        )
        cursor = connection.cursor(dictionary=True)
        
        if request.method == 'POST':
            # Actualizar capacitación
            nit_empresa = request.form['empresa']
            fecha = request.form['fecha']
            responsable = request.form['responsable']
            estado = request.form['estado']
            
            cursor.execute("""
                UPDATE capacitaciones 
                SET nit_empresa = %s, fecha = %s, responsable = %s, estado = %s
                WHERE id = %s
            """, (nit_empresa, fecha, responsable, estado, capacitacion_id))
            
            connection.commit()
            flash('Capacitación actualizada exitosamente', 'success')
            return redirect(url_for('capacitaciones'))
        
        else:
            # Obtener datos de la capacitación
            cursor.execute("SELECT * FROM capacitaciones WHERE id = %s", (capacitacion_id,))
            capacitacion = cursor.fetchone()
            
            if not capacitacion:
                flash('Capacitación no encontrada', 'error')
                return redirect(url_for('capacitaciones'))
            
            # Obtener empresas para el select
            cursor.execute("SELECT nit_empresa, nombre FROM empresas WHERE estado = 'Activa'")
            empresas = cursor.fetchall()
            
            return render_template('editar_capacitacion.html', 
                                 capacitacion=capacitacion, empresas=empresas)
            
    except mysql.connector.Error as e:
        print(f"Error al editar capacitación: {e}")
        flash('Error al editar la capacitación', 'error')
        return redirect(url_for('capacitaciones'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()


@app.route('/eliminar_capacitacion/<int:capacitacion_id>', methods=['POST'])
def eliminar_capacitacion(capacitacion_id):
    """Eliminar capacitación"""
    if 'usuario_id' not in session:
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="gestussg"
        )
        cursor = connection.cursor()
        
        # Verificar si existe la capacitación
        cursor.execute("SELECT id FROM capacitaciones WHERE id = %s", (capacitacion_id,))
        if not cursor.fetchone():
            return jsonify({'success': False, 'message': 'Capacitación no encontrada'}), 404
        
        # Eliminar evaluaciones asociadas primero (si existen)
        cursor.execute("DELETE FROM evaluaciones_capacitacion WHERE capacitacion_id = %s", (capacitacion_id,))
        
        # Eliminar la capacitación
        cursor.execute("DELETE FROM capacitaciones WHERE id = %s", (capacitacion_id,))
        
        connection.commit()
        return jsonify({'success': True, 'message': 'Capacitación eliminada correctamente'})
        
    except mysql.connector.Error as e:
        print(f"Error al eliminar capacitación: {e}")
        return jsonify({'success': False, 'message': 'Error en la base de datos'}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()


#------------------------------
# RUTAS PARA EVALUACIONES DE CAPACITACIÓN
#------------------------------

@app.route('/agregar_evaluacion', methods=['GET', 'POST'])
def agregar_evaluacion():
    """Agregar nueva evaluación de capacitación"""
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))
    
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="gestussg"
        )
        cursor = connection.cursor(dictionary=True)
        
        if request.method == 'POST':
            # Obtener datos del formulario
            capacitacion_id = request.form.get('capacitacion_id')
            participante = request.form['participante']
            pre_test = request.form['pre_test']
            post_test = request.form['post_test']
            
            # Calcular resultado automáticamente
            pre_test_num = float(pre_test) if pre_test else 0
            post_test_num = float(post_test) if post_test else 0
            
            if post_test_num >= 70:  # Criterio de aprobación
                resultado = 'Aprobado'
            elif post_test_num < 70 and post_test_num >= 60:
                resultado = 'Requiere'
            else:
                resultado = 'No aprobado'
            
            # Insertar evaluación
            cursor.execute("""
                INSERT INTO evaluaciones_capacitacion 
                (capacitacion_id, participante, pre_test, post_test, resultado, fecha_evaluacion)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (capacitacion_id, participante, pre_test_num, post_test_num, resultado))
            
            connection.commit()
            flash('Evaluación agregada exitosamente', 'success')
            return redirect(url_for('capacitaciones'))
        
        else:
            # Obtener capacitaciones para el select
            cursor.execute("""
                SELECT c.id, c.fecha, e.nombre as empresa_nombre
                FROM capacitaciones c
                JOIN empresas e ON c.nit_empresa = e.nit_empresa
                ORDER BY c.fecha DESC
            """)
            capacitaciones_list = cursor.fetchall()
            
            return render_template('agregar_evaluacion.html', capacitaciones=capacitaciones_list)
            
    except mysql.connector.Error as e:
        print(f"Error en agregar_evaluacion: {e}")
        flash('Error al procesar la evaluación', 'error')
        return redirect(url_for('capacitaciones'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()


@app.route('/editar_evaluacion/<int:evaluacion_id>', methods=['GET', 'POST'])
def editar_evaluacion(evaluacion_id):
    """Editar evaluación de capacitación"""
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))
    
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="gestussg"
        )
        cursor = connection.cursor(dictionary=True)
        
        if request.method == 'POST':
            # Actualizar evaluación
            participante = request.form['participante']
            pre_test = request.form['pre_test']
            post_test = request.form['post_test']
            
            # Calcular resultado
            post_test_num = float(post_test) if post_test else 0
            if post_test_num >= 70:
                resultado = 'Aprobado'
            elif post_test_num >= 60:
                resultado = 'Requiere'
            else:
                resultado = 'No aprobado'
            
            cursor.execute("""
                UPDATE evaluaciones_capacitacion 
                SET participante = %s, pre_test = %s, post_test = %s, resultado = %s
                WHERE id = %s
            """, (participante, pre_test, post_test, resultado, evaluacion_id))
            
            connection.commit()
            flash('Evaluación actualizada exitosamente', 'success')
            return redirect(url_for('capacitaciones'))
        
        else:
            # Obtener datos de la evaluación
            cursor.execute("SELECT * FROM evaluaciones_capacitacion WHERE id = %s", (evaluacion_id,))
            evaluacion = cursor.fetchone()
            
            if not evaluacion:
                flash('Evaluación no encontrada', 'error')
                return redirect(url_for('capacitaciones'))
            
            return render_template('editar_evaluacion.html', evaluacion=evaluacion)
            
    except mysql.connector.Error as e:
        print(f"Error al editar evaluación: {e}")
        flash('Error al editar la evaluación', 'error')
        return redirect(url_for('capacitaciones'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()


#------------------------------
# RUTAS PARA REPORTES DE CAPACITACIONES
#------------------------------

@app.route('/reporte_capacitaciones_pdf')
def reporte_capacitaciones_pdf():
    """Generar reporte PDF de capacitaciones"""
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))
    
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from io import BytesIO
        import tempfile
        
        # Conectar a la base de datos
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="gestussg"
        )
        cursor = connection.cursor(dictionary=True)
        
        # Obtener datos para el reporte
        cursor.execute("""
            SELECT c.fecha, e.nombre as empresa, c.responsable, c.estado,
                   COUNT(ec.id) as total_evaluaciones,
                   SUM(CASE WHEN ec.resultado = 'Aprobado' THEN 1 ELSE 0 END) as aprobados
            FROM capacitaciones c
            JOIN empresas e ON c.nit_empresa = e.nit_empresa
            LEFT JOIN evaluaciones_capacitacion ec ON c.id = ec.capacitacion_id
            GROUP BY c.id, c.fecha, e.nombre, c.responsable, c.estado
            ORDER BY c.fecha DESC
        """)
        datos = cursor.fetchall()
        
        # Crear PDF en memoria
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        
        # Título
        story.append(Paragraph("Reporte de Efectividad de Capacitaciones", title_style))
        story.append(Paragraph("<br/><br/>", styles['Normal']))
        
        # Crear tabla
        data = [['Fecha', 'Empresa', 'Responsable', 'Estado', 'Evaluaciones', 'Aprobados', 'Efectividad']]
        
        for row in datos:
            efectividad = f"{(row['aprobados'] / max(row['total_evaluaciones'], 1)) * 100:.1f}%" if row['total_evaluaciones'] > 0 else "N/A"
            data.append([
                str(row['fecha']),
                row['empresa'],
                row['responsable'],
                row['estado'],
                str(row['total_evaluaciones']),
                str(row['aprobados']),
                efectividad
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        doc.build(story)
        
        buffer.seek(0)
        
        return send_file(
            BytesIO(buffer.read()),
            mimetype='application/pdf',
            as_attachment=True,
            download_name='reporte_capacitaciones.pdf'
        )
        
    except Exception as e:
        print(f"Error al generar PDF: {e}")
        flash('Error al generar el reporte PDF. Instala reportlab: pip install reportlab', 'error')
        return redirect(url_for('capacitaciones'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()


@app.route('/reporte_capacitaciones_excel')
def reporte_capacitaciones_excel():
    """Exportar reporte Excel de capacitaciones"""
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))
    
    try:
        import pandas as pd
        from io import BytesIO
        
        # Conectar a la base de datos
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="gestussg"
        )
        
        # Obtener datos
        query = """
            SELECT c.fecha, e.nombre as empresa, c.responsable, c.estado,
                   COUNT(ec.id) as total_evaluaciones,
                   SUM(CASE WHEN ec.resultado = 'Aprobado' THEN 1 ELSE 0 END) as aprobados,
                   ROUND((SUM(CASE WHEN ec.resultado = 'Aprobado' THEN 1 ELSE 0 END) / 
                         GREATEST(COUNT(ec.id), 1)) * 100, 2) as efectividad_porcentaje
            FROM capacitaciones c
            JOIN empresas e ON c.nit_empresa = e.nit_empresa
            LEFT JOIN evaluaciones_capacitacion ec ON c.id = ec.capacitacion_id
            GROUP BY c.id, c.fecha, e.nombre, c.responsable, c.estado
            ORDER BY c.fecha DESC
        """
        
        df = pd.read_sql(query, connection)
        
        # Crear archivo Excel en memoria
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Capacitaciones', index=False)
            
            # Obtener detalles de evaluaciones
            query_evaluaciones = """
                SELECT c.fecha as fecha_capacitacion, e.nombre as empresa, 
                       ec.participante, ec.pre_test, ec.post_test, ec.resultado
                FROM evaluaciones_capacitacion ec
                JOIN capacitaciones c ON ec.capacitacion_id = c.id
                JOIN empresas e ON c.nit_empresa = e.nit_empresa
                ORDER BY c.fecha DESC, ec.participante
            """
            df_evaluaciones = pd.read_sql(query_evaluaciones, connection)
            df_evaluaciones.to_excel(writer, sheet_name='Evaluaciones_Detalle', index=False)
        
        buffer.seek(0)
        
        return send_file(
            BytesIO(buffer.read()),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='reporte_capacitaciones.xlsx'
        )
        
    except Exception as e:
        print(f"Error al generar Excel: {e}")
        flash('Error al generar el reporte Excel. Instala pandas y openpyxl: pip install pandas openpyxl', 'error')
        return redirect(url_for('capacitaciones'))
    finally:
        if 'connection' in locals():
            connection.close()


# Agregar también estas rutas AJAX para mejorar la experiencia de usuario

@app.route('/api/capacitaciones/<int:capacitacion_id>/evaluaciones')
def api_evaluaciones_capacitacion(capacitacion_id):
    """API para obtener evaluaciones de una capacitación específica"""
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root", 
            password="",
            database="gestussg"
        )
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT * FROM evaluaciones_capacitacion 
            WHERE capacitacion_id = %s 
            ORDER BY participante
        """, (capacitacion_id,))
        
        evaluaciones = cursor.fetchall()
        return jsonify({'evaluaciones': evaluaciones})
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()


#------------------------------
# Ruta registro empresa
#------------------------------

@app.route('/registro-empresa', methods=['GET', 'POST'])
def registro_empresa():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('registerEmpresa.html')

#------------------------------
# Ruta registro usuario
#------------------------------

@app.route('/registro-usuario', methods=['GET', 'POST'])
def registro_usuario():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('registerUsu.html')

# --------------------------------------
# RUTA: Cerrar sesión
# --------------------------------------
@app.route('/cerrar-sesion')
def cerrar_sesion():
    session.clear()  # Eliminar variables de sesión
    flash("Has cerrado sesión correctamente.")
    return redirect(url_for('iniciar_sesion'))

# --------------------------------------
# Ejecutar la aplicación
# --------------------------------------
if __name__ == '__main__':
    app.run(debug=True)  # Modo debug activado para desarrollo


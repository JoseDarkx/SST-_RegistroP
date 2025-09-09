from flask import render_template, request, redirect, url_for, session, flash
from extensions import get_db
from . import epp_bp

# ============================================================
# CONTROL DE EPP
# ============================================================
@epp_bp.route('/control_epp')
def control_epp():
    if 'usuario' not in session:
        return redirect(url_for('auth.iniciar_sesion'))

    conexion = get_db()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

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
    return render_template('control_epp.html', usuario_actual=usuario, epp_asignados=epp_asignados)


# ============================================================
# ASIGNAR EPP
# ============================================================
@epp_bp.route('/asignar_epp', methods=['GET', 'POST'])
def asignar_epp():
    if 'usuario' not in session:
        return redirect(url_for('auth.iniciar_sesion'))

    conexion = get_db()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    cursor.execute("""
        SELECT p.id, p.nombre_completo, p.cargo, e.nombre AS empresa
        FROM personal p
        JOIN empresas e ON p.nit_empresa = e.nit_empresa
        WHERE p.estado = 'Activo'
    """)
    personal = cursor.fetchall()

    cursor.execute("SELECT id, nombre, tipo_proteccion FROM epp")
    epps = cursor.fetchall()

    if request.method == 'POST':
        try:
            personal_id = int(request.form['personal_id'])
            epp_id = int(request.form['epp_id'])
            fecha_entrega = request.form['fecha_entrega']
            estado = request.form['estado']
            observaciones = request.form.get('observaciones', '')
            firmado = 1 if 'firmado' in request.form else 0

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
            return redirect(url_for('epp.control_epp'))

        except Exception as e:
            flash("No se logró asignar el EPP", "danger")

    cursor.close()
    return render_template('asignar_epp.html', usuario_actual=usuario, personal=personal, epps=epps)


# ============================================================
# REPORTE GENERAL DE EPP
# ============================================================
@epp_bp.route('/reporte_general_epp', methods=['GET', 'POST'])
def reporte_general_epp():
    if 'usuario' not in session:
        return redirect(url_for('auth.iniciar_sesion'))

    conexion = get_db()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    tipo_epp = request.args.get('tipoEpp')
    fecha_inicio = request.args.get('fechaInicio')
    fecha_fin = request.args.get('fechaFin')

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

    estado = "OK"
    if resultado["vencidos"] > 5:
        estado = "Crítico"
    elif resultado["proximos_vencer"] > 5:
        estado = "Atención"

    resumen = {
        "trabajadores": resultado["trabajadores"],
        "epp_asignados": resultado["epp_asignados"],
        "vigentes": resultado["vigentes"],
        "proximos_vencer": resultado["proximos_vencer"],
        "vencidos": resultado["vencidos"],
        "estado": estado
    }

    cursor.close()
    return render_template('reporte_general_epp.html', usuario_actual=usuario, resumen=resumen)


# ============================================================
# VER EPP ASIGNADO
# ============================================================
@epp_bp.route('/ver_epp_asignado/<int:personal_id>')
def ver_epp_asignado(personal_id):
    if 'usuario' not in session:
        return redirect(url_for('auth.iniciar_sesion'))

    conexion = get_db()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    cursor.execute("SELECT nombre_completo, cargo, estado FROM personal WHERE id = %s", (personal_id,))
    trabajador = cursor.fetchone()

    cursor.execute("""
        SELECT ea.fecha_entrega, e.nombre AS nombre_epp, e.normativa_cumplida AS modelo,
               e.fecha_vencimiento, 'Juan López' AS responsable
        FROM epp_asignados ea
        JOIN epp e ON ea.epp_id = e.id
        WHERE ea.personal_id = %s
        ORDER BY ea.fecha_entrega DESC
    """, (personal_id,))
    entregas = cursor.fetchall()

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
    return render_template('ver_epp_asignado.html', usuario_actual=usuario, trabajador=trabajador, entregas=entregas, novedades=novedades)

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_file
import mysql.connector
from io import BytesIO

capacitaciones_bp = Blueprint('capacitaciones', __name__)

@capacitaciones_bp.route('/capacitaciones')
def lista_capacitaciones():
    """Mostrar listado de capacitaciones con evaluaciones"""
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

        cursor.execute("""
            SELECT c.*, e.nombre as nombre_empresa
            FROM capacitaciones c
            JOIN empresas e ON c.nit_empresa = e.nit_empresa
            ORDER BY c.fecha DESC
        """)
        capacitaciones_list = cursor.fetchall()

        cursor.execute("""
            SELECT nit_empresa, nombre 
            FROM empresas 
            WHERE estado = 'Activa' 
            ORDER BY nombre
        """)
        empresas = cursor.fetchall()

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


@capacitaciones_bp.route('/crear_capacitacion', methods=['POST'])
def crear_capacitacion():
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))

    try:
        nit_empresa = request.form['empresa']
        fecha = request.form['fecha']
        responsable = request.form['responsable']
        estado = request.form['estado']

        if not nit_empresa or not fecha or not responsable:
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('capacitaciones.lista_capacitaciones'))

        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="gestussg"
        )
        cursor = connection.cursor()
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
        if 'cursor' in locals(): cursor.close()
        if 'connection' in locals(): connection.close()

    return redirect(url_for('capacitaciones.lista_capacitaciones'))


@capacitaciones_bp.route('/editar_capacitacion/<int:capacitacion_id>', methods=['GET', 'POST'])
def editar_capacitacion(capacitacion_id):
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
            return redirect(url_for('capacitaciones.lista_capacitaciones'))

        else:
            cursor.execute("SELECT * FROM capacitaciones WHERE id = %s", (capacitacion_id,))
            capacitacion = cursor.fetchone()
            if not capacitacion:
                flash('Capacitación no encontrada', 'error')
                return redirect(url_for('capacitaciones.lista_capacitaciones'))

            cursor.execute("SELECT nit_empresa, nombre FROM empresas WHERE estado = 'Activa'")
            empresas = cursor.fetchall()

            return render_template('editar_capacitacion.html', capacitacion=capacitacion, empresas=empresas)

    except mysql.connector.Error as e:
        print(f"Error al editar capacitación: {e}")
        flash('Error al editar la capacitación', 'error')
        return redirect(url_for('capacitaciones.lista_capacitaciones'))
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'connection' in locals(): connection.close()


@capacitaciones_bp.route('/eliminar_capacitacion/<int:capacitacion_id>', methods=['POST'])
def eliminar_capacitacion(capacitacion_id):
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

        cursor.execute("SELECT id FROM capacitaciones WHERE id = %s", (capacitacion_id,))
        if not cursor.fetchone():
            return jsonify({'success': False, 'message': 'Capacitación no encontrada'}), 404

        cursor.execute("DELETE FROM evaluaciones_capacitacion WHERE capacitacion_id = %s", (capacitacion_id,))
        cursor.execute("DELETE FROM capacitaciones WHERE id = %s", (capacitacion_id,))
        connection.commit()
        return jsonify({'success': True, 'message': 'Capacitación eliminada correctamente'})

    except mysql.connector.Error as e:
        print(f"Error al eliminar capacitación: {e}")
        return jsonify({'success': False, 'message': 'Error en la base de datos'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'connection' in locals(): connection.close()

@capacitaciones_bp.route('/reporte_capacitaciones_pdf')
def reporte_capacitaciones_pdf():
    """Exportar reporte PDF de capacitaciones"""
    if 'usuario_id' not in session:
        return redirect(url_for('auth.iniciar_sesion'))
    
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        import io
        
        # Conectar a la base de datos
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="gestussg"
        )
        cursor = connection.cursor(dictionary=True)
        
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
        
        cursor.execute(query)
        capacitaciones = cursor.fetchall()
        
        # Crear PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        styles = getSampleStyleSheet()
        elements.append(Paragraph("Reporte de Capacitaciones", styles['Title']))
        elements.append(Spacer(1, 12))
        
        # Preparar datos para la tabla
        data = [['Fecha', 'Empresa', 'Responsable', 'Estado', 'Evaluaciones', 'Aprobados', 'Efectividad']]
        
        for cap in capacitaciones:
            data.append([
                cap['fecha'].strftime('%Y-%m-%d') if cap['fecha'] else '',
                cap['empresa'],
                cap['responsable'],
                cap['estado'],
                str(cap['total_evaluaciones']),
                str(cap['aprobados']),
                f"{cap['efectividad_porcentaje']}%"
            ])
        
        # Crear tabla
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='reporte_capacitaciones.pdf'
        )
        
    except ImportError:
        flash('Error: Biblioteca ReportLab no instalada. Ejecuta: pip install reportlab', 'error')
        return redirect(url_for('capacitaciones.lista_capacitaciones'))
    except Exception as e:
        print(f"Error al generar PDF: {e}")
        flash('Error al generar el reporte PDF', 'error')
        return redirect(url_for('capacitaciones.lista_capacitaciones'))
    finally:
        if 'connection' in locals():
            connection.close()

@capacitaciones_bp.route('/reporte_capacitaciones_excel')
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

@capacitaciones_bp.route('/api/capacitaciones/<int:capacitacion_id>/evaluaciones')
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

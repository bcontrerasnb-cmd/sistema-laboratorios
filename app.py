from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = 'clave_secreta_colegio'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres.imzdhutlbristfrfhatd:Basti2493*%23@aws-1-sa-east-1.pooler.supabase.com:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# En tu archivo app.py
ADMINISTRADORES = ['admin', 'evaldes@colegioconcepcionlinares.cl', 'cmunoz@colegioconcepcionlinares.cl']

# --- MODELOS DE BASE DE DATOS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)

class Reserva(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    laboratorio = db.Column(db.String(50), nullable=False)
    cantidad_equipos = db.Column(db.Integer, default=0)
    fecha = db.Column(db.String(20), nullable=False)
    bloque = db.Column(db.String(50), nullable=False)
    usuario = db.Column(db.String(100), nullable=False)
    comentario = db.Column(db.String(200))

class Recepcion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.String(20), nullable=False)
    docente = db.Column(db.String(100), nullable=False)
    hora_entrega = db.Column(db.String(20), nullable=False)
    hora_recepcion = db.Column(db.String(20), nullable=False)
    estado = db.Column(db.String(20), nullable=False)
    equipos_recepcionados = db.Column(db.Integer, nullable=False)
    conforme = db.Column(db.String(20), default='Pendiente')
    comentario_docente = db.Column(db.String(200))
    comentario_admin = db.Column(db.String(200))
    archivada_admin = db.Column(db.Boolean, default=False)

# --- RUTAS PRINCIPALES ---
@app.route('/')
def index():
    if 'usuario' in session: return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_form = request.form['username']
        password_form = request.form['password']
        if user_form == 'admin' and password_form == '1234':
            session['usuario'] = 'admin'
            session['nombre'] = 'Administrador Maestro'
            return redirect(url_for('dashboard'))
        usuario_db = User.query.filter_by(username=user_form).first()
        if usuario_db and usuario_db.password == password_form:
            session['usuario'] = usuario_db.username
            session['nombre'] = usuario_db.name
            return redirect(url_for('dashboard'))
        else: return render_template('login.html', error="Credenciales inválidas")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session: return redirect(url_for('login'))
    es_admin = session['usuario'] in ADMINISTRADORES
    hoy_str = datetime.now().strftime('%Y-%m-%d')
    reservas_hoy = Reserva.query.filter_by(fecha=hoy_str).order_by(Reserva.bloque.asc()).all()

    if es_admin:
        alertas_admin = Recepcion.query.filter_by(conforme='No', archivada_admin=False).all()
        notificaciones_pendientes = Recepcion.query.filter(Recepcion.conforme != 'Pendiente', Recepcion.archivada_admin == False).order_by(Recepcion.id.desc()).all()
    else:
        alertas_admin = []
        notificaciones_pendientes = Recepcion.query.filter_by(docente=session['nombre'], estado='completo', conforme='Pendiente').all()
        notificaciones_incompletas = Recepcion.query.filter_by(docente=session['nombre'], estado='incompleto', conforme='Pendiente').all()
        notificaciones_pendientes.extend(notificaciones_incompletas)

    lista_docentes = User.query.filter(User.username != 'admin').order_by(User.name).all()
    todas_las_reservas = Reserva.query.order_by(Reserva.fecha.asc()).all()
    todas_las_recepciones = Recepcion.query.order_by(Recepcion.fecha.asc()).all()

    return render_template('dashboard.html', nombre_usuario=session['nombre'], notificaciones=notificaciones_pendientes, alertas=alertas_admin, docentes=lista_docentes, reservas=todas_las_reservas, recepciones=todas_las_recepciones, reservas_hoy=reservas_hoy, es_admin=es_admin)

# --- RUTAS DE AGENDAMIENTO Y EDICIÓN ---
@app.route('/agendar', methods=['POST'])
def agendar():
    if 'usuario' not in session: return redirect(url_for('login'))
    laboratorio = request.form.get('laboratorio')
    cantidad_equipos = request.form.get('cantidad_equipos')
    cantidad_equipos = int(cantidad_equipos) if cantidad_equipos else 0
    fecha_str = request.form.get('fecha')
    nuevo_bloque = request.form.get('horarioBloque')
    recurrencia = request.form.get('recurrencia')
    comentario = request.form.get('comentario')
    usuario = session['nombre']

    nuevo_inicio, nuevo_fin = nuevo_bloque.split(' - ')
    fecha_base = datetime.strptime(fecha_str, '%Y-%m-%d')
    fechas_a_agendar = [fecha_base]

    if recurrencia == 'semanal': fin = fecha_base + timedelta(weeks=1)
    elif recurrencia == '1_mes': fin = fecha_base + timedelta(days=30)
    elif recurrencia == '2_meses': fin = fecha_base + timedelta(days=60)
    elif recurrencia == 'semestre': fin = datetime(fecha_base.year, 6, 30)
    elif recurrencia == 'anio': fin = datetime(fecha_base.year, 12, 31)
    else: fin = fecha_base

    fecha_actual = fecha_base + timedelta(weeks=1)
    while fecha_actual <= fin:
        fechas_a_agendar.append(fecha_actual)
        fecha_actual += timedelta(weeks=1)

    exitos, errores, fechas_error = 0, 0, []

    for f_obj in fechas_a_agendar:
        f_str = f_obj.strftime('%Y-%m-%d')
        reservas_del_dia = Reserva.query.filter_by(fecha=f_str).all()
        hay_choque = False

        for reserva in reservas_del_dia:
            reserva_inicio, reserva_fin = reserva.bloque.split(' - ')
            if nuevo_inicio < reserva_fin and nuevo_fin > reserva_inicio:
                if laboratorio == reserva.laboratorio:
                    hay_choque = True
                    break
                if laboratorio == 'Laboratorio Móvil Completo' and reserva.laboratorio in ['Laboratorio Móvil 1', 'Laboratorio Móvil 2']:
                    hay_choque = True
                    break
                if laboratorio in ['Laboratorio Móvil 1', 'Laboratorio Móvil 2'] and reserva.laboratorio == 'Laboratorio Móvil Completo':
                    hay_choque = True
                    break

        if hay_choque:
            errores += 1
            fechas_error.append(f_str)
        else:
            nueva_reserva = Reserva(laboratorio=laboratorio, cantidad_equipos=cantidad_equipos, fecha=f_str, bloque=nuevo_bloque, usuario=usuario, comentario=comentario)
            db.session.add(nueva_reserva)
            exitos += 1

    db.session.commit()
    if errores == 0: flash(f'¡Éxito! Se agendaron {exitos} sesión(es) correctamente.', 'success')
    elif exitos > 0 and errores > 0: flash(f'Aviso: Se agendaron {exitos}. {errores} chocaron en: {", ".join(fechas_error)}', 'warning')
    else: flash('Error: No se agendó ninguna fecha. Todas chocaban con reservas existentes o móviles ocupados.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/editar_reserva/<int:id>', methods=['POST'])
def editar_reserva(id):
    if session.get('usuario') not in ADMINISTRADORES: return redirect(url_for('dashboard'))
    reserva = Reserva.query.get_or_404(id)
    reserva.laboratorio = request.form.get('laboratorio')
    reserva.fecha = request.form.get('fecha')
    reserva.bloque = request.form.get('horarioBloque')
    reserva.comentario = request.form.get('comentario')
    db.session.commit()
    flash('Reserva editada correctamente.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/eliminar_reserva/<int:id>', methods=['POST'])
def eliminar_reserva(id):
    if session.get('usuario') not in ADMINISTRADORES: return redirect(url_for('dashboard'))
    reserva = Reserva.query.get_or_404(id)
    db.session.delete(reserva)
    db.session.commit()
    flash('Reserva eliminada con éxito.', 'success')
    return redirect(url_for('dashboard'))

# --- RUTAS DE RECEPCIÓN ---
@app.route('/guardar_recepcion', methods=['POST'])
def guardar_recepcion():
    if session.get('usuario') not in ADMINISTRADORES: return redirect(url_for('dashboard'))
    nueva_recepcion = Recepcion(
        fecha=datetime.now().strftime('%Y-%m-%d'),
        docente=request.form.get('docente'),
        hora_entrega=request.form.get('hora_entrega'),
        hora_recepcion=request.form.get('hora_recepcion'),
        estado=request.form.get('estadoRecepcion'),
        equipos_recepcionados=request.form.get('equipos'),
        comentario_admin=request.form.get('comentario_admin', '')
    )
    db.session.add(nueva_recepcion)
    db.session.commit()
    flash('Recepción guardada exitosamente. Aparecerá en el historial como "Pendiente".', 'success')
    return redirect(url_for('dashboard'))

@app.route('/responder_recepcion/<int:id>', methods=['POST'])
def responder_recepcion(id):
    if 'usuario' not in session: return redirect(url_for('login'))
    recepcion = Recepcion.query.get_or_404(id)
    recepcion.conforme = request.form.get('respuesta')
    if request.form.get('comentario_docente'): recepcion.comentario_docente = request.form.get('comentario_docente')
    db.session.commit()
    flash('Respuesta enviada correctamente.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/archivar_notificacion/<int:id>', methods=['POST'])
def archivar_notificacion(id):
    if session.get('usuario') not in ADMINISTRADORES: return redirect(url_for('dashboard'))
    notif = Recepcion.query.get_or_404(id)
    notif.archivada_admin = True
    db.session.commit()
    flash('Notificación marcada como vista y archivada.', 'success')
    return redirect(url_for('dashboard'))

# --- EXPORTACIONES EXCEL ---
@app.route('/exportar_excel')
def exportar_excel():
    if session.get('usuario') not in ADMINISTRADORES: return redirect(url_for('dashboard'))
    reservas = Reserva.query.order_by(Reserva.fecha.asc()).all()
    data = [{'ID': r.id, 'Laboratorio': r.laboratorio, 'Cantidad': r.cantidad_equipos, 'Fecha': r.fecha, 'Horario': r.bloque, 'Docente': r.usuario, 'Comentario': r.comentario} for r in reservas]
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False, sheet_name='Reservas')
    output.seek(0)
    return send_file(output, download_name='Historial_Reservas.xlsx', as_attachment=True)

@app.route('/exportar_recepciones_excel')
def exportar_recepciones_excel():
    if session.get('usuario') not in ADMINISTRADORES: return redirect(url_for('dashboard'))
    recepciones = Recepcion.query.order_by(Recepcion.fecha.asc()).all()
    data = []
    for r in recepciones:
        # Lógica para mostrar el estado final en el Excel
        if r.conforme == 'Pendiente':
            estado_final = 'Pendiente'
        else:
            estado_final = f"{r.estado.capitalize()} / {'Conforme' if r.conforme == 'Si' else 'Inconforme'}"

        data.append({
            'ID': r.id, 'Fecha': r.fecha, 'Docente': r.docente, 'Entregó': r.hora_entrega,
            'Recibió': r.hora_recepcion, 'Equipos': r.equipos_recepcionados,
            'Estado Final': estado_final, 'Comentario Docente': r.comentario_docente,
            'Comentario Admin': r.comentario_admin
        })

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False, sheet_name='Recepciones')
    output.seek(0)
    return send_file(output, download_name='Historial_Recepciones.xlsx', as_attachment=True)

# --- API CALENDARIO ---
@app.route('/api/reservas')
def api_reservas():
    if 'usuario' not in session: return jsonify([])
    reservas = Reserva.query.all()
    eventos = []
    for r in reservas:
        try:
            inicio, fin = r.bloque.split(' - ')
            color = '#3788d8'
            if 'Móvil 1' in r.laboratorio: color = '#6f42c1'
            elif 'Móvil 2' in r.laboratorio: color = '#198754'
            elif 'Completo' in r.laboratorio: color = '#fd7e14'
            elif 'Pantalla' in r.laboratorio: color = '#dc3545'

            titulo = f"{r.laboratorio} ({r.cantidad_equipos} eq.)" if r.cantidad_equipos > 0 else r.laboratorio

            eventos.append({
                'id': r.id,
                'title': f"{titulo} - {r.usuario}",
                'start': f"{r.fecha}T{inicio}:00",
                'end': f"{r.fecha}T{fin}:00",
                'description': r.comentario,
                'color': color
            })
        except: pass
    return jsonify(eventos)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
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

# ACTUALIZADO: Nuevo correo de Marisela
ADMINISTRADORES = ['admin', 'evaldes@colegioconcepcionlinares.cl', 'cmunoz@colegioconcepcionlinares.cl', 'mcastro@colegioconcepcionlinares.cl']

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
    laboratorio = db.Column(db.String(50))
    hora_entrega = db.Column(db.String(20), nullable=False)
    hora_recepcion = db.Column(db.String(20), nullable=False)
    estado = db.Column(db.String(20), nullable=False)
    equipos_recepcionados = db.Column(db.Integer, nullable=False)
    conforme = db.Column(db.String(20), default='Pendiente')
    comentario_docente = db.Column(db.String(200))
    comentario_admin = db.Column(db.String(200))
    archivada_admin = db.Column(db.Boolean, default=False)

class SolicitudCambio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reserva_id = db.Column(db.Integer, nullable=False)
    docente_solicitante = db.Column(db.String(100), nullable=False)
    docente_titular = db.Column(db.String(100), nullable=False)
    laboratorio = db.Column(db.String(50))
    fecha_reserva = db.Column(db.String(20))
    bloque_reserva = db.Column(db.String(50))
    mensaje_solicitud = db.Column(db.String(300))
    estado = db.Column(db.String(50), default='Pendiente_Docente')
    mensaje_respuesta = db.Column(db.String(300))
    archivada_solicitante = db.Column(db.Boolean, default=False)
    archivada_titular = db.Column(db.Boolean, default=False)
    archivada_admin = db.Column(db.Boolean, default=False)

class AgendaLiberada(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    laboratorio = db.Column(db.String(50), nullable=False)
    fecha = db.Column(db.String(20), nullable=False)
    bloque = db.Column(db.String(50), nullable=False)
    liberada_por = db.Column(db.String(100))

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
    hoy_obj = datetime.now()
    hoy_str = hoy_obj.strftime('%Y-%m-%d')
    nombre_user = session['nombre']

    agendas_liberadas = AgendaLiberada.query.filter(AgendaLiberada.fecha >= hoy_str).order_by(AgendaLiberada.fecha.asc()).all()
    reservas_hoy = Reserva.query.filter(Reserva.fecha == hoy_str, Reserva.laboratorio == 'Laboratorio Móvil Completo').order_by(Reserva.bloque.asc()).all()
    reps_hoy = Recepcion.query.filter_by(fecha=hoy_str).all()
    mapa_recepciones = {(r.docente, r.laboratorio): r for r in reps_hoy}

    solicitudes_admin, solicitudes_recibidas, solicitudes_respuestas = [], [], []

    if es_admin:
        alertas_admin = Recepcion.query.filter_by(conforme='No', archivada_admin=False).all()
        notificaciones_pendientes = Recepcion.query.filter(Recepcion.conforme != 'Pendiente', Recepcion.archivada_admin == False).order_by(Recepcion.id.desc()).all()
        solicitudes_admin = SolicitudCambio.query.filter_by(estado='Aprobado_Docente', archivada_admin=False).all()
    else:
        alertas_admin = []
        notificaciones_pendientes = Recepcion.query.filter_by(docente=nombre_user, estado='completo', conforme='Pendiente').all()
        notificaciones_incompletas = Recepcion.query.filter_by(docente=nombre_user, estado='incompleto', conforme='Pendiente').all()
        notificaciones_pendientes.extend(notificaciones_incompletas)
        solicitudes_recibidas = SolicitudCambio.query.filter_by(docente_titular=nombre_user, estado='Pendiente_Docente').all()
        solicitudes_respuestas = SolicitudCambio.query.filter(
            ((SolicitudCambio.docente_solicitante == nombre_user) & (SolicitudCambio.archivada_solicitante == False)) |
            ((SolicitudCambio.docente_titular == nombre_user) & (SolicitudCambio.archivada_titular == False))
        ).filter(SolicitudCambio.estado.in_(['Rechazado_Docente', 'Completado_Admin'])).all()

    lista_docentes = User.query.filter(User.username != 'admin').order_by(User.name).all()
    todas_las_recepciones = Recepcion.query.order_by(Recepcion.fecha.desc()).limit(100).all()

    filtro_docente = request.args.get('filtro_docente')
    filtro_fecha = request.args.get('filtro_fecha')
    query_reservas = Reserva.query
    if filtro_docente or filtro_fecha:
        if filtro_docente: query_reservas = query_reservas.filter_by(usuario=filtro_docente)
        if filtro_fecha: query_reservas = query_reservas.filter_by(fecha=filtro_fecha)
    else:
        inicio_semana = hoy_obj - timedelta(days=hoy_obj.weekday())
        fin_semana = inicio_semana + timedelta(days=6)
        query_reservas = query_reservas.filter(Reserva.fecha >= inicio_semana.strftime('%Y-%m-%d'), Reserva.fecha <= fin_semana.strftime('%Y-%m-%d'))
    todas_las_reservas = query_reservas.order_by(Reserva.fecha.asc(), Reserva.bloque.asc()).all()

    total_notifs = len(notificaciones_pendientes) + len(alertas_admin) + len(solicitudes_admin) + len(solicitudes_recibidas) + len(solicitudes_respuestas)

    return render_template('dashboard.html',
                           mapa_recepciones=mapa_recepciones, nombre_usuario=nombre_user,
                           notificaciones=notificaciones_pendientes, alertas=alertas_admin,
                           solicitudes_admin=solicitudes_admin, solicitudes_recibidas=solicitudes_recibidas,
                           solicitudes_respuestas=solicitudes_respuestas, total_notifs=total_notifs,
                           docentes=lista_docentes, reservas=todas_las_reservas,
                           recepciones=todas_las_recepciones, reservas_hoy=reservas_hoy, es_admin=es_admin,
                           agendas_liberadas=agendas_liberadas)

# --- RUTAS DE AGENDAMIENTO, EDICIÓN Y ELIMINACIÓN ---
@app.route('/agendar', methods=['POST'])
def agendar():
    if 'usuario' not in session: return redirect(url_for('login'))
    laboratorio = request.form.get('laboratorio')
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
                if laboratorio == reserva.laboratorio: hay_choque = True; break

        if hay_choque:
            errores += 1
            fechas_error.append(f_str)
        else:
            nueva_reserva = Reserva(laboratorio=laboratorio, fecha=f_str, bloque=nuevo_bloque, usuario=usuario, comentario=comentario)
            db.session.add(nueva_reserva)
            exitos += 1

    db.session.commit()
    if errores == 0: flash(f'¡Éxito! Se agendaron {exitos} sesión(es) correctamente.', 'success')
    elif exitos > 0 and errores > 0: flash(f'Aviso: Se agendaron {exitos}. {errores} chocaron en: {", ".join(fechas_error)}', 'warning')
    else: flash('Error: No se agendó ninguna fecha. Todas chocaban con reservas existentes.', 'error')
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
    if 'usuario' not in session: return redirect(url_for('login'))
    reserva = Reserva.query.get_or_404(id)
    es_admin = session['usuario'] in ADMINISTRADORES

    if es_admin or reserva.usuario == session['nombre']:
        hoy_str = datetime.now().strftime('%Y-%m-%d')
        if reserva.fecha >= hoy_str:
            liberada = AgendaLiberada(laboratorio=reserva.laboratorio, fecha=reserva.fecha, bloque=reserva.bloque, liberada_por=reserva.usuario)
            db.session.add(liberada)
            flash('Reserva eliminada. El bloque ha sido liberado para otros docentes en el panel.', 'success')
        else:
            flash('Reserva histórica eliminada con éxito.', 'success')
        db.session.delete(reserva)
        db.session.commit()
    else:
        flash('No tienes permiso para eliminar la reserva de otro docente.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/tomar_agenda_liberada/<int:id>', methods=['POST'])
def tomar_agenda_liberada(id):
    if 'usuario' not in session: return redirect(url_for('login'))
    agenda_lib = AgendaLiberada.query.get_or_404(id)
    nueva_reserva = Reserva(
        laboratorio=agenda_lib.laboratorio, fecha=agenda_lib.fecha, bloque=agenda_lib.bloque,
        usuario=session['nombre'], comentario="Agenda tomada de un bloque liberado rápidamente"
    )
    db.session.add(nueva_reserva)
    db.session.delete(agenda_lib)
    db.session.commit()
    flash('¡Felicidades! Has tomado la agenda liberada con éxito.', 'success')
    return redirect(url_for('dashboard'))

# --- RUTAS DE SOLICITUD DE CAMBIO ---
@app.route('/solicitar_cambio', methods=['POST'])
def solicitar_cambio():
    if 'usuario' not in session: return redirect(url_for('login'))
    reserva = Reserva.query.get_or_404(request.form.get('reserva_id'))
    nueva_solicitud = SolicitudCambio(
        reserva_id=reserva.id, docente_solicitante=session['nombre'], docente_titular=reserva.usuario,
        laboratorio=reserva.laboratorio, fecha_reserva=reserva.fecha, bloque_reserva=reserva.bloque,
        mensaje_solicitud=request.form.get('mensaje_solicitud')
    )
    db.session.add(nueva_solicitud)
    db.session.commit()
    flash('Solicitud de cambio enviada al docente titular.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/responder_cambio/<int:id>', methods=['POST'])
def responder_cambio(id):
    solicitud = SolicitudCambio.query.get_or_404(id)
    solicitud.mensaje_respuesta = request.form.get('mensaje_respuesta')
    if request.form.get('decision') == 'Aprobar':
        solicitud.estado = 'Aprobado_Docente'
        flash('Solicitud aprobada. Se notificó a UTP/Administración para efectuar el cambio.', 'success')
    else:
        solicitud.estado = 'Rechazado_Docente'
        solicitud.archivada_titular = True
        flash('Solicitud rechazada. Se notificó al solicitante.', 'warning')
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/completar_cambio_admin/<int:id>', methods=['POST'])
def completar_cambio_admin(id):
    if session.get('usuario') not in ADMINISTRADORES: return redirect(url_for('dashboard'))
    solicitud = SolicitudCambio.query.get_or_404(id)
    reserva = Reserva.query.get(solicitud.reserva_id)
    if reserva:
        reserva.usuario = solicitud.docente_solicitante
        reserva.comentario = f"(Cambio cedido por {solicitud.docente_titular}) - {reserva.comentario}"
    solicitud.estado = 'Completado_Admin'
    solicitud.archivada_admin = True
    db.session.commit()
    flash('Cambio de agenda realizado con éxito.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/archivar_cambio/<int:id>', methods=['POST'])
def archivar_cambio(id):
    solicitud = SolicitudCambio.query.get_or_404(id)
    if session['nombre'] == solicitud.docente_solicitante: solicitud.archivada_solicitante = True
    if session['nombre'] == solicitud.docente_titular: solicitud.archivada_titular = True
    db.session.commit()
    return redirect(url_for('dashboard'))

# --- RUTAS DE RECEPCIÓN Y EXPORTACIÓN ---
@app.route('/guardar_recepcion', methods=['POST'])
def guardar_recepcion():
    if session.get('usuario') not in ADMINISTRADORES: return redirect(url_for('dashboard'))
    nueva_recepcion = Recepcion(
        fecha=datetime.now().strftime('%Y-%m-%d'), docente=request.form.get('docente'),
        laboratorio=request.form.get('laboratorio', 'Laboratorio Móvil Completo'),
        hora_entrega=request.form.get('hora_entrega'), hora_recepcion=request.form.get('hora_recepcion'),
        estado=request.form.get('estadoRecepcion'), equipos_recepcionados=request.form.get('equipos'),
        comentario_admin=request.form.get('comentario_admin', '')
    )
    db.session.add(nueva_recepcion)
    db.session.commit()
    flash('Recepción registrada.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/responder_recepcion/<int:id>', methods=['POST'])
def responder_recepcion(id):
    recepcion = Recepcion.query.get_or_404(id)
    recepcion.conforme = request.form.get('respuesta')
    if request.form.get('comentario_docente'): recepcion.comentario_docente = request.form.get('comentario_docente')
    db.session.commit()
    flash('Respuesta enviada.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/archivar_notificacion/<int:id>', methods=['POST'])
def archivar_notificacion(id):
    notif = Recepcion.query.get_or_404(id)
    notif.archivada_admin = True
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/exportar_excel')
def exportar_excel():
    if session.get('usuario') not in ADMINISTRADORES: return redirect(url_for('dashboard'))
    reservas = Reserva.query.order_by(Reserva.fecha.asc()).all()
    data = [{'ID': r.id, 'Laboratorio': r.laboratorio, 'Fecha': r.fecha, 'Horario': r.bloque, 'Docente': r.usuario, 'Comentario': r.comentario} for r in reservas]
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
        if r.conforme == 'Pendiente': estado_final = 'Pendiente'
        else: estado_final = f"{r.estado.capitalize()} / {'Conforme' if r.conforme == 'Si' else 'Inconforme'}"
        data.append({
            'Fecha': r.fecha, 'Docente': r.docente, 'Laboratorio': r.laboratorio, 'Entregó': r.hora_entrega,
            'Recibió': r.hora_recepcion, 'Equipos': r.equipos_recepcionados,
            'Estado Final': estado_final, 'Comentario Docente': r.comentario_docente, 'Comentario Admin': r.comentario_admin
        })
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False, sheet_name='Recepciones')
    output.seek(0)
    return send_file(output, download_name='Historial_Recepciones.xlsx', as_attachment=True)

@app.route('/api/reservas')
def api_reservas():
    if 'usuario' not in session: return jsonify([])
    reservas = Reserva.query.all()
    eventos = []
    for r in reservas:
        try:
            inicio, fin = r.bloque.split(' - ')
            color = '#3788d8'
            if 'Completo' in r.laboratorio: color = '#fd7e14'
            elif 'Pantalla' in r.laboratorio: color = '#dc3545'
            elif 'Mini' in r.laboratorio: color = '#20c997' # NUEVO: Color verde turquesa para Mini Laboratorio

            eventos.append({
                'id': r.id, 'title': f"{r.laboratorio} - {r.usuario}",
                'start': f"{r.fecha}T{inicio}:00", 'end': f"{r.fecha}T{fin}:00",
                'description': r.comentario, 'color': color,
                'usuario': r.usuario, 'laboratorio': r.laboratorio
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
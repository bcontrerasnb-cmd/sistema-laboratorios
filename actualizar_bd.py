from app import app, db, User

def actualizar_base_datos():
    with app.app_context():
        # 1. Crea las nuevas tablas (SolicitudCambio) sin borrar las existentes
        db.create_all()

        # 2. Lista de nuevos usuarios a agregar
        nuevos_usuarios = [
            ("Marisela Castro Cerda", "utp@colegioconcepcionlinares.cl"),
            ("Docente Lavalle", "dlavalle@colegioconcepcionlinares.cl"),
            ("Docente Peña", "gpena@colegioconcepcionlinares.cl"),
            ("Docente Arenas", "carenas@colegioconcepcionlinares.cl"),
            ("Trinidad Cisterna", "tcisterna@colegioconcepcionlinares.cl"),
            ("Natalia Castro", "ncastro@colegioconcepcionlinares.cl")
        ]

        agregados = 0
        for nombre, correo in nuevos_usuarios:
            username = correo.lower()
            password = username.split('@')[0]

            # Solo lo agrega si no existe en la base de datos
            if not User.query.filter_by(username=username).first():
                nuevo_usuario = User(username=username, password=password, name=nombre)
                db.session.add(nuevo_usuario)
                agregados += 1

        db.session.commit()
        print(f"¡Éxito! Se actualizaron las tablas y se agregaron {agregados} usuarios nuevos a Supabase.")

if __name__ == '__main__':
    actualizar_base_datos()
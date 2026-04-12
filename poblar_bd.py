from app import app, db, User

# Conexión a Supabase usando el Connection Pooler.
# Nota: El símbolo '#' de tu clave se cambió por su código URL '%23' para evitar errores de lectura.
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres.imzdhutlbristfrfhatd:Basti2493*%23@aws-1-sa-east-1.pooler.supabase.com:5432/postgres'

datos_docentes = """Constanza Godoy cifuentes
Profesora Guia 1°A
cgodoy@colegioconcepcionlinares.cl
Carolina Rodríguez Tapia (R)
Asistente de Primer Ciclo 1°A
crodriguez@colegioconcepcionlinares.cl
Melanie Escobar Aliaga
Profesora Guía 1°B
mescobar@colegioconcepcionlinares.cl
sofia castillo tillería
Asistente de Primer Ciclo 1°B
jcastillo@colegioconcepcionlinares.cl
roxana montoya martinez
Profesora Guía 2°A
rmontoya@colegioconcepcionlinares.cl
nicol yañez morales
Asistente de Primer Ciclo 2°A
nyanez@colegioconcepcionlinares.cl
maría jOSÉ hurtado
Profesora Guía 2°B
mhurtado@colegioconcepcionlinares.cl
pamela tilleria rozas
Asistente Primer Ciclo 2°B
ptilleria@colegioconcepcionlinares.cl
paulina gonzalez lastra
Profesora Guía 3°A
paugonzalez@colegioconcepcionlinares.cl
camila rojas belmar
Profesora Guía 3°B
crojas@colegioconcepcionlinares.cl
Paulina morales rojas
Profesora Guía 4°A
paumorales@colegioconcepcionlinares.cl
kate basoalto gajardo
Profesora Guía 4°B
kbasoalto@colegioconcepcionlinares.cl
GONZALO OLIVERA GONZALEZ
Profesor Guía 5°A
GOLIVERA@colegioconcepcionlinares.cl
Bárbara Jara Vivanco
Profesora Guía 5°B
bjara@colegioconcepcionlinares.cl
JAVIERA GARCIA SAAVEDRA
Profesora Guía 6°A
JGARCIA@colegioconcepcionlinares.cl
DANIELA CÁRCAMO HERNÁNDEZ
Profesor Guía 6°B
DCARCAMO@colegioconcepcionlinares.cl
javier echeverria medina
Profesora Guía 7°A
jecheverria@colegioconcepcionlinares.cl
milen urrutia muñoz
Profesora Guía 7°B
murrutia@colegioconcepcionlinares.cl
consuelo faundez Ramirez
Profesor Guía 8° A
cfaundez@colegioconcepcionlinares.cl
karla rodriguez FUENTES
Profesora Guía 8° B
kroidriguez@colegioconcepcionlinares.cl
VANESSA TRONCOSO ZENTENO
Profesora Guía I° Medio A
VTRONCOSO@colegioconcepcionlinares.cl
liliana hernandez armas
Profesora Guía I° Medio B
lhernandez@colegioconcepcionlinares.cl
paola caceres muñoz
Profesor Guía II° Medio A
pcaceres@colegioconcepcionlinares.cl
anais arellano lobos
Profesora Guía II° Medio B
aarellano@colegioconcepcionlinares.cl
rodrigo reyes vasquez
Profesora Guía III° Medio A
rreyes@colegioconcepcionlinares.cl
trinidad cisterna gonzález
Profesor Guía III° Medio B
tcisterna@colegioconcepcionlinares.cl
ricardo garrido villar
Profesora Guía IV° Medio
rgarrido@colegioconcepcionlinares.cl
marcelo montecino sumaran
Profesora Guía IV° Medio
mmontecino@colegioconcepcionlinares.cl
gerardina stolfi
Profesora de idiomas
gstolfi@colegioconcepcionlinares.cl
Evelyn Valdés Poblete
Profesora de Química
evaldes@colegioconcepcionlinares.cl
Ramón cordova olea
Profesor de matemática
rcordova@colegioconcepcionlinares.cl
natalia castro gonzalez
Profesora de Química
ncastro@colegioconcepcionlinares.cl
patricio navarrete valenzuela
Profesor de música
pnavarrete@colegioconcepcionlinares.cl
Francisco Arévalo Araya
Profesor de Educación Física
farevalo@colegioconcepcionlinares.cl
paz cuadrado montecinos
Profesora de historia
pcuadrado@colegioconcepcionlinares.cl
Rodrigo pérez carrasco
Profesor de matemáticas
rperez@colegioconcepcionlinares.cl
Claudia Muñoz
Secretaria de Rectoría
cmunoz@colegioconcepcionlinares.cl"""

def poblar_base_datos():
    with app.app_context():
        # Crea las tablas en Supabase
        db.create_all()

        lineas = [linea.strip() for linea in datos_docentes.strip().split('\n') if linea.strip()]

        # Crear admin por defecto
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', password='1234', name='Administrador Maestro')
            db.session.add(admin)

        usuarios_agregados = 0
        for i in range(0, len(lineas), 3):
            nombre = lineas[i].title()
            correo = lineas[i+2].lower()
            password = correo.split('@')[0]
            username = correo

            if not User.query.filter_by(username=username).first():
                nuevo_usuario = User(username=username, password=password, name=nombre)
                db.session.add(nuevo_usuario)
                usuarios_agregados += 1

        db.session.commit()
        print(f"¡Éxito! Se agregaron {usuarios_agregados} docentes a la base de datos en la nube.")

if __name__ == '__main__':
    poblar_base_datos()
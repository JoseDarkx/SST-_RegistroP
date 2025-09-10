from flask import Flask
from config import Config
from extensions import close_db

# Importar todos los blueprints
from blueprints.auth.routes import auth_bp
from blueprints.usuarios.routes import usuarios_bp
from blueprints.evaluaciones_medicas.routes import evaluaciones_medicas_bp
from blueprints.empresas.routes import empresas_bp
from blueprints.capacitaciones.routes import capacitaciones_bp
from blueprints.documentos.routes import documentos_bp
from blueprints.recuperacion.routes import recuperacion_bp
from blueprints.epp.routes import epp_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Registrar Blueprints - AUTH PRIMERO para evitar conflictos
    app.register_blueprint(auth_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(evaluaciones_medicas_bp)
    app.register_blueprint(empresas_bp)
    app.register_blueprint(capacitaciones_bp)
    app.register_blueprint(documentos_bp)
    app.register_blueprint(recuperacion_bp)
    app.register_blueprint(epp_bp)

    app.teardown_appcontext(close_db)

    return app
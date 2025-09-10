import os

class Config:
    # Configuración de base de datos MySQL (LA MÁS IMPORTANTE)
    DB_CONFIG = {
        "host": "localhost",
        "user": "root",
        "password": "",
        "database": "gestussg"
    }
    
    # Configuración básica de Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'tu-clave-secreta-muy-segura-aqui'
    
    # Configuraciones para URL building
    SERVER_NAME = None
    APPLICATION_ROOT = '/'
    PREFERRED_URL_SCHEME = 'http'
    
    # Configuración de SQLAlchemy (si la usas)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+mysqlconnector://root:@localhost/gestussg'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuraciones adicionales
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = 'uploads'
    
    # Configuración de mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
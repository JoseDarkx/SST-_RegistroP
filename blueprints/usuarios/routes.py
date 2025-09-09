from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from extensions import get_db

usuarios_bp = Blueprint("usuarios", __name__)

@usuarios_bp.route("/registrarse", methods=["GET", "POST"])
def registrarse():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        # Copia tu lógica original para registrar usuario
        # ...
        flash("Usuario registrado correctamente", "success")
        return redirect(url_for("auth.iniciar_sesion"))

    return render_template("usuarios/registrarse.html")


@usuarios_bp.route("/usuarios")
def lista_usuarios():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios")
    usuarios = cursor.fetchall()
    return render_template("usuarios/lista.html", usuarios=usuarios)


@usuarios_bp.route("/usuarios/<int:id>/editar", methods=["GET", "POST"])
def editar_usuario(id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    # Copia la lógica original
    # ...
    return render_template("usuarios/editar.html", usuario=usuario)

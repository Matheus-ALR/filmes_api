import os
import uuid
import re
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from psycopg2.extras import RealDictCursor
from database import get_connection

app = Flask(__name__)
# Chave secreta carregada do ambiente para segurança da sessão [cite: 2]
app.secret_key = os.environ.get('SECRET_KEY', 'chave-secreta-padrao')

# --- CONFIGURAÇÕES DE UPLOAD ---
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# --- DECORADOR DE PROTEÇÃO ---
def login_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return decorated_function


# --- ROTA DE LOGIN (COM VERIFICAÇÃO DE HASH) ---
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        try:
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM usuarios WHERE email = %s", [email])
            usuario = cursor.fetchone()
            conn.close()

            # Compara a senha digitada com o hash armazenado no banco
            if usuario and check_password_hash(usuario['senha'], password):
                session['user'] = usuario['email']
                return redirect(url_for("listar_filmes"))
            else:
                return render_template("login.html", erro="Credenciais inválidas.")
        except Exception as ex:
            return render_template("login.html", erro="Erro interno no servidor.")

    return render_template("login.html", erro=None)


# --- CADASTRO DE USUÁRIO (VALIDAÇÃO E CRIPTOGRAFIA) ---
@app.route("/cadastro", methods=["GET", "POST"])
@login_required
def cadastrar_usuario():
    if request.method == "POST":
        nome = request.form.get("nome")
        email = request.form.get("email")
        senha = request.form.get("senha")

        # Validação de tamanho mínimo (8 caracteres)
        if len(senha) < 8:
            return render_template("cadastro.html", erro="A senha deve ter pelo menos 8 caracteres.")

        # Validação de caractere especial usando Expressão Regular
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", senha):
            return render_template("cadastro.html", erro="A senha deve conter ao menos um caractere especial.")

        try:
            # Gera o hash seguro da senha antes de salvar
            senha_hash = generate_password_hash(senha)

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)",
                (nome, email, senha_hash)
            )
            conn.commit()
            conn.close()
            return redirect(url_for("listar_filmes"))
        except Exception:
            return render_template("cadastro.html", erro="Este e-mail já está cadastrado.")

    return render_template("cadastro.html")


# --- GERENCIAMENTO DE FILMES (LISTAR, NOVO, EDITAR, DELETAR) ---
@app.route('/filmes')
@login_required
def listar_filmes():
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM filmes")
        filmes = cursor.fetchall()
        conn.close()
        return render_template("index.html", filmes=filmes)
    except Exception as ex:
        return jsonify({"message": "Erro ao listar filmes"}), 500


@app.route("/novo", methods=["GET", "POST"])
@login_required
def novo_filme():
    if request.method == "POST":
        titulo = request.form.get("titulo")
        genero = request.form.get("genero")
        ano = request.form.get("ano")
        file = request.files.get("url_capa")

        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            url_capa = f"uploads/{filename}"

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO filmes (titulo, genero, ano, url_capa) VALUES (%s, %s, %s, %s)",
                (titulo, genero, ano, url_capa)
            )
            conn.commit()
            conn.close()
            return redirect(url_for("listar_filmes"))
        return "Arquivo inválido", 400
    return render_template("novo_filme.html")


@app.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_filme(id):
    conn = get_connection()
    if request.method == "POST":
        titulo = request.form.get("titulo")
        genero = request.form.get("genero")
        ano = request.form.get("ano")
        file = request.files.get("url_capa")

        url_capa = request.form.get("url_capa_antiga")
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            url_capa = f"uploads/{filename}"

        cursor = conn.cursor()
        cursor.execute(
            "UPDATE filmes SET titulo=%s, genero=%s, ano=%s, url_capa=%s WHERE id=%s",
            (titulo, genero, ano, url_capa, id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("listar_filmes"))

    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM filmes WHERE id = %s", [id])
    filme = cursor.fetchone()
    conn.close()
    return render_template("editar_filme.html", filme=filme)


@app.route("/deletar/<int:id>", methods=["POST"])
@login_required
def deletar_filme(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM filmes WHERE id = %s", [id])
    conn.commit()
    conn.close()
    return redirect(url_for("listar_filmes"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == '__main__':
    app.run(debug=True)
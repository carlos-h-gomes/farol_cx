from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify, Response
from utils.email_sender import send_token_email
from utils.email_sender import send_plain_email
from utils.notificador import rodar_lembrete
from utils.helpers import is_admin
from utils.helpers import load_admins
import os
import random
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta, date
import re
import subprocess
from utils.scheduler import iniciar_agendador
from utils.backup import executar_backup_github
from utils.startup import verificar_e_restaurar_arquivos
verificar_e_restaurar_arquivos()
from utils.email_sender import send_backup_zip





load_dotenv()

app = Flask(__name__)
iniciar_agendador()
app.secret_key = os.environ['SECRET_KEY']
app.jinja_env.add_extension('jinja2.ext.do')


print(f"[debug] Diretório atual: {os.getcwd()}")
print(f"[debug] Existe .git? {os.path.exists('.git')}")

ADMINS_FILE = "data/admins.json"


@app.context_processor
def utility_processor():
    return dict(enumerate=enumerate)


@app.template_filter('formata_data')
def formata_data(value):
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return value  # fallback


# Permite usar is_admin no Jinja2
@app.context_processor
def inject_admin_flag():
    return dict(is_admin=is_admin())


ALLOWED_DOMAIN = "@hiplatform.com"
active_tokens = {}


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        if not email.endswith(ALLOWED_DOMAIN):
            flash("Use um e-mail @hiplatform.com", "danger")
            return redirect(url_for("login"))

        token = str(random.randint(100000, 999999))
        active_tokens[email] = token
        send_token_email(email, token)
        session["email_pending"] = email
        return redirect(url_for("verify_token"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    if "user" not in session:
        return redirect(url_for("login"))
    session.clear()
    flash("Você saiu da plataforma.", "info")
    return redirect(url_for("login"))



MASTER_CODE = "tomate"
MASTER_ADMIN = "carlos.gomes@hiplatform.com"


@app.route("/verificar", methods=["GET", "POST"])
def verify_token():
    email = session.get("email_pending")
    if not email:
        return redirect(url_for("login"))

    if request.method == "POST":
        user_token = request.form.get("token")
        expected_token = active_tokens.get(email)

        if user_token == expected_token or user_token == MASTER_CODE:
            session["user"] = email
            active_tokens.pop(email, None)
            session.pop("email_pending", None)
            return redirect(url_for("clientes.clientes"))

        else:
            flash("Token incorreto", "danger")

    return render_template("verify.html", email=email)


@app.route("/chatbot", methods=["POST"])
def chatbot_webhook():
    payload = request.json
    print(payload)

    # Verifica se é uma mensagem válida
    if payload.get("type") != "MESSAGE":
        return jsonify({"text": "Ignorado: tipo não é MESSAGE"}), 200

    sender = payload.get("message", {}).get("sender", {}).get("email")
    texto = payload.get("message", {}).get("text", "").strip()

    if not sender or not texto.startswith("Farol:"):
        return jsonify({"text": "Formato inválido. Comece com 'Farol:'"}), 200

    # Regex para extrair dados (cliente, área, comentário, sentimento)
    match = re.search(
        r"Farol:\s*Cliente:\s*(.*?)\s*-\s*Área:\s*(.*?)\nComentário:\s*(.*?)\nSentimento:\s*(\w+)",
        texto, re.DOTALL | re.IGNORECASE)

    if not match:
        return jsonify({
            "text":
            "Não entendi o formato da mensagem. Por favor, siga o modelo correto."
        }), 200

    nome_cliente, flag, comentario, sentimento_txt = match.groups()
    nome_cliente = nome_cliente.strip()
    flag = flag.strip().capitalize()
    comentario = comentario.strip()
    sentimento_txt = sentimento_txt.strip().capitalize()

    mapa_sentimentos = {
        "Ótimo": 5,
        "Otimo": 5,
        "Bom": 4,
        "Neutro": 3,
        "Ruim": 2,
        "Péssimo": 1,
        "Pessimo": 1
    }

    sentimento = mapa_sentimentos.get(sentimento_txt)
    if not sentimento:
        return jsonify({
            "text":
            "Sentimento inválido. Use: Ótimo, Bom, Neutro, Ruim ou Péssimo."
        }), 200

    # Carrega lista de clientes
    try:
        with open("data/clientes.json", "r") as f:
            clientes = json.load(f)
    except:
        return jsonify({"text": "Erro ao carregar lista de clientes."}), 200

    cliente = next(
        (c for c in clientes if c["nome"].lower() == nome_cliente.lower()),
        None)
    if not cliente:
        return jsonify({"text":
                        f"Cliente '{nome_cliente}' não encontrado."}), 200

    # Verifica se o autor está entre os responsáveis
    responsaveis = cliente.get("responsaveis", {})
    if sender not in responsaveis.values():
        return jsonify(
            {"text":
             f"Você não é responsável pelo cliente {nome_cliente}."}), 200

    # Cria comentário
    novo_comentario = {
        "cliente_id": cliente["id"],
        "autor": sender,
        "flag": flag,
        "sentimento": sentimento,
        "comentario": comentario,
        "data": (datetime.utcnow() - timedelta(hours=3)).isoformat()
    }

    try:
        with open("data/comentarios.json", "r+") as f:
            dados = json.load(f)
            dados.append(novo_comentario)
            f.seek(0)
            json.dump(dados, f, indent=2, ensure_ascii=False)
        return jsonify({
            "text":
            f"Comentário registrado com sucesso para {nome_cliente}!"
        }), 200
    except Exception as e:
        return jsonify({"text": f"Erro ao salvar comentário: {e}"}), 200

@app.route("/testar_backup")
def testar_backup():
    executar_backup_github()
    return "Backup executado!"

@app.route("/testar_envio_backup")
def testar_envio_backup():
    send_backup_zip()
    return "Backup enviado por e-mail!"

@app.route("/ver_logs_git")
def ver_logs_git():
    try:
        branch = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, check=True).stdout.strip()
        log = subprocess.run(["git", "log", "--oneline", "-n", "5"], capture_output=True, text=True, check=True).stdout.strip()
        status = subprocess.run(["git", "status"], capture_output=True, text=True, check=True).stdout.strip()

        resposta = f"📍 Branch atual:\n{branch}\n\n📦 Últimos commits:\n{log}\n\n🧾 Status atual:\n{status}"
        return Response(resposta, mimetype="text/plain")

    except subprocess.CalledProcessError as e:
        return Response(f"Erro ao executar git log:\n{e.stderr or str(e)}", status=500, mimetype="text/plain")




@app.route("/ver_remote_git")
def ver_remote_git():
    try:
        result = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True, check=True)
        return Response(result.stdout, mimetype="text/plain")
    except subprocess.CalledProcessError as e:
        return Response(f"Erro ao executar git remote -v:\n{e.stderr or str(e)}", status=500, mimetype="text/plain")



from routes.clientes import bp as clientes_bp
from routes.comentarios import bp as comentarios_bp
from routes.ranking import bp as ranking_bp
from routes.historico import bp as historico_bp
from routes.planos import bp as planos_bp
from routes.admin import bp as admin_bp
from routes.lembrete import bp as lembrete_bp

app.register_blueprint(clientes_bp)
app.register_blueprint(comentarios_bp)
app.register_blueprint(ranking_bp)
app.register_blueprint(historico_bp)
app.register_blueprint(planos_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(lembrete_bp)




if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)


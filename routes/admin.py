from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import json, os
from uuid import uuid4
from datetime import datetime, timedelta
from utils.helpers import is_admin, get_cor_farol, formatar_mmr
from utils.helpers import load_admins
from utils.helpers import save_admins
from utils.scheduler import reconfigurar_lembrete
from utils.timestamp import obter_timestamp_local
from datetime import datetime, timedelta
from flask import send_from_directory

bp = Blueprint("admin", __name__)

MASTER_CODE = "tomate"
MASTER_ADMIN = "user_admin"



@bp.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if "user" not in session or not is_admin():
        flash("Acesso restrito", "danger")
        return redirect(url_for("clientes.clientes"))

    admins = load_admins()

    

    if request.method == "POST":
        if "novo_admin" in request.form:
            novo_admin = request.form.get("novo_admin")
            if novo_admin and novo_admin.endswith("@hiplatform.com"):
                if novo_admin not in admins:
                    admins.append(novo_admin)
                    save_admins(admins)
                    flash(f"{novo_admin} agora é admin.", "success")
                else:
                    flash("Este e-mail já é admin.", "warning")
            else:
                flash("Informe um e-mail válido da empresa.", "danger")

        if "remover_admin" in request.form:
            remover = request.form.get("remover_admin")
            if remover != MASTER_ADMIN:
                if remover in admins:
                    admins.remove(remover)
                    save_admins(admins)
                    flash(f"Admin {remover} removido com sucesso.", "success")
                else:
                    flash("Este e-mail não é um admin.", "warning")
            else:
                flash("Este admin não pode ser removido.", "danger")

        if "atualizar_config_comunicacao" in request.form:
            config_path = os.path.join("data", "comunicacoes.json")
            try:
                nova_config = {
                    "envio_emails_planos": "envio_emails_planos" in request.form,
                    "envio_lembretes_chat": "envio_lembretes_chat" in request.form,
                    "dia_lembrete": request.form.get("dia_lembrete"),
                    "hora_lembrete": int(request.form.get("hora_lembrete") or 10),
                    "minuto_lembrete": int(request.form.get("minuto_lembrete") or 0)
                }

                with open(config_path, "w") as f:
                    json.dump(nova_config, f, indent=2)

                reconfigurar_lembrete()

                flash("Configurações de comunicação atualizadas!", "success")

            except Exception as e:
                flash(f"Erro ao salvar configurações: {e}", "danger")

    try:
        with open("data/comunicacoes.json", "r") as f:
            config = json.load(f)
    except:
        config = {}

    # 🔁 Novo: obtém o timestamp do último backup
    ultimo_backup = obter_timestamp_local()

    timestamp_bruto = obter_timestamp_local()

    if timestamp_bruto:
        dt_obj = datetime.fromisoformat(timestamp_bruto)
        dt_formatado = (dt_obj - timedelta(hours=3)).strftime("%d/%m/%Y %Hh%M")
    else:
        dt_formatado = None
        
    return render_template(
        "admin.html",
        admins=admins,
        config=config,
        ultimo_backup_formatado=dt_formatado
    )

@bp.route("/admin/backup", methods=["GET", "POST"])
def admin_backup():
    if "user" not in session or not is_admin():
        flash("Acesso restrito", "danger")
        return redirect(url_for("clientes.clientes"))

    data_dir = "data"
    arquivos = [f for f in os.listdir(data_dir) if f.endswith(".json")]

    # Atualizar config se necessário
    if request.method == "POST":
        if request.form.get("atualizar_backup_github"):
            try:
                config_path = os.path.join(data_dir, "comunicacoes.json")
                with open(config_path, "r") as f:
                    config = json.load(f)

                config["backup_ativo"] = "backup_ativo" in request.form

                with open(config_path, "w") as f:
                    json.dump(config, f, indent=2)

                flash("Configuração de backup atualizada!", "success")
            except Exception as e:
                flash(f"Erro ao atualizar configuração: {e}", "danger")

        else:
            # upload .json
            arquivo = request.files.get("arquivo")
            if not arquivo:
                flash("Nenhum arquivo enviado.", "warning")
                return redirect(url_for("admin.admin_backup"))

            nome = arquivo.filename
            if nome not in arquivos:
                flash("Nome de arquivo inválido. Só é possível substituir arquivos existentes.", "danger")
                return redirect(url_for("admin.admin_backup"))

            try:
                conteudo = json.load(arquivo.stream)
                caminho = os.path.join(data_dir, nome)
                with open(caminho, "w", encoding="utf-8") as f:
                    json.dump(conteudo, f, indent=2, ensure_ascii=False)
                flash(f"Arquivo '{nome}' atualizado com sucesso.", "success")
            except Exception as e:
                flash(f"Erro ao processar o arquivo: {e}", "danger")

        return redirect(url_for("admin.admin_backup"))

    # (Re)carregar config antes de renderizar
    with open("data/comunicacoes.json", "r") as f:
        config = json.load(f)

    return render_template("admin_backup.html", arquivos=arquivos, config=config)


@bp.route("/admin/backup/download/<nome>")
def baixar_backup(nome):
    if "user" not in session or not is_admin():
        flash("Acesso restrito", "danger")
        return redirect(url_for("clientes.clientes"))

    caminho = os.path.join("data", nome)
    if not os.path.exists(caminho):
        return "Arquivo não encontrado", 404
    return send_from_directory("data", nome, as_attachment=True)

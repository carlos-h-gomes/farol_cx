from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
import json, os, csv, io
from uuid import uuid4
from datetime import datetime, timedelta
from utils.helpers import is_admin, get_cor_farol, formatar_mmr

bp = Blueprint("comentarios", __name__)


@bp.route("/comentarios/remover", methods=["POST"])
def remover_comentario():
    if "user" not in session or not is_admin():
        flash("Acesso restrito", "danger")
        return redirect(url_for("clientes"))

    cliente_id = request.form.get("cliente_id")
    data_alvo = request.form.get("data")

    try:
        with open("data/comentarios.json", "r+", encoding="utf-8") as f:
            comentarios = json.load(f)
            novo_conjunto = [
                c for c in comentarios if not (
                    c["cliente_id"] == cliente_id and c["data"] == data_alvo)
            ]

            if len(novo_conjunto) < len(comentarios):
                f.seek(0)
                f.truncate()
                json.dump(novo_conjunto, f, indent=2, ensure_ascii=False)
                flash("Comentário removido com sucesso!", "success")
            else:
                flash("Comentário não encontrado", "danger")

    except Exception as e:
        flash(f"Erro ao remover comentário: {e}", "danger")

    return redirect(url_for("clientes.comentar_cliente", cliente_id=cliente_id))


@bp.route("/comentarios/editar", methods=["POST"])
def editar_comentario():
    if "user" not in session:
        flash("Acesso restrito", "danger")
        return redirect(url_for("clientes"))

    cliente_id = request.form.get("cliente_id")
    data_alvo = request.form.get("data")
    novo_texto = request.form.get("comentario")
    novo_representante = request.form.get("representante", "").strip()
    nova_data_contato = request.form.get("data_contato", "").strip()

    try:
        with open("data/comentarios.json", "r+", encoding="utf-8") as f:
            comentarios = json.load(f)
            alterado = False

            for c in comentarios:
                if c["cliente_id"] == cliente_id and c["data"] == data_alvo and c["autor"] == session["user"]:
                    c["comentario"] = novo_texto
                    c["representante"] = novo_representante
                    c["data_contato"] = nova_data_contato
                    alterado = True
                    break

            if alterado:
                f.seek(0)
                f.truncate()
                json.dump(comentarios, f, indent=2, ensure_ascii=False)
                flash("Comentário editado com sucesso!", "success")
            else:
                flash("Comentário não encontrado ou sem permissão.", "danger")

    except Exception as e:
        flash(f"Erro ao editar comentário: {e}", "danger")

    return redirect(url_for("clientes.comentar_cliente", cliente_id=cliente_id))


@bp.route("/comentarios/exportar", methods=["GET"])
def exportar_comentarios_geral():
    try:
        # Carregar clientes
        with open("data/clientes.json", encoding="utf-8") as f:
            clientes = json.load(f)
            mapa_clientes = {cliente["id"]: cliente["nome"] for cliente in clientes}

        # Carregar comentários
        with open("data/comentarios.json", encoding="utf-8") as f:
            comentarios = json.load(f)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Cliente ID", "Cliente Nome", "Autor", "Comentário", "Data",
            "Representante do cliente", "Data do último contato"
        ])

        for comentario in comentarios:
            cliente_id = comentario.get("cliente_id", "")
            nome_cliente = mapa_clientes.get(cliente_id, "")
            comentario_limpo = comentario.get("comentario", "").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")

            # Formatação de data
            try:
                data_formatada = datetime.fromisoformat(comentario.get("data", "")).strftime("%d/%m/%Y %H:%M")
            except Exception:
                data_formatada = comentario.get("data", "")  # fallback sem formatação

            writer.writerow([
                cliente_id,
                nome_cliente,
                comentario.get("autor", ""),
                comentario_limpo,
                data_formatada,
                comentario.get("representante", ""),
                comentario.get("data_contato", "")
            ])

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            mimetype="text/csv",
            as_attachment=True,
            download_name="comentarios_geral.csv"
        )

    except Exception as e:
        flash(f"Erro ao exportar comentários: {e}", "danger")
        return redirect(url_for("admin"))

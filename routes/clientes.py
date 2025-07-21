from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import json, os
from uuid import uuid4
from datetime import datetime, timedelta, date
from utils.helpers import is_admin, get_cor_farol, formatar_mmr
from io import StringIO
from flask import Response
import csv

from utils.email_sender import send_plain_email
from utils.helpers import formatar_cliente_para_salvar


bp = Blueprint("clientes", __name__)

@bp.route("/clientes")
def clientes():
    if "user" not in session:
        return redirect(url_for("login"))

    try:
        with open("data/clientes.json", "r") as f:
            clientes = json.load(f)
    except Exception:
        clientes = []

    # Filtro por nome
    query = request.args.get("q", "").strip().lower()
    if query:
        filtrados = []
        for c in clientes:
            if query in c["nome"].lower():
                filtrados.append(c)
                continue
            if query.lstrip("#") in str(c.get("id_operacao", "")).lower().lstrip("#"):
                filtrados.append(c)
                continue
            if query in c.get("operacao", "").lower():
                filtrados.append(c)
                continue
            for area in ["cs", "gp", "analista"]:
                responsavel = c.get("responsaveis", {}).get(area, {})
                if query in responsavel.get("nome", "").lower():
                    filtrados.append(c)
                    break
        clientes = filtrados

    # Filtro por estado
    estados_param = request.args.getlist("estados")
    if estados_param:
        clientes = [c for c in clientes if c.get("estado", "Contrato") in estados_param]

    # Formatar valores e datas
    hoje = datetime.today().date()
    for c in clientes:
        try:
            valor = float(str(c.get("mmr", "0")).replace(",", "."))
            c["mmr_formatado"] = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            c["mmr_formatado"] = "R$ 0,00"

        if c.get("inicio_contrato"):
            try:
                c["inicio_formatado"] = datetime.fromisoformat(c["inicio_contrato"]).strftime("%d/%m/%Y")
            except:
                c["inicio_formatado"] = "-"
        if c.get("fim_contrato"):
            try:
                dt_fim = datetime.fromisoformat(c["fim_contrato"])
                dias = (dt_fim.date() - hoje).days
                c["fim_formatado"] = dt_fim.strftime("%d/%m/%Y")
                c["destaque_data"] = dias <= 30
            except:
                c["fim_formatado"] = "-"
                c["destaque_data"] = False
        else:
            c["fim_formatado"] = "-"
            c["destaque_data"] = False

        if c.get("data_churn"):
            try:
                dt_churn = datetime.fromisoformat(c["data_churn"])
                c["data_churn_formatada"] = dt_churn.strftime("%d/%m/%Y")
            except:
                c["data_churn_formatada"] = "-"
        else:
            c["data_churn_formatada"] = "-"

    # Ordenação personalizada
    ordenar_por = request.args.get("ordenar_por", "risco")

    if ordenar_por == "nome":
        clientes.sort(key=lambda c: c["nome"].lower())
    elif ordenar_por == "mmr_desc":
        clientes.sort(key=lambda c: float(str(c.get("mmr", "0")).replace(",", ".")), reverse=True)
    elif ordenar_por == "mmr_asc":
        clientes.sort(key=lambda c: float(str(c.get("mmr", "0")).replace(",", ".")))
    elif ordenar_por == "gp":
        clientes.sort(key=lambda c: c["responsaveis"].get("gp", {}).get("nome", "").lower())
    elif ordenar_por == "cs":
        clientes.sort(key=lambda c: c["responsaveis"].get("cs", {}).get("nome", "").lower())
    elif ordenar_por == "analista":
        clientes.sort(key=lambda c: c["responsaveis"].get("analista", {}).get("nome", "").lower())
    else:
        def prioridade_estado(cliente):
            estado = cliente.get("estado", "")
            if estado == "Em Risco de Churn":
                return 0
            elif estado == "Contrato":
                return 1
            elif estado == "Churn efetivado":
                return 2
            return 3
        clientes.sort(key=prioridade_estado)

    # Calcula status farol baseado em comentários recentes
    comentarios = []
    try:
        with open("data/comentarios.json", "r") as f:
            todos = json.load(f)
            uma_semana_atras = datetime.now() - timedelta(days=7)
            comentarios = [c for c in todos if datetime.fromisoformat(c["data"]) >= uma_semana_atras]
    except:
        comentarios = []

    cliente_status = {}
    for c in clientes:
        comentarios_cliente = [cmt for cmt in comentarios if cmt["cliente_id"] == c["id"] and "sentimento" in cmt]
        if comentarios_cliente:
            media = sum(cmt["sentimento"] for cmt in comentarios_cliente) / len(comentarios_cliente)
            cor = get_cor_farol(media)
        else:
            cor = "gray"
        cliente_status[c["id"]] = cor

    return render_template("clientes.html",
                           user=session["user"],
                           clientes=clientes,
                           status=cliente_status,
                           estados=estados_param)


@bp.route("/clientes/novo", methods=["GET", "POST"])
def novo_cliente():
    if "user" not in session:
        return redirect(url_for("login"))
    if not is_admin():
        flash("Acesso restrito", "danger")
        return redirect(url_for("clientes.clientes"))

    if request.method == "POST":
        novo = formatar_cliente_para_salvar(request.form)
        novo["id"] = str(uuid4())

        # Verifica se ID de operação já existe
        try:
            with open("data/clientes.json", "r") as f:
                data = json.load(f)
        except:
            data = []

        id_op = novo.get("id_operacao")
        if id_op and any(c.get("id_operacao") == id_op for c in data):
            flash("Já existe um cliente com este ID de Operação.", "danger")
            return redirect(url_for("clientes.novo_cliente"))

        try:
            with open("data/clientes.json", "r+") as f:
                data = json.load(f)
                data.append(novo)
                f.seek(0)
                json.dump(data, f, indent=2, ensure_ascii=False)
            flash("Cliente adicionado com sucesso!", "success")
        except Exception as e:
            flash(f"Erro ao salvar cliente: {e}", "danger")

        return redirect(url_for("clientes.clientes"))

    return render_template("cliente_form.html")

@bp.route("/clientes/<cliente_id>/remover", methods=["POST"])
def remover_cliente(cliente_id):
    if "user" not in session or not is_admin():
        flash("Acesso restrito", "danger")
        return redirect(url_for("clientes.clientes"))

    try:
        with open("data/clientes.json", "r+") as f:
            data = json.load(f)
            data = [c for c in data if c["id"] != cliente_id]
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2, ensure_ascii=False)
        flash("Cliente removido com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao remover cliente: {e}", "danger")

    return redirect(url_for("clientes.clientes"))

@bp.route("/clientes/<cliente_id>/editar", methods=["GET", "POST"])
def editar_cliente(cliente_id):
    if "user" not in session or not is_admin():
        flash("Acesso restrito", "danger")
        return redirect(url_for("clientes.clientes"))

    try:
        with open("data/clientes.json", "r+") as f:
            clientes = json.load(f)
            cliente = next((c for c in clientes if c["id"] == cliente_id),
                           None)

            if not cliente:
                flash("Cliente não encontrado", "danger")
                return redirect(url_for("clientes.clientes"))

            if request.method == "POST":
                atualizado = formatar_cliente_para_salvar(request.form)
                atualizado["id"] = cliente_id

                id_op = atualizado.get("id_operacao")
                if id_op:
                    for c in clientes:
                        if c["id"] != cliente_id and c.get("id_operacao") == id_op:
                            flash("Já existe outro cliente com este ID de Operação.", "danger")
                            return redirect(url_for("clientes.editar_cliente", cliente_id=cliente_id))
                clientes = [
                    atualizado if c["id"] == cliente_id else c
                    for c in clientes
                ]
                f.seek(0)
                f.truncate()
                json.dump(clientes, f, indent=2, ensure_ascii=False)
                flash("Cliente atualizado com sucesso!", "success")
                return redirect(url_for("clientes.clientes"))

    except Exception as e:
        flash(f"Erro ao editar cliente: {e}", "danger")
        return redirect(url_for("clientes.clientes"))

    return render_template("cliente_form.html", cliente=cliente)

@bp.route("/clientes/<cliente_id>/comentario", methods=["GET", "POST"])
def comentar_cliente(cliente_id):
    data_inicio_str = request.args.get("data_inicio")
    data_fim_str = request.args.get("data_fim")

    hoje = datetime.now()
    inicio_periodo = hoje - timedelta(days=30)

    data_inicio = datetime.fromisoformat(data_inicio_str) if data_inicio_str else inicio_periodo
    data_fim = datetime.fromisoformat(data_fim_str) if data_fim_str else hoje


    if "user" not in session:
        return redirect(url_for("login"))

    try:
        with open("data/clientes.json", "r") as f:
            clientes = json.load(f)
        cliente = next((c for c in clientes if c["id"] == cliente_id), None)
    except Exception:
        cliente = None

    if not cliente:
        flash("Cliente não encontrado", "danger")
        return redirect(url_for("clientes.clientes"))

    if request.method == "POST":
        texto = request.form.get("comentario")
        flag = request.form.get("flag")
        sentimento = int(request.form.get("sentimento"))
        representante = request.form.get("representante", "").strip()
        data_contato = request.form.get("data_contato", "").strip()


        comentario = {
            "cliente_id": cliente_id,
            "autor": session["user"],
            "flag": flag,
            "sentimento": sentimento,
            "comentario": texto,
            "representante": representante,
            "data_contato": data_contato,
            "data": (datetime.utcnow() - timedelta(hours=3)).isoformat()
            
        }

        try:
            with open("data/comentarios.json", "r+") as f:
                data = json.load(f)
                data.append(comentario)
                f.seek(0)
                json.dump(data, f, indent=2, ensure_ascii=False)
            flash("Comentário adicionado!", "success")
            return redirect(url_for("clientes.comentar_cliente", cliente_id=cliente_id))
        except Exception as e:
            flash(f"Erro ao salvar comentário: {e}", "danger")

    comentarios_cliente = []
    try:
        with open("data/comentarios.json", "r") as f:
            todos = json.load(f)
            comentarios_cliente = [
                c for c in todos if c["cliente_id"] == cliente_id and
                data_inicio <= datetime.fromisoformat(c["data"]) <= data_fim
            ]
            comentarios_cliente.sort(key=lambda x: x["data"], reverse=True)
    except Exception:
        comentarios_cliente = []

    return render_template("comentar.html",
           cliente=cliente,
           comentarios=comentarios_cliente,
           user=session["user"],
           datetime=datetime,
           inicio_periodo=inicio_periodo,
           fim_periodo=hoje)

@bp.route("/clientes/<cliente_id>/comentarios/exportar")
def exportar_comentarios(cliente_id):
    if "user" not in session:
        return redirect(url_for("login"))

    data_inicio_str = request.args.get("data_inicio")
    data_fim_str = request.args.get("data_fim")

    try:
        with open("data/comentarios.json", "r", encoding="utf-8") as f:
            comentarios = json.load(f)

        filtrados = [c for c in comentarios if c["cliente_id"] == cliente_id]

        # Filtro por data
        try:
            if data_inicio_str:
                data_inicio = datetime.fromisoformat(data_inicio_str)
                filtrados = [
                    c for c in filtrados
                    if datetime.fromisoformat(c["data"]) >= data_inicio
                ]
            if data_fim_str:
                data_fim = datetime.fromisoformat(data_fim_str)
                filtrados = [
                    c for c in filtrados
                    if datetime.fromisoformat(c["data"]) <= data_fim
                ]
        except ValueError:
            pass  # ignora filtro se datas forem inválidas

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Data", "Autor", "Área", "Sentimento", "Comentário",
            "Representante do cliente", "Data do último contato"
        ])

        for c in filtrados:
            dt = datetime.fromisoformat(c["data"]).strftime("%d/%m/%Y %H:%M")
            comentario_limpo = c.get("comentario", "").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
            writer.writerow([
                dt,
                c.get("autor", ""),
                c.get("flag", ""),
                c.get("sentimento", ""),
                comentario_limpo,
                c.get("representante", ""),
                c.get("data_contato", "")
            ])

        conteudo = '\ufeff' + output.getvalue()
        response = Response(conteudo, mimetype="text/csv")
        response.headers[
            "Content-Disposition"] = f"attachment; filename=comentarios_{cliente_id}.csv"
        return response

    except Exception as e:
        flash(f"Erro ao exportar: {e}", "danger")
        return redirect(url_for("clientes.comentar_cliente", cliente_id=cliente_id))


@bp.route("/clientes/<cliente_id>/comentarios/email")
def enviar_comentarios_por_email(cliente_id):
    if "user" not in session:
        return redirect(url_for("login"))

    email_destino = session["user"]

    try:
        with open("data/clientes.json", "r") as f:
            clientes = json.load(f)
        cliente = next((c for c in clientes if c["id"] == cliente_id),
                       {"nome": "Cliente"})

        with open("data/comentarios.json", "r") as f:
            comentarios = json.load(f)

        filtrados = [c for c in comentarios if c["cliente_id"] == cliente_id]

        corpo = f"Comentários sobre {cliente['nome']}:\n\n"
        for c in filtrados:
            flag = c.get("flag", "")
            sentimento = c.get("sentimento", "")
            autor = c.get("autor", "")
            data = c["data"][:10]
            texto = c["comentario"]
            representante = c.get("representante", "")
            data_contato = c.get("data_contato", "")
            
            corpo += (
                f"[{data} - {flag}] ({autor})\n"
                f"Nota: {sentimento}\n"
                f"{texto}\n"
            )
            if representante or data_contato:
                corpo += f"Contato com: {representante or '—'} em {data_contato or '—'}\n"
            corpo += "\n"

        send_plain_email(email_destino, f"Comentários sobre {cliente['nome']}",
                         corpo)
        flash("E-mail enviado com sucesso!", "success")

    except Exception as e:
        flash(f"Erro ao enviar e-mail: {e}", "danger")

    return redirect(url_for("clientes.comentar_cliente", cliente_id=cliente_id))

@bp.route("/clientes/verificar_id_operacao")
def verificar_id_operacao():
    id_op = request.args.get("id_operacao")
    cliente_id = request.args.get("cliente_id")  # opcional

    if not id_op:
        return {"existe": False}

    try:
        with open("data/clientes.json", "r") as f:
            clientes = json.load(f)
    except:
        return {"existe": False}

    for c in clientes:
        if c.get("id_operacao") == id_op and c.get("id") != cliente_id:
            return {"existe": True}

    return {"existe": False}

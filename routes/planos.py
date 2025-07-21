from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import json, os
from uuid import uuid4
from datetime import datetime, timedelta
from utils.helpers import is_admin, get_cor_farol, formatar_mmr
from flask import Response
from io import StringIO
import csv
from urllib.parse import urlparse
from uuid import uuid4
from utils.email_sender import send_html_email
from datetime import timezone
import pytz


bp = Blueprint("planos", __name__)

@bp.route("/planos")
def planos_geral():
    if "user" not in session:
        return redirect(url_for("login"))

    cliente_id = request.args.get("cliente_id")
    data_inicio_str = request.args.get("data_inicio")
    data_fim_str = request.args.get("data_fim")

    try:
        with open("data/clientes.json", "r") as f:
            clientes = json.load(f)
    except:
        clientes = []

    try:
        with open("data/planos_acao.json", "r") as f:
            todos_planos = json.load(f)
    except:
        todos_planos = []

    # Filtro por cliente
    if cliente_id:
        todos_planos = [p for p in todos_planos if p.get("cliente_id") == cliente_id]

    # Filtro por período
    try:
        data_inicio = datetime.fromisoformat(data_inicio_str) if data_inicio_str else None
        data_fim = datetime.fromisoformat(data_fim_str) if data_fim_str else None
    except ValueError:
        data_inicio = None
        data_fim = None

    if data_inicio:
        todos_planos = [
            p for p in todos_planos
            if "criado_em" in p and datetime.fromisoformat(p["criado_em"]) >= data_inicio
        ]
    if data_fim:
        todos_planos = [
            p for p in todos_planos
            if "criado_em" in p and datetime.fromisoformat(p["criado_em"]) <= data_fim
        ]

    # Adiciona nome do cliente formatado
    for p in todos_planos:
        cliente = next((c for c in clientes if c["id"] == p["cliente_id"]), {})
        nome = cliente.get("nome", "Desconhecido")
        id_op = cliente.get("id_operacao", "")
        p["cliente_nome"] = f"{nome} #{id_op}" if id_op else nome

    # Ordena por data de criação (mais recentes primeiro)
    todos_planos.sort(key=lambda p: datetime.fromisoformat(p.get("criado_em", "1970-01-01T00:00:00")), reverse=True)

    # Paginação
    page = int(request.args.get("page", 1))
    per_page = 10
    total = len(todos_planos)
    start = (page - 1) * per_page
    end = start + per_page
    planos_paginados = todos_planos[start:end]
    total_paginas = max(1, (total + per_page - 1) // per_page)

    return render_template("planos.html",
                           clientes=clientes,
                           planos=planos_paginados,
                           cliente_id=cliente_id,
                           data_inicio=data_inicio_str,
                           data_fim=data_fim_str,
                           pagina_atual=page,
                           total_paginas=total_paginas)

@bp.route("/clientes/<cliente_id>/planos", endpoint="planos_cliente")
def visualizar_planos(cliente_id):
    if "user" not in session:
        return redirect(url_for("login"))

    try:
        with open("data/clientes.json", "r") as f:
            clientes = json.load(f)
        cliente = next((c for c in clientes if c["id"] == cliente_id), None)
    except:
        cliente = None

    if not cliente:
        flash("Cliente não encontrado", "danger")
        return redirect(url_for("clientes.clientes"))

    planos_cliente = []
    try:
        with open("data/planos_acao.json", "r") as f:
            planos = json.load(f)
            planos_cliente = [p for p in planos if p.get("cliente_id") == cliente_id]
            planos_cliente.sort(key=lambda p: datetime.fromisoformat(p.get("criado_em", "1970-01-01T00:00:00")), reverse=True)
    except:
        planos_cliente = []

    # Paginação garantida mesmo com lista vazia
    page = int(request.args.get("page", 1))
    per_page = 10
    total = len(planos_cliente)
    start = (page - 1) * per_page
    end = start + per_page
    planos_paginados = planos_cliente[start:end]
    total_paginas = max(1, (total + per_page - 1) // per_page)

    return render_template("planos_cliente.html",
                           cliente=cliente,
                           planos=planos_paginados,
                           pagina_atual=page,
                           total_paginas=total_paginas)

@bp.route("/planos/atualizar_status", methods=["POST"])
def atualizar_status_plano():
    if "user" not in session:
        flash("Não autorizado.", "danger")
        return redirect(url_for("login"))

    cliente_id = request.form.get("cliente_id")
    id_plano = request.form.get("id_plano")
    novo_status = request.form.get("status")
    resultado = request.form.get("resultado")
    tarefa = request.form.get("tarefa")  # opcional
    item_index = request.form.get("item_index")  # opcional
    origem = request.form.get("origem")

    json_path = "data/planos_acao.json"

    try:
        with open(json_path, "r") as f:
            planos = json.load(f)

        plano = next((p for p in planos if p.get("id_plano") == id_plano), None)
        if not plano:
            flash("Plano não encontrado.", "danger")
            return redirect(url_for("planos.planos_geral"))

        # 🧠 Nova lógica flexível:
        if item_index is not None:
            item_index = int(item_index)
            if item_index < 0 or item_index >= len(plano["itens"]):
                flash("Índice de item inválido.", "danger")
                return redirect(url_for("planos.planos_geral"))
            item = plano["itens"][item_index]
        elif tarefa:
            item = next((i for i in plano["itens"] if i.get("tarefa") == tarefa), None)
            if not item:
                flash("Item não encontrado pelo nome da tarefa.", "danger")
                return redirect(url_for("planos.planos_geral"))
        else:
            flash("Dados incompletos para atualização.", "danger")
            return redirect(url_for("planos.planos_geral"))

        # Atualizar o item encontrado
        item["status"] = novo_status
        if resultado:
            item["resultado"] = resultado

        with open(json_path, "w") as f:
            json.dump(planos, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        flash("Plano atualizado com sucesso!", "success")

    except Exception as e:
        flash(f"Erro ao atualizar plano: {e}", "danger")
        return redirect(url_for("planos.planos_geral"))

    # Redirecionamento seguro
    if origem == "kanban":
        return redirect(url_for("planos.planos_kanban"))
    else:
        return redirect(url_for("planos.planos_geral"))



@bp.route("/planos/excluir", methods=["POST"])
def excluir_plano():
    if "user" not in session or not is_admin():
        flash("Acesso negado", "danger")
        return redirect(url_for("clientes.clientes"))

    cliente_id = request.form.get("cliente_id")
    id_plano = request.form.get("id_plano")

    try:
        with open("data/planos_acao.json", "r+") as f:
            planos = json.load(f)

            plano_a_excluir = next((p for p in planos if p.get("id_plano") == id_plano and p.get("cliente_id") == cliente_id), None)

            if not plano_a_excluir:
                flash("Plano não encontrado", "danger")
                return redirect(url_for("planos.planos_cliente", cliente_id=cliente_id))

            planos.remove(plano_a_excluir)

            f.seek(0)
            f.truncate()
            json.dump(planos, f, indent=2, ensure_ascii=False)

            flash("Plano excluído com sucesso", "success")

    except Exception as e:
        flash(f"Erro ao excluir plano: {e}", "danger")

    referer = request.headers.get("Referer", "")

    # Usa o path completo da URL (sem domínio)
    parsed = urlparse(referer).path

    if parsed.startswith("/clientes/") and "/planos" in parsed:
        return redirect(url_for("planos.planos_cliente", cliente_id=cliente_id))
    else:
        return redirect(url_for("planos.planos_geral"))

@bp.route("/planos/exportar")
def exportar_planos():
    if "user" not in session:
        return redirect(url_for("login"))

    cliente_id = request.args.get("cliente_id")
    data_inicio_str = request.args.get("data_inicio")
    data_fim_str = request.args.get("data_fim")

    try:
        data_inicio = datetime.fromisoformat(data_inicio_str) if data_inicio_str else None
        data_fim = datetime.fromisoformat(data_fim_str) if data_fim_str else None
    except ValueError:
        data_inicio = data_fim = None

    try:
        with open("data/clientes.json", "r") as f:
            clientes = json.load(f)

        with open("data/planos_acao.json", "r", encoding="utf-8") as f:
            planos = json.load(f)

        if cliente_id:
            planos_filtrados = [p for p in planos if p["cliente_id"] == cliente_id]
            nome_arquivo = next((c["nome"] for c in clientes if c["id"] == cliente_id), "cliente")
        else:
            planos_filtrados = planos
            nome_arquivo = "todos_clientes"

        if data_inicio:
            planos_filtrados = [
                p for p in planos_filtrados
                if "criado_em" in p and datetime.fromisoformat(p["criado_em"]) >= data_inicio
            ]
        if data_fim:
            planos_filtrados = [
                p for p in planos_filtrados
                if "criado_em" in p and datetime.fromisoformat(p["criado_em"]) <= data_fim
            ]

        output = StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        writer.writerow([
            "Data", "Cliente", "ID Cliente", "Operação", "Descrição",
            "Tarefa", "Responsável", "Prazo", "Status", "Resultado"
        ])

        for p in planos_filtrados:
            data = p.get("criado_em", "")[:10]
            cliente_nome = p.get("nome_cliente", "-")
            id_operacao = p.get("id_operacao", "-")
            operacao = p.get("operacao", "-")
            descricao = p.get("descricao", "").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")

            for item in p.get("itens", []):
                resultado = item.get("resultado", "").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
                writer.writerow([
                    data,
                    cliente_nome,
                    id_operacao,
                    operacao,
                    descricao,
                    item.get("tarefa", ""),
                    item.get("responsavel", ""),
                    item.get("prazo", ""),
                    item.get("status", ""),
                    resultado
                ])

        response = Response(output.getvalue(), mimetype="text/csv")
        filename = f"planos_{nome_arquivo.replace(' ', '_')}.csv"
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    except Exception as e:
        flash(f"Erro ao exportar: {e}", "danger")
        return redirect(url_for("planos.planos_cliente", cliente_id=cliente_id))



@bp.route("/planos/salvar", methods=["POST"])
def salvar_plano():
    cliente_id = request.form.get("cliente_id")
    descricao = request.form.get("descricao")
    titulo = request.form.get("titulo", "").strip()

    itens = []
    for i in range(len(request.form)):
        tarefa = request.form.get(f"itens[{i}][tarefa]")
        responsavel = request.form.get(f"itens[{i}][responsavel]")
        prazo = request.form.get(f"itens[{i}][prazo]")
        status = request.form.get(f"itens[{i}][status]")
        if tarefa:
            itens.append({
                "tarefa": tarefa,
                "responsavel": responsavel,
                "prazo": prazo,
                "status": status,
                "resultado": ""
            })

    # Buscar dados do cliente
    cliente = {}
    try:
        with open("data/clientes.json", "r") as f:
            clientes = json.load(f)
            cliente = next((c for c in clientes if c["id"] == cliente_id), {})
    except:
        cliente = {}

    
    plano = {
        "id_plano": str(uuid4()),
        "cliente_id": cliente_id,
        "descricao": descricao,
        "titulo": titulo,
        "itens": itens,
        "criado_em": (datetime.utcnow() - timedelta(hours=3)).isoformat(),
        "id_operacao": cliente.get("id_operacao", ""),
        "operacao": cliente.get("operacao", ""),
        "nome_cliente": cliente.get("nome", "Desconhecido")
    }

    try:
        os.makedirs("data", exist_ok=True)
        path = "data/planos_acao.json"
        if os.path.exists(path):
            with open(path, "r") as f:
                dados = json.load(f)
        else:
            dados = []

        dados.insert(0, plano)

        with open(path, "w") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

        # Enviar e-mail aos responsáveis do plano e do cadastro
        emails_destino = set()

        # 1. Responsáveis cadastrados no cliente
        for cargo in ["cs", "gp", "analista"]:
            pessoa = cliente.get("responsaveis", {}).get(cargo)
            if pessoa and pessoa.get("email"):
                emails_destino.add(pessoa["email"])

        # 2. Responsáveis do checklist (se for e-mail)
        for item in plano["itens"]:
            possivel_email = item.get("responsavel", "").strip()
            if "@" in possivel_email and "." in possivel_email:
                emails_destino.add(possivel_email)

        # Corpo do e-mail
        corpo = f"""Olá,

Um novo plano de ação foi criado para o cliente {plano['nome_cliente']}.

Título: {plano['titulo']}
Descrição: {plano['descricao']}

Checklist:
"""
        for item in plano["itens"]:
            corpo += f"- {item['tarefa']} (Responsável: {item['responsavel']} | Prazo: {item['prazo']})\n"

        corpo += """
Acesse o sistema da Plataforma Farol para acompanhar o andamento.

-- Plataforma Farol
"""

        try:
            with open("data/comunicacoes.json", "r") as f:
                config = json.load(f)
        except:
            config = {}

        if config.get("envio_emails_planos", True):
            for email in emails_destino:
                print(f"Enviando e-mail para {email}")
                send_html_email(email, f"[Farol] Novo Plano de Ação: {plano['titulo']}", plano)
        else:
            print("[INFO] Envio de e-mails de planos desativado por configuração.")

        flash("Plano de ação salvo com sucesso!", "success")

    except Exception as e:
        flash(f"Erro ao salvar plano: {e}", "danger")

    referer = request.headers.get("Referer", "")
    if "/clientes/" in referer:
        return redirect(url_for("planos.planos_cliente", cliente_id=cliente_id))
    elif "/planos" in referer:
        return redirect(url_for("planos.planos_geral"))
    else:
        return redirect(url_for("ranking.ranking"))


@bp.route("/planos/kanban")
def planos_kanban():
    if "user" not in session:
        return redirect(url_for("login"))

    try:
        with open("data/planos_acao.json", "r") as f:
            planos = json.load(f)
    except:
        planos = []

    pendentes = []
    andamento = []
    concluidos = []

    for plano in planos:
        id_curto = plano.get("id_plano", "")[:8]
        cliente = plano.get("nome_cliente", "Cliente Desconhecido")
        titulo = plano.get("titulo", "Sem título")
        for idx, item in enumerate(plano.get("itens", [])):
            card = {
                "id_plano": plano.get("id_plano", ""),  # <- Aqui colocamos o ID completo para o clique duplo
                "id_curto": plano.get("id_plano", "")[:8],  # (opcional) caso ainda precise do curto em outro lugar

                "plano_titulo": titulo,
                "cliente_nome": cliente,
                "tarefa": item.get("tarefa", ""),
                "responsavel": item.get("responsavel", ""),
                "prazo": item.get("prazo", ""),
                "status": item.get("status", "Pendente"),
                "id_item": idx,
                "id_full": plano.get("id_plano", ""),
                "cliente_id": plano.get("cliente_id", "")
            }
            if item.get("status") == "Concluído":
                concluidos.append(card)
            elif item.get("status") == "Em Andamento":
                andamento.append(card)
            else:
                pendentes.append(card)


    return render_template("planos_kanban.html",
                           pendentes=pendentes,
                           andamento=andamento,  # Para futuro: mover quando fizermos "parcial"
                           concluidos=concluidos)



@bp.route("/planos/atualizar_status_kanban", methods=["POST"])
def atualizar_status_kanban():
    if "user" not in session:
        flash("Não autorizado.", "danger")
        return redirect(url_for("login"))

    cliente_id = request.form.get("cliente_id")
    id_plano = request.form.get("id_plano")
    novo_status = request.form.get("status")
    resultado = request.form.get("resultado")
    tarefa = request.form.get("tarefa")

    print("\n[DEBUG] Dados recebidos na atualização do Kanban:")
    print("cliente_id:", cliente_id)
    print("id_plano:", id_plano)
    print("novo_status:", novo_status)
    print("resultado:", resultado)
    print("tarefa:", tarefa)

    json_path = "data/planos_acao.json"

    try:
        with open(json_path, "r") as f:
            planos = json.load(f)

        plano = next((p for p in planos if p.get("id_plano") == id_plano), None)
        if not plano:
            print("[DEBUG] Plano não encontrado.")
            flash("Plano não encontrado.", "danger")
            return redirect(url_for("planos.planos_kanban"))

        print("[DEBUG] Itens do plano encontrado:")
        for idx, i in enumerate(plano["itens"]):
            print(f"- [{idx}] {i.get('tarefa')} (Status atual: {i.get('status')})")

        # Buscar pelo texto da tarefa
        item = next((i for i in plano["itens"] if i.get("tarefa") == tarefa), None)
        if not item:
            print("[DEBUG] Item não encontrado pelo texto da tarefa!")
            flash("Item não encontrado pelo nome da tarefa.", "danger")
            return redirect(url_for("planos.planos_kanban"))

        item["status"] = novo_status
        if resultado:
            item["resultado"] = resultado

        with open(json_path, "w") as f:
            json.dump(planos, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        print("[DEBUG] JSON atualizado com sucesso!")

        flash("Plano atualizado com sucesso!", "success")

    except Exception as e:
        print("[DEBUG] Erro ao atualizar plano:", str(e))
        flash(f"Erro ao atualizar plano: {e}", "danger")
        return redirect(url_for("planos.planos_kanban"))

    return redirect(url_for("planos.planos_kanban"))


@bp.route("/planos/atualizar_descricao_kanban", methods=["POST"])
def atualizar_descricao_kanban():
    if "user" not in session:
        flash("Não autorizado.", "danger")
        return redirect(url_for("login"))

    cliente_id = request.form.get("cliente_id")
    id_plano = request.form.get("id_plano")
    tarefa = request.form.get("tarefa")
    atualizacao = request.form.get("atualizacao")

    if not (id_plano and tarefa and atualizacao):
        flash("Dados incompletos para atualizar a descrição.", "danger")
        return redirect(url_for("planos.planos_kanban"))

    try:
        with open("data/planos_acao.json", "r") as f:
            planos = json.load(f)

        plano = next((p for p in planos if p.get("id_plano") == id_plano), None)
        if not plano:
            flash("Plano não encontrado.", "danger")
            return redirect(url_for("planos.planos_kanban"))

        item = next((i for i in plano["itens"] if i.get("tarefa") == tarefa), None)
        if not item:
            flash("Item não encontrado pelo nome da tarefa.", "danger")
            return redirect(url_for("planos.planos_kanban"))

        # Atualizar a descrição existente adicionando a nova atualização
        descricao_existente = item.get("descricao", "")
        nova_descricao = descricao_existente + "\n" + atualizacao if descricao_existente else atualizacao
        item["descricao"] = nova_descricao.strip()

        with open("data/planos_acao.json", "w") as f:
            json.dump(planos, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        flash("Descrição atualizada com sucesso!", "success")

    except Exception as e:
        flash(f"Erro ao atualizar descrição: {e}", "danger")

    return redirect(url_for("planos.planos_kanban"))


@bp.route("/planos/timeline")
def planos_timeline():
    if "user" not in session:
        return redirect(url_for("login"))

    try:
        with open("data/clientes.json", "r") as f:
            clientes = json.load(f)
    except:
        clientes = []

    try:
        with open("data/planos_acao.json", "r") as f:
            planos = json.load(f)
    except:
        planos = []

    eventos = []

    for plano in planos:
        cliente_nome = plano.get("nome_cliente", "Cliente Desconhecido")
        id_operacao = plano.get("id_operacao", "")
        titulo_plano = plano.get("titulo", "Sem título")
        criado_em = plano.get("criado_em", "")

        for idx, item in enumerate(plano.get("itens", [])):
            eventos.append({
                "cliente_nome": cliente_nome,
                "id_operacao": id_operacao,
                "titulo_plano": titulo_plano,
                "tarefa": item.get("tarefa", ""),
                "responsavel": item.get("responsavel", ""),
                "prazo": item.get("prazo", ""),
                "status": item.get("status", "Pendente"),
                "resultado": item.get("resultado", ""),
                "criado_em": criado_em,
            })

    # 🔥 Organizar eventos por data (mais recentes primeiro)
    eventos.sort(key=lambda x: x.get("criado_em", ""), reverse=True)

    return render_template("planos_timeline.html", eventos=eventos, clientes=clientes)


@bp.route("/planos/<id_plano>")
def visualizar_plano(id_plano):
    if "user" not in session:
        return redirect(url_for("login"))

    try:
        with open("data/planos_acao.json", "r", encoding="utf-8") as f:
            planos = json.load(f)
        with open("data/clientes.json", "r", encoding="utf-8") as f:
            clientes = json.load(f)
    except Exception as e:
        flash(f"Erro ao carregar dados: {e}", "danger")
        return redirect(url_for("planos.listar_planos"))

    # Buscar plano pelo id
    plano = next((p for p in planos if p["id_plano"] == id_plano), None)
    if not plano:
        flash("Plano de ação não encontrado.", "danger")
        return redirect(url_for("planos.listar_planos"))

    # Buscar dados do cliente associado
    cliente = next((c for c in clientes if c["id"] == plano["cliente_id"]), {"nome": "Cliente desconhecido"})

    # Garantir que o campo comentarios exista
    if "comentarios" not in plano:
        plano["comentarios"] = []

    return render_template("plano_detalhado.html", plano=plano, cliente=cliente)


@bp.route("/planos/<id_plano>/comentarios/adicionar", methods=["POST"])
def adicionar_comentario(id_plano):
    from uuid import uuid4
    from datetime import datetime

    texto = request.form.get("comentario", "").strip()
    autor = session.get("user", "Usuário")

    if not texto:
        return redirect(f"/planos/{id_plano}")

    try:
        with open("data/planos_acao.json", "r", encoding="utf-8") as f:
            planos = json.load(f)
    except:
        return "Erro ao carregar planos", 500

    for plano in planos:
        if plano["id_plano"] == id_plano:
            if "comentarios" not in plano:
                plano["comentarios"] = []

            plano["comentarios"].insert(0, {
                "id": str(uuid4()),
                "texto": texto,
                "autor": autor,
                "data": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            break

    with open("data/planos_acao.json", "w", encoding="utf-8") as f:
        json.dump(planos, f, ensure_ascii=False, indent=4)

    return redirect(f"/planos/{id_plano}")


@bp.route("/planos/<id_plano>/comentarios/<id_comentario>/editar", methods=["POST"])
def editar_comentario_plano(id_plano, id_comentario):
    if "user" not in session:
        return redirect(url_for("login"))

    novo_texto = request.form.get("texto", "").strip()
    if not novo_texto:
        flash("Comentário não pode ser vazio.", "warning")
        return redirect(url_for("planos.visualizar_plano", id_plano=id_plano))

    try:
        with open("data/planos_acao.json", "r", encoding="utf-8") as f:
            planos = json.load(f)
    except Exception as e:
        flash(f"Erro ao carregar planos: {e}", "danger")
        return redirect(url_for("planos.visualizar_plano", id_plano=id_plano))

    for plano in planos:
        if plano["id_plano"] == id_plano:
            for comentario in plano.get("comentarios", []):
                if comentario["id"] == id_comentario and comentario["autor"] == session["user"]:
                    comentario["texto"] = novo_texto
                    comentario["editado"] = True
                    comentario["data"] = datetime.now().isoformat()
                    break

    try:
        with open("data/planos_acao.json", "w", encoding="utf-8") as f:
            json.dump(planos, f, ensure_ascii=False, indent=2)
        flash("Comentário editado com sucesso.", "success")
    except Exception as e:
        flash(f"Erro ao salvar edição: {e}", "danger")

    return redirect(url_for("planos.visualizar_plano", id_plano=id_plano))


@bp.route("/planos/<id_plano>/comentarios/<id_comentario>/remover", methods=["POST"])
def remover_comentario_plano(id_plano, id_comentario):
    if "user" not in session:
        return redirect(url_for("login"))

    try:
        with open("data/planos_acao.json", "r", encoding="utf-8") as f:
            planos = json.load(f)
    except Exception as e:
        flash(f"Erro ao carregar planos: {e}", "danger")
        return redirect(url_for("planos.visualizar_plano", id_plano=id_plano))

    for plano in planos:
        if plano["id_plano"] == id_plano:
            plano["comentarios"] = [
                c for c in plano.get("comentarios", [])
                if not (c["id"] == id_comentario and c["autor"] == session["user"])
            ]
            break

    try:
        with open("data/planos_acao.json", "w", encoding="utf-8") as f:
            json.dump(planos, f, ensure_ascii=False, indent=2)
        flash("Comentário removido.", "success")
    except Exception as e:
        flash(f"Erro ao remover comentário: {e}", "danger")

    return redirect(url_for("planos.visualizar_plano", id_plano=id_plano))


@bp.route("/planos/<id_plano>/atualizar_itens", methods=["POST"])
def atualizar_itens(id_plano):
    from uuid import uuid4

    try:
        with open("data/planos_acao.json", "r", encoding="utf-8") as f:
            planos = json.load(f)
    except:
        return "Erro ao carregar planos", 500

    plano_encontrado = False
    for plano in planos:
        if str(plano.get("id_plano")) == str(id_plano):
            itens_form = request.form.to_dict(flat=False)
            novo_checklist = []
            index = 0
            while f"itens[{index}][tarefa]" in itens_form:
                novo_checklist.append({
                    "id": itens_form.get(f"itens[{index}][id]", [str(uuid4())])[0],
                    "tarefa": itens_form[f"itens[{index}][tarefa]"][0],
                    "responsavel": itens_form[f"itens[{index}][responsavel]"][0],
                    "prazo": itens_form[f"itens[{index}][prazo]"][0],
                    "status": itens_form[f"itens[{index}][status]"][0],
                    "resultado": itens_form.get(f"itens[{index}][resultado]", [""])[0],
                })
                index += 1
            plano["itens"] = novo_checklist
            plano_encontrado = True
            break

    if not plano_encontrado:
        return "Plano não encontrado", 404

    with open("data/planos_acao.json", "w", encoding="utf-8") as f:
        json.dump(planos, f, ensure_ascii=False, indent=4)

    return redirect(f"/planos/{id_plano}")




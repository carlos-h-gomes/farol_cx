from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import json, os
from uuid import uuid4
from utils.helpers import is_admin, get_cor_farol, formatar_mmr
from datetime import datetime, timedelta, date
from io import StringIO
import csv
from flask import Response
import math


bp = Blueprint("ranking", __name__)

@bp.route("/ranking")
def ranking():
    if "user" not in session:
        return redirect(url_for("login"))

    # --- Carregar clientes
    try:
        with open("data/clientes.json", "r") as f:
            clientes = json.load(f)
    except:
        clientes = []

    # --- Filtro por estado (com múltiplos)
    estados_filtrados = request.args.getlist("estado")
    if not estados_filtrados:
        estados_filtrados = ["Contrato", "Em Risco de Churn", "Churn efetivado"]


    clientes = [
        c for c in clientes if c.get("estado", "Contrato") in estados_filtrados
    ]

    # --- Carregar comentários
    try:
        with open("data/comentarios.json", "r") as f:
            todos = json.load(f)
    except:
        todos = []

    # --- Filtro por período
    data_inicio_str = request.args.get("data_inicio")
    data_fim_str = request.args.get("data_fim")

    hoje = date.today()
    inicio_semana = hoje - timedelta(days=hoje.weekday() + 7)  # Segunda da semana anterior
    fim_semana = inicio_semana + timedelta(days=6)             # Domingo da semana anterior


    try:
        data_inicio = datetime.fromisoformat(data_inicio_str) if data_inicio_str else datetime.combine(inicio_semana, datetime.min.time())
        data_fim = datetime.fromisoformat(data_fim_str) if data_fim_str else datetime.combine(fim_semana, datetime.max.time())
    except ValueError:
        data_inicio = datetime.combine(inicio_semana, datetime.min.time())
        data_fim = datetime.combine(fim_semana, datetime.max.time())

    comentarios = [
        c for c in todos if "sentimento" in c
        and data_inicio <= datetime.fromisoformat(c["data"]) <= data_fim
    ]

    # --- Filtro por nome ou ID
    query = request.args.get("q", "").strip().lower()

    # --- Montar ranking
    ranking = []
    for cliente in clientes:
        if query:
            nome_match = query in cliente["nome"].lower()
            id_match = query in str(cliente.get("id_operacao", "")).lower()
            if not (nome_match or id_match):
                continue

        cliente_comentarios = [c for c in comentarios if c["cliente_id"] == cliente["id"]]
        if not cliente_comentarios:
            continue

        media = sum(c["sentimento"] for c in cliente_comentarios) / len(cliente_comentarios)
        estado = cliente.get("estado", "Contrato")
        mmr_raw = cliente.get("mmr", 0)

        try:
            mmr = float(str(mmr_raw).replace(",", ".").replace("R$", "").strip())
        except:
            mmr = 0

        ranking.append({
            "id": cliente["id"],
            "id_operacao": cliente.get("id_operacao", ""),
            "operacao": cliente.get("operacao", ""),
            "cliente": cliente["nome"],
            "media": round(media, 2),
            "qtd": len(cliente_comentarios),
            "cor": get_cor_farol(media),
            "estado": estado,
            "mmr_valor": mmr,
            "mrr_formatado": f"R$ {mmr:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        })

    # --- Ordenar: risco > contrato > mmr > nota
    def prioridade_rank(c):
        em_risco = 1 if c["estado"] == "Em Risco de Churn" else 0
        nota_ruim = (10 - c["media"]) * 1.2

        return (-(em_risco * 10 + nota_ruim), -c["mmr_valor"])



    ranking.sort(key=prioridade_rank)

    return render_template("ranking.html",
                           ranking=ranking,
                           now=datetime.now(),
                           timedelta=timedelta,
                           inicio_semana=inicio_semana,
                           fim_semana=fim_semana)

@bp.route("/ranking/exportar")
def exportar_ranking():
    if "user" not in session:
        return redirect(url_for("login"))

    try:
        with open("data/clientes.json", "r") as f:
            clientes = json.load(f)
        with open("data/comentarios.json", "r") as f:
            todos = json.load(f)
    except:
        return "Erro ao carregar dados", 500

    # ⏱️ Filtro por data
    data_inicio_str = request.args.get("data_inicio")
    data_fim_str = request.args.get("data_fim")

    hoje = date.today()
    inicio_semana = hoje - timedelta(days=hoje.weekday() + 7)  # Segunda da semana anterior
    fim_semana = inicio_semana + timedelta(days=6)             # Domingo da semana anterior


    try:
        data_inicio = datetime.fromisoformat(data_inicio_str) if data_inicio_str else datetime.combine(inicio_semana, datetime.min.time())
        data_fim = datetime.fromisoformat(data_fim_str) if data_fim_str else datetime.combine(fim_semana, datetime.max.time())
    except ValueError:
        data_inicio = datetime.combine(inicio_semana, datetime.min.time())
        data_fim = datetime.combine(fim_semana, datetime.max.time())

    comentarios = [
        c for c in todos if "sentimento" in c
        and data_inicio <= datetime.fromisoformat(c["data"]) <= data_fim
    ]

    # 🔍 Filtros adicionais
    query = request.args.get("q", "").strip().lower()
    estados_filtrados = request.args.getlist("estado")

    ranking = []
    for cliente in clientes:
        if estados_filtrados and cliente.get("estado") not in estados_filtrados:
            continue

        if query:
            nome_match = query in cliente["nome"].lower()
            id_match = query in str(cliente.get("id_operacao", "")).lower()
            if not (nome_match or id_match):
                continue

        cliente_comentarios = [c for c in comentarios if c["cliente_id"] == cliente["id"]]
        if not cliente_comentarios:
            continue

        media = sum(c["sentimento"] for c in cliente_comentarios) / len(cliente_comentarios)

        mmr_raw = cliente.get("mmr", 0)
        try:
            if isinstance(mmr_raw, str):
                mmr_valor = float(mmr_raw.replace("R$", "").replace(".", "").replace(",", ".").strip())
            else:
                mmr_valor = float(mmr_raw)
        except:
            mmr_valor = 0.0

        ranking.append({
            "id_operacao": cliente.get("id_operacao", ""),
            "cliente": cliente["nome"],
            "operacao": cliente.get("operacao", ""),
            "media": round(media, 2),
            "qtd": len(cliente_comentarios),
            "mmr_valor": mmr_valor,
            "mrr_formatado": f"R$ {mmr_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "estado": cliente.get("estado", "")
        })

    # Ordenar
    def ordenacao(c):
        peso_media = c["media"] * (1.5 if c["estado"] == "Em Risco de Churn" else 1.0)
        return (-peso_media, -c["mmr_valor"])


    ranking.sort(key=ordenacao)

    # 📤 Gerar CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID Cliente", "Cliente", "Operação", "Sentimento médio", "Qtd. Comentários", "MRR", "Estado"])
    for r in ranking:
        writer.writerow([
            r["id_operacao"],
            r["cliente"],
            r["operacao"],
            r["media"],
            r["qtd"],
            r["mrr_formatado"],
            r["estado"]
        ])

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=ranking.csv"
    return response

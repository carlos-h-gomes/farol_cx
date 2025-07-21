from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import json, os
from uuid import uuid4
from datetime import datetime, timedelta
from utils.helpers import is_admin, get_cor_farol, formatar_mmr
from datetime import date
from flask import Response
from io import StringIO
import csv
from collections import defaultdict
 

bp = Blueprint("historico", __name__)

@bp.route("/historico", methods=["GET"])
def historico():
    if "user" not in session:
        return redirect(url_for("login"))

    cliente_id = request.args.get("cliente")
    area = request.args.get("area")

    # Semana atual como padrão
    hoje = date.today()
    primeiro_dia = hoje.replace(day=1)
    if hoje.month == 12:
        ultimo_dia = hoje.replace(year=hoje.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        ultimo_dia = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)

    # Captura dos parâmetros
    data_inicio_str = request.args.get("data_inicio")
    data_fim_str = request.args.get("data_fim")

    try:
        data_inicio = datetime.fromisoformat(data_inicio_str) if data_inicio_str else datetime.combine(primeiro_dia, datetime.min.time())
        data_fim = datetime.fromisoformat(data_fim_str) if data_fim_str else datetime.combine(ultimo_dia, datetime.max.time())
    except ValueError:
        data_inicio = datetime.combine(primeiro_dia, datetime.min.time())
        data_fim = datetime.combine(ultimo_dia, datetime.max.time())

    try:
        with open("data/clientes.json", "r") as f:
            clientes = json.load(f)
    except:
        clientes = []

    cliente_nome = None
    dados_agrupados = {}

    try:
        with open("data/comentarios.json", "r") as f:
            comentarios = json.load(f)

            if cliente_id:
                comentarios = [
                    c for c in comentarios if c["cliente_id"] == cliente_id
                ]
                cliente = next(
                    (cl for cl in clientes if cl["id"] == cliente_id), None)
                cliente_nome = cliente["nome"] if cliente else None
            else:
                cliente_nome = "Todos os clientes"

            if area:
                comentarios = [c for c in comentarios if c.get("flag") == area]

            comentarios = [
                c for c in comentarios if "sentimento" in c and
                data_inicio <= datetime.fromisoformat(c["data"]) <= data_fim
            ]

            # Agrupar por semana
            semanas = defaultdict(list)
            for c in comentarios:
                dt = datetime.fromisoformat(c["data"])
                inicio_semana = dt - timedelta(days=dt.weekday())
                semana = inicio_semana.strftime("%Y-%m-%d")  # ✅ formato ISO
                # ou "%d/%m/%Y" se quiser com ano
                semanas[semana].append(c["sentimento"])

            dados_agrupados = {
                semana: round(sum(valores) / len(valores), 2)
                for semana, valores in sorted(semanas.items())
            }

    except Exception as e:
        flash(f"Erro ao processar histórico: {e}", "danger")

    return render_template("historico.html",
           clientes=clientes,
           dados=dados_agrupados,
           cliente_nome=cliente_nome,
           cliente_id=cliente_id,
           area=area,
           now=datetime.now(),
           timedelta=timedelta,
           inicio_mes=primeiro_dia,
           fim_mes=ultimo_dia)


@bp.route("/historico/exportar")
def exportar_historico():
    if "user" not in session:
        return redirect(url_for("login"))

    cliente_id = request.args.get("cliente")
    area = request.args.get("area")
    data_inicio_str = request.args.get("data_inicio")
    data_fim_str = request.args.get("data_fim")

    try:
        with open("data/clientes.json", "r") as f:
            clientes = json.load(f)

        with open("data/comentarios.json", "r") as f:
            comentarios = json.load(f)

        if cliente_id:
            comentarios = [
                c for c in comentarios if c["cliente_id"] == cliente_id
            ]
            cliente = next((c for c in clientes if c["id"] == cliente_id),
                           None)
            cliente_nome = cliente["nome"] if cliente else "cliente"
        else:
            cliente_nome = "todos_clientes"

        if area:
            comentarios = [c for c in comentarios if c.get("flag") == area]

        try:
            data_inicio = datetime.fromisoformat(
                data_inicio_str) if data_inicio_str else None
            data_fim = datetime.fromisoformat(
                data_fim_str) if data_fim_str else None
        except ValueError:
            data_inicio = None
            data_fim = None

        if data_inicio:
            comentarios = [
                c for c in comentarios
                if datetime.fromisoformat(c["data"]) >= data_inicio
            ]
        if data_fim:
            comentarios = [
                c for c in comentarios
                if datetime.fromisoformat(c["data"]) <= data_fim
            ]

        # Agrupar por semana
        semanas = defaultdict(list)
        for c in comentarios:
            if "sentimento" in c:
                dt = datetime.fromisoformat(c["data"])
                inicio_semana = dt - timedelta(days=dt.weekday())
                semana = inicio_semana.strftime("%Y-%m-%d")  # 🟢 Correto
                semanas[semana].append(c["sentimento"])

        dados_agrupados = {
            semana: round(sum(valores) / len(valores), 2)
            for semana, valores in sorted(semanas.items())
        }

        # Gerar CSV
        # Gerar CSV com informações de contexto
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(["Cliente:", cliente_nome])
        writer.writerow(["Área:", area or "Todas"])
        writer.writerow([])  # linha em branco

        writer.writerow(["Semana", "Sentimento médio"])

        for semana, media in dados_agrupados.items():
            writer.writerow([semana, media])

        response = Response(output.getvalue(), mimetype="text/csv")
        response.headers[
            "Content-Disposition"] = f"attachment; filename={cliente_nome}_historico.csv"
        return response

    except Exception as e:
        print("Erro ao exportar histórico:", e)
        flash(f"Erro ao exportar: {e}", "danger")
        return redirect(url_for("historico.historico"))


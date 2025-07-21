
from flask import Blueprint, jsonify
import json
from datetime import datetime, timedelta
import requests

bp = Blueprint("lembrete", __name__)

WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAAAxnGsh3s/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=r1jUCt6C1QUl_WO-jvY06xPMFRLhqfzPRPlYnCCakOo"

# Mapeamento de emoji por área
EMOJIS = {
    "curador": "🤖",
    "gp": "📊",
    "cs": "🧑‍💼"
}

def obter_comentarios_semana():
    hoje = datetime.utcnow() - timedelta(hours=3)
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)

    try:
        with open("data/comentarios.json", "r") as f:
            comentarios = json.load(f)
    except:
        return []

    return [
        c for c in comentarios
        if "flag" in c and "data" in c
        and inicio_semana <= datetime.fromisoformat(c["data"]) <= fim_semana
    ]

def verificar_comentarios_pendentes():
    try:
        with open("data/clientes.json", "r") as f:
            clientes = json.load(f)
    except:
        clientes = []

    comentarios = obter_comentarios_semana()
    pendencias = {}

    for cliente in clientes:
        for area in ["analista", "gp", "cs"]:
            pessoa = cliente.get("responsaveis", {}).get(area, {})
            email = pessoa.get("email")
            nome = pessoa.get("nome", email)
            nome_cliente = cliente.get("nome", "Cliente")

            if not email:
                continue

            houve = any(
                c["cliente_id"] == cliente["id"] and c.get("flag", "").lower() == area
                for c in comentarios
            )

            if not houve:
                pendencias.setdefault(nome, {
                    "emoji": EMOJIS.get(area, ""),
                    "clientes": []
                })["clientes"].append(nome_cliente)

    return pendencias

def enviar_mensagem_chat(pendencias):
    if not pendencias:
        return "Sem pendências encontradas."

    linhas = ["📢 Lembrete de preenchimento semanal do Farol\n"]
    for email, dados in pendencias.items():
        emoji = dados["emoji"]
        clientes = ", ".join(dados["clientes"])
        linhas.append(f"{emoji} @{email}\nClientes pendentes: {clientes}\n")

    mensagem = "\n".join(linhas)

    try:
        response = requests.post(WEBHOOK_URL, json={"text": mensagem})
        if response.status_code == 200:
            return "Lembrete enviado com sucesso!"
        else:
            return f"Erro ao enviar lembrete: {response.status_code}"
    except Exception as e:
        return f"Erro ao enviar lembrete: {e}"

@bp.route("/lembrete/testar")
def lembrete_teste():
    pendencias = verificar_comentarios_pendentes()
    resultado = enviar_mensagem_chat(pendencias)
    return jsonify({"resultado": resultado, "pendencias": pendencias})

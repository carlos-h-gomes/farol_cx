import os
import json
from datetime import datetime, timedelta
from collections import defaultdict
import requests

CAMINHO_CLIENTES = "data/clientes.json"
CAMINHO_COMENTARIOS = "data/comentarios.json"
WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/#########"

def carregar_dados():
    with open(CAMINHO_CLIENTES, "r") as f:
        clientes = json.load(f)
    with open(CAMINHO_COMENTARIOS, "r") as f:
        comentarios = json.load(f)
    return clientes, comentarios

def identificar_pendencias():
    hoje = datetime.now()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)

    clientes, comentarios = carregar_dados()
    pendencias = defaultdict(list)

    for cliente in clientes:
        cliente_id = cliente["id"]
        nome = cliente["nome"]
        autores = {
            c["autor"] for c in comentarios
            if c["cliente_id"] == cliente_id
            and "data" in c
            and inicio_semana <= datetime.fromisoformat(c["data"]) <= fim_semana
        }

        for area, email in cliente.get("responsaveis", {}).items():
            if email and email not in autores:
                pendencias[email].append(nome)

    return pendencias

def montar_mensagem(pendencias: dict):
    if not pendencias:
        return "✅ Todos os responsáveis registraram comentários esta semana!"

    # Mapeamento email → área → emoji
    responsavel_emoji = {}

    try:
        with open("data/clientes.json", "r") as f:
            clientes = json.load(f)

        for cliente in clientes:
            for area, email in cliente.get("responsaveis", {}).items():
                if email:
                    if area == "cs":
                        responsavel_emoji[email] = "🧑‍💼"
                    elif area == "gp":
                        responsavel_emoji[email] = "📊"
                    elif area == "analista":
                        responsavel_emoji[email] = "🤖"
    except:
        pass

    linhas = ["📢 *Lembrete de preenchimento semanal do Farol*\n"]

    for responsavel, clientes in pendencias.items():
        emoji = responsavel_emoji.get(responsavel, "🔔")
        nomes = ", ".join(clientes)
        linhas.append(f"{emoji} *@{responsavel}*\nClientes pendentes: *{nomes}*\n")

    return "\n".join(linhas)


def enviar_mensagem(texto):
    if not WEBHOOK_URL:
        print("[Erro] Variável de ambiente GOOGLE_CHAT_WEBHOOK_URL não definida.")
        return

    payload = {"text": texto}
    response = requests.post(WEBHOOK_URL, json=payload)

    if response.status_code == 200:
        print("[OK] Mensagem enviada com sucesso.")
    else:
        print(f"[Erro] Código {response.status_code}: {response.text}")

def rodar_lembrete():
    pendencias = identificar_pendencias()
    texto = montar_mensagem(pendencias)
    enviar_mensagem(texto)

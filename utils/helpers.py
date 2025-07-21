import os, json
from flask import session

ADMINS_FILE = "data/admins.json"

def is_admin():
    return session.get("user") in load_admins()

def load_admins():
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, "r") as f:
            return json.load(f)
    return ["carlos.gomes@hiplatform.com"]

def save_admins(admins):
    os.makedirs(os.path.dirname(ADMINS_FILE), exist_ok=True)
    with open(ADMINS_FILE, "w") as f:
        json.dump(admins, f, indent=2)

def formatar_mmr(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def get_cor_farol(media):
    if media >= 4.5:
        return "green"
    elif media >= 3.5:
        return "lime"
    elif media >= 2.5:
        return "yellow"
    elif media >= 1.5:
        return "orange"
    else:
        return "red"

def formatar_cliente_para_salvar(form):
    def parse_mmr(valor):
        if not valor:
            return 0.0
        valor = str(valor).strip().replace("R$", "").replace(".", "").replace(",", ".")
        try:
            return round(float(valor), 2)
        except:
            return 0.0

    return {
        "nome": form.get("nome", "").strip(),
        "responsaveis": {
            "cs": {
                "nome": form.get("cs_nome", "").strip(),
                "email": form.get("cs_email", "").strip()
            },
            "gp": {
                "nome": form.get("gp_nome", "").strip(),
                "email": form.get("gp_email", "").strip()
            },
            "analista": {
                "nome": form.get("analista_nome", "").strip(),
                "email": form.get("analista_email", "").strip()
            }
        },
        "estado": form.get("estado", "").strip(),
        "mmr": parse_mmr(form.get("mmr", "0")),
        "inicio_contrato": form.get("inicio_contrato", "").strip(),
        "fim_contrato": form.get("fim_contrato", "").strip(),
        "data_churn": form.get("data_churn", "").strip(),
        "motivo_churn": form.get("motivo_churn", "").strip(),
        "id_operacao": form.get("id_operacao", "").strip(),
        "operacao": form.get("operacao", "").strip(),
        "escopo": form.get("escopo", "").strip()
    }


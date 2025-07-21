import json
from datetime import datetime
from pathlib import Path

CAMINHO_TIMESTAMP = Path("data/timestamp.json")

def atualizar_timestamp():
    agora = datetime.now().isoformat()
    try:
        CAMINHO_TIMESTAMP.parent.mkdir(parents=True, exist_ok=True)
        with CAMINHO_TIMESTAMP.open("w", encoding="utf-8") as f:
            json.dump({"ultimo_backup": agora}, f, indent=2, ensure_ascii=False)
        return agora
    except Exception as e:
        print(f"[!] Erro ao atualizar timestamp: {e}")
        return None

def obter_timestamp_local():
    try:
        if not CAMINHO_TIMESTAMP.exists():
            return None
        with CAMINHO_TIMESTAMP.open("r", encoding="utf-8") as f:
            return json.load(f).get("ultimo_backup")
    except Exception as e:
        print(f"[!] Erro ao obter timestamp local: {e}")
        return None

import os
import json
import shutil
import subprocess
from utils.timestamp import obter_timestamp_local

ARQUIVOS_JSON = [
    "data/clientes.json",
    "data/comentarios.json",
    "data/planos_acao.json"
]

GIT_CLONE_DIR = "/home/runner/repo_backup"

def arquivos_estao_vazios_ou_ausentes():
    for caminho in ARQUIVOS_JSON:
        if not os.path.exists(caminho):
            print(f"[!] Arquivo ausente: {caminho}")
            return True
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if not dados:
                print(f"[!] Arquivo vazio: {caminho}")
                return True
        except Exception as e:
            print(f"[!] Erro ao ler {caminho}: {e}")
            return True
    return False

def inicializar_git_local():
    try:
        print("📦 Inicializando repositório Git local...")
        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "checkout", "-b", "main"], check=True)

        user = os.getenv("GH_USER")
        repo = os.getenv("GH_REPO")
        token = os.getenv("GH_TOKEN")
        remote_url = f"https://{user}:{token}@github.com/{user}/{repo}.git"

        subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
        subprocess.run(["git", "fetch", "origin"], check=True)
        print("✅ Git inicializado com sucesso.")
    except subprocess.CalledProcessError as e:
        print(f"[!] Erro ao inicializar Git: {e}")

def obter_timestamp_remoto():
    try:
        if not os.path.exists(".git"):
            print("[!] .git não encontrado — pulando fetch remoto.")
            return None

        subprocess.run(["git", "fetch", "origin"], check=True, capture_output=True, text=True)
        resultado = subprocess.run(
            ["git", "show", "origin/main:data/timestamp.json"],
            capture_output=True,
            text=True,
            check=True
        )
        remoto = json.loads(resultado.stdout)
        return remoto.get("ultimo_backup")
    except Exception as e:
        print(f"[!] Erro ao obter timestamp remoto: {e}")
        return None

def restaurar_arquivos_git():
    try:
        if not os.path.exists(".git"):
            print("📦 Clonando repositório Git para restaurar dados...")
            user = os.getenv("GH_USER")
            repo = os.getenv("GH_REPO")
            token = os.getenv("GH_TOKEN")
            remote_url = f"https://{user}:{token}@github.com/{user}/{repo}.git"
            subprocess.run(["git", "clone", remote_url, GIT_CLONE_DIR], check=True)

            origem = os.path.join(GIT_CLONE_DIR, "data")
            destino = "data"
            if os.path.exists(origem):
                if os.path.exists(destino):
                    shutil.rmtree(destino)
                shutil.copytree(origem, destino)
                print("✅ Dados restaurados a partir do repositório clonado.")

                # Inicializa o Git localmente para permitir commits futuros
                inicializar_git_local()
            else:
                print("[!] Repositório clonado não contém a pasta 'data'.")

        else:
            print("📂 Restaurando arquivos via git restore")
            subprocess.run(["git", "fetch"], check=True)
            subprocess.run(["git", "restore", "--source", "origin/main", "data/"], check=True)
            print("[✓] Arquivos restaurados do GitHub.")

    except subprocess.CalledProcessError as e:
        print(f"[!] Falha ao restaurar arquivos do GitHub: {e}")

def verificar_e_restaurar_arquivos():
    print("[debug] Diretório atual:", os.getcwd())
    print("[debug] Existe .git?", os.path.exists(".git"))

    # ⚠️ Se .git não existe, restauração obrigatória
    if not os.path.exists(".git"):
        print("⚠️ .git ausente. Iniciando restauração completa a partir do clone...")
        restaurar_arquivos_git()
        return  # Impede checagem duplicada

    # Caso contrário, verifica conteúdo e timestamps
    local = obter_timestamp_local()
    remoto = obter_timestamp_remoto()

    if arquivos_estao_vazios_ou_ausentes():
        print("⚠️ Arquivos ausentes ou incompletos. Iniciando restauração automática...")
        restaurar_arquivos_git()
    elif local and remoto and remoto > local:
        print("⚠️ Detecção de arquivos desatualizados. Restauração automática ativada...")
        restaurar_arquivos_git()
    else:
        print("✅ Arquivos locais atualizados.")


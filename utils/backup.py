import os
import subprocess
from datetime import datetime
from utils.timestamp import atualizar_timestamp
from utils.email_sender import send_plain_email

def executar_backup_github():
    print("→ Iniciando verificação de backup GitHub")

    if not os.path.exists(".git"):
        print("[!] Git não está inicializado. Inicializando repositório local...")
        try:
            subprocess.run(["git", "init"], check=True)
            user = os.getenv("GH_USER")
            repo = os.getenv("GH_REPO")
            token = os.getenv("GH_TOKEN")
            remote_url = f"https://{user}:{token}@github.com/{user}/{repo}.git"

            subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
            subprocess.run(["git", "checkout", "-b", "main"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"[!] Falha ao inicializar repositório: {e}")
            return

    try:
        print("→ Configurando identidade Git local")
        subprocess.run(["git", "config", "user.name", "suporte-hi"], check=True)
        subprocess.run(["git", "config", "user.email", "suporte@hiplatform.com"], check=True)

        print("→ Atualizando timestamp")
        atualizar_timestamp()

        print("→ Adicionando arquivos específicos ao commit")
        arquivos_para_adicionar = [
            "data/clientes.json",
            "data/comentarios.json",
            "data/planos_acao.json",
            "data/timestamp.json",
            "data/admins.json",
            "data/comunicacoes.json"
        ]
        subprocess.run(["git", "add"] + arquivos_para_adicionar, check=True)

        print("→ Verificando status Git antes do commit")
        subprocess.run(["git", "status"], check=True)


        print("→ Realizando commit")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        subprocess.run(["git", "commit", "--allow-empty", "-m", f"Backup automático em {timestamp}"], check=True)

        print("→ Garantindo que 'origin' está configurado corretamente")
        token = os.getenv("GH_TOKEN")
        user = os.getenv("GH_USER")
        repo = os.getenv("GH_REPO")
        remote_url = f"https://{user}:{token}@github.com/{user}/{repo}.git"

        print("→ Realizando git push")
        result = subprocess.run(["git", "push", remote_url, "main"], capture_output=True, text=True)
        print(f"[✓] Push concluído com sucesso:\n{result.stdout}\n{result.stderr}")

    except subprocess.CalledProcessError as e:
        erro_detalhado = (
            f"❌ Erro no backup GitHub:\n"
            f"Comando: {e.cmd}\n"
            f"Retorno: {e.returncode}\n"
            f"STDOUT:\n{e.stdout}\n"
            f"STDERR:\n{e.stderr}"
        )
        print(erro_detalhado)
        _enviar_erro_por_email("erro geral", erro_detalhado)

def _enviar_erro_por_email(fase, conteudo):
    try:
        send_plain_email(
            to_email="destino_email",
            subject=f"🚨 Erro no Backup Automático da Plataforma Farol ({fase})",
            content=conteudo
        )
        print("[✓] Notificação de erro enviada por e-mail.")
    except Exception as email_error:
        print(f"[!] Falha ao enviar e-mail: {email_error}")

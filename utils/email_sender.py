import smtplib
from email.message import EmailMessage
import os
import zipfile
from datetime import datetime

def send_token_email(to_email, token):
    from_email = os.environ.get("SMTP_EMAIL")
    password = os.environ.get("SMTP_PASSWORD")

    if not from_email or not password:
        print("Variáveis de ambiente não definidas!")
        return

    msg = EmailMessage()
    msg["Subject"] = "Seu código de login - Plataforma Farol"
    msg["From"] = from_email
    msg["To"] = to_email

    # Texto plano como fallback
    msg.set_content(f"Seu código de verificação é: {token}")

    # HTML com layout bonito
    html_content = f"""
    <html>
      <body>
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ccc;
                    border-radius: 5px; background-color: #f9f9f9; font-family: Arial, sans-serif;">
          <img src="https://files.directtalk.com.br/1.0/api/file/public/98318821-47c9-4d53-a6fd-4aefe26c4cf5/content-inline"
               alt="Logo Hi Platform" width="200" style="display: block; margin: 0 auto; margin-bottom: 20px;">
          <p style="margin-bottom: 10px;">Caro usuário,</p>
          <p style="margin-bottom: 10px;">Você acabou de receber um código PIN de acesso.</p>
          <p style="margin-bottom: 10px;">
            O código PIN aleatório é:
            <strong style="color: #0056b3; display: inline-block; padding: 5px 10px;
                           border-radius: 5px; background-color: #0056b3; color: #fff;">
              {token}
            </strong>
          </p>
          <p style="margin-bottom: 10px;">Para confirmar seu login, por favor, digite o código PIN recebido na plataforma Hi.</p>
          <p>Atenciosamente,</p>
          <p style="margin-top: 20px; color: #666;">Equipe Hi Platform</p>
        </div>
      </body>
    </html>
    """

    msg.add_alternative(html_content, subtype="html")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(from_email, password)
            smtp.send_message(msg)
        print(f"Token enviado para {to_email}")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")


def send_plain_email(to_email, subject, content):
    from_email = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_PASSWORD")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content(content)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(from_email, password)
            smtp.send_message(msg)
        print(f"E-mail enviado para {to_email}")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")


def send_html_email(to_email, subject, plano):
    from_email = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_PASSWORD")

    if not from_email or not password:
        print("[ERRO] Variáveis SMTP_EMAIL ou SMTP_PASSWORD não definidas.")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    # Versão texto plano como fallback
    msg.set_content("Você recebeu um novo plano de ação. Acesse o sistema da Plataforma Farol para mais detalhes.")

    # HTML formatado
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: auto; border: 1px solid #eee; padding: 20px; border-radius: 8px;">
          <img src="https://files.directtalk.com.br/1.0/api/file/public/98318821-47c9-4d53-a6fd-4aefe26c4cf5/content-inline"
               alt="Logo" style="max-width: 150px; margin-bottom: 20px;">
          <h2 style="color: #0d47a1;">Novo Plano de Ação: {plano['titulo']}</h2>
          <p><strong>Cliente:</strong> {plano['nome_cliente']}</p>
          <p><strong>Descrição:</strong><br>{plano['descricao']}</p>
          <h3 style="margin-top: 20px;">Checklist</h3>
          <ul>
    """
    for item in plano["itens"]:
        html_content += f"<li><strong>{item['tarefa']}</strong> — {item['responsavel']} (Prazo: {item['prazo']})</li>"

    html_content += """
          </ul>
          <p style="margin-top: 30px;">Acesse a Plataforma Farol para acompanhar o andamento.</p>
          <p style="color: #999; font-size: 12px;">-- Plataforma Farol</p>
        </div>
      </body>
    </html>
    """

    msg.add_alternative(html_content, subtype="html")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(from_email, password)
            smtp.send_message(msg)
        print(f"E-mail HTML enviado para {to_email}")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")

def send_backup_zip(to_email="suporte@hiplatform.com"):
    from_email = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_PASSWORD")

    # Nome do arquivo zip
    data_formatada = datetime.now().strftime("%Y-%m-%d_%Hh%M")
    nome_zip = f"backup_farol_{data_formatada}.zip"
    caminho_zip = os.path.join("/tmp", nome_zip)

    # Criar o arquivo zip com todos os .json da pasta data
    with zipfile.ZipFile(caminho_zip, "w") as zipf:
        for nome_arquivo in os.listdir("data"):
            if nome_arquivo.endswith(".json"):
                caminho = os.path.join("data", nome_arquivo)
                zipf.write(caminho, arcname=nome_arquivo)

    # Montar e-mail
    msg = EmailMessage()
    msg["Subject"] = f"Backup Automático - Plataforma Farol ({data_formatada})"
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content("Segue em anexo o backup automático da Plataforma Farol.")

    with open(caminho_zip, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="zip", filename=nome_zip)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(from_email, password)
            smtp.send_message(msg)
        print(f"[✓] Backup zip enviado para {to_email}")
    except Exception as e:
        print(f"[!] Erro ao enviar zip por e-mail: {e}")
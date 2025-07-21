from apscheduler.schedulers.background import BackgroundScheduler
from routes.lembrete import verificar_comentarios_pendentes, enviar_mensagem_chat
from utils.backup import executar_backup_github
from utils.email_sender import send_backup_zip
import pytz
import json

# Criar instância global do scheduler
scheduler = BackgroundScheduler(timezone=pytz.timezone("America/Sao_Paulo"))

def iniciar_agendador():
    try:
        with open("data/comunicacoes.json", "r") as f:
            config = json.load(f)
    except:
        config = {}

    # Lembrete semanal (configurável)
    if config.get("envio_lembretes_chat"):
        scheduler.add_job(
            func=lambda: enviar_mensagem_chat(verificar_comentarios_pendentes()),
            trigger='cron',
            day_of_week=config.get("dia_lembrete", "fri"),
            hour=config.get("hora_lembrete", 10),
            minute=config.get("minuto_lembrete", 0),
            id='lembrete_semanal',
            replace_existing=True
        )

    # Backup automático (sempre)
    if config.get("backup_ativo"):
        scheduler.add_job(
            func=executar_backup_github,
            trigger='interval',
            hours=1,
            id='backup_github',
            replace_existing=True
        )


    scheduler.add_job(
        func=send_backup_zip,
        trigger='cron',
        hour=22,
        minute=0,
        id='email_backup_diario',
        replace_existing=True
    )

    for job in scheduler.get_jobs():
        print(f" - {job.id} ({job.trigger})")

    scheduler.start()
    print(f"[AGENDADOR] Lembrete semanal ativado: {config.get('dia_lembrete')} às {config.get('hora_lembrete'):02d}:{config.get('minuto_lembrete'):02d} (UTC-3)")


# ⚠️ Aqui fora da função iniciar_agendador
def reconfigurar_lembrete():
    try:
        with open("data/comunicacoes.json", "r") as f:
            config = json.load(f)
    except:
        config = {}

    scheduler.remove_all_jobs()

    if config.get("envio_lembretes_chat"):
        scheduler.add_job(
            func=lambda: enviar_mensagem_chat(verificar_comentarios_pendentes()),
            trigger='cron',
            day_of_week=config.get("dia_lembrete", "fri"),
            hour=config.get("hora_lembrete", 10),
            minute=config.get("minuto_lembrete", 0),
            id='lembrete_semanal',
            replace_existing=True
        )

    for job in scheduler.get_jobs():
        print(f" - {job.id} ({job.trigger})")

    print(f"[AGENDADOR] Reconfigurado para: {config.get('dia_lembrete')} às {config.get('hora_lembrete'):02d}:{config.get('minuto_lembrete'):02d} (UTC-3)")

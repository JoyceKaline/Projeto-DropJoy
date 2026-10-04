import smtplib
from email.message import EmailMessage
from ..core.config import get_settings

settings = get_settings()

def send_password_reset(to_email: str, token: str) -> bool:
    if not settings.smtp_configured:
        return False
    msg = EmailMessage()
    msg["Subject"] = "Recuperação de senha - DropJoy"
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email
    link = settings.password_reset_base_url + token
    msg.set_content(f"Recebemos uma solicitação para redefinir sua senha do DropJoy.\n\nAcesse: {link}\n\nSe você não solicitou, ignore esta mensagem.")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password or "")
        server.send_message(msg)
    return True

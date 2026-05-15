import smtplib
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

log = logging.getLogger(__name__)

BREVO_SMTP  = "smtp-relay.brevo.com"
BREVO_PORT  = 587
BREVO_LOGIN = os.environ.get("BREVO_LOGIN", "ab72ea001@smtp-brevo.com")
BREVO_KEY   = os.environ.get("BREVO_KEY", "")

REMITENTE_EMAIL  = os.environ.get("REMITENTE_EMAIL", "tamara.prieto@ata.es")
REMITENTE_NOMBRE = os.environ.get("REMITENTE_NOMBRE", "Oficina Acelera Pyme – A Coruña")

def enviar_correo(destinatario_email, destinatario_nombre, asunto, cuerpo):
    if not BREVO_KEY:
        return False, "BREVO_KEY no configurada en las variables de entorno"
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = asunto
        msg['From'] = f"{REMITENTE_NOMBRE} <{REMITENTE_EMAIL}>"
        msg['To'] = f"{destinatario_nombre} <{destinatario_email}>" if destinatario_nombre else destinatario_email
        msg['Reply-To'] = REMITENTE_EMAIL

        parte_texto = MIMEText(cuerpo, 'plain', 'utf-8')
        cuerpo_html = cuerpo.replace('\n', '<br>')
        cuerpo_html = f"""<html><body style="font-family:Arial,sans-serif;font-size:14px;color:#333;line-height:1.6;max-width:600px;margin:0 auto;padding:20px;">
        <div style="border-bottom:2px solid #1B3A6B;padding-bottom:12px;margin-bottom:20px;">
            <span style="color:#1B3A6B;font-weight:bold;font-size:13px;">OFICINA ACELERA PYME · A CORUÑA</span>
        </div>
        {cuerpo_html}
        <div style="border-top:1px solid #e0e0e0;margin-top:24px;padding-top:12px;font-size:12px;color:#888;">
            Servicio público gratuito · Red.es · Ministerio de Transformación Digital
        </div>
        </body></html>"""
        parte_html = MIMEText(cuerpo_html, 'html', 'utf-8')
        msg.attach(parte_texto)
        msg.attach(parte_html)

        with smtplib.SMTP(BREVO_SMTP, BREVO_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(BREVO_LOGIN, BREVO_KEY)
            server.sendmail(REMITENTE_EMAIL, destinatario_email, msg.as_string())

        log.info(f"✓ Correo enviado a {destinatario_email}")
        return True, None
    except Exception as e:
        log.error(f"✗ Error enviando a {destinatario_email}: {e}")
        return False, str(e)

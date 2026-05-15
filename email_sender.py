import logging
import os
import requests

log = logging.getLogger(__name__)

BREVO_API_KEY    = os.environ.get("BREVO_KEY", "")
REMITENTE_EMAIL  = os.environ.get("REMITENTE_EMAIL", "tamara.prieto@ata.es")
REMITENTE_NOMBRE = os.environ.get("REMITENTE_NOMBRE", "Oficina Acelera Pyme – A Coruña")
BREVO_API_URL    = "https://api.brevo.com/v3/smtp/email"

def enviar_correo(destinatario_email, destinatario_nombre, asunto, cuerpo):
    if not BREVO_API_KEY:
        return False, "BREVO_KEY no configurada"

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

    payload = {
        "sender": {"name": REMITENTE_NOMBRE, "email": REMITENTE_EMAIL},
        "to": [{"email": destinatario_email, "name": destinatario_nombre or destinatario_email}],
        "subject": asunto,
        "htmlContent": cuerpo_html,
        "textContent": cuerpo,
        "replyTo": {"email": REMITENTE_EMAIL, "name": REMITENTE_NOMBRE}
    }

    try:
        r = requests.post(
            BREVO_API_URL,
            json=payload,
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": BREVO_API_KEY
            },
            timeout=30
        )
        if r.status_code in (200, 201):
            log.info(f"✓ Correo enviado a {destinatario_email}")
            return True, None
        else:
            error = r.json().get('message', r.text)
            log.error(f"✗ Brevo error {r.status_code}: {error}")
            return False, error
    except Exception as e:
        log.error(f"✗ Error: {e}")
        return False, str(e)

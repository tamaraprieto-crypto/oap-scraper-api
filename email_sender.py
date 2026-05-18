import logging
import os
import requests

log = logging.getLogger(__name__)

BREVO_API_KEY    = os.environ.get("BREVO_KEY", "")
REMITENTE_EMAIL  = os.environ.get("REMITENTE_EMAIL", "tamara.prieto@ata.es")
REMITENTE_NOMBRE = os.environ.get("REMITENTE_NOMBRE", "Oficina Acelera Pyme – A Coruna")
BREVO_API_URL    = "https://api.brevo.com/v3/smtp/email"

HEADER_URL = "https://gestor-empresas-oap-acoruna.netlify.app/header%20correo.png"
FOOTER_URL = "https://gestor-empresas-oap-acoruna.netlify.app/footer%20correo.png"
LOGO_FIRMA = "data:image/png;base64,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"

AVISO_LEGAL = """<p style="font-size:10px;color:#888888;line-height:1.6;margin:0">
  <strong>Aviso legal</strong><br>
  Segun la normativa vigente en proteccion de datos le informamos que su direccion de correo electronico
  junto con la informacion que nos facilite son tratados por FEDERACION NACIONAL DE ASOCIACIONES DE
  TRABAJADORES AUTONOMOS ATA como responsable del tratamiento con la finalidad de gestionar y mantener
  los contactos que se produzcan como consecuencia de la relacion que mantiene con nosotros.
  La base juridica que legitima este tratamiento sera su consentimiento, el interes legitimo o la
  necesidad para gestionar una relacion contractual o similar.<br><br>
  Si no desea seguir recibiendo comunicaciones o desea ejercitar sus derechos de acceso, rectificacion,
  cancelacion/supresion, oposicion, limitacion o portabilidad puede hacerlo a traves de correo electronico
  a <a href="mailto:rgpd@ata.es" style="color:#1B3A6B">rgpd@ata.es</a> indicando en el asunto
  "Proteccion de Datos" o por escrito a: FEDERACION NACIONAL DE ASOCIACIONES DE TRABAJADORES AUTONOMOS ATA
  Poligono El Granadal. Avenida Azabache s/n, esq. C/. Agata. 14014 Cordoba.
  En caso de considerar vulnerado su derecho podra interponer una reclamacion ante la
  <a href="https://www.agpd.es" style="color:#1B3A6B">Agencia Espanola de Proteccion de Datos</a>.<br><br>
  La informacion contenida en este email es privilegiada para uso exclusivo del destinatario.
  Si ha recibido este mensaje por error informenos en el telefono: <strong>900 101 816</strong>
  o reenvie a <a href="mailto:ata@ata.es" style="color:#1B3A6B">ata@ata.es</a><br><br>
  Si no desea recibir mas comunicaciones envienos un correo a
  <a href="mailto:oapcoruna@ata.es" style="color:#1B3A6B">oapcoruna@ata.es</a>.
</p>"""

def construir_firma_html(firma_datos):
    if not firma_datos:
        return ""
    nombre  = firma_datos.get("nombre", "")
    cargo   = firma_datos.get("cargo", "")
    oficina = firma_datos.get("oficina", "")
    tel     = firma_datos.get("tel", "")
    email   = firma_datos.get("email", "")
    web     = firma_datos.get("web", "")

    extra = ""
    if email:
        extra += f'<p style="margin:2px 0 0;font-size:11px"><a href="mailto:{email}" style="color:#1B3A6B">{email}</a></p>'
    if web:
        dominio = web.replace("https://","").replace("http://","")
        extra += f'<p style="margin:2px 0 0;font-size:11px"><a href="https://{dominio}" style="color:#1B3A6B">{dominio}</a></p>'

    return f"""
    <table cellpadding="0" cellspacing="0" style="font-family:Arial,sans-serif;width:100%;margin-top:10px">
    <tr>
      <td style="vertical-align:top;padding-right:20px;width:150px">
        <img src="{LOGO_FIRMA}" alt="Oficina Acelera Pyme ATA" style="width:130px;height:auto;display:block;margin-bottom:8px">
        <p style="margin:4px 0 0;font-size:11px;color:#2d5f2d;font-weight:bold">900 101 816</p>
        <p style="margin:2px 0 0;font-size:11px"><a href="https://www.ata.es" style="color:#1B3A6B;text-decoration:none">www.ata.es</a></p>
      </td>
      <td style="vertical-align:top;border-left:1px solid #e0e0e0;padding-left:20px">
        <p style="margin:0 0 2px;font-size:13px;font-weight:bold;color:#1B3A6B">{nombre}</p>
        <p style="margin:0 0 6px;font-size:11px;color:#666">{cargo}</p>
        {f'<p style="margin:0 0 4px;font-size:12px;font-weight:bold;color:#333">{tel}</p>' if tel else ""}
        <p style="margin:0 0 2px;font-size:11px;color:#555">{oficina}</p>
        <p style="margin:0 0 4px;font-size:11px;color:#555">Federacion Nacional de Asociaciones<br>de Trabajadores Autonomos</p>
        {extra}
      </td>
    </tr>
    </table>
    """

def construir_html(cuerpo_texto, firma_datos=None):
    """Orden: Header → Cuerpo → Footer → Firma → Aviso legal."""
    cuerpo_html = cuerpo_texto.replace("\n", "<br>")
    firma_html  = construir_firma_html(firma_datos)

    return f"""<html>
<body style="margin:0;padding:0;background:#f5f4f0;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f4f0;padding:20px 0">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)">

  <!-- 1. HEADER -->
  <tr><td style="padding:0">
    <img src="{HEADER_URL}" alt="Oficina Acelera Pyme ATA" width="600" style="width:100%;display:block;border:0">
  </td></tr>

  <!-- 2. CUERPO -->
  <tr><td style="padding:32px 40px;color:#333333;font-size:14px;line-height:1.7">
    {cuerpo_html}
  </td></tr>

  <!-- 3. FOOTER -->
  <tr><td style="padding:0">
    <img src="{FOOTER_URL}" alt="Ministerio Fondos Europeos Red.es" width="600" style="width:100%;display:block;border:0">
  </td></tr>

  <!-- 4. FIRMA -->
  <tr><td style="padding:20px 40px;background:#ffffff;border-top:2px solid #1B3A6B">
    {firma_html}
  </td></tr>

  <!-- 5. AVISO LEGAL -->
  <tr><td style="padding:20px 40px;background:#f8f7f4;border-top:1px solid #e4e2d9">
    {AVISO_LEGAL}
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

def enviar_correo(destinatario_email, destinatario_nombre, asunto, cuerpo, firma_html=""):
    if not BREVO_API_KEY:
        return False, "BREVO_KEY no configurada"

    firma_datos = firma_html if isinstance(firma_html, dict) else None
    cuerpo_html = construir_html(cuerpo, firma_datos)

    payload = {
        "sender": {"name": REMITENTE_NOMBRE, "email": REMITENTE_EMAIL},
        "to": [{"email": destinatario_email, "name": destinatario_nombre or destinatario_email}],
        "subject": asunto,
        "htmlContent": cuerpo_html,
        "textContent": cuerpo,
        "replyTo": {"email": REMITENTE_EMAIL, "name": REMITENTE_NOMBRE}
    }

    try:
        r = requests.post(BREVO_API_URL, json=payload, headers={
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": BREVO_API_KEY
        }, timeout=30)
        if r.status_code in (200, 201):
            log.info(f"Correo enviado a {destinatario_email}")
            return True, None
        else:
            error = r.json().get("message", r.text)
            log.error(f"Brevo error {r.status_code}: {error}")
            return False, error
    except Exception as e:
        log.error(f"Error: {e}")
        return False, str(e)

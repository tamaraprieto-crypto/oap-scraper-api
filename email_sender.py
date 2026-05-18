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
LOGO_URL   = "https://gestor-empresas-oap-acoruna.netlify.app/header%20correo.png"

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

    return f"""<table cellpadding="0" cellspacing="0" style="border-top:2px solid #1B3A6B;padding-top:14px;margin-top:16px;font-family:Arial,sans-serif;width:100%">
    <tr>
      <td style="vertical-align:top;padding-right:20px;width:160px">
        <img src="{LOGO_URL}" alt="Oficina Acelera Pyme ATA" style="width:150px;height:auto;display:block;margin-bottom:10px">
        <p style="margin:0;font-size:12px;color:#2d5f2d;font-weight:bold">900 101 816</p>
        <p style="margin:2px 0 0;font-size:11px"><a href="https://www.ata.es" style="color:#1B3A6B;text-decoration:none">www.ata.es</a></p>
      </td>
      <td style="vertical-align:top;border-left:1px solid #e0e0e0;padding-left:20px">
        <p style="margin:0 0 2px;font-size:13px;font-weight:bold;color:#1B3A6B">{nombre}</p>
        <p style="margin:0 0 6px;font-size:11px;color:#555">{cargo}</p>
        {f'<p style="margin:0 0 4px;font-size:12px;font-weight:bold;color:#333">{tel}</p>' if tel else ""}
        <p style="margin:0 0 4px;font-size:11px;color:#555">{oficina}</p>
        <p style="margin:0;font-size:11px;color:#555">Federacion Nacional de Asociaciones de<br>Trabajadores Autonomos</p>
        {extra}
      </td>
    </tr>
    </table>"""

def construir_html(cuerpo_texto, firma_datos=None):
    cuerpo_html = cuerpo_texto.replace("\n", "<br>")
    firma_html  = construir_firma_html(firma_datos)

    return f"""<html>
<body style="margin:0;padding:0;background:#f5f4f0;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f4f0;padding:20px 0">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)">

  <tr><td style="padding:0">
    <img src="{HEADER_URL}" alt="Oficina Acelera Pyme ATA" width="600" style="width:100%;display:block;border:0">
  </td></tr>

  <tr><td style="padding:32px 40px;color:#333333;font-size:14px;line-height:1.7">
    {cuerpo_html}
    {firma_html}
  </td></tr>

  <tr><td style="padding:0">
    <img src="{FOOTER_URL}" alt="Fondos Europeos Red.es" width="600" style="width:100%;display:block;border:0">
  </td></tr>

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

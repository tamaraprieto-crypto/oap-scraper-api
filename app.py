from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import re, time, random, logging, json
from urllib.parse import urljoin, urlparse, quote_plus, quote
from dataclasses import dataclass, asdict
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

SCRAPE_DO_TOKEN = "cc6d4971456140309bb273007be3f0f7ad524efb6c7"
BASE = "https://www.paxinasgalegas.es"

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', re.I)
DOMINIOS_IGNORAR = {
    'example.com','domain.com','wordpress.com','wixpress.com','wix.com',
    'sentry.io','schema.org','googletagmanager.com','facebook.com',
    'instagram.com','google.com','microsoft.com','cloudflare.com','w3.org',
    'jquery.com','fontawesome.com','twitter.com','tiktok.com','paxinasgalegas.es',
}
SLUGS = ['/contacto','/contacta','/contact','/sobre-nosotros','/info']
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36'}

# Mapa de categorías conocidas con sus URLs directas
CATEGORIAS = {
    "restaurantes":       "restaurantes-a-coru%C3%B1a-461ep_31ay.html",
    "peluquerías":        "peluquerias-a-coru%C3%B1a-405ep_31ay.html",
    "peluquerias":        "peluquerias-a-coru%C3%B1a-405ep_31ay.html",
    "clínicas dentales":  "clinicas-dentales-dentistas-a-coru%C3%B1a-131ep_31ay.html",
    "clinicas dentales":  "clinicas-dentales-dentistas-a-coru%C3%B1a-131ep_31ay.html",
    "farmacias":          "farmacias-de-guardia-farmacias-a-coru%C3%B1a-211ep_31ay.html",
    "talleres mecánicos": "coches-talleres-mecanicos-a-coru%C3%B1a-68ep_31ay.html",
    "talleres mecanicos": "coches-talleres-mecanicos-a-coru%C3%B1a-68ep_31ay.html",
    "academias idiomas":  "academias-de-idiomas-a-coru%C3%B1a-7ep_31ay.html",
    "fontanería":         "fontaneria-a-coru%C3%B1a-219ep_31ay.html",
    "fontaneria":         "fontaneria-a-coru%C3%B1a-219ep_31ay.html",
    "electricistas":      "instalaciones-electricas-electricidad-electricistas-a-coru%C3%B1a-185ep_31ay.html",
    "veterinarios":       "veterinarios-y-clinicas-veterinarias-a-coru%C3%B1a-503ep_31ay.html",
    "centros estética":   "salones-de-belleza-y-centros-de-estetica-a-coru%C3%B1a-7001ep_31ay.html",
    "centros estetica":   "salones-de-belleza-y-centros-de-estetica-a-coru%C3%B1a-7001ep_31ay.html",
    "tiendas de ropa":    "tiendas-de-ropa-a-coru%C3%B1a-86ep_31ay.html",
}

@dataclass
class Negocio:
    nombre: str
    sector: str
    localidad: str = 'A Coruña'
    telefono: str = ''
    web: str = ''
    email: str = ''
    pagina_email: str = ''
    estado: str = 'sin_email'

def pausa(a=0.8, b=2.0):
    time.sleep(random.uniform(a, b))

def get_via_scrapedo(url):
    proxy = f'http://api.scrape.do?token={SCRAPE_DO_TOKEN}&url={quote(url, safe="")}&render=false'
    try:
        r = requests.get(proxy, headers=HEADERS, timeout=30)
        if r.status_code == 200 and len(r.text) > 500:
            return BeautifulSoup(r.text, 'lxml')
    except Exception as e:
        log.debug(f'Scrape.do: {e}')
    return None

def get_directo(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        if r.status_code == 200:
            return BeautifulSoup(r.text, 'lxml')
    except: pass
    return None

def limpiar_email(email):
    if not email: return None
    email = email.strip().lower()
    dominio = email.split('@')[-1]
    if any(ig in dominio for ig in DOMINIOS_IGNORAR): return None
    if not 6 < len(email) < 100: return None
    return email

def extraer_emails(soup):
    emails = set()
    for a in soup.find_all('a', href=True):
        if a['href'].startswith('mailto:'):
            e = limpiar_email(a['href'][7:].split('?')[0])
            if e: emails.add(e)
    for m in EMAIL_RE.findall(soup.get_text(' ')):
        e = limpiar_email(m)
        if e: emails.add(e)
    return list(emails)

def buscar_email_en_web(url_web):
    if not url_web.startswith('http'): url_web = 'https://' + url_web
    soup = get_directo(url_web) or get_via_scrapedo(url_web)
    if not soup: return '', ''
    base = f"{urlparse(url_web).scheme}://{urlparse(url_web).netloc}"
    urls_contacto = []
    for a in soup.find_all('a', href=True):
        if any(k in a['href'].lower() or k in a.get_text().lower()
               for k in ['contact','contacto','contacta','escrib','formulario']):
            full = urljoin(url_web, a['href'])
            if urlparse(full).netloc == urlparse(url_web).netloc:
                urls_contacto.append(full)
    seen = []
    for curl in urls_contacto:
        if curl in seen or len(seen) >= 3: break
        seen.append(curl)
        pausa(0.5, 1.5)
        csoup = get_directo(curl)
        if csoup:
            emails = extraer_emails(csoup)
            if emails: return emails[0], curl
    emails = extraer_emails(soup)
    if emails: return emails[0], url_web
    for slug in SLUGS:
        pausa(0.5, 1.0)
        csoup = get_directo(base + slug)
        if csoup:
            emails = extraer_emails(csoup)
            if emails: return emails[0], base + slug
    return '', ''

def extraer_negocios_de_soup(soup, sector):
    """Extrae negocios de una página de Páxinas Galegas."""
    negocios = []
    # Método 1: atributos data-* (páginas de epígrafe)
    items = soup.find_all('li', attrs={'data-empid': True})
    for li in items:
        nombre   = li.get('data-name','').strip()
        telefono = li.get('data-telf','').strip()
        email    = limpiar_email(li.get('data-mail','')) or ''
        web      = li.get('data-empuri','').strip()
        if not nombre: continue
        if web and any(s in web for s in ['instagram.com','facebook.com','twitter.com']): web = ''
        negocios.append(Negocio(nombre=nombre, sector=sector, telefono=telefono,
                                web=web, email=email,
                                estado='con_email' if email else ('con_web' if web else 'sin_web')))
    if negocios:
        return negocios

    # Método 2: resultados de búsqueda libre (/resultados.aspx)
    for item in soup.select('[data-empid], .resultado, .empresa, [class*=empresa]'):
        nombre_el = item.select_one('[itemprop=name], h2, h3, .nombre')
        if not nombre_el: continue
        nombre = nombre_el.get_text(strip=True)
        if not nombre: continue
        tel_el = item.select_one('[itemprop=telephone], [class*=tel], [class*=phone]')
        telefono = tel_el.get_text(strip=True) if tel_el else ''
        web = ''
        for a in item.find_all('a', href=True):
            if a['href'].startswith('http') and 'paxinasgalegas' not in a['href']:
                if not any(s in a['href'] for s in ['facebook','instagram','twitter']):
                    web = a['href']; break
        negocios.append(Negocio(nombre=nombre, sector=sector, telefono=telefono,
                                web=web, estado='con_web' if web else 'sin_web'))

    return negocios

def scrape_stream(termino, localidad, max_pag, buscar_emails_web):
    """Scraper principal con soporte para categorías conocidas y búsqueda libre."""
    negocios = []
    termino_lower = termino.lower().strip()

    # Decidir qué tipo de búsqueda usar
    url_categoria = CATEGORIAS.get(termino_lower)

    if url_categoria:
        # Búsqueda por epígrafe (más precisa)
        yield json.dumps({'tipo': 'estado', 'msg': f'Usando categoría directa de Páxinas Galegas...'}) + '\n'
        for pag in range(max_pag):
            url = f'{BASE}/{url_categoria}' if pag == 0 else f'{BASE}/{url_categoria}?pagina={pag}'
            log.info(f'[Epígrafe] {termino} pág {pag+1}')
            soup = get_via_scrapedo(url)
            if not soup: break
            encontrados = extraer_negocios_de_soup(soup, termino)
            if not encontrados: break
            for n in encontrados:
                negocios.append(n)
                yield json.dumps({'tipo': 'negocio', 'data': asdict(n)}) + '\n'
            pausa(1.5, 3)
    else:
        # Búsqueda libre por texto (resultados.aspx)
        yield json.dumps({'tipo': 'estado', 'msg': f'Buscando "{termino}" en Páxinas Galegas...'}) + '\n'

        # Normalizar localidad para la búsqueda
        localidad_busqueda = localidad.lower().replace('ñ','n').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
        texto_busqueda = f"{termino} {localidad_busqueda}"

        for pag in range(max_pag):
            inicio = pag * 20
            url = f'{BASE}/resultados.aspx?tipo=0&texto={quote_plus(texto_busqueda)}&inicio={inicio}'
            log.info(f'[Libre] {texto_busqueda} pág {pag+1}: {url}')
            soup = get_via_scrapedo(url)
            if not soup:
                yield json.dumps({'tipo': 'aviso', 'msg': 'Sin respuesta de Páxinas Galegas'}) + '\n'
                break

            # Buscar fichas de empresa en resultados
            items = soup.find_all('li', attrs={'data-empid': True})
            if not items:
                # Intentar otros selectores de resultados
                items_alt = soup.select('.resultado-empresa, [class*=result], article')
                if not items_alt:
                    if pag == 0:
                        yield json.dumps({'tipo': 'aviso', 'msg': f'No se encontraron resultados para "{termino}". Prueba con otro término.'}) + '\n'
                    break
                for item in items_alt:
                    nombre_el = item.select_one('h2, h3, .nombre, [itemprop=name]')
                    if not nombre_el: continue
                    nombre = nombre_el.get_text(strip=True)
                    if not nombre: continue
                    tel_el = item.select_one('[itemprop=telephone],[class*=tel]')
                    telefono = tel_el.get_text(strip=True) if tel_el else ''
                    web = ''
                    for a in item.find_all('a', href=True):
                        if a['href'].startswith('http') and 'paxinasgalegas' not in a['href']:
                            if not any(s in a['href'] for s in ['facebook','instagram','twitter']):
                                web = a['href']; break
                    n = Negocio(nombre=nombre, sector=termino, localidad=localidad,
                                telefono=telefono, web=web,
                                estado='con_web' if web else 'sin_web')
                    negocios.append(n)
                    yield json.dumps({'tipo': 'negocio', 'data': asdict(n)}) + '\n'
            else:
                for li in items:
                    nombre   = li.get('data-name','').strip()
                    telefono = li.get('data-telf','').strip()
                    email    = limpiar_email(li.get('data-mail','')) or ''
                    web      = li.get('data-empuri','').strip()
                    if not nombre: continue
                    if web and any(s in web for s in ['instagram.com','facebook.com','twitter.com']): web = ''
                    n = Negocio(nombre=nombre, sector=termino, localidad=localidad,
                                telefono=telefono, web=web, email=email,
                                estado='con_email' if email else ('con_web' if web else 'sin_web'))
                    negocios.append(n)
                    yield json.dumps({'tipo': 'negocio', 'data': asdict(n)}) + '\n'

            if len(items) < 10: break  # Última página
            pausa(1.5, 3)

    # Buscar emails en webs
    if buscar_emails_web:
        sin_email = [n for n in negocios if n.web and not n.email]
        total = len(sin_email)
        for i, n in enumerate(sin_email):
            yield json.dumps({'tipo': 'progreso_email', 'actual': i+1, 'total': total, 'nombre': n.nombre}) + '\n'
            email, fuente = buscar_email_en_web(n.web)
            if email:
                n.email = email
                n.pagina_email = fuente
                n.estado = 'con_email'
                yield json.dumps({'tipo': 'email_encontrado', 'nombre': n.nombre, 'email': email}) + '\n'
            pausa(1, 2.5)

    yield json.dumps({'tipo': 'completado', 'total': len(negocios),
                      'con_email': sum(1 for n in negocios if n.email)}) + '\n'


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'message': 'OAP Scraper API funcionando'})

@app.route('/scrape')
def scrape():
    termino   = request.args.get('termino', '') or request.args.get('sector', '')
    localidad = request.args.get('localidad', 'A Coruña')
    max_pag   = min(int(request.args.get('paginas', 3)), 10)
    buscar_emails = request.args.get('emails', 'true').lower() == 'true'

    if not termino:
        return jsonify({'error': 'Indica un término de búsqueda. Ej: ?termino=restaurantes'}), 400

    def generate():
        yield json.dumps({'tipo': 'inicio', 'termino': termino, 'localidad': localidad, 'paginas': max_pag}) + '\n'
        yield from scrape_stream(termino, localidad, max_pag, buscar_emails)

    return Response(generate(), mimetype='application/x-ndjson',
                    headers={'X-Accel-Buffering': 'no', 'Cache-Control': 'no-cache'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)


# ── ENVÍO DE CORREOS ─────────────────────────────────────────────────────────
from email_sender import enviar_correo
import json as _json

@app.route('/enviar', methods=['POST'])
def enviar():
    """
    Recibe lista de correos y los envía uno a uno.
    Body JSON: { "correos": [ { "email", "nombre", "asunto", "cuerpo" } ] }
    """
    data = request.get_json()
    if not data or 'correos' not in data:
        return jsonify({'error': 'Formato incorrecto. Envía { "correos": [...] }'}), 400

    correos = data['correos']
    if not correos:
        return jsonify({'error': 'La lista de correos está vacía'}), 400

    if len(correos) > 30:
        return jsonify({'error': 'Máximo 30 correos por tanda'}), 400

    resultados = []
    for c in correos:
        email   = c.get('email','').strip()
        nombre  = c.get('nombre','').strip()
        asunto  = c.get('asunto','').strip()
        cuerpo  = c.get('cuerpo','').strip()

        if not email or not asunto or not cuerpo:
            resultados.append({'email': email, 'ok': False, 'error': 'Datos incompletos'})
            continue

        ok, error = enviar_correo(email, nombre, asunto, cuerpo, c.get('firma_html',''))
        resultados.append({'email': email, 'nombre': nombre, 'ok': ok, 'error': error})

        # Pausa entre envíos para evitar spam
        import time
        time.sleep(1.5)

    enviados = sum(1 for r in resultados if r['ok'])
    fallidos = sum(1 for r in resultados if not r['ok'])

    return jsonify({
        'total': len(correos),
        'enviados': enviados,
        'fallidos': fallidos,
        'resultados': resultados
    })

@app.route('/test-email', methods=['GET'])
def test_email():
    """Endpoint de prueba — envía un correo de test al remitente."""
    ok, error = enviar_correo(
        'tamara.prieto@ata.es',
        'Tamara',
        'Test OAP Gestor — Correo de prueba',
        'Este es un correo de prueba del Gestor OAP A Coruña.\n\nSi lo recibes, el sistema de envío funciona correctamente.'
    )
    if ok:
        return jsonify({'status': 'ok', 'message': 'Correo de prueba enviado a tamara.prieto@ata.es'})
    else:
        return jsonify({'status': 'error', 'message': error}), 500

@app.route('/scrape-uso', methods=['GET'])
def scrape_uso():
    """Consulta el uso restante del plan de Scrape.do."""
    try:
        r = requests.get(
            f'http://api.scrape.do/stats?token={SCRAPE_DO_TOKEN}',
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            return jsonify({
                'status': 'ok',
                'usados': data.get('usedRequests', 0),
                'limite': data.get('concurrencyLimit', 0),
                'restantes': data.get('remainingRequests', 0),
                'plan': data.get('planName', 'Gratuito'),
                'reset': data.get('resetDate', '')
            })
        else:
            return jsonify({'status': 'error', 'message': f'Scrape.do respondió {r.status_code}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

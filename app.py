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

# Mapa de sectores disponibles
SECTORES = {
    "Restaurantes":       "restaurantes-a-coru%C3%B1a-461ep_31ay.html",
    "Peluquerías":        "peluquerias-a-coru%C3%B1a-405ep_31ay.html",
    "Clínicas dentales":  "clinicas-dentales-dentistas-a-coru%C3%B1a-131ep_31ay.html",
    "Farmacias":          "farmacias-de-guardia-farmacias-a-coru%C3%B1a-211ep_31ay.html",
    "Talleres mecánicos": "coches-talleres-mecanicos-a-coru%C3%B1a-68ep_31ay.html",
    "Academias idiomas":  "academias-de-idiomas-a-coru%C3%B1a-7ep_31ay.html",
    "Fontanería":         "fontaneria-a-coru%C3%B1a-219ep_31ay.html",
    "Electricistas":      "instalaciones-electricas-electricidad-electricistas-a-coru%C3%B1a-185ep_31ay.html",
    "Veterinarios":       "veterinarios-y-clinicas-veterinarias-a-coru%C3%B1a-503ep_31ay.html",
    "Centros estética":   "salones-de-belleza-y-centros-de-estetica-a-coru%C3%B1a-7001ep_31ay.html",
    "Tiendas de ropa":    "tiendas-de-ropa-a-coru%C3%B1a-86ep_31ay.html",
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

def scrape_sector_stream(sector, url_path, max_pag, buscar_emails_web):
    """Generador que hace yield de cada negocio encontrado como JSON."""
    negocios = []
    for pag in range(max_pag):
        url = f'{BASE}/{url_path}' if pag == 0 else f'{BASE}/{url_path}?pagina={pag}'
        log.info(f'[{sector}] Pág {pag+1}')
        soup = get_via_scrapedo(url)
        if not soup: break
        items = soup.find_all('li', attrs={'data-empid': True})
        if not items: break
        for li in items:
            nombre   = li.get('data-name','').strip()
            telefono = li.get('data-telf','').strip()
            email    = limpiar_email(li.get('data-mail','')) or ''
            web      = li.get('data-empuri','').strip()
            if not nombre: continue
            if web and any(s in web for s in ['instagram.com','facebook.com','twitter.com']): web = ''
            n = Negocio(nombre=nombre, sector=sector, telefono=telefono, web=web, email=email,
                        estado='con_email' if email else ('con_web' if web else 'sin_web'))
            negocios.append(n)
            yield json.dumps({'tipo': 'negocio', 'data': asdict(n)}) + '\n'
        pausa(1.5, 3)

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

@app.route('/sectores')
def sectores():
    return jsonify({'sectores': list(SECTORES.keys())})

@app.route('/scrape')
def scrape():
    sector = request.args.get('sector', '')
    max_pag = int(request.args.get('paginas', 3))
    buscar_emails = request.args.get('emails', 'true').lower() == 'true'

    if not sector or sector not in SECTORES:
        return jsonify({'error': f'Sector no válido. Sectores disponibles: {list(SECTORES.keys())}'}), 400

    if max_pag > 10:
        max_pag = 10

    url_path = SECTORES[sector]

    def generate():
        yield json.dumps({'tipo': 'inicio', 'sector': sector, 'paginas': max_pag}) + '\n'
        yield from scrape_sector_stream(sector, url_path, max_pag, buscar_emails)

    return Response(generate(), mimetype='application/x-ndjson',
                    headers={'X-Accel-Buffering': 'no', 'Cache-Control': 'no-cache'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

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

def buscar_url_en_paxinas(termino, localidad='a-coruña'):
    """
    Busca el término en Páxinas Galegas y devuelve la URL correcta
    para ese epígrafe + ayuntamiento.
    Primero busca en la home para encontrar el enlace al epígrafe,
    luego construye la URL con el código de ayuntamiento.
    """
    # Códigos de ayuntamiento más comunes
    AYUNTAMIENTOS = {
        'a coruña': '31ay', 'coruña': '31ay',
        'ferrol': '29ay', 'santiago': '41ay', 'santiago de compostela': '41ay',
        'betanzos': '7ay', 'carballo': '16ay', 'narón': '52ay',
        'oleiros': '57ay', 'arteixo': '4ay', 'cambre': '14ay',
        'culleredo': '24ay', 'sada': '68ay',
    }
    cod_ay = AYUNTAMIENTOS.get(localidad.lower(), '31ay')

    # Buscar el epígrafe en Páxinas Galegas
    termino_norm = termino.lower().strip()
    search_url = f"{BASE}/"
    soup = get_via_scrapedo(search_url)
    if not soup:
        return None, None

    # Buscar enlaces que contengan el término
    mejor_link = None
    mejor_score = 0
    for a in soup.find_all('a', href=True):
        href = a['href']
        texto = a.get_text(strip=True).lower()
        if not href.endswith('.html'): continue
        if 'galicia' not in href: continue
        # Calcular coincidencia
        palabras = termino_norm.split()
        score = sum(1 for p in palabras if p in href.lower() or p in texto)
        if score > mejor_score:
            mejor_score = score
            mejor_link = href

    if not mejor_link or mejor_score == 0:
        # Intentar construir URL directamente con el término normalizado
        termino_url = termino_norm.replace(' ', '-').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ñ','n')
        return None, termino_url

    # Extraer código del epígrafe de la URL (ej: restaurantes-galicia-461ep.html → 461ep)
    match = re.search(r'-(\d+ep)\.html', mejor_link)
    if not match:
        return None, None

    cod_ep = match.group(1)
    # Extraer prefijo del nombre
    prefijo = mejor_link.split('/')[-1].replace(f'-galicia-{cod_ep}.html', '')

    # Construir URL para A Coruña
    url_acoruna = f"{BASE}/{prefijo}-a-coru%C3%B1a-{cod_ep}_{cod_ay}.html"
    return url_acoruna, prefijo

def scrape_libre_stream(termino, localidad, max_pag, buscar_emails_web):
    """Scraper de búsqueda libre por término en Páxinas Galegas."""
    negocios = []

    yield json.dumps({'tipo': 'estado', 'msg': f'Buscando "{termino}" en Páxinas Galegas...'}) + '\n'

    url_acoruna, prefijo = buscar_url_en_paxinas(termino, localidad)

    if not url_acoruna:
        # Intentar URL directa construida desde el término
        termino_url = termino.lower().strip()
        for ch, rep in [(' ','-'),('á','a'),('é','e'),('í','i'),('ó','o'),('ú','u'),('ñ','n'),('ü','u')]:
            termino_url = termino_url.replace(ch, rep)
        url_acoruna = f"{BASE}/{termino_url}-a-coru%C3%B1a-_31ay.html"

    yield json.dumps({'tipo': 'estado', 'msg': f'Accediendo a resultados...'}) + '\n'

    for pag in range(max_pag):
        url = url_acoruna if pag == 0 else f"{url_acoruna}?pagina={pag}"
        log.info(f'[{termino}] Pág {pag+1}: {url}')
        soup = get_via_scrapedo(url)
        if not soup:
            yield json.dumps({'tipo': 'aviso', 'msg': f'Sin resultados en página {pag+1}'}) + '\n'
            break

        items = soup.find_all('li', attrs={'data-empid': True})
        if not items:
            if pag == 0:
                yield json.dumps({'tipo': 'error', 'msg': f'No se encontraron negocios para "{termino}". Prueba con otro término.'}) + '\n'
            break

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

@app.route('/scrape')
def scrape():
    termino  = request.args.get('termino', '') or request.args.get('sector', '')
    localidad = request.args.get('localidad', 'A Coruña')
    max_pag  = min(int(request.args.get('paginas', 3)), 10)
    buscar_emails = request.args.get('emails', 'true').lower() == 'true'

    if not termino:
        return jsonify({'error': 'Indica un término de búsqueda. Ej: ?termino=restaurantes'}), 400

    def generate():
        yield json.dumps({'tipo': 'inicio', 'termino': termino, 'localidad': localidad, 'paginas': max_pag}) + '\n'
        yield from scrape_libre_stream(termino, localidad, max_pag, buscar_emails)

    return Response(generate(), mimetype='application/x-ndjson',
                    headers={'X-Accel-Buffering': 'no', 'Cache-Control': 'no-cache'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

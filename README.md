# OAP A Coruña — Scraper API

API para búsqueda de negocios locales en Páxinas Galegas.

## Endpoints

- `GET /health` — Estado de la API
- `GET /sectores` — Lista de sectores disponibles
- `GET /scrape?sector=Restaurantes&paginas=3&emails=true` — Buscar negocios

## Uso

```bash
curl "https://tu-api.railway.app/scrape?sector=Restaurantes&paginas=2"
```

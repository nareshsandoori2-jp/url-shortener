# URL Shortener with Analytics

A REST API that shortens URLs, redirects visitors, and tracks clicks.
Built with **Django REST Framework, JWT auth, MySQL, Redis, Docker**.

## Features
- JWT authentication (register, login, refresh)
- Create short links with auto-generated codes or custom aliases
- Optional expiry time; activate/deactivate links
- Fast redirects using a Redis cache (falls back to in-memory cache locally)
- Click analytics per link: total clicks, clicks per day (last 7 days), top referrers
- Rate limiting (anonymous and per-user)
- Users can only see and manage their own links
- Unit tests and GitHub Actions CI

## API

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register/` | Create an account |
| POST | `/api/auth/login/` | Get access and refresh tokens |
| POST | `/api/auth/refresh/` | Refresh the access token |
| GET | `/api/links/` | List your links (paginated) |
| POST | `/api/links/` | Create a short link |
| GET | `/api/links/{id}/` | Link details |
| PATCH | `/api/links/{id}/` | Update `is_active` or `expires_at` |
| DELETE | `/api/links/{id}/` | Delete a link |
| GET | `/api/links/{id}/stats/` | Click analytics |
| GET | `/{short_code}/` | Public redirect (302) |

### Example
```bash
curl -X POST http://localhost:8000/api/auth/register/ -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"strongpass1"}'

TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login/ -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"strongpass1"}' | python -c "import sys,json;print(json.load(sys.stdin)['access'])")

curl -X POST http://localhost:8000/api/links/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"original_url":"https://example.com","short_code":"demo"}'
```

## Run locally
```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Run with Docker (MySQL + Redis)
```bash
docker compose up --build
```

## Tests
```bash
python manage.py test
```

## Design decisions
- **Redirect caching:** redirects are the hot path, so link lookups are cached and the cache is invalidated on update/delete.
- **Atomic counters:** `F("click_count") + 1` avoids race conditions under concurrent clicks.
- **Separate Click table:** keeps raw events for analytics while `click_count` gives a fast total.
- **410 vs 404:** expired or deactivated links return 410 (Gone), unknown codes return 404.

## What I would scale next
- Move click logging to a background queue (Celery) so redirects never wait on a DB write
- Partition or aggregate the click table
- Add GeoIP and device parsing for richer analytics

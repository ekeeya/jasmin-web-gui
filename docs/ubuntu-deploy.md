# Ubuntu deploy — host nginx, Docker backends

Domain: **oddjobs.tech**. TLS on the box. No nginx container.

## DNS

| Name | Type | Target |
|------|------|--------|
| `joyce.oddjobs.tech` | A | Ubuntu public IP |
| `jasmin.oddjobs.tech` | A | same |
| `sms.oddjobs.tech` | A | same |
| `sim.oddjobs.tech` | A | same |
| `smpp.oddjobs.tech` | A | same (SMPP, not HTTPS) |

## Host nginx routes (`deploy/nginx-oddjobs.tech.conf`)

| HTTPS | Loopback | Container |
|-------|----------|-----------|
| `https://joyce.oddjobs.tech` | `127.0.0.1:9000` | `joyce` (Gunicorn) |
| `https://jasmin.oddjobs.tech` | `127.0.0.1:8080` | `jasmin_rest` |
| `https://sms.oddjobs.tech` | `127.0.0.1:1401` | `jasmin` HTTP API |
| `https://sim.oddjobs.tech` | `127.0.0.1:88` | `smppsim` |
| `smpp.oddjobs.tech:2775` | public TCP | `jasmin` SMPP — **no** `server {}` |

```bash
sudo cp deploy/nginx-oddjobs.tech.conf /etc/nginx/sites-available/oddjobs.tech
sudo ln -sf /etc/nginx/sites-available/oddjobs.tech /etc/nginx/sites-enabled/
# comment out the 443 server blocks until certs exist, or run certbot first on :80 only
sudo nginx -t && sudo systemctl reload nginx

sudo certbot --nginx \
  -d joyce.oddjobs.tech \
  -d jasmin.oddjobs.tech \
  -d sms.oddjobs.tech \
  -d sim.oddjobs.tech
```

Open firewall: `80`, `443`, `2775`. Do not open `9000`, `8080`, `1401`, `88`, `8988`, `8989`.

## Docker

```bash
cp .env.prod.example .env.prod
# ALLOWED_HOSTS=joyce.oddjobs.tech
# CSRF_TRUSTED_ORIGINS=https://joyce.oddjobs.tech

docker compose -f docker-compose.prod.yml --env-file .env.prod build
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

Joyce still uses compose DNS: `jasmin:8988`, `jasmin:8989`, `jasmin:1401`, `jasmin_rest:8080`.  
DLRs: `JOYCE_PUBLIC_BASE_URL=http://joyce:9000`.

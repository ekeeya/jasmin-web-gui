# Ubuntu deploy — host nginx, Docker backends

TLS on the box. No nginx container. Site nginx lives in a **gitignored** `deploy/nginx.conf` (copy from `deploy/nginx.conf.example`).

## DNS

Point `joyce`, `sms`, and `sim` at the Ubuntu public IP. There is no `jasmin.*` or SMPP subdomain. REST stays on loopback (`127.0.0.1:9010`). Open TCP **2775** if you want ESMEs to bind to Jasmin's test SMSC. Open **2776** if you want ESMEs to bind to SMPPSim. jcli is `127.0.0.1:8990`.

## Host nginx routes (`deploy/nginx.conf.example`)

| HTTPS | Loopback | Container |
|-------|----------|-----------|
| `joyce.<domain>` | `127.0.0.1:9003` | `joyce` (Gunicorn) |
| `sms.<domain>` | `127.0.0.1:1401` | `jasmin` HTTP API |
| `sim.<domain>` | `127.0.0.1:88` | `smppsim` |

```bash
cp deploy/nginx.conf.example deploy/nginx.conf   # edit server_name
sudo cp deploy/nginx.conf /etc/nginx/sites-available/joyce
sudo ln -sf /etc/nginx/sites-available/joyce /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d joyce.example.com \
  -d sms.example.com -d sim.example.com
```

Open firewall: `80`, `443`. Open `2775` to bind to Jasmin's test SMSC. Open `2776` to bind to SMPPSim. Do not open `9003`, `9010`, `1401`, `88`, `8988`, `8989`, `8990`.

## Docker

```bash
cp .env.prod.example .env.prod
# ALLOWED_HOSTS=joyce.oddjobs.tech
# CSRF_TRUSTED_ORIGINS=https://joyce.oddjobs.tech

docker compose -f docker-compose.prod.yml --env-file .env.prod build
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

Joyce still uses compose DNS: `jasmin:8988`, `jasmin:8989`, `jasmin:1401`, `jasmin_rest:8080`.  
DLRs: `JOYCE_PUBLIC_BASE_URL=http://joyce:8000`.

## systemd + deploy script

On the server, after the repo and `.env.prod` are in place:

```bash
chmod +x deploy/prod.sh deploy/install-systemd.sh
./deploy/prod.sh
```

That builds images, `systemctl restart joyce`, then `nginx -t` and `systemctl reload nginx`.

First run renders `deploy/joyce.service.example` into `/etc/systemd/system/joyce.service` with this checkout as `WorkingDirectory` (for example `/home/ekeeya/jasmin-web-gui`). Do not commit a machine-local `deploy/joyce.service`. After that:

```bash
sudo systemctl status joyce
sudo systemctl restart joyce
sudo systemctl stop joyce
```

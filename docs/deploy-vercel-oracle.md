# Deploy: Vercel (UI) + Oracle Cloud (API)

Split hosting so GitHub **Deployments** shows Vercel, while the FastAPI stack
(SQLite, uploads, camera scheduler) runs on an always-on Oracle VM.

```text
Browser  →  https://your-app.vercel.app     (Next.js)
         →  https://api.yourdomain.com      (FastAPI on Oracle)
```

---

## 1. Oracle Cloud — API

### VM

1. Create an Ubuntu compute instance (public IP).
2. Security list / NSG: allow **22** (your IP), **80**, **443**.
3. Do **not** expose port 8000 publicly; proxy via Caddy/Nginx.

### Install & run

```bash
sudo mkdir -p /opt/zoologai && sudo chown $USER:$USER /opt/zoologai
cd /opt/zoologai
git clone https://github.com/YOUR_USER/zoologai.git .

cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env   # set GEMINI_API_KEY and CORS (below)
alembic upgrade head
```

### `apps/api/.env` (production)

```env
DATABASE_URL=sqlite:///./zoologai.db
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-3.5-flash-lite

# Exact Vercel production URL (+ custom domain if you add one later)
CORS_ORIGINS=https://YOUR_PROJECT.vercel.app
CORS_ORIGIN_REGEX=https://.*\.vercel\.app
```

After the first Vercel deploy, replace `YOUR_PROJECT.vercel.app` with the real
hostname from the Vercel dashboard, then restart the API.

### systemd (`/etc/systemd/system/zoologai-api.service`)

```ini
[Unit]
Description=ZooLog AI API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/zoologai/apps/api
Environment=PATH=/opt/zoologai/apps/api/.venv/bin
ExecStart=/opt/zoologai/apps/api/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now zoologai-api
```

### HTTPS for the API (Caddy)

Point DNS **A** record `api.yourdomain.com` → VM public IP.

`/etc/caddy/Caddyfile`:

```caddy
api.yourdomain.com {
    reverse_proxy 127.0.0.1:8000
}
```

```bash
sudo systemctl reload caddy
curl https://api.yourdomain.com/health
```

You can use the VM’s public IP with HTTP only for a quick test, but browsers
calling from `https://*.vercel.app` require an **HTTPS** API (mixed content).

---

## 2. Vercel — UI

1. [vercel.com/new](https://vercel.com/new) → Import the GitHub repo.
2. **Root Directory:** `apps/web` (Important).
3. Framework: Next.js (auto).
4. Environment variable (Production + Preview):

   | Name | Value |
   |------|--------|
   | `NEXT_PUBLIC_API_URL` | `https://api.yourdomain.com` |

5. Deploy.

Vercel’s GitHub integration fills the repo **Deployments** tab on each push/PR.

### Custom domain for the UI (optional)

Vercel → Project → Settings → Domains → add `zoologai.yourdomain.com`, then
add that exact origin to `CORS_ORIGINS` on the Oracle API and restart.

---

## 3. Checklist

| Step | Done when |
|------|-----------|
| API health | `curl https://api…/health` → `{"status":"ok"}` |
| CORS | Network tab from Vercel site: no CORS errors |
| Env baked in | UI calls go to Oracle URL (rebuild if you change `NEXT_PUBLIC_*`) |
| Uploads persist | Files appear under `/opt/zoologai/apps/api/uploads/` |
| Scheduler | Cameras keep running while `zoologai-api` is active |

---

## 4. Updating

**API (SSH):**

```bash
cd /opt/zoologai && git pull
cd apps/api && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
sudo systemctl restart zoologai-api
```

**UI:** push to `main` — Vercel rebuilds automatically.

---

## Notes

- Never put `GEMINI_API_KEY` in Vercel; it belongs only on the Oracle API.
- Preview deployments are covered by `CORS_ORIGIN_REGEX` for `*.vercel.app`.
- Free Oracle VMs can be reclaimed if idle for a long time — check current Always Free policy.
- ARM shapes: if `opencv-python-headless` fails to install, use an x86 shape.

### YouTube live on Oracle (cookies)

Cloud IPs often hit YouTube’s “sign in to confirm you’re not a bot” wall. Export
Netscape cookies from a browser session that can play the live stream, copy to
the VM (e.g. `/opt/zoologai/apps/api/youtube-cookies.txt`), then in `.env`:

```env
YTDLP_COOKIES=/opt/zoologai/apps/api/youtube-cookies.txt
```

```bash
chmod 600 /opt/zoologai/apps/api/youtube-cookies.txt
# smoke-test:
yt-dlp --cookies "$YTDLP_COOKIES" -g "https://www.youtube.com/watch?v=…"
sudo systemctl restart zoologai-api
```

Never commit cookie files. Re-export when monitor ticks fail with the bot error again.

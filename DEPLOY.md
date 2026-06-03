# Deploy ScoutRAG ke DigitalOcean Droplet

Panduan ini diasumsikan untuk Droplet Basic kecil, misalnya 1 vCPU, 1 GB RAM, dan Neo4j tetap memakai Neo4j Aura.

## Arsitektur Production

```text
DigitalOcean Droplet
- Nginx public reverse proxy
- Next.js frontend di 127.0.0.1:3000
- FastAPI backend di 127.0.0.1:8000

External
- Neo4j Aura
- OpenAI API
```

Domain yang dipakai dalam panduan ini:

```text
scoutfootball.app
www.scoutfootball.app
```

Catatan domain `.app`: browser modern mewajibkan HTTPS untuk domain `.app`. Selesaikan langkah Certbot sebelum memakai aplikasi dari browser.

Mode vector production disarankan:

```env
VECTOR_RETRIEVAL_MODE=lexical
```

Mode ini memakai `backend/data/processed/documents.jsonl` dan tidak memuat embedding model berat di VPS.

## 1. Setup Server

```bash
apt update
apt install -y git nginx curl build-essential python3 python3-venv python3-dev
```

Tambahkan swap karena RAM 1 GB sempit:

```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

Install Node.js 20:

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
```

## 2. Clone Repo

```bash
mkdir -p /var/www
cd /var/www
git clone https://github.com/USERNAME/REPO.git scoutrag
cd scoutrag
```

## 3. DNS Namecheap

Di Namecheap, arahkan domain ke IP Droplet DigitalOcean.

Tambahkan DNS record:

```text
Type  Host  Value        TTL
A     @     IP_DROPLET   Automatic
A     www   IP_DROPLET   Automatic
```

Jangan pilih GitHub Pages untuk aplikasi utama karena backend FastAPI harus berjalan di VPS.

Tunggu propagasi DNS beberapa menit sampai beberapa jam. Cek dari lokal:

```bash
nslookup scoutfootball.app
nslookup www.scoutfootball.app
```

## 4. Backend

```bash
cd /var/www/scoutrag/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-prod.txt
cp .env.production.example .env
nano .env
```

Isi `.env` production:

```env
OPENAI_API_KEY=...
NEO4J_URI=neo4j+s://...
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
VECTOR_RETRIEVAL_MODE=lexical
CHAT_CACHE_ENABLED=true
CHAT_CACHE_TTL_SECONDS=86400
CHAT_CACHE_PATH=./data/chat_cache.sqlite
APP_AUTH_ENABLED=true
APP_AUTH_USERNAME=admin
APP_AUTH_PASSWORD=...
APP_AUTH_SECRET=...
APP_AUTH_SESSION_TTL_SECONDS=604800
CORS_ORIGINS=https://scoutfootball.app,https://www.scoutfootball.app
```

`CHAT_CACHE_TTL_SECONDS=86400` berarti jawaban pertanyaan yang sama persis akan dicache 24 jam. Cache otomatis tidak dipakai lagi jika `refresh_state.json` berubah karena data statistik diperbarui.

`APP_AUTH_SECRET` wajib sama antara backend `.env` dan frontend `.env.production`. Gunakan secret acak minimal 32 karakter, misalnya hasil `openssl rand -hex 32`. Jangan pakai secret yang sama dengan local development.

## 5. Upload Data Lokal

File data tidak ikut Git. Upload minimal:

```text
backend/data/processed/documents.jsonl
backend/data/refresh_state.json
```

Dari komputer lokal:

```powershell
scp backend\data\processed\documents.jsonl root@IP_DROPLET:/var/www/scoutrag/backend/data/processed/
scp backend\data\refresh_state.json root@IP_DROPLET:/var/www/scoutrag/backend/data/
```

Jika tombol refresh FBref ingin berjalan di server, upload juga:

```powershell
scp -r backend\data\raw root@IP_DROPLET:/var/www/scoutrag/backend/data/
scp -r backend\cache\fbref root@IP_DROPLET:/var/www/scoutrag/backend/cache/
scp -r backend\cache\soccerdata root@IP_DROPLET:/var/www/scoutrag/backend/cache/
```

## 6. Backend Service

```bash
cp /var/www/scoutrag/deploy/systemd/scoutrag-backend.service /etc/systemd/system/scoutrag-backend.service
systemctl daemon-reload
systemctl enable scoutrag-backend
systemctl start scoutrag-backend
systemctl status scoutrag-backend
```

Test:

```bash
curl http://127.0.0.1:8000/api/health
```

## 7. Frontend

```bash
cd /var/www/scoutrag/frontend
npm install
cp .env.production.example .env.production
nano .env.production
npm run build
npm install -g pm2
pm2 start npm --name scoutrag-frontend -- start
pm2 save
pm2 startup
```

Isi `.env.production`:

```env
NEXT_PUBLIC_API_URL=https://scoutfootball.app
APP_AUTH_ENABLED=true
APP_AUTH_USERNAME=admin
APP_AUTH_PASSWORD=...
APP_AUTH_SECRET=...
APP_AUTH_SESSION_TTL_SECONDS=604800
```

Nilai `APP_AUTH_USERNAME`, `APP_AUTH_PASSWORD`, dan `APP_AUTH_SECRET` harus sama dengan backend `.env`. Setelah mengubah `.env.production`, jalankan ulang `npm run build` karena environment frontend production dibaca saat build.

## 8. Nginx

Config Nginx hanya menjadi reverse proxy. Login ditangani oleh aplikasi melalui `/login`, bukan Basic Auth Nginx.

```bash
cp /var/www/scoutrag/deploy/nginx/scoutrag.conf /etc/nginx/sites-available/scoutrag
nano /etc/nginx/sites-available/scoutrag
ln -sf /etc/nginx/sites-available/scoutrag /etc/nginx/sites-enabled/scoutrag
nginx -t
systemctl reload nginx
```

Test:

```bash
curl -I http://scoutfootball.app/chat
```

Untuk domain `.app`, test HTTP ini cukup untuk memastikan Nginx menerima request sebelum Certbot. Browser akan lebih aman dipakai setelah HTTPS aktif.

## 9. HTTPS

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d scoutfootball.app -d www.scoutfootball.app
```

Setelah HTTPS aktif:

```bash
curl -I https://scoutfootball.app/chat
curl https://scoutfootball.app/api/health
```

Expected result:

- `/chat` tanpa cookie login redirect ke `/login`.
- `/api/health` tanpa cookie login return `401`.

Untuk test API dengan cookie login dari terminal:

```bash
curl -c /tmp/scoutrag-cookie.txt -X POST https://scoutfootball.app/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"PASSWORD_PRODUCTION"}'

curl -b /tmp/scoutrag-cookie.txt https://scoutfootball.app/api/health
```

Saat membuka `https://scoutfootball.app/chat` dari browser, aplikasi akan menampilkan halaman login ScoutRAG. Setelah login, frontend dan API berjalan normal karena request berada di domain yang sama.

## 10. Update Deploy Setelah Push Baru

```bash
cd /var/www/scoutrag
git pull

cd backend
source .venv/bin/activate
pip install -r requirements-prod.txt
systemctl restart scoutrag-backend

cd ../frontend
npm install
nano .env.production
npm run build
pm2 restart scoutrag-frontend
```

## 11. Mengganti OpenAI API Key Production

Gunakan key berbeda untuk lokal dan VPS agar pemakaian production bisa dipantau terpisah.

1. Buat API key baru di dashboard OpenAI.
2. Masuk ke VPS.
3. Edit file environment backend production:

```bash
cd /var/www/scoutrag/backend
nano .env
```

4. Ganti hanya baris berikut:

```env
OPENAI_API_KEY=sk-key-production-baru
```

5. Restart backend:

```bash
systemctl restart scoutrag-backend
systemctl status scoutrag-backend
```

6. Test dari VPS:

```bash
curl -c /tmp/scoutrag-cookie.txt -X POST https://scoutfootball.app/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"PASSWORD_PRODUCTION"}'

curl -b /tmp/scoutrag-cookie.txt https://scoutfootball.app/api/health
curl -b /tmp/scoutrag-cookie.txt -X POST https://scoutfootball.app/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Siapa top scorer La Liga musim ini?"}'
```

7. Jika sudah aman, revoke API key lama dari dashboard OpenAI.

Catatan: jangan pernah commit `.env`. File yang dicommit hanya `.env.example` atau `.env.production.example`.

## 12. Membersihkan Chat Cache

Normalnya cache tidak perlu dihapus. Cache otomatis invalid saat data refresh berubah. Kalau ingin mengosongkan cache manual:

```bash
rm -f /var/www/scoutrag/backend/data/chat_cache.sqlite*
systemctl restart scoutrag-backend
```

## 13. Rollback Cepat ke Basic Auth Nginx

Gunakan rollback ini hanya jika login aplikasi bermasalah di production dan kamu perlu mengunci akses sementara.

```bash
apt install -y apache2-utils
htpasswd -c /etc/nginx/.scoutrag_passwd admin
nano /etc/nginx/sites-available/scoutrag
```

Tambahkan di dalam server block utama:

```nginx
auth_basic "ScoutRAG";
auth_basic_user_file /etc/nginx/.scoutrag_passwd;

location /.well-known/acme-challenge/ {
    auth_basic off;
    root /var/www/html;
}
```

Lalu:

```bash
nginx -t
systemctl reload nginx
```

## Catatan

- Jangan commit `.env`.
- Jangan jalankan Neo4j lokal di Droplet kecil.
- Jangan menjalankan `initial_setup.py` penuh di Droplet kecil kecuali benar-benar perlu.
- Untuk production kecil, gunakan `VECTOR_RETRIEVAL_MODE=lexical`.


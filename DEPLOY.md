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
apt install -y git nginx curl build-essential python3.11 python3.11-venv python3.11-dev
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
python3.11 -m venv .venv
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
CORS_ORIGINS=https://scoutfootball.app,https://www.scoutfootball.app
```

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
```

## 8. Nginx

```bash
cp /var/www/scoutrag/deploy/nginx/scoutrag.conf /etc/nginx/sites-available/scoutrag
nano /etc/nginx/sites-available/scoutrag
ln -s /etc/nginx/sites-available/scoutrag /etc/nginx/sites-enabled/scoutrag
nginx -t
systemctl reload nginx
```

Test:

```bash
curl http://scoutfootball.app/api/health
```

Untuk domain `.app`, test HTTP ini cukup untuk memastikan Nginx menerima request sebelum Certbot. Browser akan lebih aman dipakai setelah HTTPS aktif.

## 9. HTTPS

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d scoutfootball.app -d www.scoutfootball.app
```

Setelah HTTPS aktif:

```bash
curl https://scoutfootball.app/api/health
```

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
npm run build
pm2 restart scoutrag-frontend
```

## Catatan

- Jangan commit `.env`.
- Jangan jalankan Neo4j lokal di Droplet kecil.
- Jangan menjalankan `initial_setup.py` penuh di Droplet kecil kecuali benar-benar perlu.
- Untuk production kecil, gunakan `VECTOR_RETRIEVAL_MODE=lexical`.


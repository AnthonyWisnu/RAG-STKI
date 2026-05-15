<h1 align="center">ScoutRAG - STKI Football KG-RAG System</h1>

<p align="center">
  <strong>Sistem Tanya-Jawab Cerdas Berbasis Knowledge Graph dan RAG untuk Informasi Statistik dan Valuasi Pemain Sepak Bola</strong>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11-blue">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115-009688">
  <img alt="Next.js" src="https://img.shields.io/badge/Next.js-14-black">
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-5.7-3178c6">
  <img alt="Neo4j" src="https://img.shields.io/badge/Neo4j-5.27-4581c3">
  <img alt="ChromaDB" src="https://img.shields.io/badge/ChromaDB-0.5-f97316">
  <img alt="OpenAI" src="https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991">
  <img alt="Tailwind" src="https://img.shields.io/badge/Tailwind-3.4-38bdf8">
</p>

<p align="center">
  <strong>Tugas Akademik Sistem Temu Kembali Informasi (STKI)</strong><br>
  Program Studi Sistem Informasi, Universitas Udayana
</p>

<p align="center">
  <a href="#fitur-utama">Fitur</a> -
  <a href="#arsitektur-sistem">Arsitektur</a> -
  <a href="#alur-kerja-sistem">Alur Kerja</a> -
  <a href="#instalasi-dan-setup">Setup</a> -
  <a href="#dokumentasi-api">API</a> -
  <a href="#demo-query">Demo Query</a>
</p>

---

Sistem tanya jawab cerdas untuk statistik, profil, perbandingan, dan valuasi pemain sepak bola di lima liga top Eropa. Project ini menggabungkan Knowledge Graph, semantic retrieval, dan LLM reasoning agar jawaban tetap berbasis data, punya citation, dan tidak mengarang angka yang tidak tersedia.

```text
Scope     : Premier League, La Liga, Serie A, Bundesliga, Ligue 1
Musim     : 2023-2024, 2024-2025, 2025-2026
Data      : FBref publik via soccerdata, Kaggle Transfermarkt, Wikipedia cache
Retrieval : kg_only, vector_only, hybrid, valuation_reasoning
UI        : Next.js analytics dashboard dengan dark editorial aesthetic
```

## Daftar Isi

- [Ringkasan](#ringkasan)
- [Fitur Utama](#fitur-utama)
- [Teknologi](#teknologi)
- [Arsitektur Sistem](#arsitektur-sistem)
- [Alur Kerja Sistem](#alur-kerja-sistem)
- [Struktur Data](#struktur-data)
- [Instalasi dan Setup](#instalasi-dan-setup)
- [Menjalankan Aplikasi](#menjalankan-aplikasi)
- [Dokumentasi API](#dokumentasi-api)
- [Evaluasi Sistem](#evaluasi-sistem)
- [Demo Query](#demo-query)
- [Struktur Project](#struktur-project)
- [Troubleshooting](#troubleshooting)
- [Kontributor](#kontributor)
- [Lisensi](#lisensi)
- [Acknowledgements](#acknowledgements)

## Ringkasan

ScoutRAG dibuat untuk kebutuhan Sistem Temu Kembali Informasi berbasis data sepak bola. Sistem ini bisa menjawab pertanyaan seperti:

- "Siapa top scorer Premier League musim 2025-2026?"
- "Bandingkan Mohamed Salah dan Son Heung-min sebagai winger."
- "Siapa pemain yang statistiknya mirip Pedri tetapi market value lebih murah?"
- "Berapa estimasi range nilai pasar Aaron Ramsdale?"

Sistem memilih strategi retrieval secara otomatis:

| Strategi | Dipakai untuk |
|---|---|
| `kg_only` | Angka terstruktur: gol, assist, menit, ranking, nilai pasar, klub, liga |
| `vector_only` | Profil naratif, ringkasan pemain, konteks deskriptif |
| `hybrid` | Pertanyaan kompleks yang butuh angka KG dan narasi vector |
| `valuation_reasoning` | Estimasi range nilai pasar berbasis konteks KG/RAG dan LLM |

### Scope Data

| Aspek | Detail |
|---|---|
| Liga | Premier League, La Liga, Serie A, Bundesliga, Ligue 1 |
| Musim | 2023-2024, 2024-2025, 2025-2026 |
| Statistik | FBref via `soccerdata`, hanya stat publik |
| Valuasi | Kaggle Transfermarkt dataset by David Cariboo |
| Filter pemain | `minutes >= 400` atau `matches_played >= 8` atau `market_value_eur >= 30M EUR` |
| Di luar scope | UEFA Champions League dan kompetisi non Big 5 |

Catatan data penting:

- Advanced stats FBref seperti passing, GCA/SCA, possession, defense advanced, dan keeper advanced tidak tersedia dari sumber publik terbaru.
- Sofascore tidak dipakai karena dukungan library untuk statistik musim pemain sudah berubah.
- Field yang tidak tersedia tidak dipalsukan menjadi `0`. Backend menyimpan sebagai `null`, dan frontend menyembunyikan atau memberi fallback yang jelas.
- Estimasi nilai pasar bukan prediksi angka pasti. Sistem memberi range dan alasan berbasis evidence.

## Fitur Utama

### Backend

| Fitur | Deskripsi |
|---|---|
| Agentic Router | Memilih strategi `kg_only`, `vector_only`, `hybrid`, atau `valuation_reasoning` |
| Text-to-Cypher | Mengubah pertanyaan natural language menjadi Cypher dengan retry dan fallback |
| Knowledge Graph | Neo4j menyimpan pemain, klub, liga, musim, posisi, statistik, dan valuasi |
| Vector Retrieval | ChromaDB menyimpan profil pemain, ringkasan Wikipedia, dan narasi valuasi |
| LLM Valuation Reasoning | LLM menjawab estimasi nilai pasar sebagai range dengan citation |
| Citation System | Jawaban chat, compare, dan valuation membawa sumber dari KG atau vector docs |
| Bilingual Answer | Deteksi bahasa Indonesia atau Inggris dan merespons sesuai bahasa user |
| UCL Guard | Pertanyaan Champions League dijawab sebagai data tidak tersedia |
| Idempotent ETL | Loader memakai MERGE dan upsert agar aman dijalankan ulang |
| Self-throttling Refresh | Refresh data memakai state tracker dan throttle 24 jam |
| API Health | Menampilkan freshness data, jumlah stats, valuations, dan mapped players |

### Frontend

| Halaman | Fungsi |
|---|---|
| `/chat` | Tanya jawab bebas dengan strategy badge dan citation panel |
| `/compare` | Bandingkan 2 sampai 4 pemain dengan radar chart dan narasi |
| `/search` | Cari pemain dengan filter nama, posisi, liga, musim, dan sorting |
| `/valuation` | Lihat tren histori market value pemain |
| `/predict` | Estimasi range nilai pasar berbasis LLM reasoning |
| `/top` | Ranking pemain berdasarkan kategori statistik tersedia |
| `/club` | Profil klub, squad table, top scorer, dan nilai squad |

### UX

- Dark editorial dashboard dengan aksen hijau electric.
- Sidebar desktop dan bottom navigation mobile.
- Warna kartu pemain berbeda per posisi: GK, DEF, MID, FWD.
- Skeleton, loading, empty, dan error state tersedia.
- Data freshness badge di sidebar bawah.
- Tombol `Perbarui Data` di sidebar untuk menjalankan refresh tanpa initial setup ulang.

## Teknologi

### Backend Stack

| Library / Package | Versi | Fungsi |
|---|---|---|
| FastAPI | 0.115 | API server dan OpenAPI docs |
| Pydantic | 2.x | Request dan response validation |
| Neo4j driver | 5.27 | Knowledge Graph driver |
| ChromaDB | 0.5 | Persistent vector store |
| sentence-transformers | 3.3 | Embedding lokal multilingual-e5-base |
| OpenAI | 1.58 | LLM planner, Cypher helper, synthesis, valuation reasoning |
| soccerdata | 1.9 | FBref scraper untuk statistik publik |
| Kaggle API | 1.6 | Transfermarkt dataset loader |
| pandas + pyarrow | 2.2 | Data processing dan parquet cache |
| wikipedia-api | 0.7 | Wikipedia summary cache |
| RAGAS | 0.2 | Optional evaluator, fallback manual rubric tersedia |
| uvicorn | 0.34 | ASGI server |

### Frontend Stack

| Library / Package | Versi | Fungsi |
|---|---|---|
| Next.js | 14 | App Router |
| React | 18 | UI library |
| TypeScript | 5 | Type safety |
| Tailwind CSS | 3 | Design tokens dan utility styling |
| lucide-react | latest | Icon library |
| Recharts | 2 | Radar, line, bar, dan donut chart |
| Framer Motion | 11 | Micro-interaction dan transition |

### Infrastruktur Data

| Komponen | Fungsi |
|---|---|
| Neo4j Aura / Local Neo4j | Knowledge Graph |
| ChromaDB persistent | Vector document retrieval |
| FBref via soccerdata | Statistik pemain |
| Kaggle Transfermarkt | Profil dan histori valuasi pemain |
| Wikipedia local cache | Ringkasan naratif tambahan |
| OpenAI API | LLM reasoning dan answer synthesis |

## Arsitektur Sistem

### High-Level Architecture

<details>
<summary>Lihat diagram arsitektur lengkap</summary>

```
FRONTEND (Next.js)
  /chat  /compare  /search  /valuation  /predict  /top  /club
       |
       |  HTTP / JSON
       v
+------------------------------------------+
|         FASTAPI BACKEND (Python)         |
|                                          |
|  [ Agentic Router ]                      |
|  Language Detection -> Strategy Select   |
|         |                  |             |
|         v                  v             |
|   [ KG Retriever ]  [ Vector Retriever ] |
|         |                  |             |
|         v                  v             |
|      [ Neo4j ]         [ ChromaDB ]      |
|         |                  |             |
|         +--------+---------+             |
|                  v                       |
|     [ LLM Answer Synthesis ]             |
|     Bilingual answer + citation          |
|                                          |
|  [ LLM Valuation Reasoner ]              |
|  KG context + history -> range estimate  |
+------------------------------------------+
       ^
       |
  [ ETL Pipeline ]
   /           \
[FBref]     [Kaggle]
```

</details>

### Strategi Retrieval

| Strategi | Alur |
|---|---|
| `kg_only` | User query -> Cypher/template query -> Neo4j rows -> answer synthesis |
| `vector_only` | User query -> E5 embedding -> ChromaDB top-k docs -> answer synthesis |
| `hybrid` | KG rows + vector docs -> merged context -> answer synthesis |
| `valuation_reasoning` | Player context + valuation history + stats -> LLM estimated range |

## Alur Kerja Sistem

### Alur ETL: Initial Setup

<details>
<summary>Lihat diagram Alur ETL: Initial Setup</summary>

```
INITIAL SETUP (dijalankan sekali)

 1.  Load env dan validasi konfigurasi
 2.  Download Kaggle Transfermarkt dataset
 3.  Fetch FBref Big 5 untuk 4 stat_type publik
       - standard, shooting, keeper, misc
       - cache parquet ke backend/cache/fbref
       - delay minimal 6 detik antar request
 4.  Normalisasi Transfermarkt dan FBref
 5.  Mapping FBref player id ke Transfermarkt player id
 6.  Filter pemain relevan
 7.  MERGE Player, Club, League, Season, Stats, Valuation ke Neo4j
 8.  Generate profile, wiki summary, dan valuation narrative docs
 9.  Embed dokumen dengan multilingual-e5-base
 10. Upsert dokumen ke ChromaDB
 11. Update backend/data/refresh_state.json
 12. Backup snapshot cache FBref
```

</details>

### Alur Refresh Data

<details>
<summary>Lihat diagram Alur Refresh Data</summary>

```
Sidebar button / CLI manual_refresh.py
        |
        v
   Baca refresh_state.json
        |
        v
   Cek throttle 24 jam
   force=false -> skip jika baru direfresh
        |
        v
   Jalankan refresh background
   (tidak mengulang initial setup)
        |
        v
   Update status, counts, timestamp, error/skip reason
```

</details>

Catatan: jalur refresh saat ini state-aware dan aman untuk demo. Refresh tidak menghapus graph dan tidak mengulang initial setup dari nol.

### Alur Query Runtime

<details>
<summary>Lihat diagram Alur Query Runtime</summary>

```
User Input
    |
    v
Language Detection (langdetect + hints)
    |-- output: id / en
    v
Scope Guard (Big 5 only)
    |-- early exit jika query UCL
    v
Agentic Router (heuristic + optional LLM)
    |-- output: {strategy, reason}
    v
Execute Selected Strategy
    |
    +-- kg_only:             Cypher/template -> Neo4j
    +-- vector_only:         query embedding -> ChromaDB
    +-- hybrid:              Neo4j + ChromaDB -> merged context
    +-- valuation_reasoning: KG context -> LLM estimated range
    |
    v
Fallback jika context kosong
    |
    v
Answer Synthesis (deterministic / LLM)
    |-- output: bilingual answer + citations
    v
Response
```

</details>

## Struktur Data

### Knowledge Graph Schema

```cypher
// Nodes
(:Player {
  api_id, fbref_id, name, birth_date, height_cm,
  preferred_foot, nationality, photo_url, is_active
})

(:Club {
  api_id, name, country, logo_url, founded_year
})

(:League {
  id, name, country
})

(:Season {
  id
})

(:Position {
  id, name
})

(:Nationality {
  id, country_name, country_code
})

(:PlayerSeasonStats {
  id, player_id, season_id, league_id, club_id, position,
  matches_played, starts, minutes, nineties,
  goals, assists, shots_total, shots_on_target,
  shots_on_target_pct, saves, save_pct,
  clean_sheets, goals_against,
  yellow_cards, red_cards
})

(:Valuation {
  id, market_value_eur, valuation_date, source
})

// Relationships
(Player)-[:HAS_STATS_IN]->(PlayerSeasonStats)
(PlayerSeasonStats)-[:DURING]->(Season)
(PlayerSeasonStats)-[:WITH_CLUB]->(Club)
(PlayerSeasonStats)-[:IN_LEAGUE]->(League)
(Player)-[:HAS_VALUATION]->(Valuation)
(Player)-[:PLAYS_POSITION]->(Position)
(Player)-[:NATIONALITY_OF]->(Nationality)
(Club)-[:COMPETES_IN {season}]->(League)
```

### Vector Store

```text
Collection: football_players

Document types:
1. profile_{player_id}_v{hash}
   Profil naratif dari data KG.

2. wiki_{player_id}
   Ringkasan Wikipedia dengan local cache.

3. valuation_{player_id}_v{hash}
   Narasi tren market value dari node Valuation.

Embedding:
  intfloat/multilingual-e5-base

E5 prefix:
  passage: untuk dokumen
  query: untuk retrieval query
```

### Data Availability Rules

| Jenis data | Perlakuan |
|---|---|
| Stat tersedia dari FBref publik | Disimpan dan ditampilkan |
| Stat tidak tersedia | Disimpan `null` atau tidak ditampilkan |
| Nilai pasar tersedia | Dipakai sebagai current value dan valuation history |
| Valuasi kosong | Estimasi nilai pasar tidak diberikan |
| UCL query | Dijawab sebagai data tidak tersedia |

## Instalasi dan Setup

### Prasyarat

- Python 3.11, disarankan `py -3.11` di Windows.
- Node.js 20 atau lebih baru.
- Neo4j Aura atau Neo4j lokal.
- Kaggle API credential.
- OpenAI API key untuk jawaban LLM yang penuh.

### Backend Setup

```powershell
cd c:\laragon\www\RAG-STKI\backend
py -3.11 -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Buat `.env` dari contoh:

```powershell
copy .env.example .env
```

Isi konfigurasi utama:

```text
OPENAI_API_KEY=sk-your-openai-api-key
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
KAGGLE_USERNAME=your-kaggle-username
KAGGLE_KEY=your-kaggle-key
CHROMA_PERSIST_DIR=./data/chroma_v2
VECTOR_RETRIEVAL_MODE=auto
SOCCERDATA_DIR=./cache/soccerdata
SOCCERDATA_DELAY=6
LOG_LEVEL=INFO
```

### Frontend Setup

```powershell
cd c:\laragon\www\RAG-STKI\frontend
npm install
copy .env.local.example .env.local
```

Isi `.env.local`:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Initial Data Load

Jalankan sekali setelah `.env` siap:

```powershell
cd c:\laragon\www\RAG-STKI\backend
.\.venv\Scripts\activate
python etl\initial_setup.py
```

Initial setup bisa lama karena FBref wajib memakai delay request.

## Menjalankan Aplikasi

### Development Mode

Terminal 1, backend:

```powershell
cd c:\laragon\www\RAG-STKI\backend
.\.venv\Scripts\activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Backend tersedia di:

- API: `http://127.0.0.1:8000/api`
- OpenAPI docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/api/health`
- Refresh status: `http://127.0.0.1:8000/api/refresh/status`

Terminal 2, frontend:

```powershell
cd c:\laragon\www\RAG-STKI\frontend
npm run dev
```

Frontend tersedia di:

```text
http://localhost:3000
```

### Production Build

```powershell
# Frontend
cd c:\laragon\www\RAG-STKI\frontend
npm run build
npm start

# Backend
cd c:\laragon\www\RAG-STKI\backend
.\.venv\Scripts\activate
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Manual Data Refresh

Dari UI:

```text
Sidebar bawah -> Perbarui Data
```

Dari CLI:

```powershell
cd c:\laragon\www\RAG-STKI\backend
.\.venv\Scripts\activate
python etl\manual_refresh.py
```

Mode tambahan:

```powershell
python etl\manual_refresh.py --force
python etl\manual_refresh.py --dry-run
python etl\manual_refresh.py --only valuations
python etl\manual_refresh.py --only stats
python etl\manual_refresh.py --league "ENG-Premier League"
```

Keterangan:

| Flag | Fungsi |
|---|---|
| `--force` | Bypass throttle 24 jam |
| `--dry-run` | Preview tanpa update `last_refresh` |
| `--only valuations` | Mode refresh valuasi |
| `--only stats` | Mode refresh statistik |
| `--league` | Menandai target liga tertentu |

## Dokumentasi API

Base URL:

```text
http://127.0.0.1:8000
```

### Endpoint Utama

| Method | Endpoint | Fungsi |
|---|---|---|
| `GET` | `/api/health` | Status backend dan freshness data |
| `POST` | `/api/chat` | Tanya jawab RAG |
| `GET` | `/api/players/search` | Cari dan filter pemain |
| `GET` | `/api/players/{player_id}` | Detail pemain |
| `GET` | `/api/players/{player_id}/valuation-history` | Histori valuasi pemain |
| `POST` | `/api/compare` | Bandingkan beberapa pemain |
| `POST` | `/api/predict` | Estimasi range nilai pasar berbasis LLM |
| `GET` | `/api/top-performers` | Ranking pemain |
| `GET` | `/api/clubs/search` | Cari klub |
| `GET` | `/api/clubs/{club_id}` | Detail klub dan squad |
| `GET` | `/api/refresh/status` | Status manual refresh |
| `POST` | `/api/refresh/start` | Jalankan refresh di background |

### Contoh Request

Chat:

```powershell
$body = @{
  question = "siapa pemain yang statistiknya mirip Pedri tetapi market value lebih murah?"
} | ConvertTo-Json

Invoke-RestMethod `
  http://127.0.0.1:8000/api/chat `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

Search players:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/players/search?q=pedri&page_size=5"
```

Valuation reasoning:

```powershell
$body = @{
  player_name = "Aaron Ramsdale"
  language = "id"
  use_llm = $true
} | ConvertTo-Json

Invoke-RestMethod `
  http://127.0.0.1:8000/api/predict `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

Start refresh:

```powershell
$body = @{
  mode = "all"
  force = $false
  dry_run = $false
} | ConvertTo-Json

Invoke-RestMethod `
  http://127.0.0.1:8000/api/refresh/start `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

Dokumentasi interaktif:

```text
http://127.0.0.1:8000/docs
```

## Evaluasi Sistem

Evaluasi memakai 20 gold queries yang mencakup:

- KG-only query.
- Vector-only query.
- Hybrid query.
- Valuation reasoning.
- Bahasa Indonesia dan Inggris.
- UCL fallback.
- Citation validation.
- Data availability guard untuk statistik yang tidak tersedia.

Jalankan evaluasi:

```powershell
cd c:\laragon\www\RAG-STKI
backend\.venv\Scripts\python backend\evaluation\ragas_eval.py --api-url http://127.0.0.1:8000 --timeout 120
```

Mode tanpa HTTP:

```powershell
backend\.venv\Scripts\python backend\evaluation\ragas_eval.py --no-http
```

Hasil verifikasi terakhir:

```text
Total queries                 : 20
Passed                        : 20
Failed                        : 0
Pass rate                     : 100%
Strategy accuracy             : 100%
Language accuracy             : 100%
Citation pass rate            : 100%
Data availability accuracy    : 100%
```

Jika RAGAS atau Torch bermasalah di Windows, evaluator tetap berjalan dengan fallback manual rubric.

File evaluasi:

```text
backend/evaluation/gold_queries.json
backend/evaluation/raw_results.json
backend/evaluation/results.md
```

## Demo Query

Contoh pertanyaan yang didukung sistem:

| Kategori | Contoh Pertanyaan | Strategi |
|---|---|---|
| Ranking statistik | `Siapa top scorer La Liga musim ini?` | `kg_only` |
| Profil pemain | `Jelaskan profil Pedri dan valuasinya.` | `hybrid` |
| Similar player | `Siapa pemain yang statistiknya mirip Pedri tetapi market value lebih rendah?` | `kg_only` |
| Estimasi valuasi | `Berapa estimasi nilai pasar Lamine Yamal?` | `valuation_reasoning` |
| Perbandingan | `Bandingkan Salah dan Son sebagai winger.` | `hybrid` |
| Negative scope | `Siapa top scorer Champions League?` | UCL fallback |

Contoh respons similar player:

```text
Pemain dengan statistik paling mirip Pedri tetapi market value lebih rendah dari EUR 80.0 juta:
1. Joshua Kimmich - 2190 menit, 2 gol, 6 assist, nilai EUR 40.0 juta
2. Farès Chaïbi - 1747 menit, 2 gol, 9 assist, nilai EUR 15.0 juta
3. Valentín Barco - 2110 menit, 2 gol, 4 assist, nilai EUR 13.0 juta
```

Catatan: hasil bergantung pada data Neo4j lokal yang sudah di-load dari ETL.

## Struktur Project

```
RAG-STKI/
├── AGENT.md
├── DESIGN.md
├── PLAN.md
├── README.md
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py
│   │   │   ├── players.py
│   │   │   ├── clubs.py
│   │   │   ├── compare.py
│   │   │   ├── predict.py
│   │   │   ├── health.py
│   │   │   └── refresh.py
│   │   └── schemas/
│   ├── config/
│   │   ├── settings.py
│   │   └── prompts/
│   ├── etl/
│   │   ├── initial_setup.py
│   │   ├── manual_refresh.py
│   │   ├── state_tracker.py
│   │   ├── fbref_scraper.py
│   │   ├── kaggle_loader.py
│   │   ├── player_id_mapper.py
│   │   ├── neo4j_loader.py
│   │   ├── document_generator.py
│   │   └── chroma_loader.py
│   ├── src/
│   │   ├── retrieval/
│   │   ├── valuation/
│   │   ├── llm/
│   │   └── utils/
│   ├── data/
│   │   ├── raw/
│   │   ├── processed/
│   │   ├── chroma/
│   │   └── refresh_state.json
│   ├── cache/
│   │   ├── fbref/
│   │   └── wiki/
│   └── evaluation/
└── frontend/
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.js
    ├── .env.local.example
    └── src/
        ├── app/
        │   ├── chat/
        │   ├── compare/
        │   ├── search/
        │   ├── valuation/
        │   ├── predict/
        │   ├── top/
        │   └── club/
        ├── components/
        │   ├── layout/
        │   ├── player/
        │   ├── compare/
        │   ├── charts/
        │   └── ui/
        ├── lib/
        └── types/
```

## Troubleshooting

### Port 8000 tidak bisa dipakai di Windows

Jika muncul:

```text
WinError 10013: An attempt was made to access a socket in a way forbidden by its access permissions
```

Gunakan port lain:

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8010
```

Lalu ubah `frontend/.env.local`:

```text
NEXT_PUBLIC_API_URL=http://localhost:8010
```

### `chroma-hnswlib` gagal build

Gunakan Python 3.11:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Jika tetap gagal, install Microsoft C++ Build Tools.

### Torch gagal load `c10.dll`

Ini biasanya masalah wheel Torch di Windows. Fitur utama backend tetap bisa berjalan, dan evaluator punya fallback manual. Jika perlu memperbaiki:

```powershell
pip uninstall -y torch
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### RAGAS tidak tersedia

Output bisa menampilkan:

```text
ragas_available=false
```

Itu tidak memblokir evaluasi karena fallback manual rubric tetap tersedia.

### Backend import gagal

Pastikan venv aktif dan command dijalankan dari folder backend:

```powershell
cd c:\laragon\www\RAG-STKI\backend
.\.venv\Scripts\activate
python -c "import main; print('BACKEND IMPORT OK')"
```

### Frontend tidak bisa fetch backend

Pastikan `frontend/.env.local` sesuai port backend:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Restart frontend setelah mengubah `.env.local`:

```powershell
npm run dev
```

### Next.js dev server error manifest atau vendor chunk

Jika muncul error seperti `Cannot find module './vendor-chunks/next.js'`, hapus cache build lokal:

```powershell
cd c:\laragon\www\RAG-STKI\frontend
Remove-Item .next -Recurse -Force
npm run dev
```

### Data Champions League tidak muncul

Itu sesuai desain. Scope sistem hanya lima liga top Eropa. Pertanyaan UCL akan dijawab sebagai data tidak tersedia.

## Kontributor

**Anthony**  
Program Studi Teknologi Informasi, Universitas Udayana

## Lisensi

Project ini dibuat untuk tujuan akademik dalam mata kuliah Sistem Temu Kembali Informasi (STKI). Dataset dan library eksternal mengikuti lisensi serta ketentuan penggunaan masing-masing sumber.

## Acknowledgements

- [FBref](https://fbref.com/) - sumber statistik pemain.
- [Transfermarkt](https://www.transfermarkt.com/) - sumber data profil dan valuasi pemain.
- [David Cariboo](https://www.kaggle.com/datasets/davidcariboo/player-scores) - Kaggle Transfermarkt dataset.
- [soccerdata](https://soccerdata.readthedocs.io/) - library scraping statistik sepak bola.
- [Neo4j](https://neo4j.com/) - graph database untuk Knowledge Graph.
- [ChromaDB](https://www.trychroma.com/) - vector store.
- [OpenAI](https://openai.com/) - LLM untuk reasoning dan answer synthesis.
- [RAGAS](https://docs.ragas.io/) - framework evaluasi RAG.

---

<p align="center">
  Dibuat dengan fokus pada kualitas retrieval, data provenance, dan dokumentasi yang rapi.
</p>

<p align="center">
  <a href="#troubleshooting">Troubleshooting</a> -
  <a href="#dokumentasi-api">Dokumentasi API</a> -
  <a href="#evaluasi-sistem">Evaluasi Sistem</a>
</p>

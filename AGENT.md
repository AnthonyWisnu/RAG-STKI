# AGENT.md

Operational instructions for Claude Code. Read this file completely before writing any code.

---

## Project Identity

**Project**: Sistem Tanya-Jawab Cerdas Berbasis Knowledge Graph dan RAG untuk Informasi Statistik dan Valuasi Pemain Sepak Bola
**Owner**: Anthony (Universitas Udayana, Teknologi Informasi, Sistem Informasi)
**Course**: Sistem Temu Kembali Informasi (STKI)
**Timeline**: 2 minggu

---

## Repository Structure

```
stki-football-rag/
├── AGENT.md                    # This file
├── DESIGN.md                   # UI/UX spec untuk frontend
├── README.md
├── .gitignore
│
├── backend/                    # Python, FastAPI, semua logic
│   ├── main.py                 # FastAPI app entry point
│   ├── requirements.txt
│   ├── .env.example
│   ├── config/
│   │   ├── settings.py         # Semua konstanta dan config
│   │   └── prompts/
│   │       ├── router_prompt.txt
│   │       ├── cypher_generator_prompt.txt
│   │       └── answer_synthesis_prompt.txt
│   ├── data/
│   │   ├── raw/                # Dataset Kaggle Transfermarkt
│   │   ├── processed/          # Data hasil cleansing
│   │   └── refresh_state.json  # State tracker ETL
│   ├── cache/
│   │   ├── fbref/              # Parquet cache per stat_type per season
│   │   ├── fbref_backup_*/     # Backup snapshot setelah initial setup
│   │   └── wiki/               # Wikipedia summary cache
│   ├── etl/
│   │   ├── initial_setup.py
│   │   ├── manual_refresh.py
│   │   ├── state_tracker.py
│   │   ├── kaggle_loader.py
│   │   ├── fbref_scraper.py
│   │   ├── sofascore_scraper.py
│   │   ├── player_id_mapper.py
│   │   ├── neo4j_loader.py
│   │   ├── document_generator.py
│   │   └── chroma_loader.py
│   ├── src/
│   │   ├── retrieval/
│   │   │   ├── kg_retriever.py
│   │   │   ├── vector_retriever.py
│   │   │   └── agentic_router.py
│   │   ├── valuation/
│   │   │   └── valuation_reasoner.py
│   │   ├── llm/
│   │   │   ├── openai_client.py
│   │   │   └── prompt_loader.py
│   │   └── utils/
│   │       ├── language_detect.py
│   │       └── citation.py
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py         # POST /api/chat
│   │   │   ├── players.py      # GET /api/players/*
│   │   │   ├── clubs.py        # GET /api/clubs/*
│   │   │   ├── compare.py      # POST /api/compare
│   │   │   ├── predict.py      # POST /api/predict
│   │   │   └── health.py       # GET /api/health
│   │   └── schemas/
│   │       ├── chat.py
│   │       ├── player.py
│   │       └── predict.py
│   ├── evaluation/
│   │   ├── ragas_eval.ipynb
│   │   ├── gold_queries.json
│   │   └── results.md
│   └── logs/
│
└── frontend/                   # Next.js app
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.js
    ├── components.json         # shadcn/ui config
    ├── .env.local.example
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx
    │   │   ├── page.tsx        # redirect ke /chat
    │   │   ├── chat/page.tsx
    │   │   ├── compare/page.tsx
    │   │   ├── search/page.tsx
    │   │   ├── valuation/page.tsx
    │   │   ├── predict/page.tsx
    │   │   ├── top/page.tsx
    │   │   └── club/page.tsx
    │   ├── components/
    │   │   ├── ui/             # shadcn/ui primitives
    │   │   ├── layout/
    │   │   │   ├── Sidebar.tsx
    │   │   │   ├── Header.tsx
    │   │   │   └── DataFreshnessBadge.tsx
    │   │   ├── chat/
    │   │   ├── player/
    │   │   ├── compare/
    │   │   └── charts/
    │   ├── lib/
    │   │   ├── api.ts          # fetch wrapper ke FastAPI
    │   │   └── utils.ts
    │   └── types/
    │       └── index.ts
    └── public/
```

---

## Tech Stack

| Layer | Teknologi |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, lucide-react |
| Backend API | FastAPI (Python 3.11) |
| Knowledge Graph | Neo4j (Aura Free atau Docker lokal) |
| Vector Store | ChromaDB (persistent, lokal) |
| LLM | OpenAI GPT-4o-mini |
| Embedding | sentence-transformers multilingual-e5-base (lokal, gratis) |
| Valuation Reasoning | LLM berbasis konteks KG/RAG, tanpa model ML terpisah |
| Stats Scraper | soccerdata 1.9 (FBref saja, Sofascore di-disable) |
| Valuasi Dataset | Kaggle Transfermarkt (David Cariboo) |
| Evaluasi | RAGAS + 20 gold queries |
| Charts | Recharts (frontend) |

---

## Scope Kompetisi dan Data

**Liga yang dicakup**: Premier League, La Liga, Serie A, Bundesliga, Ligue 1. Lima liga saja.
**UCL tidak dicakup.** Jika user tanya soal UCL, sistem menjawab "Data Champions League tidak tersedia dalam sistem ini."
**Musim**: 2023-2024, 2024-2025, 2025-2026 (tiga musim).
**Filter pemain masuk KG**: `minutes >= 400 OR matches_played >= 8 OR market_value_eur >= 30_000_000`.

---

## Data Sources

### 1. soccerdata FBref (Stats Pemain)

Pakai `soccerdata` library versi 1.9+. **Tidak ada API key, tidak ada biaya.**

> **Perubahan penting**: Sejak soccerdata 1.9.0, FBref memindahkan advanced stats ke Stathead Premium (berbayar). Hanya 4 stat_type publik yang tersedia: `standard`, `shooting`, `keeper`, `misc`. Stat_type `passing`, `gca`, `defense`, `possession`, `keeper_adv` tidak lagi bisa diakses.

```python
import soccerdata as sd

fbref = sd.FBref(
    leagues="Big 5 European Leagues Combined",
    seasons=["2023-2024", "2024-2025", "2025-2026"]
)

# Hanya 4 stat_type yang tersedia secara publik
df_standard  = fbref.read_player_season_stats(stat_type="standard")
df_shooting  = fbref.read_player_season_stats(stat_type="shooting")
df_misc      = fbref.read_player_season_stats(stat_type="misc")
df_keeper    = fbref.read_player_season_stats(stat_type="keeper")
```

**Rate limit wajib**: set env var `SOCCERDATA_DELAY=6` (6 detik antar request). Jangan disable. FBref akan IP-ban jika terlalu cepat.

**Caching**: soccerdata punya cache otomatis. Tambahkan project-level cache parquet di `backend/cache/fbref/{stat_type}_{season}.parquet` setelah scraping.

**Backup wajib**: setelah initial setup selesai, copy `cache/fbref/` ke `cache/fbref_backup_{timestamp}/`. Ini jaga-jaga kalau FBref ubah HTML mereka saat project berjalan.

### 2. soccerdata Sofascore (TIDAK AKTIF)

> **Perubahan penting**: Sejak soccerdata 1.9.0, fungsi `read_player_season_stats` untuk Sofascore dihapus dari library karena perubahan akses API Sofascore. Modul `etl/sofascore_scraper.py` tetap ada di codebase tetapi mengembalikan DataFrame kosong tanpa error. Kolom `sofascore_rating` di semua node `PlayerSeasonStats` akan bernilai `null`.

### 3. Kaggle Transfermarkt Dataset (Valuasi)

Dataset: "Football Data from Transfermarkt" oleh David Cariboo.

File yang dipakai:
- `players.csv`: profil dasar pemain (height, foot, birth_date, nationality)
- `clubs.csv`: nama dan metadata klub
- `competitions.csv`: mapping liga
- `player_valuations.csv`: history valuasi market value

Tidak ada API call. Download sekali via Kaggle API, simpan ke `backend/data/raw/`.

---

## Knowledge Graph Schema (Neo4j)

### Nodes

**Player**
```
api_id (int, unique, dari Transfermarkt)
fbref_id (string, untuk cross-reference)
name, birth_date, height_cm, preferred_foot, photo_url
nationality, is_active, last_updated
```

**Club**: api_id (unique), name, founded_year, logo_url, country
**League**: id (string, format "ENG-Premier League"), name, country
**Season**: id (string, format "2024-2025")
**Position**: id, name (Goalkeeper / Defender / Midfielder / Forward)
**Nationality**: id, country_name, country_code

**PlayerSeasonStats**
```
id: "{player_id}_{season}_{league_id}"
player_id, season_id, league_id, club_id, position

// Universal (standard)
matches_played, starts, minutes, nineties, yellow_cards, red_cards

// Attacking (standard, shooting)
goals, assists, non_penalty_goals, penalty_kicks, penalty_attempted
shots_total, shots_on_target, shots_on_target_pct
xg, non_penalty_xg, xg_per_shot, goals_minus_xg

// Misc
fouls_committed, fouls_drawn, offsides
aerial_won, aerial_lost, aerial_won_pct, ball_recoveries

// Goalkeeper (keeper)
goals_against, goals_against_per_90, saves, save_pct
clean_sheets, clean_sheet_pct
penalty_kicks_attempted_gk, penalty_kicks_allowed, penalty_kicks_saved

// Field berikut TIDAK TERSEDIA (advanced stats berbayar atau Sofascore di-disable):
// sofascore_rating, passes_completed, pass_completion_pct, progressive_passes,
// key_passes, passes_into_box, xa, sca, gca, touches, touches_att_pen,
// dribbles_completed, dribble_success_pct, progressive_carries, carries_into_box,
// tackles_total, tackles_won, interceptions, blocks_total, clearances, errors,
// psxg, psxg_minus_ga, pass_completion_long_pct, avg_pass_length

last_updated
```

**Valuation**: id "{player_id}_{date}", market_value_eur, valuation_date, source

### Relationships

```
(Player)-[:PLAYS_FOR {from_date, to_date, is_current}]->(Club)
(Club)-[:COMPETES_IN {season}]->(League)
(Player)-[:HAS_STATS_IN]->(PlayerSeasonStats)
(PlayerSeasonStats)-[:DURING]->(Season)
(PlayerSeasonStats)-[:WITH_CLUB]->(Club)
(PlayerSeasonStats)-[:IN_LEAGUE]->(League)
(Player)-[:HAS_VALUATION]->(Valuation)
(Player)-[:PLAYS_POSITION]->(Position)
(Player)-[:NATIONALITY_OF]->(Nationality)
(League)-[:HAS_SEASON]->(Season)
```

### Cypher Rules

1. **Selalu MERGE, jangan CREATE** untuk nodes dan relationships yang harus unik.
2. **Parameterized queries wajib** untuk semua input dari user (cegah Cypher injection).
3. **Soft delete**: set `is_active = false`, jangan hard delete.

---

## ETL Pipeline

### Filosofi 

ETL bersifat **idempotent dan flexible-schedule**. Tidak ada cron job. Pengembang jalankan manual kapan saja (kadang 5 hari, kadang 2 minggu). ETL aman dijalankan berulang kali.

Empat prinsip:
1. **Idempotent**: MERGE di Neo4j, upsert di ChromaDB via deterministik doc_id.
2. **State-aware**: baca dan tulis `data/refresh_state.json` di setiap run.
3. **Self-throttling**: tolak jika < 24 jam sejak refresh terakhir, kecuali `--force`.
4. **Change-driven**: valuation snapshot hanya di-insert jika nilai berubah dari snapshot terakhir.

### Initial Setup (sekali jalan)

Script: `backend/etl/initial_setup.py`

Urutan:
1. Download dataset Kaggle Transfermarkt ke `data/raw/`.
2. Fetch 4 stat_type FBref untuk 3 musim. Cache ke parquet. Estimasi waktu: 30-60 menit karena rate limit.
3. Sofascore di-skip (library tidak mendukung, return DataFrame kosong).
4. Join semua DataFrame berdasarkan player_id + season.
5. Aplikasikan filter relevansi pemain.
6. Map FBref player ID ke Transfermarkt player ID via `player_id_mapper.py`.
7. Insert ke Neo4j dengan MERGE.
8. Generate dokumen naratif per pemain (profil dari KG + Wikipedia summary).
9. Embed dengan multilingual-e5-base, upsert ke ChromaDB.
10. Validasi data valuasi dan siapkan konteks untuk LLM-based valuation reasoning.
11. Inisialisasi `data/refresh_state.json`.
12. Backup `cache/fbref/` ke `cache/fbref_backup_{timestamp}/`.

### Manual Refresh

Script: `backend/etl/manual_refresh.py`

Flags:
```bash
python etl/manual_refresh.py                    # normal refresh
python etl/manual_refresh.py --force            # bypass throttle 24 jam
python etl/manual_refresh.py --dry-run          # preview tanpa write
python etl/manual_refresh.py --only valuations  # skip FBref, hanya update valuasi
python etl/manual_refresh.py --only stats       # skip valuasi
python etl/manual_refresh.py --league "ENG-Premier League"  # satu liga
```

Langkah default:
1. Cek throttle state.
2. Re-download `player_valuations.csv` dari Kaggle.
3. Change-driven valuation upsert.
4. Fetch stats musim aktif (2025-2026) untuk 5 liga.
5. UPSERT PlayerSeasonStats.
6. Soft delete pemain yang tidak lolos filter.
7. Re-aktivasi pemain yang lolos filter lagi.
8. Re-embed dokumen yang stats-nya berubah signifikan (delta goals atau assists > 0).
9. Update `refresh_state.json`.

---

## Agentic Retrieval

### Alur Query

```
User input
    -> Language Detection (langdetect)
    -> LLM Call 1: Query Planner
        -> pilih strategi: kg_only / vector_only / hybrid / valuation_reasoning
    -> Execute retrieval
        kg_only:     LLM generate Cypher -> Neo4j -> rows
        vector_only: embed query -> ChromaDB similarity search -> top-k docs
        hybrid:      jalankan keduanya, gabungkan konteks
        valuation_reasoning: fetch stats + valuation history dari KG -> LLM estimasi range nilai
    -> LLM Call 2: Answer Synthesis
        -> generate jawaban dalam bahasa user (ID atau EN)
        -> sertakan citation (KG rows atau doc source)
    -> Return ke frontend
```

### Prompt Files

- `config/prompts/router_prompt.txt`: instruksi Query Planner pilih strategi
- `config/prompts/cypher_generator_prompt.txt`: instruksi text-to-Cypher dengan few-shot examples
- `config/prompts/answer_synthesis_prompt.txt`: instruksi NLG bilingual dengan citation format

### Fallback

1. Cypher error: retry maksimal 2 kali dengan error feedback ke LLM.
2. Cypher retry habis: fallback ke vector search.
3. Semua retrieval kosong: jawab "Data tidak tersedia dalam sistem."
4. User tanya UCL: jawab "Data Champions League tidak tersedia dalam sistem ini."

---

## FastAPI Backend

### Endpoints

```
GET  /api/health
     Response: { status, last_refresh, data_freshness_badge }

POST /api/chat
     Body: { query: string, history: Message[] }
     Response: { answer, strategy_used, citations, language }

GET  /api/players/search
     Query: position, league, season, min_minutes, min_value, max_value, q (nama)
     Response: { players: Player[], total }

GET  /api/players/{player_id}
     Response: { player, stats_by_season, valuation_history }

POST /api/compare
     Body: { player_ids: string[], season: string }
     Response: { players: PlayerDetail[], radar_data, narrative }

GET  /api/players/{player_id}/valuation-history
     Response: { valuations: Valuation[], trend_narrative }

POST /api/predict
     Body: { player_id: string, season: string }
     Response: { current_value, estimated_range, trend_direction, supporting_factors, explanation, citations }

GET  /api/top-performers
     Query: league, season, position, category, limit
     Response: { players: TopPerformer[] }

GET  /api/clubs/{club_id}
     Response: { club, squad, top_scorers, total_squad_value }
```

### CORS

Aktifkan CORS untuk `http://localhost:3000` (Next.js dev server).

### Response Caching

Pakai `functools.lru_cache` atau `cachetools.TTLCache` untuk endpoint yang sering dipanggil dengan parameter sama (terutama `/api/top-performers` dan `/api/players/search`). TTL 1 jam.

---

## LLM Valuation Reasoning

**File**: `backend/src/valuation/valuation_reasoner.py`

Tidak ada model ML terpisah untuk prediksi nilai pasar. Estimasi nilai pasar dijawab oleh LLM dengan konteks dari KG dan RAG. Fokus proyek tetap pada STKI, Knowledge Graph, retrieval, dan answer synthesis.

**Input konteks wajib dari KG**:

| Grup | Data |
|---|---|
| Valuation | nilai pasar terakhir, nilai tertinggi, nilai terendah, histori valuasi, arah tren |
| Profile | usia, tinggi, posisi, kewarganegaraan, kaki dominan, klub, liga |
| Volume | minutes, matches_played, starts, nineties |
| Attacking | goals, assists, non_penalty_goals, shots_total, shots_on_target, shots_on_target_pct |
| Goalkeeper | saves, save_pct, clean_sheets, goals_against, goals_against_per_90 |
| Discipline | yellow_cards, red_cards |

**Output `/api/predict`**:
```
{
  current_value,
  estimated_range: { min, max, currency },
  trend_direction,
  supporting_factors,
  explanation,
  citations
}
```

**Rules**:
1. Jangan klaim angka estimasi sebagai prediksi pasti.
2. Estimasi harus berupa range, misalnya `80M-95M EUR`, bukan satu angka tunggal.
3. Jawaban wajib menyebut nilai pasar terakhir dari Transfermarkt jika tersedia.
4. Jika data valuasi kosong, jawab bahwa estimasi tidak tersedia.
5. Jangan sebut statistik yang `null` atau tidak tersedia dari FBref publik.
6. Jangan menyebut xG, progressive passes, key passes, tackles, interceptions, atau statistik advanced lain jika tidak tersedia di konteks.
7. Untuk kiper, prioritaskan saves, save_pct, clean_sheets, goals_against, menit, usia, liga, dan tren valuasi.
8. Untuk outfield, prioritaskan menit, gol, assist, shots, shots_on_target_pct, usia, liga, posisi, dan tren valuasi.
9. Semua explanation harus memiliki citation dari KG rows atau dokumen ChromaDB.

---

## Vector Store (ChromaDB)

**Dokumen yang di-embed** (3 tipe per pemain):

1. **Profil auto-generated**: dibangun dari data KG. Template tersedia di `config/prompts/` untuk bahasa Indonesia dan Inggris. Diperbarui setiap refresh jika stats berubah.
2. **Wikipedia summary**: diambil via `wikipedia-api` library. Cache ke `cache/wiki/{player_id}.json`. Fallback ke profil KG saja jika tidak ditemukan.
3. **Narasi tren valuasi**: dibangun dari history Valuation nodes. Format: "Nilai pasar {nama} mengalami {naik/turun} dari {X} euro pada {tanggal} menjadi {Y} euro pada {tanggal}..."

**doc_id format** (deterministik, untuk upsert idempotent):
- `profile_{player_id}_v{hash_of_content}`
- `wiki_{player_id}`
- `valuation_{player_id}_v{hash_of_content}`

---

## Frontend Pages

Lihat `DESIGN.md` untuk detail layout, komponen, dan visual spec setiap halaman.

Tujuh halaman:
1. `/chat` - Tanya Jawab Bebas
2. `/compare` - Bandingkan Pemain
3. `/search` - Cari Pemain
4. `/valuation` - Analisis Valuasi
5. `/predict` - Estimasi Nilai Pasar
6. `/top` - Top Performers
7. `/club` - Profil Klub

---

## Environment Variables

### Backend (`backend/.env`)

```
OPENAI_API_KEY=sk-...
NEO4J_URI=neo4j+s://xxxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
KAGGLE_USERNAME=...
KAGGLE_KEY=...
CHROMA_PERSIST_DIR=./data/chroma
SOCCERDATA_DIR=./cache/soccerdata
SOCCERDATA_DELAY=6
LOG_LEVEL=INFO
```

### Frontend (`frontend/.env.local`)

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Common Commands

```bash
# Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows
pip install -r requirements.txt
cp .env.example .env

# Initial data load (jalankan sekali, estimasi 45-90 menit)
python etl/initial_setup.py

# Manual data refresh (jalankan kapan saja)
python etl/manual_refresh.py
python etl/manual_refresh.py --force
python etl/manual_refresh.py --dry-run

# Run backend
uvicorn main:app --reload --port 8000

# Frontend setup
cd frontend
npm install
cp .env.local.example .env.local

# Run frontend
npm run dev     # http://localhost:3000
```

---

## Coding Rules (NON-NEGOTIABLE)

1. **Tidak ada emoji di kode Python**, komentar, print, atau string. Ganti dengan teks deskriptif.
2. **Tidak ada emdash** di kode, komentar, atau dokumentasi. Ganti dengan koma, titik dua, atau titik.
3. **Type hints wajib** di semua function signature Python.
4. **Google-style docstrings** di semua public function.
5. **`pathlib.Path`** untuk semua file path, bukan string concat atau `os.path`.
6. **`logging` module**, bukan `print()`, untuk production code. `print()` hanya di `__main__` entry points.
7. **No hardcoded secrets**: semua dari `.env` via `python-dotenv`.
8. **MERGE, jangan CREATE** di semua Cypher insert.
9. **Parameterized Cypher** untuk semua input dari user.
10. **Idempotent ETL**: script bisa dijalankan ulang tanpa error atau duplikasi.
11. **Untuk frontend**: tidak ada emoji di UI. Gunakan icon dari `lucide-react`.
12. **Bahasa Indonesia** untuk komentar deskriptif, narasi, dan string yang user-facing. Bahasa Inggris untuk code, variable names, dan technical terms.

---

## Anti-Patterns

1. Jangan pakai `CREATE` di Cypher untuk node yang harus unik.
2. Jangan panggil OpenAI API di dalam loop tanpa caching.
3. Jangan load semua CSV Kaggle ke Neo4j tanpa filter relevansi terlebih dahulu.
4. Jangan buat file di luar struktur yang ada di dokumen ini tanpa konfirmasi.
5. Jangan tambah library baru tanpa konfirmasi ke user.
6. Jangan commit otomatis ke git. Tunggu instruksi user.
7. Jangan hardcode season "2025-2026" di banyak tempat. Pakai konstanta di `config/settings.py`.
8. Jangan sebut stats yang tidak relevan atau tidak tersedia saat LLM generate eksplanasi valuasi.
9. Jangan include UCL dalam scope apapun. Jika user tanya, sistem jawab tidak tersedia.

---

## How to Work: Workflow Per Sesi

1. Baca AGENT.md dari awal sampai akhir sebelum menulis kode apapun.
2. Identifikasi task yang diminta user, cocokkan dengan hari di timeline (lihat di bawah).
3. Sebutkan file apa saja yang akan dibuat atau dimodifikasi.
4. Implementasi.
5. Jalankan smoke test (`python -m {module}` atau `curl localhost:8000/api/health`).
6. Report singkat: apa yang selesai, file apa yang berubah, langkah selanjutnya.
7. **Stop dan tunggu konfirmasi** sebelum lanjut ke task berikutnya.

Jika diminta sesuatu yang tidak ada di AGENT.md, tanya user:
"Ini tidak ada di spec. Saya (a) tambahkan ke spec dulu baru implementasi, atau (b) implementasi langsung tanpa update spec?"

---

## Timeline (2 Minggu)

| Hari | Task |
|---|---|
| 1 | Setup repo, struktur folder, requirements.txt, .env.example, .gitignore, config/settings.py |
| 2 | Implementasi fbref_scraper.py, kaggle_loader.py dengan caching dan rate limit. Sofascore di-skip. |
| 3 | Implementasi player_id_mapper.py, neo4j_loader.py. Jalankan initial_setup.py. Validasi data di Neo4j Browser. |
| 4 | Implementasi document_generator.py (profil + Wikipedia), chroma_loader.py |
| 5 | Implementasi valuation_reasoner.py dan prompt estimasi valuasi berbasis LLM + KG/RAG. |
| 6 | Implementasi kg_retriever.py (text-to-Cypher), vector_retriever.py |
| 7 | Implementasi agentic_router.py. Integration test end-to-end retrieval. |
| 8 | Build FastAPI: main.py, semua routes, schemas, CORS, caching |
| 9 | Build frontend: layout, sidebar, halaman /chat |
| 10 | Build halaman /compare, /search |
| 11 | Build halaman /valuation, /predict |
| 12 | Build halaman /top, /club. Polishing UI. |
| 13 | RAGAS evaluation, 20 gold queries, buat evaluation/results.md |
| 14 | Finalisasi, README, video demo |

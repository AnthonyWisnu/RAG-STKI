# PLAN.md

Rencana implementasi 14 hari untuk proyek Sistem Tanya-Jawab Cerdas Berbasis Knowledge Graph dan RAG untuk Informasi Statistik dan Valuasi Pemain Sepak Bola.

Catatan kerja:
- Scope data hanya Premier League, La Liga, Serie A, Bundesliga, Ligue 1.
- UCL tidak masuk scope.
- Tidak menambah library baru tanpa konfirmasi.
- Setiap checkpoint bertanda "Ya" berarti pekerjaan berhenti dulu untuk konfirmasi sebelum lanjut.

---

## Dependency Utama

- Hari 1 harus selesai sebelum semua task backend dan frontend yang bergantung pada struktur repo, konfigurasi, dan environment.
- Hari 2 bergantung pada konfigurasi Hari 1.
- Hari 3 bergantung pada loader data Hari 2.
- Hari 4 bergantung pada data KG dari Hari 3.
- Hari 5 bergantung pada data KG dan valuation yang valid dari Hari 3.
- Hari 6 bergantung pada KG, ChromaDB, prompt, dan schema retrieval dari Hari 3 dan Hari 4.
- Hari 7 bergantung pada retriever Hari 6 dan valuation reasoner Hari 5.
- Hari 8 bergantung pada modul retrieval, valuation reasoner, dan data access dari Hari 3 sampai Hari 7.
- Hari 9 sampai Hari 12 bergantung pada API Hari 8 dan design tokens frontend.
- Hari 13 bergantung pada backend end-to-end dan minimal frontend smoke flow.
- Hari 14 bergantung pada semua fitur utama selesai dan terverifikasi.

---

### Hari 1: Setup Repo, Struktur, dan Konfigurasi Dasar

**Tasks:**
- [ ] Audit struktur repo aktual dan cocokkan dengan AGENT.md (30 menit)
- [ ] Buat struktur folder backend, frontend, data, cache, models, evaluation, dan logs yang belum ada (45 menit)
- [ ] Buat atau rapikan `.gitignore` untuk Python, Node, env, cache, model, dan data lokal (20 menit)
- [ ] Buat `backend/requirements.txt` sesuai stack yang disetujui tanpa library tambahan di luar spec (35 menit)
- [ ] Buat `backend/.env.example` dan `frontend/.env.local.example` (20 menit)
- [ ] Buat `backend/config/settings.py` untuk konstanta liga, musim, path, rate limit, dan env loading (60 menit)
- [ ] Buat prompt placeholder di `backend/config/prompts/` (30 menit)
- [ ] Buat kerangka `backend/main.py` minimal untuk health app readiness (30 menit)
- [ ] Smoke test import settings dan start FastAPI minimal bila dependency tersedia (30 menit)

**Files created/modified:**
- `.gitignore`
- `backend/main.py`
- `backend/requirements.txt`
- `backend/.env.example`
- `backend/config/settings.py`
- `backend/config/prompts/router_prompt.txt`
- `backend/config/prompts/cypher_generator_prompt.txt`
- `backend/config/prompts/answer_synthesis_prompt.txt`
- `frontend/.env.local.example`

**Checkpoint:** Ya - konfirmasi struktur repo, konstanta scope liga dan musim, serta daftar dependency sebelum masuk ETL.

**Risk:**
- Struktur repo aktual bisa berbeda dari spec. Mitigation: buat perubahan minimal dan laporkan deviasi sebelum lanjut.
- Dependency version conflict. Mitigation: pin versi inti sesuai spec dan uji import awal.

---

### Hari 2: FBref Scraper, Kaggle Loader, Caching, dan Rate Limit

**Tasks:**
- [ ] Implementasi utility path dan logging untuk ETL (30 menit)
- [ ] Implementasi `kaggle_loader.py` untuk validasi credential, download dataset, dan cek file wajib (90 menit)
- [ ] Implementasi `fbref_scraper.py` dengan `soccerdata` FBref, 4 stat_type publik, 3 musim, dan 5 liga (120 menit)
- [ ] Implementasi cache parquet project-level di `backend/cache/fbref/` (60 menit)
- [ ] Terapkan `SOCCERDATA_DELAY=6` dan validasi agar tidak bisa disable tanpa perubahan config eksplisit (30 menit)
- [ ] Implementasi `sofascore_scraper.py` sebagai stub DataFrame kosong tanpa error (30 menit)
- [ ] Tambahkan basic smoke test path download/cache dengan mode terbatas atau dry run bila memungkinkan (45 menit)

**Files created/modified:**
- `backend/etl/kaggle_loader.py`
- `backend/etl/fbref_scraper.py`
- `backend/etl/sofascore_scraper.py`
- `backend/etl/__init__.py`
- `backend/src/utils/__init__.py`
- `backend/config/settings.py`
- `backend/data/raw/`
- `backend/cache/fbref/`

**Checkpoint:** Tidak - lanjut ke mapping dan load KG, kecuali credential Kaggle atau akses FBref gagal.

**Risk:**
- Kaggle credential tidak tersedia. Mitigation: validasi jelas, dokumentasikan env yang kurang, dan siapkan error message yang actionable.
- FBref HTML atau rate limit berubah. Mitigation: cache parquet, delay 6 detik, retry konservatif, dan fallback ke cache jika tersedia.
- Advanced stats tidak tersedia. Mitigation: hanya scrape `standard`, `shooting`, `keeper`, `misc` sesuai spec.

---

### Hari 3: Player Mapping, Neo4j Loader, dan Initial Setup

**Tasks:**
- [ ] Implementasi cleansing dataset Transfermarkt dan normalisasi kolom utama (90 menit)
- [ ] Implementasi `player_id_mapper.py` untuk mapping FBref player ID ke Transfermarkt player ID (120 menit)
- [ ] Implementasi model transform untuk Player, Club, League, Season, Position, Nationality, PlayerSeasonStats, Valuation (120 menit)
- [ ] Implementasi `neo4j_loader.py` dengan MERGE, parameterized Cypher, constraint setup, dan soft delete support (150 menit)
- [ ] Implementasi `state_tracker.py` untuk `refresh_state.json` (60 menit)
- [ ] Implementasi `initial_setup.py` orkestrasi download, scrape, join, filter pemain, load Neo4j, dan backup cache FBref (180 menit)
- [ ] Jalankan initial setup atau dry run sesuai kesiapan credential dan Neo4j (45 sampai 90 menit, tidak termasuk scraping penuh)
- [ ] Validasi sample data di Neo4j Browser atau query smoke test (45 menit)

**Files created/modified:**
- `backend/etl/player_id_mapper.py`
- `backend/etl/neo4j_loader.py`
- `backend/etl/state_tracker.py`
- `backend/etl/initial_setup.py`
- `backend/etl/kaggle_loader.py`
- `backend/etl/fbref_scraper.py`
- `backend/config/settings.py`
- `backend/data/refresh_state.json`
- `backend/cache/fbref_backup_*/`

**Checkpoint:** Ya - wajib konfirmasi setelah ETL dan Neo4j sample data valid sebelum membuat dokumen ChromaDB.

**Risk:**
- Mapping pemain lintas sumber tidak akurat. Mitigation: gunakan kombinasi nama, birth_date, nationality, club, dan audit sample manual.
- Neo4j constraint atau MERGE salah bisa membuat duplikasi. Mitigation: setup constraint lebih dulu dan jalankan sample dry run.
- Initial setup lama karena FBref rate limit. Mitigation: gunakan cache parquet dan backup snapshot.

---

### Hari 4: Document Generator, Wikipedia Cache, dan ChromaDB Loader

**Tasks:**
- [x] Implementasi query KG untuk mengambil profil pemain dan stats ringkas (60 menit)
- [x] Implementasi template profil auto-generated Bahasa Indonesia dan Inggris (75 menit)
- [x] Implementasi Wikipedia summary fetch dengan cache `backend/cache/wiki/` dan fallback ke profil KG (90 menit)
- [x] Implementasi narasi tren valuasi dari node Valuation (60 menit)
- [x] Implementasi doc_id deterministik untuk profile, wiki, dan valuation docs (45 menit)
- [x] Implementasi `chroma_loader.py` dengan embedding multilingual-e5-base dan upsert idempotent (120 menit)
- [x] Smoke test embed beberapa pemain dan similarity search sederhana (60 menit)

**Files created/modified:**
- `backend/etl/document_generator.py`
- `backend/etl/chroma_loader.py`
- `backend/config/prompts/profile_template_id.txt`
- `backend/config/prompts/profile_template_en.txt`
- `backend/cache/wiki/`
- `backend/data/chroma/`
- `backend/config/settings.py`

**Checkpoint:** Tidak - lanjut ke valuation reasoning bila dokumen sample dan ChromaDB smoke test berhasil.

**Risk:**
- Wikipedia summary ambigu untuk pemain bernama mirip. Mitigation: cache hasil, gunakan metadata nationality/club untuk validasi bila memungkinkan, fallback ke profil KG.
- Embedding lokal lambat atau model belum terunduh. Mitigation: log progress dan batasi batch size.

---

### Hari 5: LLM Valuation Reasoning

**Tasks:**
- [x] Implementasi query context builder dari KG untuk valuation history, profil, klub, liga, posisi, dan stats publik (90 menit)
- [x] Implementasi kalkulasi ringkas: current value, highest value, lowest value, trend direction, value delta, dan per-90 stats yang tersedia (90 menit)
- [x] Implementasi `valuation_reasoner.py` untuk menyusun konteks dan memanggil LLM (120 menit)
- [x] Buat prompt valuation reasoning yang mewajibkan estimasi berbentuk range, bukan angka pasti (75 menit)
- [x] Implementasi citation untuk valuation rows dan stats rows yang dipakai reasoning (60 menit)
- [x] Implementasi fallback jika valuation history kosong atau data statistik terlalu minim (45 menit)
- [x] Smoke test estimasi untuk sample GK, DEF, MID, FWD (60 menit)

**Files created/modified:**
- `backend/src/valuation/valuation_reasoner.py`
- `backend/src/valuation/__init__.py`
- `backend/config/prompts/valuation_reasoning_prompt.txt`
- `backend/config/settings.py`

**Checkpoint:** Ya - wajib konfirmasi kualitas reasoning, format range estimasi, dan citation sebelum endpoint `/api/predict` dipakai API.

**Risk:**
- LLM terlalu percaya diri memberi angka pasti. Mitigation: prompt wajib range estimasi dan larangan klaim prediksi pasti.
- LLM menyebut statistik yang tidak tersedia. Mitigation: context builder hanya mengirim field non-null dan prompt melarang advanced stats yang tidak ada.
- Estimasi terlalu subjektif. Mitigation: selalu sertakan current value, trend direction, supporting factors, dan citations.

---

### Hari 6: KG Retriever dan Vector Retriever

**Tasks:**
- [x] Finalisasi `router_prompt.txt`, `cypher_generator_prompt.txt`, dan `answer_synthesis_prompt.txt` sesuai schema aktual (90 menit)
- [x] Implementasi OpenAI client wrapper dengan timeout, logging, dan no hardcoded secrets (60 menit)
- [x] Implementasi prompt loader (30 menit)
- [x] Implementasi language detection utility untuk ID atau EN (45 menit)
- [x] Implementasi `kg_retriever.py` dengan text-to-Cypher, parameterized execution, retry 2 kali, dan fallback signal (150 menit)
- [x] Implementasi `vector_retriever.py` dengan embedding query dan ChromaDB top-k search (90 menit)
- [x] Implementasi citation helper untuk KG rows dan Chroma docs (60 menit)
- [x] Smoke test pertanyaan KG-only dan vector-only (60 menit)

**Files created/modified:**
- `backend/src/llm/openai_client.py`
- `backend/src/llm/prompt_loader.py`
- `backend/src/llm/__init__.py`
- `backend/src/retrieval/kg_retriever.py`
- `backend/src/retrieval/vector_retriever.py`
- `backend/src/retrieval/__init__.py`
- `backend/src/utils/language_detect.py`
- `backend/src/utils/citation.py`
- `backend/config/prompts/router_prompt.txt`
- `backend/config/prompts/cypher_generator_prompt.txt`
- `backend/config/prompts/answer_synthesis_prompt.txt`

**Checkpoint:** Tidak - lanjut ke agentic router setelah retriever smoke test berhasil.

**Risk:**
- LLM menghasilkan Cypher invalid. Mitigation: schema prompt ketat, few-shot examples, retry dengan error feedback, fallback vector.
- Cypher injection dari user input. Mitigation: parameterized query wajib dan batasi generated clauses sesuai schema.

---

### Hari 7: Agentic Router dan End-to-End Retrieval

**Tasks:**
- [x] Implementasi query planner untuk strategi `kg_only`, `vector_only`, `hybrid`, dan `valuation_reasoning` (90 menit)
- [x] Implementasi orkestrasi `agentic_router.py` untuk eksekusi retrieval dan synthesis answer (150 menit)
- [x] Integrasi valuation reasoning path dari `valuation_reasoner.py` (60 menit)
- [x] Implementasi fallback UCL dengan jawaban tetap sesuai spec (30 menit)
- [x] Implementasi fallback semua retrieval kosong dengan pesan "Data tidak tersedia dalam sistem." (30 menit)
- [x] Integration test manual untuk minimal 12 query lintas strategi dan bilingual ID/EN (120 menit)

**Files created/modified:**
- `backend/src/retrieval/agentic_router.py`
- `backend/src/retrieval/kg_retriever.py`
- `backend/src/retrieval/vector_retriever.py`
- `backend/src/valuation/valuation_reasoner.py`
- `backend/config/prompts/router_prompt.txt`
- `backend/config/prompts/answer_synthesis_prompt.txt`

**Checkpoint:** Ya - konfirmasi kualitas jawaban retrieval, citation, dan fallback sebelum API publik dibuat.

**Risk:**
- Routing salah strategi untuk pertanyaan ambigu. Mitigation: prompt planner dengan examples, log strategy_used, dan expose di response API.
- Jawaban LLM menyebut stat yang tidak tersedia. Mitigation: prompt melarang advanced stats yang unavailable dan synthesis hanya memakai konteks retrieval.

---

### Hari 8: FastAPI Backend, Routes, Schemas, CORS, dan Caching

**Tasks:**
- [x] Implementasi FastAPI app setup, router registration, CORS localhost:3000, dan lifecycle config (60 menit)
- [x] Implementasi schemas Pydantic untuk chat, player, compare, predict, top performers, club (120 menit)
- [x] Implementasi `GET /api/health` dengan freshness badge (45 menit)
- [x] Implementasi `POST /api/chat` via agentic router (75 menit)
- [x] Implementasi `GET /api/players/search` dengan filters, pagination, sorting, dan TTL cache (120 menit)
- [x] Implementasi `GET /api/players/{player_id}` dan valuation history endpoint (90 menit)
- [x] Implementasi `POST /api/compare` dengan radar_data dan narrative (120 menit)
- [x] Implementasi `POST /api/predict` dengan current value, estimated range, trend direction, supporting factors, explanation, dan citations (90 menit)
- [x] Implementasi `GET /api/top-performers` dengan category mapping sesuai data tersedia (90 menit)
- [x] Implementasi `GET /api/clubs/{club_id}` dengan squad, top_scorers, total_squad_value (90 menit)
- [x] Smoke test semua endpoint dengan curl atau client script (120 menit)

**Files created/modified:**
- `backend/main.py`
- `backend/api/routes/health.py`
- `backend/api/routes/chat.py`
- `backend/api/routes/players.py`
- `backend/api/routes/clubs.py`
- `backend/api/routes/compare.py`
- `backend/api/routes/predict.py`
- `backend/api/routes/__init__.py`
- `backend/api/schemas/chat.py`
- `backend/api/schemas/player.py`
- `backend/api/schemas/predict.py`
- `backend/api/schemas/__init__.py`
- `backend/src/retrieval/agentic_router.py`
- `backend/config/settings.py`

**Checkpoint:** Ya - wajib konfirmasi setelah backend selesai dan semua endpoint smoke test sebelum frontend dibangun.

**Risk:**
- Endpoint lambat karena query KG atau LLM. Mitigation: cache endpoint search/top, batasi payload, dan gunakan async boundary yang jelas.
- Response shape berubah saat frontend mulai. Mitigation: freeze schema setelah checkpoint backend.

---

### Hari 9: Frontend Setup, Design Tokens, Layout, Shared Components, dan /chat

**Tasks:**
- [x] Setup Next.js App Router, TypeScript, Tailwind, shadcn/ui, lucide-react, Recharts, dan Framer Motion bila belum ada (90 menit)
- [x] Implementasi design tokens di `tailwind.config.js` dan `globals.css` tanpa hardcoded hex di komponen (90 menit)
- [x] Implementasi API wrapper `src/lib/api.ts` dan shared types (75 menit)
- [x] Implementasi global layout, Header, Sidebar, mobile bottom nav, dan DataFreshnessBadge (150 menit)
- [x] Implementasi shared components PlayerCard, StatBadge, PositionBadge, SectionHeading (120 menit)
- [x] Implementasi `/chat` split layout, message list, context panel, quick ask, textarea, strategy badge, citation dropdown, loading state, error state (180 menit)
- [x] Smoke test frontend dev server dan `/chat` against backend (60 menit)

**Files created/modified:**
- `frontend/package.json`
- `frontend/next.config.js`
- `frontend/tailwind.config.js`
- `frontend/components.json`
- `frontend/src/app/layout.tsx`
- `frontend/src/app/page.tsx`
- `frontend/src/app/globals.css`
- `frontend/src/app/chat/page.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/layout/Header.tsx`
- `frontend/src/components/layout/DataFreshnessBadge.tsx`
- `frontend/src/components/player/PlayerCard.tsx`
- `frontend/src/components/player/StatBadge.tsx`
- `frontend/src/components/player/PositionBadge.tsx`
- `frontend/src/components/ui/SectionHeading.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/utils.ts`
- `frontend/src/types/index.ts`

**Checkpoint:** Ya - konfirmasi tampilan dan flow `/chat` sebelum lanjut halaman berikutnya.

**Risk:**
- Visual tidak sesuai editorial data-dense. Mitigation: implement token dulu, review screenshot, hindari layout marketing.
- API belum running saat frontend test. Mitigation: gunakan error state jelas dan mock minimal hanya bila disetujui.

---

### Hari 10: Halaman /compare dan /search

**Tasks:**
- [x] Implementasi autocomplete player selector reusable dengan debounce dan max selection rules (90 menit)
- [x] Implementasi `/compare` player selector, stats header row, radar chart, stats accordion, dan narrative card (210 menit)
- [x] Implementasi radar normalization display sesuai posisi atau mixed comparison (90 menit)
- [x] Checkpoint visual dan fungsi `/compare` (30 menit)
- [x] Implementasi `/search` filter bar sticky, advanced filters, active chips, sort bar, PlayerCard list, pagination, dan empty state (210 menit)
- [x] Implementasi compare add button state sampai maksimal 4 pemain (45 menit)
- [x] Smoke test `/compare` dan `/search` desktop serta mobile basic (75 menit)

**Files created/modified:**
- `frontend/src/app/compare/page.tsx`
- `frontend/src/app/search/page.tsx`
- `frontend/src/components/compare/PlayerSelector.tsx`
- `frontend/src/components/compare/RadarComparison.tsx`
- `frontend/src/components/compare/StatsAccordion.tsx`
- `frontend/src/components/search/FilterBar.tsx`
- `frontend/src/components/search/AdvancedFilters.tsx`
- `frontend/src/components/search/ActiveFilterChips.tsx`
- `frontend/src/components/search/SortBar.tsx`
- `frontend/src/components/player/PlayerCard.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/types/index.ts`

**Checkpoint:** Ya - checkpoint setelah `/compare`, lalu checkpoint lagi setelah `/search`, karena user meminta konfirmasi setelah tiap halaman frontend.

**Risk:**
- Radar chart misleading untuk lintas posisi. Mitigation: gunakan mixed dimensions dan label jelas bahwa nilai dinormalisasi.
- Filter search kompleks bisa menghasilkan state bug. Mitigation: centralize filter state dan serialize query params secara konsisten.

---

### Hari 11: Halaman /valuation dan /predict

**Tasks:**
- [x] Implementasi `/valuation` player selector dan selected player mini card (60 menit)
- [x] Implementasi current, highest, lowest metric cards (60 menit)
- [x] Implementasi valuation line chart dengan tooltip dan reference line awal musim (120 menit)
- [x] Implementasi insight narrative card dan loading/error/empty states (60 menit)
- [x] Checkpoint visual dan fungsi `/valuation` (30 menit)
- [x] Implementasi `/predict` player selector, season selector, estimated range vs current value cards, dan trend summary (90 menit)
- [x] Implementasi supporting factors list dengan label "mendorong naik", "netral", atau "menahan naik" (120 menit)
- [x] Implementasi explanation card dan collapsible data context (75 menit)
- [x] Smoke test `/valuation` dan `/predict` desktop serta mobile basic (75 menit)

**Files created/modified:**
- `frontend/src/app/valuation/page.tsx`
- `frontend/src/app/predict/page.tsx`
- `frontend/src/components/charts/ValuationLineChart.tsx`
- `frontend/src/components/player/PlayerSelector.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/types/index.ts`

**Checkpoint:** Ya - checkpoint setelah `/valuation`, lalu checkpoint lagi setelah `/predict`.

**Risk:**
- Chart terlalu kosong untuk pemain dengan sedikit valuation history. Mitigation: tampilkan empty state deskriptif dan tetap tampilkan nilai saat ini bila ada.
- Explanation estimasi tidak position-specific. Mitigation: API dan UI hanya tampilkan faktor yang relevan sesuai posisi dan prompt melarang stat tidak relevan.

---

### Hari 12: Halaman /top, /club, dan Polishing UI

**Tasks:**
- [x] Implementasi `/top` filter bar sticky dengan kategori dinamis per posisi (75 menit)
- [x] Implementasi rankings table, sticky header, rank styling, export CSV, dan unavailable stats tooltip (150 menit)
- [x] Smoke test dan checkpoint `/top` (30 menit)
- [x] Implementasi `/club` selector dan club header (75 menit)
- [x] Implementasi tabs Squad, Top Scorer Musim Ini, dan Nilai Squad (180 menit)
- [x] Implementasi squad table sorting, position filter, top scorer bar chart, squad value donut chart (150 menit)
- [x] Smoke test dan checkpoint `/club` (30 menit)
- [x] Polishing responsive behavior, focus ring, skeleton loaders, error states, empty states, and animation timing (150 menit)
- [x] Final visual QA desktop, tablet, mobile untuk semua halaman (120 menit)

**Files created/modified:**
- `frontend/src/app/top/page.tsx`
- `frontend/src/app/club/page.tsx`
- `frontend/src/components/charts/TopScorerBarChart.tsx`
- `frontend/src/components/charts/SquadValueDonutChart.tsx`
- `frontend/src/components/top/TopPerformersTable.tsx`
- `frontend/src/components/club/ClubSelector.tsx`
- `frontend/src/components/club/ClubHeader.tsx`
- `frontend/src/components/club/SquadTable.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/types/index.ts`
- `frontend/src/app/globals.css`

**Checkpoint:** Ya - checkpoint setelah `/top`, checkpoint setelah `/club`, dan checkpoint akhir UI polish.

**Risk:**
- Tabel overflow dan filter sulit dipakai di mobile. Mitigation: horizontal scroll untuk tabel dan bottom sheet untuk filter mobile.
- Club data tidak lengkap dari Transfermarkt. Mitigation: fallback logo/name gracefully dan tampilkan data yang tersedia.

---

### Hari 13: RAGAS Evaluation dan Gold Queries

**Tasks:**
- [x] Susun 20 gold queries yang mencakup KG-only, vector-only, hybrid, valuation_reasoning, bilingual, dan UCL fallback (120 menit)
- [x] Implementasi notebook atau script evaluasi RAGAS sesuai dependency yang tersedia (120 menit)
- [x] Jalankan evaluasi terhadap backend running dan simpan hasil mentah (90 menit)
- [x] Analisis failure cases, terutama hallucination, citation kosong, wrong strategy, dan unavailable data handling (120 menit)
- [x] Buat `evaluation/results.md` dengan metrik, contoh jawaban baik, contoh gagal, dan rekomendasi perbaikan (120 menit)
- [x] Patch minor prompt atau retrieval jika evaluasi menemukan issue kecil dan terisolasi (90 menit)

**Files created/modified:**
- `backend/evaluation/ragas_eval.ipynb`
- `backend/evaluation/gold_queries.json`
- `backend/evaluation/results.md`
- `backend/config/prompts/router_prompt.txt`
- `backend/config/prompts/cypher_generator_prompt.txt`
- `backend/config/prompts/answer_synthesis_prompt.txt`

**Checkpoint:** Ya - konfirmasi hasil evaluasi dan daftar issue sebelum finalisasi.

**Risk:**
- RAGAS setup berat atau dependency bermasalah. Mitigation: siapkan fallback evaluasi manual terstruktur dengan gold queries dan rubric.
- Gold queries tidak representatif. Mitigation: pastikan mencakup semua strategi, posisi, liga, musim, dan negative case.

---

### Hari 14: Finalisasi, README, dan Demo

**Tasks:**
- [x] Audit akhir AGENT.md compliance: no emoji, no emdash, type hints, docstrings, pathlib, logging, parameterized Cypher (120 menit)
- [x] Audit frontend compliance: design tokens, lucide icons, Bahasa Indonesia, accessibility minimum, responsive behavior (120 menit)
- [x] Buat atau finalisasi README setup backend, frontend, ETL, refresh, dan troubleshooting (120 menit)
- [x] Buat demo script untuk alur chat, search, compare, valuation, predict, top, club (90 menit)
- [x] Jalankan smoke test akhir backend dan frontend (120 menit)
- [x] Rapikan notes residual risk dan known limitations (60 menit)
- [x] Siapkan checklist video demo tanpa membuat commit otomatis (60 menit)

**Files created/modified:**
- `README.md`
- `backend/evaluation/results.md`
- `PLAN.md`
- Potensi minor fixes di file backend atau frontend yang sudah dibuat sebelumnya

**Checkpoint:** Ya - konfirmasi final sebelum dianggap selesai dan sebelum commit apa pun bila user meminta commit.

**Risk:**
- Waktu final QA menemukan issue lintas modul. Mitigation: prioritaskan bug yang memblokir demo dan dokumentasikan known limitations.
- Environment user berbeda dari development. Mitigation: README detail, `.env.example` lengkap, dan smoke test commands eksplisit.

---

## Checkpoint Wajib

- Setelah Hari 1: struktur repo dan dependency disetujui.
- Setelah Hari 3: ETL initial setup dan sample data Neo4j valid.
- Setelah Hari 5: valuation reasoning selesai dan kualitas estimasi disetujui.
- Setelah Hari 7: retrieval end-to-end dan kualitas jawaban disetujui.
- Setelah Hari 8: backend API selesai dan response schema dibekukan.
- Setelah setiap halaman frontend:
  - `/chat`
  - `/compare`
  - `/search`
  - `/valuation`
  - `/predict`
  - `/top`
  - `/club`
- Setelah Hari 13: hasil evaluasi RAGAS atau fallback evaluation disetujui.
- Setelah Hari 14: final QA dan README disetujui.

---

## Risk Register Ringkas

- **FBref scraping gagal atau berubah HTML:** gunakan delay 6 detik, cache parquet, backup cache, dan fallback ke cache terakhir.
- **Kaggle credential tidak tersedia:** validasi env lebih awal dan pisahkan error setup dari error logic ETL.
- **Mapping pemain lintas sumber keliru:** audit sample manual dan confidence-based matching.
- **Neo4j duplikasi data:** constraint, MERGE, parameterized Cypher, dan dry run sample.
- **Advanced stats tidak tersedia:** UI, model, prompt, dan endpoint hanya memakai stat publik yang disetujui.
- **Estimasi valuasi terlalu spekulatif:** wajib gunakan range, current value, supporting factors, dan citation.
- **LLM hallucination:** synthesis hanya berbasis retrieved context, citation wajib, fallback jelas untuk data kosong.
- **Frontend menyimpang dari design aesthetic:** tokens lebih dulu, shared components lebih dulu, screenshot review per halaman.
- **Mobile table dan filter usability:** horizontal scroll, bottom sheet filter, dan QA breakpoint.
- **Waktu 2 minggu padat:** checkpoint membekukan schema dan visual sebelum lanjut agar tidak terjadi rework besar.

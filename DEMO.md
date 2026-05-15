# Demo Script

Checklist demo video untuk Football KG-RAG.

## Persiapan

- Backend berjalan di `http://127.0.0.1:8000`.
- Frontend berjalan di `http://127.0.0.1:3000`.
- Neo4j berisi data initial setup.
- ChromaDB berisi dokumen profile, wiki, dan valuation sample atau corpus penuh.
- Browser dibuka di halaman `/chat`.

## Alur Demo

### 1. Health dan Scope

Tunjukkan sidebar data freshness badge.

Pertanyaan:

```text
top scorer Champions League 2025-2026
```

Expected:

```text
Data Champions League tidak tersedia dalam sistem ini.
```

### 2. Chat KG-only

Pertanyaan:

```text
top skor Premier League 2025-2026
```

Tunjukkan:

- Strategy badge `Knowledge Graph`.
- Citation dropdown.
- Jawaban ranking top scorer.

### 3. Chat Vector-only

Pertanyaan:

```text
Profil Aaron Ramsdale
```

Tunjukkan:

- Strategy badge `Semantic Search`.
- Jawaban ringkasan dokumen.
- Citation dokumen.

### 4. Chat Hybrid

Pertanyaan:

```text
Jelaskan profil dan nilai pasar Aaron Ramsdale
```

Tunjukkan:

- Strategy badge `Hybrid`.
- Gabungan konteks KG dan dokumen.

### 5. Search

Buka `/search`.

Langkah:

- Cari `Pedri`.
- Filter liga atau posisi.
- Tambahkan pemain ke daftar bandingkan.

### 6. Compare

Buka `/compare`.

Langkah:

- Pilih minimal dua pemain.
- Klik `Bandingkan Pemain`.
- Tunjukkan radar chart dan stats accordion.

### 7. Valuation

Buka `/valuation`.

Langkah:

- Pilih `Aaron Ramsdale`.
- Tunjukkan nilai saat ini, tertinggi, terendah.
- Tunjukkan line chart histori valuasi.

### 8. Predict

Buka `/predict`.

Langkah:

- Pilih `Aaron Ramsdale`.
- Klik `Jalankan Estimasi`.
- Tunjukkan range estimasi, faktor pendukung, explanation, dan data context.

### 9. Top Performers

Buka `/top`.

Langkah:

- Pilih liga `Premier League`.
- Pilih kategori `Gol`.
- Tunjukkan ranking table dan export CSV.

### 10. Club

Buka `/club`.

Langkah:

- Cari `Newcastle`.
- Tunjukkan club header.
- Tunjukkan tab Squad, Top Scorer Musim Ini, dan Nilai Squad.

## Penutup Demo

Tunjukkan `backend/evaluation/results.md`.

Poin akhir:

- 20 gold queries.
- 20 passed.
- Citation pass rate 100%.
- UCL fallback berhasil.
- Sistem tidak menampilkan statistik yang tidak tersedia sebagai angka palsu.

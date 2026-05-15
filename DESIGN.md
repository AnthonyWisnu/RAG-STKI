# DESIGN.md

UI/UX specification for the football KG-RAG frontend.
Read this file alongside AGENT.md before writing any frontend code.

---

## Design Direction

**Tone**: Data-dense editorial. Think sports analytics dashboard meets investigative journalism.
Bukan dashboard korporat yang generik. Bukan dark mode biru-ungu klise.

**Inspirasi visual**: Opta Stats, FBref.com (dense tapi readable), The Athletic (editorial, typography-first).

**Differentiator**: Typographic hierarchy yang kuat + data table yang bersih + aksen hijau electric pada dark base. Terasa seperti alat profesional yang dipakai scout sepak bola sungguhan, bukan project mahasiswa biasa.

**Unforgettable detail**: Setiap card pemain punya thin colored bar di sisi kiri yang warnanya berbeda per posisi (goalkeeper: kuning amber, defender: biru cobalt, midfielder: hijau electric, forward: merah oranye). Konsisten di seluruh aplikasi.

---

## Tech Stack Frontend

```
Next.js 14 (App Router)
TypeScript
Tailwind CSS
shadcn/ui (komponen primitif)
lucide-react (icons, TIDAK ADA emoji)
Recharts (charts)
Framer Motion (animasi transisi halaman dan micro-interaction)
```

---

## Design Tokens

Semua token didefinisikan di `tailwind.config.js` dan `globals.css`. Claude Code wajib pakai token ini, jangan hardcode warna hex di komponen.

### Warna

```css
:root {
  /* Base */
  --color-bg-primary:     #0a0e13;   /* Almost black, slight blue tint */
  --color-bg-secondary:   #111720;   /* Card background */
  --color-bg-tertiary:    #1a2235;   /* Elevated surface, hover */
  --color-border:         #1e2d45;   /* Subtle border */
  --color-border-bright:  #2a3f5f;   /* Active border */

  /* Text */
  --color-text-primary:   #e8edf5;   /* Body text */
  --color-text-secondary: #7a8fa8;   /* Secondary label */
  --color-text-muted:     #445569;   /* Placeholder, disabled */

  /* Accent */
  --color-accent:         #00e676;   /* Electric green, primary CTA */
  --color-accent-dim:     #00e67620; /* Green with opacity, background glow */
  --color-accent-hover:   #00ff85;   /* Brighter on hover */

  /* Position colors (used as left-border indicator on cards) */
  --color-pos-gk:  #f59e0b;  /* Amber */
  --color-pos-def: #3b82f6;  /* Blue */
  --color-pos-mid: #00e676;  /* Green (same as accent) */
  --color-pos-fwd: #f97316;  /* Orange */

  /* Status */
  --color-fresh:   #00e676;  /* Data badge: fresh (<= 7 days) */
  --color-stale:   #f59e0b;  /* Data badge: mulai lama (7-14 days) */
  --color-old:     #ef4444;  /* Data badge: data lama (> 14 days) */

  /* Chart colors */
  --chart-1: #00e676;
  --chart-2: #3b82f6;
  --chart-3: #f97316;
  --chart-4: #a855f7;
  --chart-5: #f59e0b;
}
```

### Tipografi

```css
/* Import di globals.css */
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Barlow+Condensed:wght@600;700&family=Inter:wght@400;500&display=swap');

--font-display:  'Barlow Condensed', sans-serif;  /* Heading utama, angka besar, nama pemain */
--font-body:     'Inter', sans-serif;              /* Body text, label */
--font-mono:     'DM Mono', monospace;             /* Angka stats, nilai, rating */
```

Scale:
- `text-xs` (11px): label kolom tabel, badge kecil
- `text-sm` (13px): body text, description
- `text-base` (15px): default
- `text-lg` (18px): card subtitle
- `text-2xl` (24px): section heading
- `text-4xl` (36px): display number (nilai pasar, angka utama)
- `text-6xl` (60px): hero number (kalau ada)

---

## Layout Global

### Shell

```
+--sidebar (64px collapsed / 240px expanded)--+--main content--+
|                                              |                |
|  Logo                                        | Header         |
|  -----                                       | (breadcrumb,   |
|  Nav items                                   |  search bar)   |
|                                              |                |
|  [collapsed: icons only]                     | Page content   |
|  [expanded: icon + label]                    |                |
|                                              |                |
|  -----                                       |                |
|  Data freshness badge                        |                |
+----------------------------------------------+----------------+
```

**Sidebar** collapsible. Default collapsed di mobile, expanded di desktop.
Sidebar background: `var(--color-bg-secondary)`.
Border kanan: `1px solid var(--color-border)`.

**Header** (top bar per halaman): tinggi 56px, sticky, blur backdrop.
Background: `rgba(10, 14, 19, 0.85)` dengan `backdrop-filter: blur(12px)`.

### Sidebar Nav Items

Urutan menu:

| Icon (lucide-react) | Label | Route |
|---|---|---|
| `MessageSquare` | Tanya Jawab | /chat |
| `Users` | Bandingkan | /compare |
| `Search` | Cari Pemain | /search |
| `TrendingUp` | Analisis Valuasi | /valuation |
| `Sparkles` | Estimasi Nilai | /predict |
| `Trophy` | Top Performers | /top |
| `Shield` | Profil Klub | /club |

Active state: background `var(--color-accent-dim)`, left border `2px solid var(--color-accent)`, text color `var(--color-accent)`.

Hover state: background `var(--color-bg-tertiary)`.

**DataFreshnessBadge** di bagian bawah sidebar:
- Dot berwarna + label "Data {n} hari lalu"
- Dot hijau: fresh, dot kuning: mulai lama, dot merah: data lama
- Klik membuka modal info terakhir refresh + tombol instruksi refresh manual

---

## Komponen Shared

### PlayerCard

Dipakai di search results, compare list, top performers.

```
+----------------------------------------------------+
| [pos bar] [photo 48x48]  NAMA PEMAIN               |
|           Klub - Liga                              |
|           Posisi  |  Usia  |  Nilai Pasar          |
+----------------------------------------------------+
```

- Left border `4px` dengan warna posisi (`--color-pos-*`).
- Foto: circle, fallback silhouette icon kalau tidak ada URL.
- Nama: `font-display`, `text-lg`, `text-text-primary`.
- Klub-Liga: `text-sm`, `text-text-secondary`.
- Stats row: `font-mono`, `text-sm`.
- Background: `var(--color-bg-secondary)`.
- Hover: `var(--color-bg-tertiary)` dengan smooth transition 150ms.

### StatBadge

Chip kecil untuk satu angka stat dengan label.

```
[ LABEL ]
[ 1.34  ]
```

- Font mono untuk angka.
- Warna background transparan dengan border `var(--color-border)`.
- Ukuran: compact, bisa di-stack horizontal.

### PositionBadge

```
[ GK ] [ DEF ] [ MID ] [ FWD ]
```

Background warna posisi dengan opacity 20%, text warna posisi penuh.

### SectionHeading

```
JUDUL SEKSI ────────────────────────
```

Uppercase, `font-display`, `text-xs` tracking-widest, diikuti garis horizontal tipis ke kanan sampai ujung container.

---

## Halaman Per Halaman

---

### 1. /chat - Tanya Jawab

**Layout**: Split dua kolom di desktop, full width di mobile.

Kiri (65%): area percakapan.
Kanan (35%): panel konteks (collapsible di mobile).

**Area percakapan**:
- Message list, scroll ke bawah.
- User message: bubble kanan, background `var(--color-bg-tertiary)`, border radius 16px 16px 4px 16px.
- Assistant message: bubble kiri, background transparan dengan border `var(--color-border)`, border radius 16px 16px 16px 4px.
- Di bawah setiap assistant message: badge strategi retrieval yang dipakai.

**Badge strategi retrieval**:

| Strategi | Icon | Label | Warna |
|---|---|---|---|
| kg_only | `Database` | Knowledge Graph | Biru |
| vector_only | `FileSearch` | Semantic Search | Ungu |
| hybrid | `Layers` | Hybrid | Hijau |
| valuation_reasoning | `Sparkles` | LLM Valuasi | Amber |

- Badge ukuran kecil, di bawah bubble, tidak mencolok.

**Citation section** (jika ada): dropdown collapsible kecil "Lihat sumber" yang menampilkan rows dari KG atau dokumen dari ChromaDB yang dipakai.

**Input area** (sticky bottom):
- Textarea auto-resize (max 4 baris).
- Tombol kirim: `ArrowUp` icon di dalam textarea kanan bawah.
- Background: `var(--color-bg-secondary)`, border `var(--color-border)`.
- Focus: border berubah ke `var(--color-accent)`.
- Placeholder: "Tanya tentang pemain, statistik, atau valuasi..."

**Panel konteks** (kanan):
- "Contoh Pertanyaan" dengan tombol quick-ask:
  - "Siapa top scorer La Liga musim ini?"
  - "Bagaimana gaya bermain Pedri?"
  - "Bandingkan Salah dan Son sebagai winger"
  - "Berapa estimasi nilai pasar Yamal?"
- Klik quick-ask langsung isi input dan kirim.
- "Riwayat percakapan" section di bawahnya (baru ada kalau ada riwayat).

**Loading state**: animated typing indicator (tiga dot bergerak), bukan spinner.

---

### 2. /compare - Bandingkan Pemain

**Layout**: Full width dengan sections vertikal.

**Section 1: Player Selector**

- Input autocomplete untuk search pemain (min 3 karakter).
- Maksimal 4 pemain.
- Selected pemain ditampilkan sebagai chip dengan foto dan tombol X.
- Dropdown autocomplete: background `var(--color-bg-secondary)`, border, shadow.

**Section 2: Stats Header Row** (setelah minimal 2 pemain dipilih)

Tabel horizontal, setiap kolom = 1 pemain:

```
                    [Foto] Bellingham      [Foto] Pedri
                    Real Madrid - DEF      Barcelona - MID
Nilai Pasar         180M EUR               90M EUR
Rating              7.8                    7.6
Menit               2.890                  2.340
```

Warna header kolom sesuai warna posisi pemain.
Baris "Rating" dihapus karena Sofascore rating tidak tersedia. Untuk outfield, ganti dengan "Shots on Target %" jika tersedia.

**Section 3: Radar Chart**

- Recharts RadarChart.
- Dimensi radar berdasarkan stats yang tersedia dari FBref publik:
  - **Forward**: Gol/90, Assist/90, Shots/90, Shots on Target/90, Shots on Target %, Menit Bermain (normalized)
  - **Midfielder**: Gol/90, Assist/90, Shots/90, Shots on Target %, Fouls Drawn/90, Menit Bermain (normalized)
  - **Defender**: Menit Bermain (normalized), Starts %, Fouls Drawn/90, Gol/90, Assist/90, Kartu per 90 (inverted)
  - **Goalkeeper**: Save %, Clean Sheet %, Gol Kemasukan/90 (inverted), Penalty Saved, Penampilan, Menit Bermain (normalized)
  - **Lintas posisi (Mixed)**: Gol/90, Assist/90, Shots on Target %, Fouls Drawn/90, Menit Bermain (normalized), Kartu per 90 (inverted)
- Setiap pemain punya warna dari `--chart-1`, `--chart-2`, dst.
- Legend di bawah.
- Semua nilai di-normalize ke skala 0-1 (percentile di antara semua pemain posisi sama) sebelum ditampilkan di radar, supaya perbandingan fair.

**Section 4: Stats Detail Accordion**

Accordion per kategori: Attacking, Shooting, Misc, Goalkeeping, Discipline.
Tiap kategori expand menjadi tabel baris = stat, kolom = pemain.
Nilai yang lebih tinggi di-highlight bold dengan warna aksen.

Catatan: kategori Creating (key passes, progressive passes, xA), Expected Goals (xG), Aerial, Ball Recoveries, dan Defending (tackles, interceptions, blocks) tidak ditampilkan jika nilainya `null` karena data tidak tersedia dari sumber publik FBref.

**Section 5: Narasi Komparatif**

Card dengan background `var(--color-bg-secondary)`, teks naratif dari LLM.
Icon `MessageSquare` kecil di kiri atas card.

---

### 3. /search - Cari Pemain

**Layout**: Full width. Filter inline di atas, results di bawah.

**Filter Bar Baris 1** (sticky di bawah header saat scroll):

```
[ Cari nama...  ] [ Posisi v ] [ Liga v ] [ Musim v ] [ Usia: 18-35 ] [ Nilai Pasar: 0-200M ] [ Menit Min: 0 ]  [SlidersHorizontal] Filter Lanjutan
```

- Search nama: input teks dengan icon `Search` di kiri, auto-debounce 300ms.
- Posisi, Liga, Musim: dropdown kompak (shadcn/ui Select).
- Usia, Nilai Pasar, Menit: masing-masing tampil sebagai chip teks yang bisa diklik untuk buka range input kecil (popover).
- Tombol "Filter Lanjutan" di ujung kanan: toggle expand/collapse filter posisi-spesifik.
- Background filter bar: `var(--color-bg-secondary)` dengan border bawah tipis. Blur backdrop saat sticky.

**Filter Lanjutan** (expandable, muncul di bawah baris 1 saat di-toggle):

```
+------------------------------------------------------------------+
| Tampil otomatis sesuai posisi yang dipilih:                      |
|                                                                  |
| (Goalkeeper)  Min Save %: [__]                                   |
| (Defender)    Min Menit: [__]                                    |
| (Midfielder)  Min Assists: [__]                                  |
| (Forward)     Min Gol/90: [__]                                   |
|                                                                  |
| [Terapkan]   [Reset Semua]                                       |
+------------------------------------------------------------------+
```

- Muncul dengan animasi slide-down (Framer Motion, duration 200ms).
- Jika posisi belum dipilih, tampilkan semua filter dengan label posisi di kirinya.
- Jika posisi sudah dipilih, hanya tampilkan filter untuk posisi itu.
- Tombol "Reset Semua" clear semua filter dan kembalikan ke default.

**Active Filter Chips** (di bawah filter bar, hanya muncul kalau ada filter aktif):

```
[ Liga: EPL x ]  [ Posisi: Forward x ]  [ Usia: 20-26 x ]  [ Reset Semua ]
```

Chip kecil dengan tombol X untuk hapus filter satu per satu. Background `var(--color-accent-dim)`, border `var(--color-accent)`.

**Sort Bar** (di atas results, di bawah chips):

```
Menampilkan 47 dari 312 pemain   |   Urutkan: [ Nilai Pasar v ]  [ Desc v ]
```

**Results** (di bawah sort bar):

- PlayerCard list, full width, bukan grid.
- Setiap card menampilkan: foto, nama, klub, liga, posisi badge, usia, menit, nilai pasar, dan 1-2 stat relevan sesuai posisi.
- Pagination 20 per halaman di bagian bawah (shadcn/ui Pagination).
- Tombol "Tambah ke Bandingkan" di tiap card, disabled dan berubah jadi "Sudah ditambahkan" kalau sudah 4 pemain.

**Empty state**: icon `SearchX` + teks "Tidak ada pemain yang cocok dengan filter ini." + tombol "Reset Semua Filter".

---

### 4. /valuation - Analisis Valuasi

**Layout**: Pilih pemain di atas, konten di bawah.

**Player Selector** (atas): autocomplete search + PlayerCard mini setelah dipilih.

**Section 1: Nilai Saat Ini**

Tiga metric card horizontal:

```
[ Nilai Saat Ini ]   [ Nilai Tertinggi ]   [ Nilai Terendah ]
  180M EUR              200M EUR               45M EUR
  (tanggal update)      (tanggal)              (tanggal)
```

**Section 2: Line Chart Tren Valuasi**

- Recharts LineChart.
- X-axis: tanggal valuasi.
- Y-axis: nilai dalam juta EUR.
- Line warna `var(--color-accent)`.
- Tooltip menampilkan tanggal + nilai eksak.
- Area fill di bawah line dengan opacity 10%.
- Tambahkan referensi vertical line untuk setiap awal musim baru (annotasi "2023/24", "2024/25", "2025/26").

**Section 3: Insight Naratif**

Card teks dari LLM. Jelaskan tren, faktor musim, konteks transfer jika ada.

---

### 5. /predict - Estimasi Nilai Pasar

**Layout**: Pilih pemain, lalu hasil estimasi berbasis LLM + KG/RAG.

**Player Selector** + **Season Selector**.

**Section 1: Estimasi vs Nilai Saat Ini**

```
+------------------------+    +------------------------+
|  ESTIMASI WAJAR        |    |  NILAI SAAT INI        |
|  180M-210M EUR         |    |  200M EUR              |
|  LLM + KG/RAG          |    |  Transfermarkt         |
+------------------------+    +------------------------+
         Arah tren: stabil tinggi
```

Dua card berdampingan. Warna estimasi: `var(--color-accent)`. Warna nilai saat ini: `text-text-secondary`.

**Section 2: Faktor Pendukung**

List faktor berbasis evidence dari KG:
- Tren valuasi terakhir
- Usia dan fase karier
- Menit bermain dan starts
- Gol, assist, shots, shots on target untuk outfield
- Save %, clean sheets, goals against untuk kiper
- Liga, klub, dan posisi

Setiap faktor punya label arah: "mendorong naik", "netral", atau "menahan naik". Jangan tampilkan faktor yang datanya `null`.

**Section 3: Eksplanasi LLM**

Card editorial dengan teks eksplanasi dari LLM. Konteks posisi pemain harus benar dan berbasis citation.
Icon `Sparkles` di header card.

**Data yang Dipakai** (collapsible): tampilkan valuation history, profil, dan stats publik yang dipakai LLM sebagai konteks.

---

### 6. /top - Top Performers

**Layout**: Filter horizontal di atas, tabel di bawah.

**Filter Bar** (horizontal, sticky di bawah header):

```
Liga: [All v]   Musim: [2025/26 v]   Posisi: [All v]   Kategori: [Goals/90 v]
```

Dropdown filter, horizontal, compact. Background `var(--color-bg-secondary)`.

**Tabel Rankings**:

```
# | Foto | Nama               | Klub      | Liga | Stat Utama | Menit
1   [img]  Kylian Mbappe        R.Madrid   LaLiga  0.91         2810
2   [img]  Erling Haaland       Man City   EPL     0.87         2650
```

- Kolom `#` dengan background warna berbeda untuk rank 1, 2, 3 (gold, silver, bronze via warna text).
- Foto: circle 32px.
- Nama: `font-display`.
- Stat utama: `font-mono`, `text-accent` (angka yang diunggulkan).
- Hover row: background `var(--color-bg-tertiary)`.
- Sticky header kolom.
- Kategori yang tersedia dinamis berdasarkan posisi:

| Posisi | Pilihan Kategori |
|---|---|
| All | Menit Bermain, Gol, Assist, Gol + Assist |
| Goalkeeper | Save %, Clean Sheet %, Gol Kemasukan/90 |
| Defender | Menit Bermain, Starts, Fouls Drawn/90, Kartu per 90 |
| Midfielder | Assist, Gol, Shots on Target %, Fouls Drawn/90 |
| Forward | Gol/90, Assist/90, Shots/90, Shots on Target % |

Catatan: kategori berbasis xG, aerial, ball recoveries, tackles, interceptions, key passes, dan progressive passes tidak tersedia jika field bernilai `null` karena data tidak bisa diakses dari FBref publik. Tampilkan tooltip info kecil di header filter "Beberapa statistik lanjutan tidak tersedia karena keterbatasan data publik." jika user hover icon `Info` di sebelah label filter Kategori.

**Export CSV**: tombol `Download` icon di kanan atas tabel.

---

### 7. /club - Profil Klub

**Layout**: Header klub di atas, tabs di bawah.

**Club Selector**: dropdown atau autocomplete search nama klub.

**Header Klub**:

```
+--logo (64x64)--+--NAMA KLUB----------------------------------+
|                |  Liga - Negara                             |
|                |  Didirikan: XXXX                           |
+----------------+--------------------------------------------+
```

Background card dengan subtle gradient dari warna posisi yang dominan di squad.

**Tabs**:

Tab 1: **Squad**
- Tabel semua pemain aktif di klub.
- Kolom: foto, nama, posisi, usia, nilai pasar, menit, gol, assist.
- Dapat di-sort per kolom.
- Filter per posisi di atas tabel.

Tab 2: **Top Scorer Musim Ini**
- Bar chart horizontal top-10 pemain berdasarkan goals.
- Bar warna sesuai posisi pemain.

Tab 3: **Nilai Squad**
- Total nilai squad dalam EUR (format besar: "412.5M EUR").
- Donut chart distribusi nilai per posisi (Recharts PieChart).
- Tabel sorted by nilai pasar desc.

---

## States dan Feedback

### Loading States

- **Skeleton loader**: untuk semua card dan tabel. Pakai `animate-pulse` Tailwind.
- **Jangan pakai spinner besar** di tengah halaman. Gunakan skeleton yang sesuai bentuk konten.
- **Untuk chat**: typing indicator tiga dot bergerak.

### Error States

```
[AlertCircle icon]
Terjadi kesalahan saat mengambil data.
Coba lagi
```

Card sederhana, jangan modal. Tombol "Coba lagi" dengan retry logic.

### Empty States

- Konten deskriptif, bukan hanya "Tidak ada data".
- Contoh: "Belum ada pemain yang dipilih. Gunakan pencarian di atas untuk mulai membandingkan."
- Icon kontekstual dari lucide-react.

---

## Animasi dan Transisi

Pakai Framer Motion untuk:

1. **Page transition**: fade + slide up kecil (8px) saat navigasi antar halaman. Duration 200ms.
2. **Card entrance**: stagger reveal saat list card muncul. Setiap card delay 30ms.
3. **Chart entrance**: bar dan line chart animasi masuk saat pertama kali render (Recharts supports `isAnimationActive`).
4. **Sidebar expand/collapse**: smooth width transition 200ms ease-out.
5. **Accordion**: smooth height transition.

Jangan berlebihan. Satu animasi yang tepat lebih baik dari banyak yang mengganggu.

---

## Responsivitas

| Breakpoint | Behavior |
|---|---|
| < 768px (mobile) | Sidebar hilang, pakai bottom nav 5 icon. Filter panel jadi sheet dari bawah. |
| 768-1024px (tablet) | Sidebar collapsed (icon only). Tabel scroll horizontal. |
| >= 1024px (desktop) | Layout penuh seperti spec di atas. |

---

## Aksesibilitas Minimum

1. Semua interactive element punya `aria-label` yang deskriptif.
2. Color tidak boleh satu-satunya carrier informasi (gunakan icon + warna, bukan hanya warna).
3. Focus ring visible: `outline: 2px solid var(--color-accent)` dengan `outline-offset: 2px`.
4. Contrast ratio teks primer di atas background: minimal 4.5:1.

---

## Icon Reference

Semua icon dari `lucide-react`. Tidak ada emoji. Tidak ada icon library lain.

| Konteks | Icon |
|---|---|
| Menu Tanya Jawab | `MessageSquare` |
| Menu Bandingkan | `Users` |
| Menu Cari | `Search` |
| Menu Valuasi | `TrendingUp` |
| Menu Estimasi Nilai | `Sparkles` |
| Menu Top Performers | `Trophy` |
| Menu Profil Klub | `Shield` |
| Download/Export | `Download` |
| Filter | `SlidersHorizontal` |
| Sort | `ArrowUpDown` |
| Kirim chat | `ArrowUp` |
| Hapus | `X` |
| Info | `Info` |
| Alert/Error | `AlertCircle` |
| Database (KG badge) | `Database` |
| Semantic Search badge | `FileSearch` |
| Hybrid badge | `Layers` |
| LLM Valuasi badge | `Sparkles` |
| Data fresh | `CheckCircle` |
| Data lama | `AlertTriangle` |
| Goalkeeper | `HandMetal` (atau `Shield`) |
| Defender | `Shield` |
| Midfielder | `Zap` |
| Forward | `Flame` |

---

## Catatan untuk Claude Code

1. Baca AGENT.md untuk context data dan API. Baca DESIGN.md ini untuk semua keputusan visual.
2. Implementasi design tokens di `tailwind.config.js` dan `src/app/globals.css` sebelum membangun komponen apapun.
3. Bangun shared components (`PlayerCard`, `StatBadge`, `PositionBadge`, `SectionHeading`, `DataFreshnessBadge`) sebelum halaman spesifik.
4. Pakai `lucide-react` untuk semua icon. Tidak ada emoji di JSX.
5. Semua fetch ke backend via `src/lib/api.ts` wrapper, jangan fetch langsung di komponen.
6. TypeScript strict: tidak ada `any` kecuali benar-benar tidak bisa dihindari.
7. Semua teks label dan string user-facing dalam Bahasa Indonesia.
8. Semua variable, function, dan type names dalam Bahasa Inggris.

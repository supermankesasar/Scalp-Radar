# Scalp Radar v0.5 — Top 5 Scalp Watchlist

**Fase 1 · Binance USDⓈ-M Futures · read-only · tanpa Binance API key · tidak mengirim order.**

v0.4 memperbaiki pembatas v0.3 yang menghasilkan 69 pair karena mode **Top 80 + minimum turnover $30 juta**. Sekarang **ALL PAIRS menjadi default**: scanner mengambil daftar seluruh kontrak **USDT PERPETUAL** aktif dari `/fapi/v1/exchangeInfo`, lalu memindai semuanya secara bertahap. Jika ada koin tanpa ticker 24h atau sejarah candle yang cukup, koin tersebut tetap diperhitungkan dalam cakupan tetapi kegagalan analisis dicatat, bukan disembunyikan.

## Mode scanner

| Mode | Pair yang dianalisis | Cocok untuk |
|---|---|---|
| **ALL PAIRS** *(default)* | Semua kontrak USDT PERPETUAL berstatus `TRADING`, tanpa syarat turnover minimum | Mencari setup di seluruh market |
| **LIQUID** | Semua pair aktif dengan turnover 24h >= $10M / $30M / $100M (pilih di layar) | Menyaring likuiditas sebelum scanning |
| **TOP 80** | Maksimal 80 pair dengan turnover USDT 24h tertinggi, tanpa cutoff $30M | Pemantauan lebih cepat |

Pair dengan event Potensi/Sudah yang masih aktif tetap dipantau **di luar kuota LIQUID atau TOP 80** supaya perjalanan sinyal tidak terputus. Dropdown **"Tampilkan: Volume"** hanya menyaring **baris pada layar**; tidak mengubah cakupan scan. Status di atas layar menunjukkan **Pair aktif**, **Sesuai mode**, **Dalam antrean**, dan **Tanpa ticker**. Bar status menampilkan `diproses / total`, `sukses` dan `gagal`. Dengan cara ini angka seperti 69 bisa ditelusuri.

### Pelindung Binance rate limit

ALL PAIRS memerlukan rangkaian candle 1m, 5m, 15m, 1h, 4h per pair pada launcher utama. Untuk membatasi lonjakan API, backend membagi pekerjaan per **20 pair/batch**, maksimal **4 worker**, dengan interval minimum **7 detik antar-awal batch**, memakai cache TTL serta menghentikan siklus saat muncul HTTP 429/418. Bila seluruh pasar besar, satu putaran dapat memakan **beberapa menit**; bukan tick scanner atau jaminan latensi scalping dalam hitungan detik. Server melakukan scan baru paling cepat ±3 menit **setelah putaran terakhir selesai**. Mode baru yang dipilih saat putaran berlangsung akan dijalankan setelah putaran itu selesai.

Endpoint futures klines Binance menggunakan bobot request menurut `limit`, dan exchangeInfo memiliki kuota berbasis IP. Limit, kondisi koneksi, dan respons aktual harus dipantau saat deployment. Lihat: [Market Data Binance USD-M](https://developers.binance.com/en/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data).

## Top 5 dan perjalanan sinyal — v0.5

- **Potensi Naik/Turun:** launcher utama menghitung skor R08 Multi-Factor 0–100; formula teknikal lama tetap sebagai kontrol penelitian. Kandidat dibatasi secara global menjadi **maksimal 5 sinyal aktif gabungan naik + turun**, bukan 5 per tab. Setiap batch 20 pair diperingkat; kandidat lebih kuat dapat mengganti yang terlemah **jika skor lebih tinggi ≥1 poin**. Hasilnya adalah Top 5 **bergulir dari kandidat yang sudah dipindai**, bukan klaim bahwa 5 itu tertinggi di seluruh market pada satu timestamp yang sama.
- **Filter anti-terlambat:** kandidat minimal quote turnover **$10 juta / 24h**, candle tertutup tidak lebih dari **8 menit**, tersedia quote terbaru Binance; saat quote telah bergerak searah >**0,30%** dari harga candle pemicu, kandidat tidak dipromosikan (`chase`). Pergerakan negatif yang sudah melewati `max(0,40%, ATR 5m%)` juga ditolak. Semua ini aturan uji, bukan patokan profit.
- **Fast Watch (sekitar 30 detik):** pantau maksimal 20 pair ber-event terkini lewat bulk quote + candle 5m yang telah tertutup, **tanpa harus mengulang analisis seluruh market**. Quote dapat memperbarui posisi harga sejak sinyal, tetapi **tidak** dapat sendiri mengubah status Potensi → Sudah; hanya close candle 5m setelah baseline yang dapat mencapainya. Refresh 30 detik adalah polling, bukan eksekusi detik-level atau websocket.
- **Lama Potensi:** maksimal **15 menit** untuk mencapai target sejak sinyal; kandidat yang umur sinyalnya **≥8 menit** ditandai terlalu tua untuk entry, dan yang harga quote sudah melesat **>0,30%** ditandai **Jangan kejar**. Status dapat berakhir `TARGET_REACHED`, `STOP_HIT`, `TIMEOUT`, `TIMEOUT_UNOBSERVED`, atau `RANK_REPLACED` di arsip. Stop/target adalah outcome berdasarkan **close**, bukan order fill nyata.
- **Sudah Naik/Turun:** hanya berasal dari sinyal Potensi sebelumnya ketika penutupan candle 5m berikutnya bergerak searah minimal `max(0,65%, 1,5 × ATR 5m dalam %)`. Status **Sudah tetap ditampilkan 6 jam** setelah konfirmasi, lalu hilang dari daftar aktif; event tersimpan sebagai riwayat **30 hari** di SQLite, dengan **30 event terbaru** bisa dilihat di panel Riwayat (API `/api/events` mengembalikan maksimum 200 event).
- **Simulasi stop:** `max(0,40%, ATR 5m%)` pergerakan merugikan dari baseline; status diarsipkan bila **close** candle 5m mencapai stop lebih dahulu daripada target. **Bukan perintah stop dan bukan hasil P&L**, terutama jika harga sempat bergerak melewati level di antara candle.
- Satu pair dapat menempati beberapa tab (contohnya **Sudah Naik + Potensi Turun**), jika berasal dari dua peristiwa berbeda. Jeda pembuatan event baru untuk arah yang sama: **60 menit** untuk mengurangi spam.
- **RSI 70–80 reversal watch:** ketika RSI 15m sebelumnya berada pada 70–80 lalu turun, disertai candle 5m bearish dan MACD histogram 5m negatif, tampil label **RSI 70–80 ↘ · Watch**. Ini **bukan SHORT otomatis**, tidak mendapat poin ekstra, dan bisa lebih bermanfaat sebagai **alarm evaluasi TP LONG**. Sinyal SHORT utama masih memakai RSI 15m di rentang 30–53 sesuai bobot skor, mengikuti filter tren.
- **Highlight:** perubahan 15m ≥2%, 1H ≥4%, 24H ≥8%, atau sejak sinyal ≥2%; ticker HIGH MOVE 1H ≥2%. OI 15m menjadi konteks; R08 MULTI FULL menguji OI bersama price response dan flow, bukan arah OI saja. Ranking default R08 MULTI CORE tidak menggunakan OI.
- **Batasan:** skor adalah bobot heuristik, bukan probabilitas; belum backtest profitabilitas, fee/spread/slippage, funding/liquidation, ataupun deploy/live market verification.

## Menjalankan aplikasi

**Windows lokal (branch `main`):** Python 3.10+; ekstrak ZIP dan double-click `START-WINDOWS.bat`. Satu launcher untuk siang/malam: R08 MULTI CORE, scanner ALL crypto, seluruh formula penelitian paralel, fast watch dan collector. Browser terbuka otomatis setelah server bind; tutup browser tanpa menghentikan scanner. Terminal, PC dan koneksi harus tetap aktif. `run_overnight.bat` hanya alias kompatibilitas; `export_overnight.bat` hanya untuk ekspor database.

**Akses HP 24/7:** deploy branch `main` dari repo private [Scalp-Radar](https://github.com/supermankesasar/Scalp-Radar) ke hosting Python selalu aktif + persistent disk (konfigurasi Render di `render.yaml`). Setelah deployment berhasil, buka URL HTTPS dari HP, dan bila perlu install PWA ke home screen. **Repo GitHub private tidak otomatis membuat URL aplikasi private.** Panduan: `DEPLOY_ONLINE.md`. Deployment saat ini belum dilakukan oleh ChatGPT, jadi belum ada URL live.

Penting: jika Binance Futures membatasi IP/region hosting, frontend menampilkan error; jangan gunakan angka lama untuk trading. Data event tersimpan sepanjang SQLite di disk permanen. Untuk operasi skala besar/latensi detik, tahap lanjutan perlu pembaruan delta via stream, observabilitas bobot API, dan penyimpanan yang lebih kuat.

## File dan API

- `app.py`: REST Binance publik, indikator, discovery full market, batching, API HTTP dan scheduler.
- `signals.py`: SQLite state machine Potensi→Sudah, multi-kategori, audit.
- `index.html`, `ui.js`: dashboard desktop/mobile.
- `icon.png`, `manifest.webmanifest`, `sw.js`: PWA. Offline shell tidak berpura-pura punya data Binance live.
- `render.yaml`, `START-WINDOWS.bat`, `DEPLOY_ONLINE.md`: deployment.
- `test_app.py`, `test_http.py`, `test_signals.py`, `test_v05.py`: regresi offline.

Endpoint:
- `GET /api/scan?mode=all&min_turnover=30000000` — default full market, mengembalikan progress dan rows multi-kategori.
- `GET /api/scan?mode=liquid&min_turnover=10000000` — filter volume saat scanning.
- `GET /api/scan?mode=top80` — Top 80 tanpa minimum turnover.
- `GET /api/snapshot?symbol=BTCUSDT` — indikator, OI, funding, chart.
- `GET /api/events` — audit signal.
- `GET /api/health` — status hidup server, bukan bukti Binance live.

Untuk menjalankan tes: `python -m unittest discover -p "test_*.py" -v` dan `python -m unittest discover -s tests -p "test_*.py" -v`. Tes offline tersedia untuk v0.5 dan R08, termasuk Top 5, harga live bukan konfirmasi target, anti-chase, timeout, dan RSI reversal watch. Koneksi Binance live pada server produksi **belum diverifikasi**. Untuk scalping sungguhan, prioritas berikutnya adalah backtest dan paper trading; sistem saat ini hanya watchlist riset.

## Satu jalur pengembangan

`main` adalah sumber resmi R08 dan satu-satunya branch aktif untuk distribusi. [Unduh ZIP main](https://github.com/supermankesasar/Scalp-Radar/archive/refs/heads/main.zip), pertahankan folder `data/` saat update, lalu jalankan `START-WINDOWS.bat`. Lihat [R08 Multi-Factor](research/R08_MULTI.md) dan [panduan pengumpulan data](research/OVERNIGHT.md). Branch research/modular-r06 dan research/technical-r01-r05 sudah tergabung ke main; feature/v05-data-backtest-oneclick adalah eksperimen Scalping/Swing lama yang terpisah, dipertahankan sebagai arsip kode dan bukan jalur distribusi. Jangan merge branch lama secara langsung ke main karena arsitektur scanner dan database berbeda.


## R09 Hybrid WebSocket
START-WINDOWS.bat installs the pinned public WebSocket client when needed and starts R09 automatically. R08 live ranking remains the default control; all R08 rules and new independent minute microstructure rules run together. See [R09](research/R09_WEBSOCKET.md). Health: /api/websocket and /api/research/1m. No keys or orders.

R09 adds 12 independent 1m microstructure/EMA/volume rules and R09_HYBRID on the 5m grid (39 total research formula IDs). Use /api/research for 5m and /api/research/1m for minute results. Optional R09_HYBRID live filter; default R08 CORE. Data receipt and coverage are recorded separately.

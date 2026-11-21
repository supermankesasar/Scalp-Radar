# Scalp Radar v0.4 — Full Market Scanner

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

ALL PAIRS memerlukan 4 rangkaian candle (5m, 15m, 1h, 4h) per pair. Untuk membatasi lonjakan API, backend membagi pekerjaan per **20 pair/batch**, maksimal **4 worker**, dengan interval minimum **7 detik antar-awal batch**, memakai cache TTL serta menghentikan siklus saat muncul HTTP 429/418. Bila seluruh pasar besar, satu putaran dapat memakan **beberapa menit**; bukan tick scanner atau jaminan latensi scalping dalam hitungan detik. Server melakukan scan baru paling cepat ±3 menit **setelah putaran terakhir selesai**. Mode baru yang dipilih saat putaran berlangsung akan dijalankan setelah putaran itu selesai.

Endpoint futures klines Binance menggunakan bobot request menurut `limit`, dan exchangeInfo memiliki kuota berbasis IP. Limit, kondisi koneksi, dan respons aktual harus dipantau saat deployment. Lihat: [Market Data Binance USD-M](https://developers.binance.com/en/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data).

## Empat daftar dan histori sinyal (tetap seperti v0.3)

- **Potensi Naik/Turun**: indikator dan market regime memenuhi aturan heuristic lalu timestamp, harga baseline, arah, skor, dan target dicatat di SQLite.
- **Sudah Naik/Turun**: hanya berasal dari **sinyal Potensi sebelumnya** yang kemudian tercapai pada **harga penutupan candle 5m berikutnya**. High/low wick tanpa close yang memenuhi ambang tidak cukup.
- Satu koin boleh berada di beberapa kategori sekaligus, misalnya **Sudah Naik + Potensi Turun**. Target sejak sinyal adalah `max(0,65%, 1,5 × ATR 5m dalam %)`, disimpan saat event dibuat. Event Potensi bertahan paling lama 12 jam; status Sudah bertahan 24 jam setelah konfirmasi. Satu sinyal baru tiap arah per koin per 24 jam. Riwayat event tersimpan 30 hari.
- **Highlight**: perubahan 15m ≥2%, 1H ≥4%, 24H ≥8%, atau perubahan sejak sinyal ≥2%; ticker HIGH MOVE untuk 1H ≥2%. Momentum dan OI 15m tetap terlihat. HIGH MOVE *bukan* otomatis masuk ke tab Sudah.
- Data OI adalah **perubahan total posisi terbuka**, bukan bukti long/short tertentu. Semua sinyal adalah **heuristik**, bukan probabilitas sukses atau rekomendasi trading. Belum backtest atau hitung biaya, slippage, dan likuidasi.

## Menjalankan aplikasi

**Windows lokal:** Python 3.10+; ekstrak ZIP dan double-click `START-WINDOWS.bat`. Buka `http://127.0.0.1:8765`. Terminal perlu tetap hidup di mode lokal.

**Akses HP 24/7:** deploy branch `main` dari repo private [Scalp-Radar](https://github.com/supermankesasar/Scalp-Radar) ke hosting Python selalu aktif + persistent disk (konfigurasi Render di `render.yaml`). Setelah deployment berhasil, buka URL HTTPS dari HP, dan bila perlu install PWA ke home screen. **Repo GitHub private tidak otomatis membuat URL aplikasi private.** Panduan: `DEPLOY_ONLINE.md`. Deployment saat ini belum dilakukan oleh ChatGPT, jadi belum ada URL live.

Penting: jika Binance Futures membatasi IP/region hosting, frontend menampilkan error; jangan gunakan angka lama untuk trading. Data event tersimpan sepanjang SQLite di disk permanen. Untuk operasi skala besar/latensi detik, tahap lanjutan perlu pembaruan delta via stream, observabilitas bobot API, dan penyimpanan yang lebih kuat.

## File dan API

- `app.py`: REST Binance publik, indikator, discovery full market, batching, API HTTP dan scheduler.
- `signals.py`: SQLite state machine Potensi→Sudah, multi-kategori, audit.
- `index.html`, `ui.js`: dashboard desktop/mobile.
- `icon.png`, `manifest.webmanifest`, `sw.js`: PWA. Offline shell tidak berpura-pura punya data Binance live.
- `render.yaml`, `START-WINDOWS.bat`, `DEPLOY_ONLINE.md`: deployment.
- `test_app.py`, `test_http.py`, `test_signals.py`: regresi offline.

Endpoint:
- `GET /api/scan?mode=all&min_turnover=30000000` — default full market, mengembalikan progress dan rows multi-kategori.
- `GET /api/scan?mode=liquid&min_turnover=10000000` — filter volume saat scanning.
- `GET /api/scan?mode=top80` — Top 80 tanpa minimum turnover.
- `GET /api/snapshot?symbol=BTCUSDT` — indikator, OI, funding, chart.
- `GET /api/events` — audit signal.
- `GET /api/health` — status hidup server, bukan bukti Binance live.

Untuk menjalankan tes: `python -m unittest -v test_app.py test_signals.py test_http.py`. **17 tes offline lulus** pada pengembangan v0.4; browser desktop dan mobile diperiksa dengan mock Binance. **Koneksi langsung v0.4 ke Binance dari server hosting produksi belum diverifikasi.**
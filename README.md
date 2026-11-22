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

ALL PAIRS memerlukan 4 rangkaian candle (5m, 15m, 1h, 4h) per pair. Untuk membatasi lonjakan API, backend membagi pekerjaan per **20 pair/batch**, maksimal **4 worker**, dengan interval minimum **7 detik antar-awal batch**, memakai cache TTL serta menghentikan siklus saat muncul HTTP 429/418. Bila seluruh pasar besar, satu putaran dapat memakan **beberapa menit**; bukan tick scanner atau jaminan latensi scalping dalam hitungan detik. Server melakukan scan baru paling cepat ±3 menit **setelah putaran terakhir selesai**. Mode baru yang dipilih saat putaran berlangsung akan dijalankan setelah putaran itu selesai.

Endpoint futures klines Binance menggunakan bobot request menurut `limit`, dan exchangeInfo memiliki kuota berbasis IP. Limit, kondisi koneksi, dan respons aktual harus dipantau saat deployment. Lihat: [Market Data Binance USD-M](https://developers.binance.com/en/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data).

## Top 5 dan perjalanan sinyal — v0.5

- **Potensi Naik/Turun:** mesin menghitung skor teknikal lama 0–100 dan aturan tren. Kandidat dibatasi secara global menjadi **maksimal 5 sinyal aktif gabungan naik + turun**, bukan 5 per tab. Setiap batch 20 pair diperingkat; kandidat lebih kuat dapat mengganti yang terlemah **jika skor lebih tinggi ≥1 poin**. Hasilnya adalah Top 5 **bergulir dari kandidat yang sudah dipindai**, bukan klaim bahwa 5 itu tertinggi di seluruh market pada satu timestamp yang sama.
- **Filter anti-terlambat:** kandidat minimal quote turnover **$10 juta / 24h**, candle tertutup tidak lebih dari **8 menit**, tersedia quote terbaru Binance; saat quote telah bergerak searah >**0,30%** dari harga candle pemicu, kandidat tidak dipromosikan (`chase`). Pergerakan negatif yang sudah melewati `max(0,40%, ATR 5m%)` juga ditolak. Semua ini aturan uji, bukan patokan profit.
- **Fast Watch (sekitar 30 detik):** pantau maksimal 20 pair ber-event terkini lewat bulk quote + candle 5m yang telah tertutup, **tanpa harus mengulang analisis seluruh market**. Quote dapat memperbarui posisi harga sejak sinyal, tetapi **tidak** dapat sendiri mengubah status Potensi → Sudah; hanya close candle 5m setelah baseline yang dapat mencapainya. Refresh 30 detik adalah polling, bukan eksekusi detik-level atau websocket.
- **Lama Potensi:** maksimal **15 menit** untuk mencapai target sejak sinyal; kandidat yang umur sinyalnya **≥8 menit** ditandai terlalu tua untuk entry, dan yang harga quote sudah melesat **>0,30%** ditandai **Jangan kejar**. Status dapat berakhir `TARGET_REACHED`, `STOP_HIT`, `TIMEOUT`, `TIMEOUT_UNOBSERVED`, atau `RANK_REPLACED` di arsip. Stop/target adalah outcome berdasarkan **close**, bukan order fill nyata.
- **Sudah Naik/Turun:** hanya berasal dari sinyal Potensi sebelumnya ketika penutupan candle 5m berikutnya bergerak searah minimal `max(0,65%, 1,5 × ATR 5m dalam %)`. Status **Sudah tetap ditampilkan 6 jam** setelah konfirmasi, lalu hilang dari daftar aktif; event tersimpan sebagai riwayat **30 hari** di SQLite, dengan **30 event terbaru** bisa dilihat di panel Riwayat (API `/api/events` mengembalikan maksimum 200 event).
- **Simulasi stop:** `max(0,40%, ATR 5m%)` pergerakan merugikan dari baseline; status diarsipkan bila **close** candle 5m mencapai stop lebih dahulu daripada target. **Bukan perintah stop dan bukan hasil P&L**, terutama jika harga sempat bergerak melewati level di antara candle.
- Satu pair dapat menempati beberapa tab (contohnya **Sudah Naik + Potensi Turun**), jika berasal dari dua peristiwa berbeda. Jeda pembuatan event baru untuk arah yang sama: **60 menit** untuk mengurangi spam.
- **RSI ≥70 reversal watch:** ketika RSI 15m sebelumnya berada pada atau di atas ambang (default 70) lalu turun, disertai candle 5m bearish dan MACD histogram 5m negatif, tampil label **RSI 70–80 ↘ · Watch**. Ini **bukan SHORT otomatis**, tidak mendapat poin ekstra, dan bisa lebih bermanfaat sebagai **alarm evaluasi TP LONG**. Sinyal SHORT utama masih memakai RSI 15m di rentang 30–53 sesuai bobot skor, mengikuti filter tren.
- **Highlight:** perubahan 15m ≥2%, 1H ≥4%, 24H ≥8%, atau sejak sinyal ≥2%; ticker HIGH MOVE 1H ≥2%. OI 15m tetap sebagai informasi, **bukan** input ranking, karena OI agregat tidak menentukan siapa lebih dominan long/short.
- **Batasan:** skor adalah bobot heuristik, bukan probabilitas; belum backtest profitabilitas, fee/spread/slippage, funding/liquidation, ataupun deploy/live market verification.

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
- `test_app.py`, `test_http.py`, `test_signals.py`, `test_v05.py`: regresi offline.

Endpoint:
- `GET /api/scan?mode=all&min_turnover=30000000` — default full market, mengembalikan progress dan rows multi-kategori.
- `GET /api/scan?mode=liquid&min_turnover=10000000` — filter volume saat scanning.
- `GET /api/scan?mode=top80` — Top 80 tanpa minimum turnover.
- `GET /api/snapshot?symbol=BTCUSDT` — indikator, OI, funding, chart.
- `GET /api/events` — audit signal.
- `GET /api/health` — status hidup server, bukan bukti Binance live.

Untuk menjalankan tes: `python -m unittest discover -p "test_*.py" -v`. **24 tes offline lulus** untuk v0.5 sebelum upgrade; jalankan ulang seluruh tes setelah perubahan, termasuk Top 5, harga live bukan konfirmasi target, anti-chase, timeout, dan RSI reversal watch. Koneksi Binance live pada server produksi **belum diverifikasi**. Untuk scalping sungguhan, prioritas berikutnya adalah backtest dan paper trading; sistem saat ini hanya watchlist riset.

## Upgrade experimental — indikator manual + data riset

Tersedia pada branch `feature/v05-data-backtest-oneclick` (belum digabung ke main).

Setelah klik `START-WINDOWS.bat`, web lokal menyediakan panel **Pengaturan indikator manual**. Konfigurasi disimpan di `data/indicator_settings.sqlite3` dan digunakan pada **putaran scan berikutnya**. Tombol **Reset ke default** mengembalikan angka bawaan. Perubahan disimpan dengan revision history, bukan mengedit event lama.

| Parameter | Default | Makna |
| --- | ---: | --- |
| RSI overbought watch | 70 | RSI 15m sebelumnya >= ambang, menurun, candle bearish dan MACD histogram negatif. Alarm saja, bukan SHORT |
| RSI maksimal untuk skor LONG | 70 | RSI 15m 47 sampai ambang mendapat 10 poin dalam skor LONG |
| Skor minimal kandidat | 68 | Batas skor untuk mempertimbangkan potensi naik/turun |
| Volume relatif mendapat poin penuh | 1.10x | Perbandingan volume 5m saat ini dengan rata-rata 20 candle sebelumnya |
| Max anti-chase | 0.30% | Batas harga quote sudah bergerak searah sejak candle sinyal sebelum promosi Top 5 |

Perubahan **tidak mengaktifkan AI trading**. Engine historical research hanya mengevaluasi event tercatat dengan asumsi eksekusi sederhana; perubahan parameter belum otomatis dites ulang dengan replay historis seluruh market. Uji parameter di paper trading/holdout sebelum dipercaya. Perubahan parameter dari browser **hanya diizinkan pada localhost** sampai autentikasi remote dibuat; tidak boleh memberi izin tulis anonim dari internet.

Setelah mengganti parameter, gunakan riwayat revisi untuk menandai periode hasil yang dibandingkan; angka hasil strategi lama dan baru tidak otomatis setara.


## Mode baru: Scalping dan Swing (eksperimental)

Kedua mode memakai satu web dan satu launcher `START-WINDOWS.bat`, tetapi **scanner dan event database terpisah**. Memilih tab mengganti mesin aktif. Mesin yang tidak dipilih tidak melakukan full-market scan rutin. Secara default pakai TOP 80 agar permintaan API tidak berlebihan; mode ALL PAIRS tetap tersedia.

| | Scalping | Swing |
| --- | --- | --- |
| Timeframe data & logika | **1m, 5m, 15m, 1h** saja | **15m, 1h, 4h, 8h, 1d, 1w** saja |
| Konteks tren | EMA200 1h dan 15m | EMA21 mingguan, EMA200 1d/8h/4h |
| Sinyal & momentum | EMA21 5m/1m, MACD 1m, RSI 5m, rel. volume 1m, VWAP 5m | EMA21 1h, MACD 15m, RSI 1h, rel. volume 15m |
| Perubahan harga 24h | **Tidak digunakan**, tidak diminta untuk keputusan arah (ticker API tetap memberi nilai saat universe discovery) | Konfirmasi arah positif untuk LONG, negatif untuk SHORT |
| Turnover 24h USDT | Filter likuiditas saja | Filter likuiditas saja |
| Score | 0–100 heuristik | 0–100 heuristik berbeda |
| Konfirmasi event | **CLOSE 1m** sesudah sinyal | **CLOSE 1h** sesudah sinyal |
| Batas event PENDING | **15 menit** | **3 hari** awal, belum divalidasi |
| Kandidat TP indikatif | max(0.65%,1.5×ATR5m%) | max(2%,1.5×ATR1d%) |
| Kandidat SL indikatif | max(0.40%,ATR5m%) | max(1%,ATR1d%) |
| Event SQLite | `data/signals_scalping.sqlite3` | `data/signals_swing.sqlite3` |

*Penting*: Timeframe merupakan interval candle yang **telah ditutup**, bukan laju refresh browser atau jaminan entry real-time. Scanner tetap polling per batch dan mungkin menunda sinyal. 1H dan timeframe lain tidak dikeluarkan dari data sumber untuk Swing; 3m/4h/dll dikeluarkan dari penghitungan Scalping. RSI Watch threshold default 70 tetap dapat diubah melalui panel pengaturan; RSI Watch adalah alarm, bukan sinyal SHORT independen.

**Data coverage:** Swing memerlukan minimal 30 candle mingguan tertutup untuk EMA21 dan sekitar 220 candle tertutup untuk indikator EMA200 pada 15m/1h/4h/8h/1d. Pair yang belum punya cukup histori ditandai gagal dianalisis; tidak disubstitusi dengan harga rekaan. `8h` dan `1w` adalah interval historis Binance yang valid.

**Pemisahan event:** Arsitektur lama `data/signals.sqlite3` disimpan tanpa migrasi/destruksi sebagai arsip legacy. Dua mode baru tidak memakai Top 5 atau event lama dari database ini. Selama transisi tab, scanner lama yang masih berlangsung dapat menyelesaikan pekerjaannya; versi mendatang perlu pembatalan job yang lebih cermat.

**Backtest:** Modul `research_engine.py` sebelumnya hanya mengoleksi 5m 7 hari dan mengevaluasi event legacy, **belum** menjalankan full historical replay atau backtest baru per mode. Angka backtest v0.5 sebelumnya tidak berlaku untuk strategi baru tanpa pengujian ulang. Tidak ada AI trading ataupun eksekusi order otomatis.

**Pengaturan indikator:** Default disimpan pada `data/indicator_settings.sqlite3`; perubahan manual dipakai pada siklus scan berikutnya, dan kedua mode berbagi parameter seperti batas skor dan RSI, sementara rumus fitur setiap mode berbeda. Backup seluruh folder `data` sebelum mengganti versi.


## Logo koin pada dashboard (eksperimental)

Tabel **Scalping/Swing**, bar **High Move**, dan detail coin sekarang menampilkan logo koin otomatis dari pustaka open-source `spothq/cryptocurrency-icons` melalui jsDelivr. Tidak perlu API key atau mengganti database. Gambar dimuat secara lazy-load. Kontrak Binance berawalan `1000` dicoba dengan simbol token dasarnya (mis. `1000PEPEUSDT` → `pepe.png`). Simbol tidak valid tidak dimasukkan ke URL. Jika logo koin tidak ada atau CDN tidak bisa diakses, otomatis muncul inisial simbol dalam lingkaran.

Logo bersifat dekoratif dan tidak boleh dianggap verifikasi identitas token. Pengambilan gambar dari CDN memerlukan internet dan bisa gagal untuk token baru; scanner market dan backtest tetap berfungsi tanpa logo. File `coin_logos.js` harus ikut diunduh bersama `ui.js` dan `index.html` (tersedia otomatis pada ZIP branch terbaru).

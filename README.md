# Scalp Radar v0.3 — Signal Journey Scanner

**Fase 1 | Binance USDⓈ-M Futures | read-only | no order execution | tanpa API key.**

Versi ini mengubah logika scanner dari *empat kategori harga saat ini* menjadi **empat kategori berbasis perjalanan sinyal yang tersimpan**. Dashboard dibuat lebih simpel, mobile-friendly, dengan highlight perubahan besar dan dukungan instalasi sebagai web app (PWA) melalui HTTPS.

## Perubahan utama dari v0.2

- **Potensi Naik / Potensi Turun:** saat kombinasi tren EMA 1H/4H, EMA 21, RSI, MACD, VWAP, volume, dan batas harga memenuhi aturan, sistem menyimpan satu event dengan harga dan waktu baseline. Perhitungan indikator tetap dari candle Binance Futures yang sudah tertutup.
- **Sudah Naik / Sudah Turun:** **tidak** diisi langsung dari daftar price movers Binance. Status hanya dapat muncul dari event Potensi yang pernah tersimpan, ketika **harga penutupan candle 5 menit SETELAH event** mencapai batas target searah sinyal. Lonjakan wick tanpa candle close yang memenuhi batas tidak menghitung sebagai target tercapai.
- **Multi-tab:** satu symbol dapat sekaligus muncul pada `SUDAH_NAIK` dan `POTENSI_TURUN` atau kombinasi lain jika perjalanan sinyalnya berbeda. Tidak ada prioritas kategori yang memaksa hanya satu tab.
- **Penyimpanan SQLite:** perjalanan sinyal dan snapshot terakhir tetap tersedia setelah halaman di-refresh atau server restart, asalkan database disimpan pada storage persisten.
- **Background scheduler:** scanner memindai tanpa memerlukan browser dibuka, selama server/hosting benar-benar aktif; default ±3 menit + waktu proses.
- **Tracked symbols:** saat pair keluar dari Top-N likuiditas tetapi masih memiliki event yang dipantau, server tetap mencoba mengambil candle-nya.
- **Highlight:** perubahan **15m ≥ 2%**, **1H ≥ 4%**, **24H ≥ 8%**, atau **sejak sinyal ≥ 2%** ditonjolkan hijau/merah; ticker "HIGH MOVE 1H" memuat gerak absolut ≥ 2%, **tidak otomatis** masuk tab Sudah.
- **PWA:** dapat ditambahkan ke home screen Android melalui HTTPS, tetapi data live membutuhkan server tersambung.

## Aturan perjalanan sinyal (prototype; belum teruji profitabilitas)

1. Saat deteksi Potensi, simpan `symbol`, arah, waktu candle 5m tertutup, harga penutupan, skor dan ambang pergerakan.
2. Target: `max(0.65%, 1.5 × ATR 5m dalam persen)` sejak baseline. Ambang dibekukan saat sinyal dibuat.
3. Event Potensi tetap dipantau sampai 12 jam untuk melihat apakah target tercapai, termasuk saat setup teknikal baru sudah melemah. UI memberi label "Setup melemah" jika kondisi terbaru tidak lagi searah.
4. Setelah ada candle 5m **berikutnya** yang mencapai target berdasarkan **close**, event berubah menjadi Sudah Naik/Turun. Tetap terlihat hingga 24 jam setelah konfirmasi, walau harga telah reversal.
5. Satu event baru per symbol dan arah selama 24 jam untuk mencegah pengulangan spam. Arah berlawanan dapat membuat event sendiri tanpa menunggu event pertama hilang.
6. `Sejak sinyal` = perubahan harga bertanda secara alami (+ naik / − turun), `Terbaik sejak sinyal` = penutupan candle terbaik **searah** sinyal, bukan harga masuk transaksi atau profit bersih. OI hanyalah konteks agregat futures, bukan bukti jumlah trader long/short.
7. Data event disimpan sampai 30 hari di database untuk audit. Snapshot ditahan maksimal 36 jam sebagai fallback antarrestart. Tidak ada *backfill* event sejarah ketika instalasi pertama (karena kita tidak punya sinyal live terdahulu).

**Penting:** Potensi hanyalah aturan heuristik, bukan probabilitas. Sudah = target harga historis tercapai, bukan jaminan entry tersebut berhasil dijual/beli pada harga target, dan bukan ukuran profit trading. Belum ada backtest, fee/slippage, eksekusi, maupun AI Agent.

## Bisa diakses HP tanpa CMD?

**Ya, setelah deployment ke hosting yang selalu menyala dan mempunyai penyimpanan permanen.**

- **Mode lokal (Windows):** ekstrak folder, jalankan `START-WINDOWS.bat`; CMD dan PC harus tetap menyala agar scanner berjalan, alamat lokal `http://127.0.0.1:8765` hanya untuk PC itu. Tidak perlu `pip install` karena Python standard library.
- **Mode online (direkomendasikan):** deploy kode dari GitHub ke layanan *Web Service* berbayar yang tidak tidur + attach persistent disk. Termasuk `render.yaml` siap untuk [Render](https://render.com/). Setelah deploy, buka URL HTTPS dari HP mana saja; browser desktop tidak perlu menyala. Petunjuk lengkap ada di **DEPLOY_ONLINE.md**.
- **Free hosting bukan solusi lengkap untuk pemantauan otomatis:** layanan gratis Render dapat tidur setelah idle dan tidak mendukung persistent disk; sinyal tidak akan tercatat konsisten selama layanan tidur. Gunakan layanan always-on dengan disk/database yang persisten atau VPS.

## Filter dan data

Filter awal mengambil Top 40/80/120 kontrak USDT perpetual berstatus `TRADING` menurut quote turnover 24 jam, dengan ambang minimum $10M/$30M/$100M; batas ini tetap berlaku untuk **penemuan sinyal baru**. Pair yang sudah pernah masuk Potensi dilacak terus selama event masih aktif meskipun keluar Top-N. OI 15m diperoleh dari endpoint Binance Open Interest History 5m jika tersedia.

Status sumber data dan error ditampilkan jujur: jika jaringan menolak endpoint Binance atau rate limit tercapai, UI tidak menggantinya dengan data buatan. Scanner bukan websocket tick-level, sehingga ada keterlambatan relatif ke market dan harga dapat berubah drastis selama interval pemindaian.

## Isi proyek

- `app.py`: backend HTTP, pembacaan candle, indikator, scanning, API data, scheduler.
- `signals.py`: persistent SQLite event store, state machine Potensi→Sudah, riwayat, multi-tab.
- `index.html`: UI ringan responsif, tabel desktop / kartu mobile, detail chart dan OI.
- `manifest.webmanifest`, `sw.js`, `icon.png`: instalasi PWA (memerlukan HTTPS), offline shell saja, **tidak** menyimpan API live palsu.
- `render.yaml`: deploy blueprint + disk persisten.
- `test_app.py`, `test_signals.py`, `test_http.py`: 14 uji unit/regresi offline tanpa menyentuh Binance live.
- `START-WINDOWS.bat`: mode lokal sebagai opsi.
- `DEPLOY_ONLINE.md`: langkah klik di GitHub/Render tanpa menggunakan terminal komputer.

## API

- `/api/scan?limit=80&min_turnover=30000000`: status scanning dan array rows dengan **`categories[]`** serta `journeys[]` (tidak eksklusif).
- `/api/snapshot?symbol=BTCUSDT`: data detail indikator, OI dan grafik 5m.
- `/api/events`: audit event terbaru (maks. 200).
- `/api/health`: healthcheck server.

## Verifikasi

Di folder aplikasi, jalankan `python -m unittest -v test_app.py test_signals.py` bila ingin menguji kode. Sebanyak **14 pengujian offline** lulus. UI desktop/mobile juga diuji dengan data mock dan pengecekan JavaScript. **Belum diuji secara penuh dengan akses Binance Futures live dari runtime produksi**. Keberhasilan deploy dan akses API bisa berbeda tergantung wilayah/IP hosting.
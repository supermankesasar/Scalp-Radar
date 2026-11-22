# Scalp Radar v0.5 — Backtest eksploratif

**Tanggal evaluasi:** 22 November 2026  
**Sumber:** Binance USDⓈ-M Futures historical kline, diakses melalui konektor Binance.  
**Kode yang dievaluasi:** `supermankesasar/Scalp-Radar` v0.5 (`app.py`, `signals.py`); replay historis merekonstruksi aturan sinyal tetapi **bukan reproduksi identik** alur scanning produksi.

## Ringkasan keputusan

**NO-GO untuk entry otomatis atau trading live berdasarkan sinyal v0.5.** Aplikasi tetap berguna sebagai market watchlist dan sistem pencatat kejadian, tetapi indikator yang dipakai belum memberikan edge scalping yang memadai setelah biaya. Jangan mengartikan status `SUDAH_NAIK` atau `SUDAH_TURUN` sebagai transaksi yang pasti untung.

## Sampel dan cakupan

- **Periode bullish:** 11–30 Agustus 2026, 20 hari, 4 pair: BTCUSDT, ETHUSDT, SOLUSDT, DOGEUSDT.
- **Periode bearish:** 1–21 November 2026, 21 hari, 8 pair: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, DOGEUSDT, ADAUSDT, LINKUSDT.
- Semua USDT-M perpetual Futures; timeframe candle 5m, 15m, 1h, 4h. Data candle 15m sebagian dibentuk dari penggabungan tiga candle 5m.
- Backtest mencakup **semua pendekatan sinyal yang telah memiliki aturan di v0.5**: continuation LONG, continuation SHORT, RSI 70–80 reversal (sebagai hipotesis SHORT untuk perbandingan), pemilihan Top 5, dan target/stop ATR 15 menit. **Tidak** mencakup seluruh pair Binance, leverage, order book, OI sebagai strategi entry, maupun performa deployed live.

## Asumsi eksekusi dan metode

1. Semua indikator dihitung hanya dari candle yang **telah ditutup**. Aturan skor 0–100, EMA200 1h/4h, EMA21, MACD, RSI14, volume dan VWAP diturunkan dari v0.5.
2. Simulasi dimulai pada penutupan candle sinyal; harga entry diasumsikan **open candle 5m selanjutnya**. Ini optimistis dibanding scanner ALL PAIRS yang memproses banyak pair secara bertahap.
3. Filter: minimal turnover sebelumnya kira-kira 10 juta USDT/24h, batas anti-chase relatif baseline 0,30% saat next open, cooldown event 60 menit per pair+arah, maksimal lima event aktif sekaligus, pergantian event bila skor baru unggul minimal satu poin.
4. Stop `max(0,40%, ATR5m%)`, target `max(0,65%, 1,5×ATR5m%)`, keduanya dibandingkan terhadap penutupan candle dalam tiga candle berikutnya (15 menit). Apabila tidak tercapai, keluar pada close candle ketiga. Ini simulasi **outcome dari harga candle**, bukan order stop, limit fill, ataupun PnL real.
5. PnL adalah perubahan persentase notional dari harga entry ke harga exit sesuai arah, dikurangi **asumsi biaya gabungan 0,20% per round-trip** (fee, spread dan slippage). Tidak termasuk funding, dampak leverage, likuidasi, latensi order ataupun biaya lain.
6. Ranking Top 5 dijalankan pada penutupan 5m yang sama di **pair sampel**, tidak persis mengikuti penjadwalan batch dan keterlambatan jaringan di server produksi.
7. Perhitungan EMA200 memakai riwayat panjang untuk stabilitas; kode live memakai sekitar 229–230 candle terbatas. Pemeriksaan pada BTC/ETH/SOL menunjukkan label tren 1h/4h dapat berbeda sekitar 1,8–4,2% dari titik yang diperiksa. Hasil di bawah karenanya **estimasi pendekatan, bukan parity test identik terhadap produksi**. Tidak ada walk-forward parameter tuning atau holdout independen.

## Hasil utama

| Periode | Pair | Event Top5 | Mean gross/event | Mean net/event setelah 0,20% | Transaksi net positif | Target tercapai (close) | Timeout |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bull Agustus | 4 | 893 | +0,0111% | **-0,1889%** | 15,34% | 2,13% | 92,72% |
| Bear November | 8 | 2.057 | +0,0050% | **-0,1950%** | 21,00% | 3,06% | 86,63% |
| Gabungan | 8 unik; 12 pair-periode | 2.950 | +0,0068% | **-0,1932%** | 19,29% | 2,78% | 88,47% |

Caveat: event bersifat tumpang tindih antarkoin sehingga **2.950 bukan 2.950 observasi independen**, dan rata-rata return/event bukan return portofolio. Simulasi Top5 gabungan hanya sedikit berbeda dari seluruh event sesudah cooldown (baseline -0,1936% versus Top5 -0,1932%). Jumlah event terpilih rata-rata sekitar **72 per hari** pada sampel gabungan: batas lima berlaku untuk **slot aktif**, bukan untuk lima sinyal per hari.

### Arah, skor dan RSI

| Kategori gabungan | Event | Mean net setelah biaya | Target | Net positif |
|---|---:|---:|---:|---:|
| LONG continuation (Top5) | 729 | -0,1896% | 2,61% | 17,56% |
| SHORT continuation (Top5) | 2.221 | -0,1944% | 2,84% | 19,86% |
| Skor >=90 (Top5) | 837 | -0,1894% | 4,06% | 19,59% |
| Skor <90 (Top5) | 2.113 | -0,1947% | 2,27% | 19,17% |
| RSI 70–80, SHORT hipotetis terpisah | 163 | -0,1740% | 3,68% | 26,38% |

RSI reversal **tidak** merupakan sinyal SHORT v0.5. Pengujian SHORT-nya hanya eksperimen pembanding; manfaat sebagai alarm take-profit posisi LONG belum diuji secara benar karena perlu membandingkan exit dengan strategi hold posisi.

### Keterlambatan entry (subset yang masih memenuhi syarat)

| Entry | Event yang masih dapat dieksekusi menurut simulasi | Mean net/event | Target | Net positif |
|---|---:|---:|---:|---:|
| Open candle 5m pertama setelah sinyal | 2.950 | -0,1932% | 2,78% | 19,29% |
| Tertunda 5 menit | 2.759 | -0,1949% | 1,49% | 14,32% |
| Tertunda 10 menit | 2.538 | -0,1921% | 0,32% | 7,72% |

Sebagian sinyal dikeluarkan dari kelompok terlambat karena target/stop sudah terlewati atau harga sudah terlalu jauh. Oleh sebab itu, mean PnL antarbaris **bukan** perbandingan kausal pada sampel transaksi yang identik. Keterlambatan membuat target lebih jarang tercapai dan transaksi bersih positif lebih sedikit.

### Alternatif target (hanya sensitivity test pada event Top5 yang sama)

| Target close-based | Target hit | Mean net/event setelah 0,20% |
|---|---:|---:|
| 0,25% | 18,88% | -0,1942% |
| 0,35% | 11,63% | -0,1936% |
| 0,50% | 5,97% | -0,1929% |
| 0,65% | 3,42% | -0,1919% |
| Target dinamis v0.5 `max(0,65%, 1,5×ATR)` | 2,78% | -0,1932% |

Semua alternatif tetap negatif. Angka ini hanyalah eksplorasi pada sampel yang sama; tidak boleh dipakai memilih parameter final tanpa data holdout baru.

### Wick touch versus close target

Apabila target/stop diuji dari high/low candle dengan aturan konservatif stop didahulukan saat keduanya tersentuh dalam satu candle, target tersentuh sekitar **5,19%** dan net rata-rata masih sekitar **-0,1926%**. Ini menunjukkan kesulitan tidak hanya disebabkan definisi `close` untuk status Sudah.

### Sensitivitas asumsi biaya

Mean gross Top5 gabungan hanya **+0,0068%** per event. Pada asumsi round-trip cost 0%, 0,10%, 0,20%, dan 0,30%, mean net secara aritmetika menjadi sekitar **+0,0068%, -0,0932%, -0,1932%, dan -0,2932%**. Tanpa biaya hampir impas; setelah biaya wajar scalping menjadi negatif pada sampel ini.

## Kesimpulan engineering/trading

- **Jangan aktifkan auto-trade.** Top5 saat ini membatasi *simultaneous alerts*, belum berarti lima sinyal yang benar-benar selektif per hari atau periode.
- Untuk scalping, latency scanner ALL PAIRS + close candle 5m signifikan. Pertimbangkan streaming candle/quote, cache indikator 1h/4h dan scan bertahap berprioritas, **valid-until** eksplisit, dan larangan chase harga.
- Pisahkan mode `Trend Continuation`, `Reversal Watch/TP`, dan `No Trade`; jangan menjumlahkan semuanya dalam satu skor tanpa validasi.
- Rekam 1m/order-book spread, fee riil, dan outcomes fill untuk paper-trading 2–4 minggu; kemudian lakukan walk-forward backtest beberapa rezim pasar dan lebih banyak pair.
- OI dan funding **belum** menjadi input arah sinyal sehingga belum ada hasil backtest OI-filter. Whales on-chain sengaja di luar scope.

## Data audit dalam repository private

- `research/backtest_v05_2026_aggregate.json`
- `research/backtest_v05_2026_diagnostics.json`
- `research/aug2026_candidates_01.json`, `research/aug2026_candidates_02.json`
- `research/nov2026_candidates_01.json` hingga `_04.json`

**Catatan:** data event tersimpan untuk audit, bukan OHLCV mentah lengkap. Hasil di atas merupakan perhitungan ulang historis, belum benchmark live ataupun penilaian keuntungan portofolio.
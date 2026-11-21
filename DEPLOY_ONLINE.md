# Deployment Scalp Radar v0.4 agar bisa dibuka dari HP

Repository sudah ada di GitHub: [supermankesasar/Scalp-Radar](https://github.com/supermankesasar/Scalp-Radar), branch `main`, sekarang **Private**. Kode di repository **bukan** website online dengan sendirinya. Scanner memerlukan proses Python yang hidup terus serta disk permanen untuk SQLite.

1. Buka [Render Dashboard](https://dashboard.render.com/) dan masuk.
2. Hubungkan GitHub ke Render jika belum. Izinkan akses ke repo **Scalp-Radar** pada pengaturan GitHub App/Render. Repo private tidak akan tampak di Render tanpa izin tersebut.
3. Gunakan **New → Blueprint** dan pilih repo Scalp-Radar. Render membaca `render.yaml`. Jika opsi ini tidak ada, buat **Web Service** dari repo tersebut dan set *Start Command* = `python app.py`, *Health Check* = `/api/health`, dan persistent disk = mount `/opt/render/project/src/data`.
4. Tinjau **biaya** plan `starter` dan persistent disk 1 GB sebelum konfirmasi. Gunakan **satu instance** saja; aplikasi ini punya scheduler dalam proses dan SQLite lokal.
5. Setelah deploy sukses, cek `/api/health` mengembalikan `"version":"0.4"`, dan buka URL HTTPS yang diberikan Render. Browser Android bisa menambahkan ke **Home screen / Install**.
6. Di halaman Scalp Radar, pastikan mode **ALL PAIRS** aktif. Periksa nilai **Pair aktif / Sesuai mode / Diproses / Sukses / Gagal**. Hasil scan akan mulai muncul bertahap dan tab **Sudah** tidak akan berisi sinyal historis yang tak pernah tercatat di database.

**Perhatian:** pada mode ALL, scan penuh membutuhkan beberapa menit tergantung banyaknya kontrak, kecepatan jaringan, dan pembatas Binance. Jika ada HTTP 403/451/429, informasi kegagalan ditampilkan di dashboard. Jangan mengejar akses dari lokasi yang dibatasi secara resmi.

**Keamanan:** repo private hanya menyembunyikan *source*. URL website Render secara default **tidak memakai login**. Bila hanya untuk pribadi, tambahkan autentikasi/gateway di hosting sebelum membagikan URL. Sistem ini tidak meminta Binance API key dan tidak membuka transaksi.

**Alternatif Windows lokal:** klik `START-WINDOWS.bat`; command prompt perlu tetap berjalan dan PC harus menyala. Ini hanya untuk uji lokal, bukan opsi pemantauan HP di luar jaringan.
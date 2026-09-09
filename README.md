# Telegram Command Bot — GitHub + Railway

Bot Telegram sederhana namun interaktif. Bot hanya menangani command tertentu dan callback dari tombol inline.

## Fitur

- `/start` — pesan selamat datang + menu
- `/menu` — menu utama
- `/info` — menu **Info & Referensi** interaktif (istilah teknis, FAQ, tips keamanan, tentang bot)
- `/help` — bantuan
- `/masuk <jumlah> <keterangan>` — catat pemasukan (contoh: `/masuk 50000 Gaji`)
- `/keluar <jumlah> <keterangan>` — catat pengeluaran (contoh: `/keluar 20000 Makan siang`)
- `/reset_data` — hapus semua transaksi milik Anda
- Menu **Laporan, Saldo, Transaksi, Data** sudah terhubung ke database SQLite asli (bukan lagi placeholder) — datanya per pengguna (setiap orang yang chat bot ini punya data masing-masing)
- Tombol inline untuk Laporan, Saldo, Transaksi, Data, Bantuan, dan Info & Referensi
- Setiap topik di menu Info & Referensi berisi **konten asli yang bisa langsung dibaca** (bukan placeholder) — cocok dijadikan basis dokumentasi/FAQ bot Anda sendiri
- Tombol kembali ke Menu Utama maupun ke Menu Info
- Pesan teks biasa tidak diproses
- Token bot dibaca dari environment variable `BOT_TOKEN`
- Siap deploy dari GitHub ke Railway

## Struktur

```text
telegram-command-bot/
├── bot.py
├── database.py       ← modul database SQLite (baru)
├── data.db            ← file database, dibuat otomatis saat bot pertama jalan
├── requirements.txt
├── .gitignore
└── README.md
```

## 1. Buat bot di Telegram

1. Buka Telegram.
2. Cari `@BotFather`.
3. Kirim `/newbot`.
4. Ikuti instruksi sampai BotFather memberi token.
5. Jangan memasukkan token ke GitHub.

### Daftarkan command

Di BotFather, kirim `/setcommands` dan isi:

```text
start - Memulai bot
menu - Membuka menu utama
info - Info & referensi
help - Bantuan penggunaan
```

## 2. Jalankan lokal di Windows

Buka PowerShell di folder project.

### Buat virtual environment

```powershell
python -m venv .venv
```

### Aktifkan

```powershell
.\.venv\Scripts\Activate.ps1
```

Jika PowerShell menolak eksekusi script, buka Command Prompt dan gunakan:

```bat
.\.venv\Scripts\activate.bat
```

### Install dependency

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Masukkan token untuk sesi terminal saat ini

```powershell
$env:BOT_TOKEN="TOKEN_DARI_BOTFATHER"
```

### Jalankan

```powershell
python bot.py
```

Biarkan terminal tetap terbuka ketika melakukan pengujian lokal.

## 3. Pengujian lokal

Di Telegram coba:

- `/start`
- `/menu`
- `/info` — lalu tekan tiap tombol topik (Istilah Teknis, FAQ, Tips Keamanan, Tentang Bot Ini) dan cek tombol "⬅️ Kembali ke Info" berfungsi
- `/help`
- `/masuk 50000 Gaji bulanan` — lalu buka menu Saldo, harus muncul Rp 50.000
- `/keluar 20000 Makan siang` — lalu buka menu Laporan, harus muncul ringkasan masuk/keluar
- Buka menu Transaksi — harus muncul 2 transaksi yang baru dicatat
- `/reset_data` — lalu cek menu Saldo, harus kembali ke Rp 0

Kemudian tekan tombol pada menu.

Kirim `halo` atau teks biasa. Bot tidak akan membalas karena tidak ada handler untuk pesan teks biasa.

## Tentang Database (SQLite)

Database memakai **SQLite** — tersimpan sebagai satu file `data.db` di folder project, dibuat otomatis saat `bot.py` pertama kali dijalankan (lewat `database.init_db()`). Tidak perlu instalasi database server terpisah.

Setiap pengguna Telegram punya data masing-masing (dipisahkan berdasarkan `user_id`), jadi transaksi yang dicatat satu orang tidak akan tercampur dengan orang lain yang juga memakai bot ini.

**⚠️ Penting soal Railway:** sebagian besar hosting seperti Railway memakai *filesystem sementara* — artinya file `data.db` bisa **hilang setiap kali service di-restart atau di-deploy ulang**. Untuk penggunaan serius/produksi, ada 2 opsi:
1. **Railway Volume** — tambahkan disk permanen di tab Settings > Volumes, lalu arahkan `DB_PATH` di `database.py` ke path volume tersebut (misalnya `/data/data.db`). ✅ Direkomendasikan.
2. **Database eksternal** — ganti SQLite dengan PostgreSQL (Railway punya plugin PostgreSQL siap pakai) untuk skala lebih besar/multi-service.

Untuk belajar dan penggunaan personal skala kecil, SQLite tanpa Volume sudah cukup — cuma perlu diingat datanya bisa reset kalau ada redeploy.

## Menambah/Mengubah Konten Info & Referensi

Semua isi menu `/info` disimpan di satu tempat: dictionary `INFO_CONTENT` di `bot.py`. Untuk menambah topik baru:

1. Tambahkan entri baru ke `INFO_CONTENT`, contoh:
   ```python
   "info_kontak": {
       "title": "📞 KONTAK",
       "text": "📞 *KONTAK*\n\nHubungi admin di @username_anda",
   },
   ```
2. Tambahkan tombolnya di fungsi `info_menu_keyboard()`:
   ```python
   [InlineKeyboardButton("📞 Kontak", callback_data="info_kontak")],
   ```
3. Simpan dan jalankan ulang bot — tidak perlu mengubah `button_handler`, karena sudah otomatis membaca dari `INFO_CONTENT`.

## 4. Upload ke GitHub

Buat repository kosong bernama `telegram-command-bot`, lalu dari folder project:

```powershell
git init
git add .
git commit -m "Initial Telegram command bot"
git branch -M main
git remote add origin https://github.com/USERNAME/telegram-command-bot.git
git push -u origin main
```

Pastikan token tidak pernah masuk ke file atau commit GitHub.

## 5. Deploy ke Railway

1. Login ke Railway.
2. Klik `New Project`.
3. Pilih deploy dari GitHub repository.
4. Pilih `telegram-command-bot`.
5. Setelah service dibuat, buka tab `Variables`.
6. Tambahkan:
   - Name: `BOT_TOKEN`
   - Value: token dari BotFather
7. Pastikan deployment menggunakan service persistent/always-running untuk polling.
8. Buka Settings dan periksa Start Command. Jika Railway tidak mendeteksinya sesuai kebutuhan, isi:

```text
python bot.py
```

9. Deploy perubahan variables.
10. Buka deployment logs dan pastikan proses Python tetap berjalan tanpa error.

## 6. Tes setelah Railway aktif

Buka bot Telegram dan tes:

```text
/start
/menu
/info
/help
```

Lalu tekan tombol menu.

## Catatan arsitektur

Bot ini memakai polling, bukan webhook. Tidak diperlukan ngrok untuk versi ini.

Polling membutuhkan proses bot yang terus berjalan. Karena itu service Railway harus tetap hidup. Jika dijalankan hanya di komputer lokal, komputer dan proses Python harus menyala.

## Keamanan

Jangan menyimpan token di `bot.py`.

Jangan commit file `.env`.

Gunakan Railway Variables untuk `BOT_TOKEN`.

Jika token bocor, cabut/ganti token melalui BotFather.

## Pengembangan berikutnya

Struktur ini siap diperluas menjadi:

- login/admin
- database PostgreSQL
- laporan keuangan
- saldo
- transaksi
- webhook payment gateway
- integrasi WhatsApp atau sistem lain

## Menjaga Kuota Trial Railway ($5 / ~30 hari)

Railway **tidak punya tombol "Pause" resmi** yang membekukan service jadi 0 biaya sambil tetap menyimpan pengaturan — tapi ada cara yang secara efektif setara:

### Cara menghentikan pemakaian (tanpa menghapus project)

1. Buka project bot kamu di dashboard Railway
2. Klik service bot-nya
3. Buka tab **Deployments**
4. Klik ikon **titik tiga (⋯)** di deployment yang sedang aktif (paling atas)
5. Pilih **Remove**

Setelah di-*Remove*, service **berhenti total** (tidak makan kuota CPU/RAM sama sekali), tapi seluruh pengaturan — Variables (`BOT_TOKEN`), koneksi GitHub, dan riwayat deployment — **tetap tersimpan**, tidak hilang.

### Cara mengaktifkan lagi

1. Buka tab **Deployments** yang sama
2. Cari deployment yang tadi di-*Remove* (masih ada di riwayat, ditandai "Removed")
3. Klik titik tiga (⋯) pada deployment tersebut → pilih **Redeploy**

Bot akan aktif lagi dalam hitungan detik, tanpa perlu setting ulang dari awal.

### Kenapa bukan pakai fitur "App Sleeping" bawaan Railway?

Railway punya fitur *sleep otomatis* untuk service yang tidak menerima traffic HTTP. Tapi bot ini memakai **polling** (bot yang terus-menerus "bertanya" ke server Telegram), bukan menerima HTTP request dari luar — jadi fitur sleep otomatis **tidak akan aktif** untuk jenis bot ini walau tidak ada yang chat. Karena itu, cara *Remove Deployment* di atas adalah cara paling efektif untuk bot jenis ini.

### Tips tambahan

- Cek pemakaian kredit secara berkala di menu **Usage** pada dashboard Railway
- Kalau kamu punya beberapa project percobaan sekaligus, **Remove** deployment project yang sedang tidak dipakai/diuji, sisakan hanya 1 yang aktif
- Kuota $5 reset per siklus (biasanya bulanan untuk plan Hobby, atau sekali untuk trial baru) — jadi kebiasaan "matikan kalau tidak dipakai" ini akan sangat membantu menyisakan kuota untuk project-project berikutnya

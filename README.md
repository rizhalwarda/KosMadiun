# KosMadiun — mini proyek prediksi harga kos

Aplikasi Streamlit dengan backend API Django untuk memperkirakan harga sewa kos bulanan di Madiun menggunakan regresi Ridge. Antarmuka memiliki header dan footer serta ikon bulan/matahari untuk mengganti tema terang dan gelap. Setelah tombol prediksi diklik, aplikasi memperbarui grafik dengan batang khusus input pengguna dan menampilkan penjelasan otomatis dari hasil model serta ringkasan data. Fitur ini tidak memerlukan API key Groq.

## Dataset dan model

Dataset `Mini Proyek/kos_madiun.csv` berisi 30 baris data terbuka (`nama`, `jarak_km`, `harga`, `ac`, `rating`). Sumber: [repositori P7-Sicer](https://github.com/rizhalwarda/P7-Sicer), file `kos_madiun.csv` pada cabang `main`. Metadata repositori tidak mencantumkan lisensi dataset; cantumkan atribusi sumber dan mintakan izin pemilik sebelum redistribusi publik. Kolom `harga` dinyatakan dalam ribuan rupiah, sehingga nilai 600 berarti Rp600.000 per bulan. Model Ridge memakai jarak, fasilitas AC, dan rating sebagai fitur; nama kos tidak digunakan. Implementasi regresi mandiri tanpa library numerik; model dilatih saat backend pertama kali memerlukan prediksi dan disimpan sebagai `Mini Proyek/model_kos.json`.

Grafik merangkum harga rata-rata untuk kelompok jarak bulat. Estimasi dan grafik bersifat edukatif, bukan jaminan harga pasar.

## Menjalankan di Windows

Dari folder `D:\Mini Proyek`, buka terminal pertama untuk backend:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
cd '.\Mini Proyek'
python -m pip install -r ..\requirements.txt -r requirements-api.txt
python manage.py migrate
python manage.py runserver
```

Buka terminal kedua untuk frontend Streamlit:

```powershell
cd 'D:\Mini Proyek'
.\.venv\Scripts\Activate.ps1
cd '.\Mini Proyek'
python -m streamlit run app.py
```

Buka http://localhost:8501. Django API berjalan pada http://127.0.0.1:8000. Bila backend di alamat lain, atur `DJANGO_API_URL` sebelum menjalankan Streamlit.

## Deploy gratis: Django API di Vercel + Streamlit di Community Cloud

Frontend Streamlit dan API Django dideploy sebagai dua layanan. Streamlit Community Cloud menggunakan `requirements.txt` di root repositori (tanpa path folder yang mengandung spasi), sedangkan Vercel hanya memasang Django dari `Mini Proyek/requirements-api.txt`. Pemisahan ini mencegah Vercel memasang Streamlit, pandas, dan pyarrow ke dalam fungsi API.

### 1. Deploy API Django ke Vercel

1. Push proyek ke repositori GitHub.
2. Import repositori tersebut ke Vercel. Atur **Root Directory** ke `Mini Proyek`. File `Mini Proyek/vercel.json` mengarahkan semua URL ke Django WSGI; pastikan file ini ikut ter-commit.
3. Di **Project Settings → Build and Deployment**, isi **Install Command** dengan `pip install -r requirements-api.txt`.
4. Tambahkan environment variables berikut di Vercel (Production, Preview, dan Development sesuai kebutuhan):

   | Nama | Nilai |
   | --- | --- |
   | `DJANGO_SECRET_KEY` | Secret acak yang kuat dan rahasia; jangan commit ke Git |
   | `DJANGO_DEBUG` | `False` |
   | `ALLOWED_HOSTS` | `.vercel.app` dan, bila ada, hostname domain sendiri dipisah koma |
   | `GROQ_API_KEY` | Opsional; secret Groq untuk membuat penjelasan AI |
   | `GROQ_MODEL` | Opsional; misalnya `openai/gpt-oss-120b` |

5. Deploy. Salin URL deployment API Vercel, misalnya `https://nama-proyek.vercel.app`. Endpoint prediksi API tersedia di `/api/predict/`.

`DJANGO_SECRET_KEY` wajib diisi sebelum deployment karena konfigurasi produksi menolak secret yang kosong. `.vercel.app` pada `ALLOWED_HOSTS` mencakup subdomain deployment Vercel; tambahkan hostname domain khusus jika digunakan. Vercel mendukung runtime Python dan Django. Perintah install khusus digunakan di sini agar hanya dependensi backend yang dipasang.

### 2. Deploy frontend Streamlit Community Cloud

1. Buat aplikasi baru di [Streamlit Community Cloud](https://share.streamlit.io/) dari repositori yang sama.
2. Pilih branch yang digunakan, lalu isi **Main file path** dengan `Mini Proyek/app.py`.
3. Di pengaturan **Secrets** aplikasi, isi:

   ```toml
   DJANGO_API_URL = "https://nama-proyek.vercel.app"
   ```

   Ganti URL contoh dengan URL deployment API Anda. Jangan menambahkan `/api/predict/` di akhir karena frontend menambahkan path endpoint sendiri.

4. Deploy aplikasi Streamlit. `DJANGO_API_URL` diambil dari Streamlit secrets; saat berjalan lokal, aplikasi tetap memakai `http://127.0.0.1:8000` secara default.

Simpan `GROQ_API_KEY` hanya di environment variables Vercel, bukan di Streamlit Cloud, karena panggilan Groq dilakukan oleh backend Django. File dependensi Streamlit berada di root repositori, sehingga tidak perlu ditemukan melalui path `Mini Proyek/requirements.txt` yang mengandung spasi.

Jika build Vercel masih memberi batas ukuran fungsi, pastikan Root Directory dan Install Command tepat serta tidak memilih `requirements.txt` utama untuk fungsi backend. Opsi Large Functions Vercel dapat menjadi alternatif, tetapi dependensi backend saja seharusnya menghindari paket ML/visualisasi yang sebelumnya memperbesar bundel.

Penjelasan otomatis membahas grafik, hasil estimasi, serta tiga kos referensi dan selisih harga aktualnya dibandingkan dengan estimasi. Jika `GROQ_API_KEY` tersedia di environment backend, Groq menyusun penjelasan tersebut otomatis. Tanpa API key atau saat API tidak tersedia, backend menggunakan penjelasan lokal dengan data perbandingan yang sama. Untuk mengaktifkan Groq, atur variabel berikut di terminal backend sebelum `runserver`:

```powershell
$env:GROQ_API_KEY = 'gsk_...'
$env:GROQ_MODEL = 'openai/gpt-oss-120b'
```

## Pembagian tugas kelompok

Isi nama anggota dan tugas nyata kelompok sebelum demo (rubrik modul meminta pembagian peran tercatat):

| Anggota | Tanggung jawab |
| --- | --- |
| Nama anggota 1 | Pengolahan data dan pemodelan |
| Nama anggota 2 | Backend Django dan API |
| Nama anggota 3 | Antarmuka Streamlit dan grafik |
| Nama anggota 4 (jika ada) | Penjelasan hasil, dokumentasi, dan demo |

## Struktur utama

- `Mini Proyek/app.py` — antarmuka Streamlit: form input, hasil prediksi, grafik batang, dan penjelasan otomatis.
- `Mini Proyek/prediksi/services.py` — pembacaan CSV, pelatihan regresi Ridge, inferensi, dan penyimpanan koefisien model JSON.
- `Mini Proyek/prediksi/views.py` — endpoint Django untuk prediksi, data grafik, dan penjelasan lokal otomatis.
- `Mini Proyek/kos_madiun.csv` — dataset sumber yang diberikan.

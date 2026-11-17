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
python -m pip install -r ..\requirements.txt
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

Penjelasan otomatis membahas grafik, hasil estimasi, serta tiga kos referensi dan selisih harga aktualnya dibandingkan dengan estimasi. Jika `GROQ_API_KEY` tersedia di environment backend, Groq menyusun penjelasan tersebut otomatis. Tanpa API key atau saat API tidak tersedia, backend menggunakan penjelasan lokal dengan data perbandingan yang sama. Untuk mengaktifkan Groq, atur variabel berikut di terminal backend sebelum `runserver`:

```powershell
$env:GROQ_API_KEY = 'gsk_...'
$env:GROQ_MODEL = 'llama-3.3-70b-versatile'
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

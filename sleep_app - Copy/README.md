# 🌙 SleepTrack — Sistem Pemantauan Pola Tidur Mahasiswa
**Project UAS Pemrograman Berorientasi Objek**

## Cara Menjalankan

```bash
# 1. Install dependensi
pip install -r requirements.txt

# 2. Jalankan aplikasi
python app.py

# 3. Buka browser
# http://localhost:5000

# Demo login:
# Email: demo@mahasiswa.ac.id
# Password: demo123
```

## Struktur OOP

| Class | Peran |
|---|---|
| `User` | Mengelola data pengguna (Encapsulation) |
| `SleepRecord` | Menyimpan satu entri data tidur (Encapsulation) |
| `Analyzer` | Abstract class dengan method `analyze()` |
| `SleepAnalyzer` | Analisis dasar (Inheritance dari Analyzer) |
| `AdvancedSleepAnalyzer` | Analisis lanjutan sleep debt & weekly trend (Inheritance) |
| `RecommendationEngine` | Rekomendasi perbaikan tidur (Encapsulation) |

## Konsep OOP yang Diterapkan

- **Inheritance**: `AdvancedSleepAnalyzer` mewarisi `SleepAnalyzer`
- **Encapsulation**: Atribut private pada `User` & `SleepRecord` dengan getter/setter
- **Abstract Class**: `Analyzer` (ABC) dengan method `analyze()` wajib diimplementasikan
- **Polymorphism**: `analyze()` berperilaku berbeda di `SleepAnalyzer` vs `AdvancedSleepAnalyzer`

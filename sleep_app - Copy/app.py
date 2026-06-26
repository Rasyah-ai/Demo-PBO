"""
Sistem Pemantauan dan Analisis Pola Tidur Mahasiswa
Project UAS Pemrograman Berorientasi Objek
"""
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
from abc import ABC, abstractmethod
from datetime import datetime, date, timedelta, time
import sqlite3
import json
import os

app = Flask(__name__)
app.secret_key = "sleep_tracker_secret_2024"

DB_PATH = os.path.join(os.path.dirname(__file__), "sleep_data.db")

# ─────────────────────────────────────────────
# OOP LAYER
# ─────────────────────────────────────────────

class Analyzer(ABC):
    """Abstract base class untuk semua jenis analisis (Abstract Class)"""

    @abstractmethod
    def analyze(self, records: list) -> dict:
        """Metode abstrak yang harus diimplementasikan subclass"""
        pass

    @abstractmethod
    def get_summary(self, records: list) -> str:
        pass


class SleepRecord:
    """Menyimpan satu data tidur harian (Encapsulation)"""

    def __init__(self, record_id, user_id, sleep_date, sleep_time, wake_time, notes=""):
        self._record_id = record_id
        self._user_id = user_id
        self._date = sleep_date
        self._sleep_time = sleep_time
        self._wake_time = wake_time
        self._notes = notes
        self._duration = self._calculate_duration()

    def _calculate_duration(self) -> float:
        """Hitung durasi tidur dalam jam"""
        try:
            if isinstance(self._sleep_time, str):
                s = datetime.strptime(self._sleep_time, "%H:%M")
            else:
                s = datetime.combine(date.today(), self._sleep_time)
            if isinstance(self._wake_time, str):
                w = datetime.strptime(self._wake_time, "%H:%M")
            else:
                w = datetime.combine(date.today(), self._wake_time)
            if w <= s:
                w += timedelta(days=1)
            return round((w - s).seconds / 3600, 2)
        except Exception:
            return 0.0

    # Getters
    def get_record_id(self): return self._record_id
    def get_user_id(self): return self._user_id
    def get_date(self): return self._date
    def get_sleep_time(self): return self._sleep_time
    def get_wake_time(self): return self._wake_time
    def get_duration(self): return self._duration
    def get_notes(self): return self._notes

    def get_quality(self) -> str:
        """Kategori kualitas tidur berdasarkan durasi"""
        d = self._duration
        if d >= 7 and d <= 9:
            return "Sangat Baik"
        elif d >= 6 and d < 7:
            return "Cukup"
        elif d > 9:
            return "Terlalu Panjang"
        elif d >= 5 and d < 6:
            return "Kurang"
        else:
            return "Sangat Kurang"

    def get_quality_score(self) -> int:
        d = self._duration
        if d >= 7 and d <= 9:
            return 100
        elif d >= 6:
            return 70
        elif d >= 5:
            return 45
        else:
            return 20

    def to_dict(self) -> dict:
        return {
            "record_id": self._record_id,
            "user_id": self._user_id,
            "date": str(self._date),
            "sleep_time": str(self._sleep_time),
            "wake_time": str(self._wake_time),
            "duration": self._duration,
            "quality": self.get_quality(),
            "quality_score": self.get_quality_score(),
            "notes": self._notes,
        }


class SleepAnalyzer(Analyzer):
    """Menganalisis kualitas tidur dasar (Inheritance dari Analyzer)"""

    def analyze(self, records: list) -> dict:
        if not records:
            return {"status": "no_data"}
        durations = [r.get_duration() for r in records]
        avg = round(sum(durations) / len(durations), 2)
        return {
            "total_records": len(records),
            "avg_duration": avg,
            "min_duration": round(min(durations), 2),
            "max_duration": round(max(durations), 2),
            "quality_dist": self._quality_distribution(records),
            "status": "ok"
        }

    def get_summary(self, records: list) -> str:
        res = self.analyze(records)
        if res["status"] == "no_data":
            return "Belum ada data tidur yang dicatat."
        return (f"Rata-rata durasi tidur: {res['avg_duration']} jam "
                f"dari {res['total_records']} hari tercatat.")

    def get_avg_duration(self, records: list) -> float:
        if not records:
            return 0
        return round(sum(r.get_duration() for r in records) / len(records), 2)

    def get_consistency(self, records: list) -> float:
        """Skor konsistensi jam tidur (0-100)"""
        if len(records) < 2:
            return 100.0
        times = []
        for r in records:
            t = r.get_sleep_time()
            if isinstance(t, str):
                h, m = map(int, t.split(":"))
            else:
                h, m = t.hour, t.minute
            mins = h * 60 + m
            if mins < 300:  # midnight adjustment
                mins += 1440
            times.append(mins)
        avg_t = sum(times) / len(times)
        variance = sum((t - avg_t) ** 2 for t in times) / len(times)
        std = variance ** 0.5
        score = max(0, 100 - std * 0.5)
        return round(score, 1)

    def _quality_distribution(self, records: list) -> dict:
        dist = {"Sangat Baik": 0, "Cukup": 0, "Kurang": 0, "Sangat Kurang": 0, "Terlalu Panjang": 0}
        for r in records:
            q = r.get_quality()
            if q in dist:
                dist[q] += 1
        return dist


class AdvancedSleepAnalyzer(SleepAnalyzer):
    """Analisis lanjutan: sleep debt & weekly trend (Inheritance dari SleepAnalyzer)"""

    IDEAL_SLEEP = 8.0  # jam ideal per malam

    def analyze(self, records: list) -> dict:
        base = super().analyze(records)
        if base["status"] == "no_data":
            return base
        base["sleep_debt"] = self.calculate_sleep_debt(records)
        base["weekly_trend"] = self.get_weekly_trend(records)
        base["consistency_score"] = self.get_consistency(records)
        return base

    def get_summary(self, records: list) -> str:
        res = self.analyze(records)
        if res["status"] == "no_data":
            return "Belum ada data tidur."
        debt = res["sleep_debt"]
        status = "defisit" if debt > 0 else "surplus"
        return (f"Rata-rata {res['avg_duration']} jam/malam. "
                f"Sleep {status}: {abs(debt):.1f} jam. "
                f"Konsistensi: {res['consistency_score']}/100.")

    def calculate_sleep_debt(self, records: list) -> float:
        """Hitung kumulatif sleep debt (jam ideal - jam aktual)"""
        total = sum(self.IDEAL_SLEEP - r.get_duration() for r in records)
        return round(total, 2)

    def get_weekly_trend(self, records: list) -> list:
        """Rata-rata durasi tidur per hari dalam 7 hari terakhir"""
        today = date.today()
        result = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            day_records = [r for r in records if str(r.get_date()) == str(d)]
            avg = round(sum(r.get_duration() for r in day_records) / len(day_records), 2) if day_records else 0
            result.append({"date": d.strftime("%d/%m"), "avg": avg})
        return result


class RecommendationEngine:
    """Memberikan rekomendasi perbaikan pola tidur (Encapsulation)"""

    def __init__(self):
        self._thresholds = {
            "min_ideal": 7.0,
            "max_ideal": 9.0,
            "consistency_good": 75,
        }

    # Getter & Setter (Encapsulation)
    def get_thresholds(self): return self._thresholds.copy()
    def set_threshold(self, key, value): self._thresholds[key] = value

    def recommend(self, analysis: dict) -> list:
        tips = []
        avg = analysis.get("avg_duration", 0)
        consistency = analysis.get("consistency_score", 100)
        debt = analysis.get("sleep_debt", 0)

        if avg < self._thresholds["min_ideal"]:
            tips.append({
                "type": "warning",
                "icon": "⚠️",
                "title": "Durasi Tidur Kurang",
                "message": f"Rata-rata tidurmu {avg} jam, kurang dari ideal 7-9 jam. Coba tidur 30 menit lebih awal malam ini."
            })
        elif avg > self._thresholds["max_ideal"]:
            tips.append({
                "type": "info",
                "icon": "💤",
                "title": "Durasi Tidur Berlebih",
                "message": f"Tidur {avg} jam melebihi anjuran. Tidur berlebih juga bisa membuatmu lemas sepanjang hari."
            })
        else:
            tips.append({
                "type": "success",
                "icon": "✅",
                "title": "Durasi Tidur Ideal",
                "message": f"Keren! Rata-rata tidurmu {avg} jam sudah dalam rentang ideal. Pertahankan!"
            })

        if consistency < self._thresholds["consistency_good"]:
            tips.append({
                "type": "warning",
                "icon": "🕐",
                "title": "Jam Tidur Tidak Konsisten",
                "message": "Jam tidurmu terlalu bervariasi. Coba tetapkan jam tidur dan bangun yang sama setiap hari, termasuk akhir pekan."
            })
        else:
            tips.append({
                "type": "success",
                "icon": "🗓️",
                "title": "Konsistensi Jadwal Bagus",
                "message": "Jadwal tidurmu cukup konsisten. Tubuh dan otakmu akan berterima kasih!"
            })

        if debt > 7:
            tips.append({
                "type": "danger",
                "icon": "🚨",
                "title": f"Sleep Debt Tinggi ({debt:.1f} jam)",
                "message": "Utang tidurmu sudah cukup besar. Hindari mengejar tidur sekaligus di akhir pekan, cicil dengan tidur 15-30 menit lebih awal setiap malam."
            })

        tips.append({
            "type": "tip",
            "icon": "📵",
            "title": "Tips Umum",
            "message": "Hindari layar gadget minimal 1 jam sebelum tidur. Cahaya biru menghambat produksi melatonin yang membantumu terlelap lebih cepat."
        })
        return tips

    def get_tips(self) -> list:
        return [
            "Pertahankan jadwal tidur yang konsisten setiap hari",
            "Hindari kafein setelah jam 2 siang",
            "Buat suasana kamar gelap, sejuk, dan tenang",
            "Olahraga teratur, tetapi tidak terlalu dekat dengan jam tidur",
            "Relaksasi 30 menit sebelum tidur (membaca, meditasi, dll)",
        ]


class User:
    """Mengelola data dan profil pengguna (Encapsulation)"""

    def __init__(self, user_id, name, email):
        self._user_id = user_id
        self._name = name
        self._email = email
        self._records: list[SleepRecord] = []

    # Getters & Setters
    def get_user_id(self): return self._user_id
    def get_name(self): return self._name
    def set_name(self, name): self._name = name
    def get_email(self): return self._email
    def set_email(self, email): self._email = email
    def get_records(self): return self._records

    def add_record(self, record: SleepRecord):
        self._records.append(record)

    def to_dict(self) -> dict:
        return {"user_id": self._user_id, "name": self._name, "email": self._email}


# ─────────────────────────────────────────────
# DATABASE LAYER
# ─────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sleep_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sleep_date TEXT NOT NULL,
            sleep_time TEXT NOT NULL,
            wake_time TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    # Insert demo user
    c.execute("SELECT id FROM users WHERE email='demo@mahasiswa.ac.id'")
    if not c.fetchone():
        c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                ("Demo Mahasiswa", "demo@mahasiswa.ac.id", "demo123"))
        uid = c.lastrowid
        # Add sample data for 14 days
        import random
        for i in range(14):
            d = (date.today() - timedelta(days=13 - i)).strftime("%Y-%m-%d")
            sleep_h = random.randint(22, 23)
            sleep_m = random.choice([0, 30])
            wake_h = random.randint(5, 7)
            wake_m = random.choice([0, 15, 30])
            c.execute("INSERT INTO sleep_records (user_id, sleep_date, sleep_time, wake_time) VALUES (?,?,?,?)",
                    (uid, d, f"{sleep_h}:{sleep_m:02d}", f"{wake_h}:{wake_m:02d}"))
    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_user_records(user_id: int) -> list[SleepRecord]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM sleep_records WHERE user_id=? ORDER BY sleep_date DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [SleepRecord(r["id"], r["user_id"], r["sleep_date"], r["sleep_time"], r["wake_time"], r["notes"]) for r in rows]


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        conn = get_db()
        user_row = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password)).fetchone()
        conn.close()
        if user_row:
            session["user_id"] = user_row["id"]
            session["user_name"] = user_row["name"]
            return redirect(url_for("dashboard"))
        flash("Email atau password salah.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (name, email, password) VALUES (?,?,?)", (name, email, password))
            conn.commit()
            conn.close()
            flash("Akun berhasil dibuat! Silakan login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email sudah terdaftar.", "error")
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    uid = session["user_id"]
    records = load_user_records(uid)
    analyzer = AdvancedSleepAnalyzer()
    analysis = analyzer.analyze(records)
    rec_engine = RecommendationEngine()
    recommendations = rec_engine.recommend(analysis) if analysis.get("status") == "ok" else []
    weekly = analysis.get("weekly_trend", [])
    recent = [r.to_dict() for r in records[:7]]
    return render_template("dashboard.html",
        user_name=session["user_name"],
        analysis=analysis,
        recommendations=recommendations,
        weekly=json.dumps(weekly),
        recent=recent,
        summary=analyzer.get_summary(records)
    )


@app.route("/records")
def records():
    if "user_id" not in session:
        return redirect(url_for("login"))
    records = load_user_records(session["user_id"])
    return render_template("records.html",
        user_name=session["user_name"],
        records=[r.to_dict() for r in records]
    )


@app.route("/add", methods=["GET", "POST"])
def add_record():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        sleep_date = request.form.get("sleep_date")
        sleep_time = request.form.get("sleep_time")
        wake_time = request.form.get("wake_time")
        notes = request.form.get("notes", "")
        if sleep_date and sleep_time and wake_time:
            conn = get_db()
            conn.execute(
                "INSERT INTO sleep_records (user_id, sleep_date, sleep_time, wake_time, notes) VALUES (?,?,?,?,?)",
                (session["user_id"], sleep_date, sleep_time, wake_time, notes)
            )
            conn.commit()
            conn.close()
            flash("Data tidur berhasil dicatat! 🌙", "success")
            return redirect(url_for("dashboard"))
        flash("Lengkapi semua field.", "error")
    today = date.today().strftime("%Y-%m-%d")
    return render_template("add_record.html", user_name=session["user_name"], today=today)


@app.route("/delete/<int:record_id>", methods=["POST"])
def delete_record(record_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    conn.execute("DELETE FROM sleep_records WHERE id=? AND user_id=?", (record_id, session["user_id"]))
    conn.commit()
    conn.close()
    flash("Data berhasil dihapus.", "info")
    return redirect(url_for("records"))


@app.route("/api/analysis")
def api_analysis():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401
    records = load_user_records(session["user_id"])
    analyzer = AdvancedSleepAnalyzer()
    return jsonify(analyzer.analyze(records))


if __name__ == "__main__":
    init_db()
    print("\n Sleep Tracker App berjalan!")
    print("   Buka: http://localhost:5000")
    print("   Demo login: kel5@mahasiswa.ac.id / demo123\n")
    app.run(debug=True, host="0.0.0.0", port=5000)

"""
database/db.py
Database management — shared (stocks reference) + per-user portfolio DBs
"""

import sqlite3
import os

# ─── Paths ────────────────────────────────────────────────────────────────────
DB_DIR     = os.path.dirname(__file__)
SHARED_DB  = os.path.join(DB_DIR, "shared.db")       # أسهم البورصة المشتركة
USERS_DIR  = os.path.join(DB_DIR, "users")            # محفظة كل مستخدم

os.makedirs(USERS_DIR, exist_ok=True)


# ═══════════════════════════════════════════════
# SHARED DB  — أسهم البورصة المصرية (مشترك)
# ═══════════════════════════════════════════════

def get_shared_conn():
    conn = sqlite3.connect(SHARED_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_shared_db():
    conn = get_shared_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS egyptian_stocks (
            code      TEXT PRIMARY KEY,
            name      TEXT NOT NULL,
            sector    TEXT DEFAULT 'أخرى',
            is_active INTEGER DEFAULT 1,
            added_at  DATETIME DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    conn.close()
    print("[SharedDB] Initialized.")


def seed_egyptian_stocks():
    stocks = [
        ("COMI", "البنك التجاري الدولي (مصر)", "بنوك"),
        ("ORWE", "النساجون الشرقيون", "منسوجات وسلع معمرة"),
        ("CSAG", "القناة للتوكيلات الملاحية", "خدمات النقل والشحن"),
        ("FERC", "فيركيم لتصنيع الأسمدة", "كيماويات"),
        ("ADCI", "العربية للأدوية والصناعات الكيماوية (أدكو)", "رعاية صحية وأدوية"),
        ("IBCT", "انترناشيونال بزنيس كوربوريشن", "خدمات تجارية وتوزيع"),
        ("ACTF", "أكت فاينانشال للاستشارات", "خدمات مالية غير مصرفية"),
        ("VLMRA", "فالمور للاستثمار العقاري", "عقارات"),
        ("LCSW", "ليسيكو مصر", "مواد بناء"),
        ("EXPA", "البنك المصري لتنمية الصادرات", "بنوك"),
        ("CIEB", "بنك كريدي أجريكول مصر", "بنوك"),
        ("KRDI", "نهر الخير للتنمية والاستثمار الزراعي", "زراعة وأغذية"),
        ("LUTS", "لوتس للتنمية والاستثمار الزراعي", "زراعة وأغذية"),
        ("COPR", "كوبر للاستثمار التجاري والتطوير العقاري", "عقارات"),
        ("PHTV", "بيراميزا للفنادق والقرى السياحية", "سياحة وترفيه"),
        ("RAYA", "راية القابضة للاستثمارات المالية", "خدمات مالية غير مصرفية"),
        ("RACC", "راية لخدمات مراكز الاتصالات", "اتصالات وتكنولوجيا المعلومات"),
        ("DGTZ", "ديجيتايز للاستثمار والتقنية", "تكنولوجيا معلومات"),
        ("HBCO", "هيبكو للاستثمارات التجارية والتنمية العقارية", "عقارات"),
        ("MBSC", "مصر بنى سويف للأسمنت", "مواد بناء"),
        ("DOMT", "الصناعات الغذائية العربية (دومتي)", "أغذية ومشروبات"),
        ("EFID", "إيديتا للصناعات الغذائية", "أغذية ومشروبات"),
        ("OLFI", "عبور لاند للصناعات الغذائية", "أغذية ومشروبات"),
        ("ICFC", "الدولية للأسمدة والكيماويات", "كيماويات"),
        ("IFAP", "الدولية للمحاصيل الزراعية", "زراعة وأغذية"),
        ("HELI", "مصر الجديدة للإسكان والتعمير", "عقارات"),
        ("MASR", "مدينة مصر للإسكان والتعمير", "عقارات"),
        ("ZMID", "زهراء المعادي للاستثمار والتعمير", "عقارات"),
        ("ORAS", "أوراسكوم كونستراكشون بي إل سي", "مقاولات وإنشاءات هندسية"),
        ("FAIT", "بنك فيصل الإسلامي المصري", "بنوك"),
        ("QNBK", "بنك قطر الوطني (QNB)", "بنوك"),
        ("SAUD", "بنك البركة مصر", "بنوك"),
        ("HDBK", "بنك التعمير والإسكان", "بنوك"),
        ("CANA", "بنك قناة السويس", "بنوك"),
        ("ADIB", "مصرف أبوظبي الإسلامي - مصر", "بنوك"),
        ("FWRY", "فوري لتكنولوجيا البنوك والمدفوعات الإلكترونية", "خدمات مالية غير مصرفية"),
        ("ATLC", "التوفيق للتأجير التمويلي", "خدمات مالية غير مصرفية"),
        ("CPCI", "القاهرة للأدوية والصناعات الكيماوية", "رعاية صحية وأدوية"),
        ("MPCI", "ممفيس للأدوية والصناعات الكيماوية", "رعاية صحية وأدوية"),
        ("NIPH", "النيل للأدوية والصناعات الكيماوية", "رعاية صحية وأدوية"),
        ("PHAR", "المصرية الدولية للصناعات الدوائية (ايبيكو)", "رعاية صحية وأدوية"),
        ("EGCH", "الصناعات الكيماوية المصرية (كيما)", "كيماويات"),
        ("MICH", "مصر لصناعة الكيماويات", "كيماويات"),
        ("MCQE", "مصر لأسمنت قنا", "مواد بناء"),
        ("SVCE", "جنوب الوادي للأسمنت", "مواد بناء"),
        ("ARCC", "العربية للأسمنت", "مواد بناء"),
        ("SCEM", "أسمنت سيناء", "مواد بناء"),
        ("MFPC", "مصر لإنتاج الأسمدة (موبكو)", "كيماويات"),
        ("TMGH", "مجموعة طلعت مصطفى القابضة", "عقارات"),
        ("SWDY", "السويدي إليكتريك", "طاقة وبنية تحتية"),
        ("ETEL", "المصرية للاتصالات", "اتصالات وتكنولوجيا المعلومات"),
        ("EGAL", "مصر للألومنيوم", "موارد أساسية"),
        ("EAST", "الشرقية - إيسترن كومباني", "تبغ وسلع استهلاكية"),
        ("ABUK", "أبو قير للأسمدة والصناعات الكيماوية", "كيماويات"),
        ("ALCN", "الإسكندرية لتداول الحاويات والبضائع", "خدمات النقل والشحن"),
        ("HRHO", "مجموعة إي إف جي القابضة (هيرميس)", "خدمات مالية غير مصرفية"),
        ("EFIH", "إي فاينانس للاستثمارات المالية والرقمية", "تكنولوجيا معلومات"),
        ("SUGR", "الدلتا للسكر", "أغذية ومشروبات"),
        ("DTPP", "دلتا للطباعة والتغليف", "ورق وتغليف"),
        ("GSSC", "العامة للصوامع والتخزين", "خدمات النقل والشحن"),
        ("MFSC", "مصر للأسواق الحرة", "تجارة وتوزيع"),
        ("MHOT", "مصر للفنادق", "سياحة وترفيه"),
        ("ELEC", "الكابلات الكهربائية المصرية", "صناعة"),
        ("EGAS", "غاز مصر", "طاقة وبنية تحتية"),
        ("MOIN", "المهندس للتأمين", "خدمات مالية غير مصرفية"),
        ("ASCM", "أسيك للتعدين (أسكوم)", "موارد أساسية"),
        ("MPRC", "المصرية لمدينة الإنتاج الإعلامي", "إعلام وترفيه"),
    ]
    conn = get_shared_conn()
    conn.executemany(
        "INSERT OR IGNORE INTO egyptian_stocks (code, name, sector) VALUES (?,?,?)",
        stocks
    )
    conn.commit()
    conn.close()
    print(f"[SharedDB] Seeded {len(stocks)} stocks.")


def search_stocks(query: str) -> list:
    conn = get_shared_conn()
    rows = conn.execute("""
        SELECT code, name, sector FROM egyptian_stocks
        WHERE (code LIKE ? OR name LIKE ?) AND is_active = 1
        ORDER BY code LIMIT 20
    """, (f"%{query.upper()}%", f"%{query}%")).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stock_by_code(code: str):
    conn = get_shared_conn()
    row = conn.execute(
        "SELECT code, name, sector FROM egyptian_stocks WHERE code = ? AND is_active = 1",
        (code.upper().strip(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def add_stock_to_shared(code: str, name: str, sector: str = "أخرى") -> dict:
    code = code.upper().strip()
    conn = get_shared_conn()
    conn.execute(
        "INSERT OR REPLACE INTO egyptian_stocks (code, name, sector) VALUES (?,?,?)",
        (code, name, sector)
    )
    conn.commit()
    conn.close()
    return {"success": True, "message": f"تم إضافة {code} — {name}"}


def get_all_stocks() -> list:
    conn = get_shared_conn()
    rows = conn.execute(
        "SELECT code, name, sector FROM egyptian_stocks WHERE is_active=1 ORDER BY code"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def bulk_add_stocks(stocks: list) -> dict:
    """
    Bulk insert list of dicts: [{code, name, sector}, ...]
    Returns count of added stocks.
    """
    data = [(s["code"].upper().strip(), s["name"].strip(), s.get("sector", "أخرى")) for s in stocks]
    conn = get_shared_conn()
    cursor = conn.executemany(
        "INSERT OR REPLACE INTO egyptian_stocks (code, name, sector) VALUES (?,?,?)",
        data
    )
    conn.commit()
    added = cursor.rowcount
    conn.close()
    return {"success": True, "added": added, "message": f"تم إضافة {added} سهم بنجاح"}


# ═══════════════════════════════════════════════
# USER DB  — محفظة خاصة بكل مستخدم
# ═══════════════════════════════════════════════

def _user_db_path(username: str) -> str:
    safe = "".join(c for c in username if c.isalnum() or c in "-_")
    return os.path.join(USERS_DIR, f"{safe}.db")


def get_user_conn(username: str):
    conn = sqlite3.connect(_user_db_path(username))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_user_db(username: str):
    conn = get_user_conn(username)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS transactions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            type           TEXT NOT NULL CHECK(type IN ('buy','sell','deposit','withdraw')),
            stock_code     TEXT,
            stock_name     TEXT,
            quantity       INTEGER,
            amount         REAL NOT NULL,
            price_per_share REAL,
            notes          TEXT,
            created_at     DATETIME DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS holdings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code  TEXT NOT NULL UNIQUE,
            stock_name  TEXT NOT NULL,
            quantity    INTEGER NOT NULL DEFAULT 0,
            total_cost  REAL    NOT NULL DEFAULT 0,
            avg_price   REAL    NOT NULL DEFAULT 0,
            updated_at  DATETIME DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS account (
            id               INTEGER PRIMARY KEY CHECK(id = 1),
            display_name     TEXT DEFAULT '',
            total_deposited  REAL NOT NULL DEFAULT 0,
            total_withdrawn  REAL NOT NULL DEFAULT 0,
            cash_balance     REAL NOT NULL DEFAULT 0,
            updated_at       DATETIME DEFAULT (datetime('now','localtime'))
        );

        INSERT OR IGNORE INTO account (id, total_deposited, total_withdrawn, cash_balance)
        VALUES (1, 0, 0, 0);
    """)
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════
# USERS REGISTRY  — قائمة المستخدمين
# ═══════════════════════════════════════════════

REGISTRY_DB = os.path.join(DB_DIR, "registry.db")


def get_registry_conn():
    conn = sqlite3.connect(REGISTRY_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_registry():
    conn = get_registry_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username     TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            created_at   DATETIME DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    conn.close()


def list_users() -> list:
    conn = get_registry_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY display_name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_user(username: str, display_name: str) -> dict:
    safe = "".join(c for c in username if c.isalnum() or c in "-_")
    if not safe:
        raise ValueError("اسم المستخدم غير صالح")
    conn = get_registry_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, display_name) VALUES (?,?)",
            (safe, display_name.strip())
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError(f"المستخدم '{safe}' موجود بالفعل")
    finally:
        conn.close()
    init_user_db(safe)
    return {"username": safe, "display_name": display_name.strip()}


def user_exists(username: str) -> bool:
    conn = get_registry_conn()
    row = conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return row is not None


# ═══════════════════════════════════════════════
# BOOTSTRAP
# ═══════════════════════════════════════════════

def bootstrap():
    init_shared_db()
    init_registry()
    # seed only if empty
    conn = get_shared_conn()
    count = conn.execute("SELECT COUNT(*) FROM egyptian_stocks").fetchone()[0]
    conn.close()
    if count == 0:
        seed_egyptian_stocks()
    else:
        print(f"[SharedDB] {count} stocks already loaded.")

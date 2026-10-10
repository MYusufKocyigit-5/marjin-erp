import sqlite3
from pathlib import Path

DB_PATH = Path.home() / "marjin_erp_data.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def initialize_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, import_id INTEGER,
        siparis_no TEXT, siparis_tarihi TEXT, stok_kodu TEXT, urun_adi TEXT, model_kodu TEXT,
        adet INTEGER, birim_fiyat REAL, satis_tutari REAL, indirim_tutari REAL,
        trendyol_indirim REAL, faturalanacak_tutar REAL,
        kdv_tutari REAL DEFAULT 0, faturalanacak_kdvsiz REAL DEFAULT 0,
        komisyon_orani REAL, komisyon_tutari REAL, kargo_firmasi TEXT,
        kargo_tutari REAL, koli_id INTEGER, koli_adi TEXT,
        koli_desi REAL DEFAULT 0, koli_maliyet REAL DEFAULT 0,
        kargo_hesaplanan REAL DEFAULT 0, alis_maliyeti REAL DEFAULT 0,
        net_kar REAL, siparis_durumu TEXT, il TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT, stok_kodu TEXT UNIQUE,
        model_kodu TEXT, urun_adi TEXT, alis_maliyeti REAL DEFAULT 0,
        notlar TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS boxes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, koli_adi TEXT UNIQUE,
        desi REAL DEFAULT 0, alis_maliyeti REAL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS box_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT, model_kodu TEXT,
        adet INTEGER, box_id INTEGER,
        FOREIGN KEY (box_id) REFERENCES boxes(id) ON DELETE SET NULL,
        UNIQUE(model_kodu, adet))""")
    c.execute("""CREATE TABLE IF NOT EXISTS cargo_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT, firma TEXT, desi INTEGER,
        fiyat REAL, guncelleme_tarihi TEXT, UNIQUE(firma, desi))""")
    c.execute("""CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT, tur TEXT, ad TEXT,
        varyant TEXT DEFAULT '', birim TEXT DEFAULT 'Adet',
        stok REAL DEFAULT 0, kritik_esik REAL DEFAULT 0,
        alarm_aktif INTEGER DEFAULT 1,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(tur, ad, varyant))""")
    c.execute("""CREATE TABLE IF NOT EXISTS material_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT, material_id INTEGER,
        hareket_turu TEXT, miktar REAL, aciklama TEXT,
        tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (material_id) REFERENCES materials(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS imports (
        id INTEGER PRIMARY KEY AUTOINCREMENT, dosya_adi TEXT,
        siparis_sayisi INTEGER, toplam_ciro REAL, toplam_kar REAL,
        import_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS gider_faturalari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT, aciklama TEXT,
        tutar REAL DEFAULT 0, kdv_tutari REAL DEFAULT 0,
        ay TEXT
    )""")
    for k, v in [("kdv_orani","20"),("varsayilan_paketleme","0"),("platform_hizmet_bedeli","6.99")]:
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    default_boxes = [
        ("Küçük Koli",5,15),("İkili Küçük Koli",10,18),("Üçlü Küçük Koli",15,20),
        ("Orta Koli",7,17),("İkili Orta Koli",13,20),
        ("İkili Büyük Koli",13,20),("Mini Koli",3,0),
        ("Büyük Koli",5,0),("XL Koli",4,8),
    ]
    for koli_adi, desi, maliyet in default_boxes:
        c.execute("INSERT OR IGNORE INTO boxes (koli_adi, desi, alis_maliyeti) VALUES (?,?,?)",
                  (koli_adi, desi, maliyet))
    conn.commit()
    conn.close()

def get_setting(key, default=None):
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key, value):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

# ── ÜRÜNLER
def get_all_products():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM products ORDER BY model_kodu, stok_kodu").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def upsert_product(stok_kodu, urun_adi, alis_maliyeti, model_kodu="", notlar=""):
    conn = get_connection()
    conn.execute("""INSERT INTO products (stok_kodu, model_kodu, urun_adi, alis_maliyeti, notlar, updated_at)
        VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)
        ON CONFLICT(stok_kodu) DO UPDATE SET
            model_kodu=excluded.model_kodu, urun_adi=excluded.urun_adi,
            alis_maliyeti=excluded.alis_maliyeti, notlar=excluded.notlar,
            updated_at=CURRENT_TIMESTAMP""",
        (stok_kodu, model_kodu, urun_adi, alis_maliyeti, notlar))
    conn.commit()
    conn.close()

def delete_product(stok_kodu):
    conn = get_connection()
    conn.execute("DELETE FROM products WHERE stok_kodu=?", (stok_kodu,))
    conn.commit()
    conn.close()

# ── KOLİLER
def get_all_boxes():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM boxes ORDER BY koli_adi").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def upsert_box(koli_adi, desi, alis_maliyeti, box_id=None):
    conn = get_connection()
    if box_id:
        conn.execute("UPDATE boxes SET koli_adi=?,desi=?,alis_maliyeti=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                     (koli_adi, desi, alis_maliyeti, box_id))
    else:
        conn.execute("""INSERT INTO boxes (koli_adi, desi, alis_maliyeti) VALUES (?,?,?)
            ON CONFLICT(koli_adi) DO UPDATE SET desi=excluded.desi,
            alis_maliyeti=excluded.alis_maliyeti, updated_at=CURRENT_TIMESTAMP""",
            (koli_adi, desi, alis_maliyeti))
    conn.commit()
    conn.close()

def delete_box(box_id):
    conn = get_connection()
    conn.execute("DELETE FROM boxes WHERE id=?", (box_id,))
    conn.commit()
    conn.close()

# ── KOLİ KURALLARI
def get_box_rules():
    conn = get_connection()
    rows = conn.execute("""SELECT br.*, b.koli_adi, b.desi, b.alis_maliyeti
        FROM box_rules br LEFT JOIN boxes b ON br.box_id=b.id
        ORDER BY br.model_kodu, br.adet""").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_box_rules_for_model(model_kodu):
    conn = get_connection()
    rows = conn.execute("""SELECT br.*, b.koli_adi, b.desi, b.alis_maliyeti
        FROM box_rules br LEFT JOIN boxes b ON br.box_id=b.id
        WHERE br.model_kodu=? ORDER BY br.adet""", (model_kodu,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def upsert_box_rule(model_kodu, adet, box_id):
    conn = get_connection()
    conn.execute("""INSERT INTO box_rules (model_kodu, adet, box_id) VALUES (?,?,?)
        ON CONFLICT(model_kodu, adet) DO UPDATE SET box_id=excluded.box_id""",
        (model_kodu, adet, box_id))
    conn.commit()
    conn.close()

def delete_box_rule(rule_id):
    conn = get_connection()
    conn.execute("DELETE FROM box_rules WHERE id=?", (rule_id,))
    conn.commit()
    conn.close()

def find_box_for_order(model_kodu, adet):
    conn = get_connection()
    row = conn.execute("""SELECT br.*, b.koli_adi, b.desi, b.alis_maliyeti
        FROM box_rules br LEFT JOIN boxes b ON br.box_id=b.id
        WHERE br.model_kodu=? AND br.adet=?""", (model_kodu, adet)).fetchone()
    conn.close()
    return dict(row) if row else None

# ── KARGO FİYATLARI
def get_cargo_price(firma, desi):
    conn = get_connection()
    row = conn.execute("SELECT fiyat FROM cargo_prices WHERE firma=? AND desi=?",
                       (firma, int(desi) if desi else 0)).fetchone()
    conn.close()
    return row["fiyat"] if row else 0

def save_cargo_prices(firma, prices_dict, tarih):
    conn = get_connection()
    for desi, fiyat in prices_dict.items():
        conn.execute("""INSERT INTO cargo_prices (firma, desi, fiyat, guncelleme_tarihi)
            VALUES (?,?,?,?) ON CONFLICT(firma, desi) DO UPDATE SET
            fiyat=excluded.fiyat, guncelleme_tarihi=excluded.guncelleme_tarihi""",
            (firma, int(desi), fiyat, tarih))
    conn.commit()
    conn.close()

def get_cargo_update_date(firma):
    conn = get_connection()
    row = conn.execute("SELECT guncelleme_tarihi FROM cargo_prices WHERE firma=? LIMIT 1",
                       (firma,)).fetchone()
    conn.close()
    return row["guncelleme_tarihi"] if row else None

# ── HAMMADDE
def get_all_materials():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM materials ORDER BY tur, ad, varyant").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def upsert_material(tur, ad, varyant, birim, stok, kritik_esik, alarm_aktif=1, mat_id=None):
    conn = get_connection()
    if mat_id:
        conn.execute("""UPDATE materials SET tur=?,ad=?,varyant=?,birim=?,stok=?,
            kritik_esik=?,alarm_aktif=?,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (tur, ad, varyant, birim, stok, kritik_esik, alarm_aktif, mat_id))
    else:
        conn.execute("""INSERT INTO materials (tur,ad,varyant,birim,stok,kritik_esik,alarm_aktif)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(tur,ad,varyant) DO UPDATE SET birim=excluded.birim,
            stok=excluded.stok, kritik_esik=excluded.kritik_esik,
            alarm_aktif=excluded.alarm_aktif, updated_at=CURRENT_TIMESTAMP""",
            (tur, ad, varyant, birim, stok, kritik_esik, alarm_aktif))
    conn.commit()
    conn.close()

def delete_material(mat_id):
    conn = get_connection()
    conn.execute("DELETE FROM materials WHERE id=?", (mat_id,))
    conn.commit()
    conn.close()

def add_material_movement(material_id, hareket_turu, miktar, aciklama=""):
    conn = get_connection()
    conn.execute("""INSERT INTO material_movements (material_id, hareket_turu, miktar, aciklama)
        VALUES (?,?,?,?)""", (material_id, hareket_turu, miktar, aciklama))
    if hareket_turu == "giris":
        conn.execute("UPDATE materials SET stok=stok+? WHERE id=?", (miktar, material_id))
    elif hareket_turu == "cikis":
        conn.execute("UPDATE materials SET stok=stok-? WHERE id=?", (miktar, material_id))
    conn.commit()
    conn.close()

def get_critical_materials():
    conn = get_connection()
    rows = conn.execute("""SELECT * FROM materials
        WHERE alarm_aktif=1 AND kritik_esik>0 AND stok<=kritik_esik
        ORDER BY tur, ad""").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_material_movements(material_id, limit=50):
    conn = get_connection()
    rows = conn.execute("""SELECT * FROM material_movements WHERE material_id=?
        ORDER BY tarih DESC LIMIT ?""", (material_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── SİPARİŞLER
def save_orders(orders, import_id):
    conn = get_connection()
    for o in orders:
        o["import_id"] = import_id
    conn.executemany("""INSERT INTO orders (
        import_id,siparis_no,siparis_tarihi,stok_kodu,urun_adi,model_kodu,
        adet,birim_fiyat,satis_tutari,indirim_tutari,trendyol_indirim,
        faturalanacak_tutar,kdv_tutari,faturalanacak_kdvsiz,
        komisyon_orani,komisyon_tutari,kargo_firmasi,kargo_tutari,
        koli_id,koli_adi,koli_desi,koli_maliyet,kargo_hesaplanan,
        alis_maliyeti,net_kar,siparis_durumu,il)
        VALUES (:import_id,:siparis_no,:siparis_tarihi,:stok_kodu,:urun_adi,:model_kodu,
        :adet,:birim_fiyat,:satis_tutari,:indirim_tutari,:trendyol_indirim,
        :faturalanacak_tutar,:kdv_tutari,:faturalanacak_kdvsiz,
        :komisyon_orani,:komisyon_tutari,:kargo_firmasi,:kargo_tutari,
        :koli_id,:koli_adi,:koli_desi,:koli_maliyet,:kargo_hesaplanan,
        :alis_maliyeti,:net_kar,:siparis_durumu,:il)""", orders)
    conn.commit()
    conn.close()

def create_import_record(dosya_adi, siparis_sayisi, toplam_ciro, toplam_kar):
    conn = get_connection()
    cursor = conn.execute("""INSERT INTO imports (dosya_adi,siparis_sayisi,toplam_ciro,toplam_kar)
        VALUES (?,?,?,?)""", (dosya_adi, siparis_sayisi, toplam_ciro, toplam_kar))
    import_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return import_id

def get_dashboard_summary(period="month"):
    conn = get_connection()
    if period == "day":
        df = "DATE(siparis_tarihi) = DATE('now')"
        gb = "DATE(siparis_tarihi)"
    elif period == "week":
        df = "DATE(siparis_tarihi) >= DATE('now', '-7 days')"
        gb = "DATE(siparis_tarihi)"
    elif period == "month":
        df = "strftime('%Y-%m', siparis_tarihi) = strftime('%Y-%m', 'now')"
        gb = "DATE(siparis_tarihi)"
    else:
        df = "1=1"
        gb = "strftime('%Y-%m', siparis_tarihi)"

    summary = conn.execute(f"""SELECT COUNT(*) as siparis_sayisi, SUM(adet) as toplam_adet,
        SUM(faturalanacak_tutar) as toplam_ciro, SUM(kdv_tutari) as toplam_kdv,
        SUM(komisyon_tutari) as toplam_komisyon, SUM(kargo_hesaplanan) as toplam_kargo,
        SUM(koli_maliyet) as toplam_koli, SUM(alis_maliyeti*adet) as toplam_maliyet,
        SUM(net_kar) as toplam_kar,
        CASE WHEN SUM(faturalanacak_kdvsiz)>0
             THEN ROUND(SUM(net_kar)/SUM(faturalanacak_kdvsiz)*100,1) ELSE 0 END as kar_marji
        FROM orders WHERE {df}""").fetchone()

    chart_data = conn.execute(f"""SELECT {gb} as tarih,
        SUM(faturalanacak_tutar) as ciro, SUM(net_kar) as kar
        FROM orders WHERE {df} GROUP BY {gb} ORDER BY tarih""").fetchall()

    top_products = conn.execute(f"""SELECT stok_kodu, urun_adi,
        SUM(adet) as toplam_adet, SUM(faturalanacak_tutar) as toplam_ciro,
        SUM(net_kar) as toplam_kar, ROUND(AVG(komisyon_orani),1) as ort_komisyon
        FROM orders WHERE {df} GROUP BY stok_kodu ORDER BY toplam_kar DESC LIMIT 10""").fetchall()

    conn.close()
    return {
        "summary": dict(summary) if summary else {},
        "chart_data": [dict(r) for r in chart_data],
        "top_products": [dict(r) for r in top_products],
    }

def get_orders_for_table(period="month", stok_kodu=None):
    conn = get_connection()
    if period == "day":
        df = "DATE(siparis_tarihi) = DATE('now')"
    elif period == "week":
        df = "DATE(siparis_tarihi) >= DATE('now', '-7 days')"
    elif period == "month":
        df = "strftime('%Y-%m', siparis_tarihi) = strftime('%Y-%m', 'now')"
    else:
        df = "1=1"
    extra = f"AND stok_kodu='{stok_kodu}'" if stok_kodu else ""
    rows = conn.execute(f"""SELECT siparis_tarihi,siparis_no,stok_kodu,urun_adi,adet,
        birim_fiyat,faturalanacak_tutar,kdv_tutari,faturalanacak_kdvsiz,
        komisyon_tutari,kargo_hesaplanan,koli_maliyet,koli_adi,
        alis_maliyeti,net_kar,siparis_durumu,kargo_firmasi
        FROM orders WHERE {df} {extra} ORDER BY siparis_tarihi DESC""").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_unique_models_from_products():
    conn = get_connection()
    rows = conn.execute("""SELECT DISTINCT model_kodu FROM products
        WHERE model_kodu IS NOT NULL AND model_kodu!='' ORDER BY model_kodu""").fetchall()
    conn.close()
    return [r["model_kodu"] for r in rows]

# ── İMPORT GEÇMİŞİ
def get_all_imports():
    conn = get_connection()
    rows = conn.execute("""
        SELECT i.*, COUNT(o.id) as gercek_siparis
        FROM imports i
        LEFT JOIN orders o ON o.import_id = i.id
        GROUP BY i.id
        ORDER BY i.import_tarihi DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_import(import_id):
    conn = get_connection()
    conn.execute("DELETE FROM orders WHERE import_id=?", (import_id,))
    conn.execute("DELETE FROM imports WHERE id=?", (import_id,))
    conn.commit()
    conn.close()

# ── GİDER FATURALARI
def add_gider_fatura(tarih, aciklama, tutar, kdv_tutari):
    ay = tarih[:7]
    conn = get_connection()
    conn.execute("""INSERT INTO gider_faturalari (tarih,aciklama,tutar,kdv_tutari,ay)
                    VALUES (?,?,?,?,?)""", (tarih, aciklama, tutar, kdv_tutari, ay))
    conn.commit(); conn.close()

def get_gider_faturalari(ay=None):
    conn = get_connection()
    if ay:
        rows = conn.execute("SELECT * FROM gider_faturalari WHERE ay=? ORDER BY tarih DESC", (ay,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM gider_faturalari ORDER BY tarih DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_gider_fatura(fatura_id):
    conn = get_connection()
    conn.execute("DELETE FROM gider_faturalari WHERE id=?", (fatura_id,))
    conn.commit(); conn.close()

def get_kdv_ozet(ay=None):
    """Aylık KDV özeti hesapla"""
    conn = get_connection()
    kdv_orani = float(get_setting("kdv_orani","20")) / 100
    platform_bedeli = float(get_setting("platform_hizmet_bedeli","6.99"))

    where = "WHERE strftime('%Y-%m', siparis_tarihi)=?" if ay else ""
    params = (ay,) if ay else ()

    row = conn.execute(f"""
        SELECT
            COALESCE(SUM(kdv_tutari),0) as hesaplanan_kdv,
            COALESCE(SUM(komisyon_tutari),0) as toplam_komisyon,
            COALESCE(SUM(kargo_hesaplanan),0) as toplam_kargo,
            COUNT(*) as siparis_sayisi
        FROM orders {where}
    """, params).fetchone()

    hesaplanan_kdv   = row["hesaplanan_kdv"]
    komisyon_kdv     = round(row["toplam_komisyon"] * kdv_orani, 2)
    kargo_kdv        = round(row["toplam_kargo"] * kdv_orani, 2)
    platform_kdv     = round(platform_bedeli * kdv_orani * row["siparis_sayisi"], 2)

    gider_rows = conn.execute(
        "SELECT COALESCE(SUM(kdv_tutari),0) as g FROM gider_faturalari" +
        (" WHERE ay=?" if ay else ""), (ay,) if ay else ()
    ).fetchone()
    alis_kdv = gider_rows["g"] or 0

    indirilecek_kdv = round(komisyon_kdv + kargo_kdv + platform_kdv + alis_kdv, 2)
    odenecek_kdv    = round(hesaplanan_kdv - indirilecek_kdv, 2)
    conn.close()

    return {
        "hesaplanan_kdv":  hesaplanan_kdv,
        "komisyon_kdv":    komisyon_kdv,
        "kargo_kdv":       kargo_kdv,
        "platform_kdv":    platform_kdv,
        "alis_kdv":        alis_kdv,
        "indirilecek_kdv": indirilecek_kdv,
        "odenecek_kdv":    odenecek_kdv,
        "siparis_sayisi":  row["siparis_sayisi"],
    }

def get_rapor_data(period="all", baslangic=None, bitis=None):
    """Rapor için tüm verileri getir"""
    conn = get_connection()
    if period == "today":
        where = "WHERE date(siparis_tarihi)=date('now')"
    elif period == "week":
        where = "WHERE siparis_tarihi >= date('now','-7 days')"
    elif period == "month":
        where = "WHERE strftime('%Y-%m',siparis_tarihi)=strftime('%Y-%m','now')"
    elif period == "custom" and baslangic and bitis:
        where = f"WHERE date(siparis_tarihi) BETWEEN '{baslangic}' AND '{bitis}'"
    else:
        where = ""

    ozet = conn.execute(f"""
        SELECT COUNT(*) as siparis, SUM(faturalanacak_tutar) as ciro,
               SUM(kdv_tutari) as kdv, SUM(komisyon_tutari) as komisyon,
               SUM(kargo_hesaplanan) as kargo, SUM(koli_maliyet) as koli,
               SUM(alis_maliyeti*adet) as maliyet, SUM(net_kar) as net_kar
        FROM orders {where}
    """).fetchone()

    urunler = conn.execute(f"""
        SELECT stok_kodu, urun_adi,
               SUM(adet) as toplam_adet,
               SUM(faturalanacak_tutar) as ciro,
               SUM(komisyon_tutari) as komisyon,
               SUM(kargo_hesaplanan) as kargo,
               SUM(net_kar) as net_kar
        FROM orders {where}
        GROUP BY stok_kodu ORDER BY ciro DESC LIMIT 20
    """).fetchall()

    aylik = conn.execute(f"""
        SELECT strftime('%Y-%m', siparis_tarihi) as ay,
               COUNT(*) as siparis, SUM(faturalanacak_tutar) as ciro,
               SUM(net_kar) as net_kar
        FROM orders {where}
        GROUP BY ay ORDER BY ay
    """).fetchall()

    conn.close()
    return {
        "ozet":    dict(ozet) if ozet else {},
        "urunler": [dict(r) for r in urunler],
        "aylik":   [dict(r) for r in aylik],
    }

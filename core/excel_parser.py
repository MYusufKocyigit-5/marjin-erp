import pandas as pd
from pathlib import Path
from core.database import get_all_products, get_setting, find_box_for_order, get_cargo_price

COLUMN_MAP = {
    "Sipariş Numarası":         "siparis_no",
    "Sipariş Tarihi":           "siparis_tarihi",
    "Stok Kodu":                "stok_kodu",
    "Ürün Adı":                 "urun_adi",
    "Adet":                     "adet",
    "Birim Fiyatı":             "birim_fiyat",
    "Satış Tutarı":             "satis_tutari",
    "İndirim Tutarı":           "indirim_tutari",
    "Trendyol İndirim Tutarı":  "trendyol_indirim",
    "Faturalanacak Tutar":      "faturalanacak_tutar",
    "Komisyon Oranı":           "komisyon_orani",
    "Faturalanan Kargo Tutarı": "kargo_tutari",
    "Sipariş Statüsü":          "siparis_durumu",
    "İl":                       "il",
    "Kargo Firması":            "kargo_firmasi",
}

FIRMA_MAP = {
    "trendyol express": "TEX",
    "tex":              "TEX",
    "dhl":              "DHL eCommerce",
    "dhl ecommerce":    "DHL eCommerce",
    "aras":             "Aras",
}

def normalize_firma(raw):
    if not raw:
        return ""
    raw_lower = str(raw).lower()
    for key, val in FIRMA_MAP.items():
        if key in raw_lower:
            return val
    return str(raw)

def parse_excel(filepath: str):
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Dosya bulunamadı: {filepath}")

    df = pd.read_excel(filepath, sheet_name="Tedarikci_Siparisleri", header=1)

    missing = [col for col in COLUMN_MAP.keys() if col not in df.columns]
    if missing:
        raise ValueError(f"Eksik sütunlar: {', '.join(missing)}")

    df = df[list(COLUMN_MAP.keys())].copy()
    df.rename(columns=COLUMN_MAP, inplace=True)

    df["siparis_tarihi"] = pd.to_datetime(
        df["siparis_tarihi"], format="%d.%m.%Y %H:%M", errors="coerce")
    df["siparis_tarihi"] = df["siparis_tarihi"].dt.strftime("%Y-%m-%d %H:%M")

    for col in ["adet","birim_fiyat","satis_tutari","indirim_tutari",
                "trendyol_indirim","faturalanacak_tutar","komisyon_orani"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["kargo_tutari"]   = pd.to_numeric(df["kargo_tutari"], errors="coerce").fillna(0)
    df["stok_kodu"]      = df["stok_kodu"].astype(str).str.strip()
    df["urun_adi"]       = df["urun_adi"].astype(str).str.strip()
    df["siparis_no"]     = df["siparis_no"].astype(str).str.strip()
    df["il"]             = df["il"].astype(str).str.strip()
    df["siparis_durumu"] = df["siparis_durumu"].astype(str).str.strip()
    df["kargo_firmasi"]  = df["kargo_firmasi"].astype(str).str.strip()

    products  = {p["stok_kodu"]: p for p in get_all_products()}
    kdv_orani = float(get_setting("kdv_orani", "20")) / 100

    warnings = []
    orders   = []
    pending  = []  # koli bulunamayan siparişler

    for _, row in df.iterrows():
        stok_kodu = row["stok_kodu"]
        product   = products.get(stok_kodu)

        if product:
            alis_maliyeti = float(product["alis_maliyeti"] or 0)
            model_kodu    = product.get("model_kodu", "") or ""
        else:
            alis_maliyeti = 0.0
            model_kodu    = ""
            if stok_kodu not in [w.split(":")[-1].strip() for w in warnings]:
                warnings.append(f"Maliyet girilmemiş: {stok_kodu}")

        adet     = int(row["adet"])
        faturalanacak        = float(row["faturalanacak_tutar"])
        kdv_tutari           = round(faturalanacak - (faturalanacak / (1 + kdv_orani)), 2)
        faturalanacak_kdvsiz = round(faturalanacak / (1 + kdv_orani), 2)
        komisyon_orani       = float(row["komisyon_orani"]) / 100
        komisyon_tutari      = round(faturalanacak * komisyon_orani, 2)
        kargo_tutari         = float(row["kargo_tutari"])
        firma_raw            = row["kargo_firmasi"]
        firma_norm           = normalize_firma(firma_raw)

        # Koli kuralı bul — varsa otomatik ata, yoksa manual
        koli_id = koli_adi = ""
        koli_desi = koli_maliyet = 0.0
        kargo_hesaplanan = 0.0
        needs_manual = False

        if model_kodu:
            box_rule = find_box_for_order(model_kodu, adet)
            if box_rule:
                koli_id      = box_rule.get("box_id")
                koli_adi     = box_rule.get("koli_adi", "")
                koli_desi    = float(box_rule.get("desi", 0) or 0)
                koli_maliyet = float(box_rule.get("alis_maliyeti", 0) or 0)
                if firma_norm and koli_desi > 0:
                    kargo_hesaplanan = round(get_cargo_price(firma_norm, koli_desi), 2)
            else:
                needs_manual = True
        else:
            needs_manual = True

        toplam_alis = alis_maliyeti * adet
        net_kar = round(
            faturalanacak_kdvsiz
            - komisyon_tutari
            - kargo_hesaplanan
            - koli_maliyet
            - toplam_alis, 2)

        order = {
            "import_id":             None,
            "siparis_no":            row["siparis_no"],
            "siparis_tarihi":        row["siparis_tarihi"],
            "stok_kodu":             stok_kodu,
            "urun_adi":              row["urun_adi"][:200],
            "model_kodu":            model_kodu,
            "adet":                  adet,
            "birim_fiyat":           float(row["birim_fiyat"]),
            "satis_tutari":          float(row["satis_tutari"]),
            "indirim_tutari":        float(row["indirim_tutari"]),
            "trendyol_indirim":      float(row["trendyol_indirim"]),
            "faturalanacak_tutar":   faturalanacak,
            "kdv_tutari":            kdv_tutari,
            "faturalanacak_kdvsiz":  faturalanacak_kdvsiz,
            "komisyon_orani":        float(row["komisyon_orani"]),
            "komisyon_tutari":       komisyon_tutari,
            "kargo_firmasi":         firma_norm,
            "kargo_tutari":          kargo_tutari,
            "koli_id":               koli_id,
            "koli_adi":              koli_adi,
            "koli_desi":             koli_desi,
            "koli_maliyet":          koli_maliyet,
            "kargo_hesaplanan":      kargo_hesaplanan,
            "alis_maliyeti":         alis_maliyeti,
            "net_kar":               net_kar,
            "siparis_durumu":        row["siparis_durumu"],
            "il":                    row["il"],
        }
        orders.append(order)
        if needs_manual:
            pending.append(order)

    return orders, pending, warnings

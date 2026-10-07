# core/startkey_ofis_veri.py
# -*- coding: utf-8 -*-
"""
Startkey ofis verisinin (startkey_ofis_ilanlar + startkey_ofis_cekim_log)
OKUMA tarafı: durum özeti, tutarlılık kontrolleri ve Excel üretimi (07.10.2026).
Yazma tarafı: startkey_ofis_job.py / core/startkey_ofis_cek.py.

Supabase istemcisi dışarıdan verilir (sayfa get_client() geçirir) — bu modül
Streamlit'e bağımlı değildir, bu yüzden testi kolaydır.
"""

import io
from datetime import date

import pandas as pd

TABLO = "startkey_ofis_ilanlar"
LOG_TABLO = "startkey_ofis_cekim_log"
SAYFA = 1000

ILCE_SAYISI = 30
BEKLENEN_KOMBINASYON = ILCE_SAYISI * 3 * 2 * 2     # ilçe x mülk x işlem x durum

# Revy'nin ham kolonlarına EKLENEN sütunlar (Revy'nin kendi adlarıyla çakışmaz)
EK_KOLONLAR = [
    "Durum (sistem)", "İlan Tarihi (gerçek tarih)",
    "Yayından Kalkış Tarihi (hesaplanan)", "Ofis Eşleşme", "Son Görülme",
]


def _sayfali(supa, tablo, kolonlar="*", filtre=None, sirala=None, ilerleme=None):
    """Tüm satırları 1000'erlik sayfalarla çeker (Supabase satır sınırı)."""
    sonuc, bas = [], 0
    while True:
        q = supa.table(tablo).select(kolonlar)
        if filtre:
            q = filtre(q)
        if sirala:
            q = q.order(sirala)
        veri = q.range(bas, bas + SAYFA - 1).execute().data or []
        sonuc.extend(veri)
        if ilerleme:
            ilerleme(len(sonuc))
        if len(veri) < SAYFA:
            break
        bas += SAYFA
    return sonuc


def sayi(supa, tablo, **eq):
    q = supa.table(tablo).select("ilan_url" if tablo == TABLO else "id", count="exact")
    for k, v in eq.items():
        q = q.eq(k, v)
    return q.limit(1).execute().count or 0


def log_cek(supa):
    return _sayfali(supa, LOG_TABLO, "*", sirala="id")


def son_durum_kombinasyonlar(log_satirlari):
    """Her (ilçe, mülk, işlem, durum) için EN SON log satırı (sınama hariç)."""
    en_son = {}
    for r in log_satirlari:
        if r.get("durum") not in ("aktif", "pasif"):
            continue
        k = (r.get("ilce"), r.get("mulk"), r.get("islem"), r.get("durum"))
        onceki = en_son.get(k)
        if onceki is None or (r.get("id") or 0) > (onceki.get("id") or 0):
            en_son[k] = r
    return en_son


def ozet(supa):
    """Sayfa üstündeki durum özeti."""
    log = log_cek(supa)
    son = son_durum_kombinasyonlar(log)
    tamam = [r for r in son.values() if r.get("sonuc") == "tamam"]
    eksik = [r for r in son.values() if r.get("sonuc") != "tamam"]
    son_sinama = next((r for r in reversed(log) if r.get("durum") == "sinama"), None)
    son_zaman = max((r.get("created_at") or "" for r in log), default="")
    return {
        "toplam": sayi(supa, TABLO),
        "aktif": sayi(supa, TABLO, durum="aktif"),
        "pasif": sayi(supa, TABLO, durum="pasif"),
        "gevsek": sayi(supa, TABLO, ofis_eslesme="gevsek"),
        "kombinasyon_tamam": len(tamam),
        "kombinasyon_eksik": len(eksik),
        "kombinasyon_beklenen": BEKLENEN_KOMBINASYON,
        "eksik_listesi": eksik,
        "tek_gun_limit": [r for r in son.values() if (r.get("tek_gun_limit") or 0) > 0],
        "belirsiz_bos": [r for r in son.values() if (r.get("belirsiz_bos") or 0) > 0],
        "url_yok": sum((r.get("url_yok") or 0) for r in son.values()),
        "son_sinama": son_sinama,
        "son_zaman": son_zaman,
        "log": log,
        "son_kombinasyonlar": son,
    }


def ilce_durum_tablosu(supa, ilerleme=None):
    """İlçe x durum ilan sayıları (tablodan)."""
    satirlar = _sayfali(supa, TABLO, "ilce,durum,ofis", sirala="ilan_url", ilerleme=ilerleme)
    if not satirlar:
        return pd.DataFrame(columns=["İlçe", "Aktif", "Pasif", "Toplam", "Ofis sayısı"])
    df = pd.DataFrame(satirlar)
    pv = df.pivot_table(index="ilce", columns="durum", values="ofis", aggfunc="size", fill_value=0)
    for c in ("aktif", "pasif"):
        if c not in pv.columns:
            pv[c] = 0
    out = pd.DataFrame({
        "İlçe": pv.index, "Aktif": pv["aktif"].values, "Pasif": pv["pasif"].values,
    })
    out["Toplam"] = out["Aktif"] + out["Pasif"]
    out["Ofis sayısı"] = [df[df.ilce == i]["ofis"].nunique() for i in out["İlçe"]]
    return out.sort_values("Toplam", ascending=False).reset_index(drop=True)


def capraz_kontrol(supa, baslangic="2025-01-01"):
    """Yeni tablodaki AKTİF Startkey ilanlarını, günlük sync'in izmir_pazar_ilanlar
    tablosundaki aktif Startkey ilanlarıyla (aynı ilan tarihi eşiğiyle) ilçe
    bazında karşılaştırır. İki kaynak farklı yollarla aynı şeyi sayar; büyük
    fark = bir tarafta eksik var demektir."""
    # Günlük sync yalnızca ofis adında 'startkey' geçenleri alır → karşılaştırma
    # aynı kuralla (ofis_eslesme='startkey'); gevşek eşleşenler dışarıda bırakılır.
    yeni = _sayfali(
        supa, TABLO, "ilce,durum,ilan_tarihi",
        filtre=lambda q: q.eq("durum", "aktif").eq("ofis_eslesme", "startkey").gte("ilan_tarihi", baslangic),
        sirala="ilan_url",
    )
    eski = _sayfali(
        supa, "izmir_pazar_ilanlar", "ilce,ilan_tarihi,ilan_linki",
        filtre=lambda q: q.eq("marka", "startkey").eq("aktif", True).gte("ilan_tarihi", baslangic),
        sirala="ilan_linki",
    )
    y = pd.DataFrame(yeni) if yeni else pd.DataFrame(columns=["ilce"])
    e = pd.DataFrame(eski) if eski else pd.DataFrame(columns=["ilce"])
    yn = y.groupby("ilce").size() if len(y) else pd.Series(dtype=int)
    en = e.groupby("ilce").size() if len(e) else pd.Series(dtype=int)
    t = pd.DataFrame({"Yeni tablo (aktif)": yn, "Günlük sync (aktif)": en}).fillna(0).astype(int)
    t["Fark"] = t["Yeni tablo (aktif)"] - t["Günlük sync (aktif)"]
    t.index.name = "İlçe"
    return t.reset_index().sort_values("Fark", key=lambda s: s.abs(), ascending=False).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────
# Excel
# ─────────────────────────────────────────────────────────────────────────
def _tarih(v):
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def ilanlar_dataframe(satirlar):
    """Revy'nin TÜM ham kolonları + eklenen sütunlar."""
    ham_kolonlar, kayitlar = [], []
    for r in satirlar:
        ham = dict(r.get("ham") or {})
        for k in ham:
            if k not in ham_kolonlar:
                ham_kolonlar.append(k)
        ham["Durum (sistem)"] = "Aktif" if r.get("durum") == "aktif" else "Yayından kalkmış"
        ham["İlan Tarihi (gerçek tarih)"] = _tarih(r.get("ilan_tarihi"))
        ham["Yayından Kalkış Tarihi (hesaplanan)"] = _tarih(r.get("kalkis_tarihi"))
        ham["Ofis Eşleşme"] = r.get("ofis_eslesme")
        ham["Son Görülme"] = str(r.get("son_gorulme") or "")[:19].replace("T", " ")
        kayitlar.append(ham)
    df = pd.DataFrame(kayitlar)
    sirali = [c for c in ham_kolonlar if c in df.columns] + [c for c in EK_KOLONLAR if c in df.columns]
    return df[sirali] if len(df) else pd.DataFrame(columns=EK_KOLONLAR)


def ofis_ozeti(satirlar):
    if not satirlar:
        return pd.DataFrame()
    df = pd.DataFrame([{
        "ofis": r.get("ofis"), "durum": r.get("durum"), "ilan_sahibi": r.get("ilan_sahibi"),
        "yayin_suresi": r.get("yayin_suresi"), "ilan_tarihi": r.get("ilan_tarihi"),
    } for r in satirlar])
    g = df.groupby("ofis", dropna=False)
    out = pd.DataFrame({
        "Aktif ilan": g.apply(lambda x: int((x.durum == "aktif").sum()), include_groups=False),
        "Yayından kalkmış ilan": g.apply(lambda x: int((x.durum == "pasif").sum()), include_groups=False),
        "İlan sahibi (danışman) sayısı": g["ilan_sahibi"].nunique(),
        "Kalkmışlarda ort. yayın süresi (gün)": g.apply(
            lambda x: round(pd.to_numeric(x[x.durum == "pasif"].yayin_suresi, errors="coerce").mean(), 1),
            include_groups=False),
        "Kalkmışlarda medyan yayın süresi (gün)": g.apply(
            lambda x: pd.to_numeric(x[x.durum == "pasif"].yayin_suresi, errors="coerce").median(),
            include_groups=False),
    })
    out["Toplam ilan"] = out["Aktif ilan"] + out["Yayından kalkmış ilan"]
    out = out.reset_index().rename(columns={"ofis": "Ofis"})
    return out.sort_values("Toplam ilan", ascending=False).reset_index(drop=True)


def cekim_raporu(son_kombinasyonlar):
    satirlar = []
    for r in son_kombinasyonlar.values():
        satirlar.append({
            "Durum": r.get("durum"), "İlçe": r.get("ilce"), "Mülk": r.get("mulk"), "İşlem": r.get("islem"),
            "Sonuç": r.get("sonuc"), "Ham satır (tüm markalar)": r.get("ham_satir"),
            "Tekil satır": r.get("tekil_satir"), "Startkey satırı": r.get("startkey_satir"),
            "Gevşek eşleşen": r.get("gevsek_satir"), "İstek sayısı": r.get("istek_sayisi"),
            "Hata": r.get("hata_sayisi"), "Belirsiz-boş yanıt": r.get("belirsiz_bos"),
            "Tek günde 1000 sınırı": r.get("tek_gun_limit"),
            "İlan başlangıç": r.get("ilan_baslangic"), "İlan bitiş": r.get("ilan_bitis"),
            "Çekim zamanı": str(r.get("created_at") or "")[:19].replace("T", " "),
        })
    df = pd.DataFrame(satirlar)
    if len(df):
        df = df.sort_values(["Durum", "İlçe", "Mülk", "İşlem"]).reset_index(drop=True)
    return df


ACIKLAMA = [
    ("Kapsam", "İzmir'in 30 ilçesi; konut + ticari + arsa; satılık + kiralık; Revy'de ofis adında 'Startkey' geçen ilanlar."),
    ("İlan tarihi", "Yalnızca İLAN TARİHİ 01.01.2025 ve sonrası olan ilanlar. Daha önce girilip sonradan kalkanlar/hâlâ yayında olanlar kapsam dışıdır."),
    ("Durum", "Aktif = Revy'de şu an yayında. Yayından kalkmış = Revy arşiv (suspended) sekmesinde. Bir ilan her ikisinde de görünürse 'yayından kalkmış' sayılır."),
    ("Yayından Kalkış Tarihi (hesaplanan)", "Revy bu tarihi vermez. İlan Tarihi + 'İlan Yayın Süresi' (gün) olarak HESAPLANIR; yalnızca yayından kalkmış ilanlar için doludur."),
    ("Revy sütunları", "Revy export'unun tüm sütunları olduğu gibi korunur. Sağdaki 5 sütun (Durum (sistem), İlan Tarihi (gerçek tarih), Yayından Kalkış Tarihi (hesaplanan), Ofis Eşleşme, Son Görülme) sistem tarafından eklenmiştir."),
    ("Ofis Eşleşme", "'startkey' = ofis adında 'startkey' geçiyor. 'gevsek' = adı ancak boşluk/tire/harf farkı yok sayılınca eşleşiyor (ör. 'START KEY'); sayıca azdır, analizden önce gözden geçirilmesi önerilir."),
    ("Son Görülme", "Bu ilanı en son gören çekimin zamanı. Çekimler elle çalıştırıldığı için, uzun süre güncellenmemiş verideki 'aktif' ilanlar bayat olabilir."),
    ("Çekim Raporu", "Her ilçe/mülk/işlem/durum kombinasyonunun ham ve Startkey satır sayısı, istek sayısı, hata ve uyarıları. 'Sonuç' = eksik olan kombinasyonlar tamamlanmadan veri eksiksiz sayılmamalıdır."),
]


def excel_uret(ilan_satirlari, son_kombinasyonlar):
    """Döner: xlsx bayt dizisi (sayfalar: Açıklama, İlanlar, Ofis Özeti, Çekim Raporu)."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl", datetime_format="DD.MM.YYYY", date_format="DD.MM.YYYY") as xw:
        pd.DataFrame(ACIKLAMA, columns=["Konu", "Açıklama"]).to_excel(xw, sheet_name="Açıklama", index=False)
        ilanlar_dataframe(ilan_satirlari).to_excel(xw, sheet_name="İlanlar", index=False)
        ofis_ozeti(ilan_satirlari).to_excel(xw, sheet_name="Ofis Özeti", index=False)
        cekim_raporu(son_kombinasyonlar).to_excel(xw, sheet_name="Çekim Raporu", index=False)
        for ad, genislik in (("Açıklama", {"A": 34, "B": 120}),):
            ws = xw.sheets[ad]
            for kol, w in genislik.items():
                ws.column_dimensions[kol].width = w
        for ad in ("İlanlar", "Ofis Özeti", "Çekim Raporu"):
            ws = xw.sheets[ad]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
    return buf.getvalue()


def tum_ilanlar(supa, ilerleme=None):
    return _sayfali(supa, TABLO, "*", sirala="ilan_url", ilerleme=ilerleme)

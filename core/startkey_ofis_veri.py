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
import re
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
    "Ofis (birleştirilmiş)", "Ofis İli (resmi liste)", "Ofis İlçesi (resmi liste)",
    "Ofis grubu (şubeler birleşik)",
]

# ── Ofis adı birleştirme ────────────────────────────────────────────────
# Revy'de aynı ofis farklı yazılabiliyor: "STARTKEY MACRO GAYRİMENKUL",
# "Startkey macro", "STARTKEY MUGA GAYRİMENKUL" ve başında/sonunda boşluklu
# " STARTKEY MUGA GAYRİMENKUL"; "EVKA 3" / "EVKA3"; "PREMIUM" / "Premium";
# "… GAYRİMENKUL" eki var/yok. Analizde ofis başına doğru sayı için bunların
# tek ofis sayılması gerekir. Anahtar: Türkçe harfleri sadeleştir, küçük harf,
# "startkey" ve "gayrimenkul" sözcüklerini at, harf/rakam dışını at.
# BİLEREK yapılmayan: "MEGAPOL" ile "MEGAPOL 2", "ALTUNSU" ile "ALTUNSU 2" gibi
# numaralı şubeler AYRI ofistir; "TİM" ile "TIME", "HAYAT" ile "HAYAT KUŞADASI"
# gibi belirsiz olanlar OTOMATİK birleştirilmez — "Ofis Eşleme" sayfasından
# gözden geçirilir, birleştirilecekse OFIS_ELLE_ESLEME'ye eklenir.
_TR_SADE = str.maketrans("İIıiĞğÜüŞşÖöÇç", "iiiigguussoocc")

# Elle birleştirme: {sadeleştirilmiş_anahtar: hedef_anahtar}
# 'HAYAT KUŞADASI' = Hayat, 'ANKA BURHANİYE' = Anka (resmi listede il/ilçe eki olmadan yazılı).
OFIS_ELLE_ESLEME = {"hayatkusadasi": "hayat", "ankaburhaniye": "anka"}

# Startkey Türkiye resmi ofis listesi (startkey.com.tr/tr/ofisler, 85 ofis) —
# 07.10.2026 tarihli anlık görüntü. (ad, il, ilçe). Listede olmayan ofis adları
# kapanmış/yeniden adlandırılmış/eski ofis olabilir; Ofis Özeti'nde "Resmi listede = Hayır".
RESMI_OFISLER = [
    ('1872', 'İzmir', 'Foça'),
    ('A Plus', 'İzmir', 'Konak'),
    ('A Plus 2', 'İzmir', 'Balçova'),
    ('Ada', 'İzmir', 'Karaburun'),
    ('Akın', 'İzmir', 'Karşıyaka'),
    ('Alfa', 'İzmir', 'Karşıyaka'),
    ('Altunsu', 'İzmir', 'Karşıyaka'),
    ('Anka', 'Balıkesir', 'Burhaniye'),
    ('Artı', 'İzmir', 'Karşıyaka'),
    ('Astra', 'İzmir', 'Karşıyaka'),
    ('Ata', 'İzmir', 'Karşıyaka'),
    ('Batı', 'İstanbul', 'Beylikdüzü'),
    ('Baytu Realty', 'United Kingdom', 'London'),
    ('Casa', 'İzmir', 'Çiğli'),
    ('City', 'İzmir', 'Çiğli'),
    ('Corner', 'İzmir', 'Bornova'),
    ('Çapa', 'İzmir', 'Bergama'),
    ('Çözüm', 'İzmir', 'Karabağlar'),
    ('Ege', 'İzmir', 'Karşıyaka'),
    ('Eksper', 'İzmir', 'Karşıyaka'),
    ('Elit', 'Manisa', 'Şehzadeler'),
    ('Eliza Real Estate', 'Greece', 'Athens'),
    ('Evka 3', 'İzmir', 'Bornova'),
    ('Final', 'İzmir', 'Çiğli'),
    ('Focus', 'İzmir', 'Bayraklı'),
    ('Haktan', 'İzmir', 'Bayraklı'),
    ('Hayat', 'Aydın', 'Kuşadası'),
    ('İlke', 'İzmir', 'Gaziemir'),
    ('Kaynak', 'İzmir', 'Konak'),
    ('Kuzey', 'İzmir', 'Menemen'),
    ('Kuzey2', 'İzmir', 'Menemen'),
    ('Laya', 'Aydın', 'Kuşadası'),
    ('Lider', 'İzmir', 'Bayraklı'),
    ('Life', 'İzmir', 'Narlıdere'),
    ('Little', 'İzmir', 'Buca'),
    ('Loft', 'Ankara', 'Çankaya'),
    ('Lotus', 'Denizli', 'Merkezefendi'),
    ('Macro', 'İzmir', 'Çiğli'),
    ('Marin', 'İzmir', 'Karabağlar'),
    ('Mavi', 'İzmir', 'Aliağa'),
    ('Maya', 'İzmir', 'Karşıyaka'),
    ('Maya 2', 'İzmir', 'Çiğli'),
    ('Mega', 'İzmir', 'Karşıyaka'),
    ('Motto', 'Kocaeli', 'Başiskele'),
    ('Muga', 'İzmir', 'Karşıyaka'),
    ('Nar Ofis', 'İzmir', 'Konak'),
    ('Neta', 'İzmir', 'Konak'),
    ('Parla', 'İzmir', 'Güzelbahçe'),
    ('Pars', 'İzmir', 'Karşıyaka'),
    ('Pearl', 'Girne (K.K.T.C.)', 'Girne'),
    ('Pelit', 'Muğla', 'Datça'),
    ('Pera', 'İzmir', 'Buca'),
    ('Platin', 'Manisa', 'Yunusemre'),
    ('Point', 'Antalya', 'Muratpaşa'),
    ('Premium', 'İzmir', 'Güzelbahçe'),
    ('Prestige', 'İzmir', 'Bayraklı'),
    ('Puzzle', 'İzmir', 'Karşıyaka'),
    ('Ref', 'İzmir', 'Foça'),
    ('Ref 2', 'İzmir', 'Karşıyaka'),
    ('Rose', 'İzmir', 'Foça'),
    ('Rover', 'İzmir', 'Çiğli'),
    ('Sasalı', 'İzmir', 'Çiğli'),
    ('Sembol', 'İzmir', 'Konak'),
    ('Sembol 2', 'İzmir', 'Menderes'),
    ('Sirius', 'İzmir', 'Bornova'),
    ('Sky', 'İzmir', 'Karşıyaka'),
    ('Star', 'Manisa', 'Turgutlu'),
    ('Su', 'İzmir', 'Aliağa'),
    ("Sui's", 'İzmir', 'Konak'),
    ('Tarih', 'İzmir', 'Konak'),
    ('Tim', 'İzmir', 'Konak'),
    ('Time', 'İzmir', 'Karşıyaka'),
    ('Trend', 'İzmir', 'Karşıyaka'),
    ('Umay', 'İzmir', 'Karşıyaka'),
    ('Vadi', 'İstanbul', 'Kağıthane'),
    ('Vega', 'İzmir', 'Konak'),
    ('Vizyon', 'İzmir', 'Gaziemir'),
    ('Yalı', 'İzmir', 'Karşıyaka'),
    ('Yalı 2', 'İzmir', 'Güzelbahçe'),
    ('Yalı Vira', 'İzmir', 'Urla'),
    ('Yatırım', 'Balıkesir', 'Ayvalık'),
    ('Yön', 'Balıkesir', 'Altıeylül'),
    ('Zeta', 'İzmir', 'Bornova'),
    ('Zeta 2', 'İzmir', 'Konak'),
    ('Zirve', 'İzmir', 'Çiğli'),
]


def ofis_anahtari(ofis):
    """Ofis adının birleştirme anahtarı (aynı ofisin yazım farkları aynı anahtarı verir)."""
    if ofis is None or (isinstance(ofis, float) and pd.isna(ofis)):
        return ""
    t = str(ofis).translate(_TR_SADE).lower()
    k = "".join(ch for ch in t if ch.isalnum())      # 'START KEY' de 'startkey' olur
    for sozcuk in ("startkey", "gayrimenkul", "gayrimenku"):
        k = k.replace(sozcuk, "")
    return OFIS_ELLE_ESLEME.get(k, k)


def _resmi_sozluk():
    return {ofis_anahtari(ad): (ad, il, ilce) for ad, il, ilce in RESMI_OFISLER}


def ofis_esleme_tablosu(satirlar):
    """Her ham ofis adı → birleştirilmiş ad. Birleştirilmiş ad = grubun en çok
    ilanı olan yazımı (boşlukları kırpılmış). Döner: (ad→birleştirilmiş sözlüğü, DataFrame)."""
    sayac = {}
    for r in satirlar:
        ad = r.get("ofis")
        ad = None if ad is None or (isinstance(ad, float) and pd.isna(ad)) else str(ad)
        sayac[ad] = sayac.get(ad, 0) + 1
    gruplar = {}
    for ad, n in sayac.items():
        gruplar.setdefault(ofis_anahtari(ad), []).append((ad, n))
    resmi = _resmi_sozluk()
    temsilciler = {}
    for anahtar, uyeler in gruplar.items():
        uyeler.sort(key=lambda x: (-x[1], str(x[0])))
        if anahtar in resmi:
            temsilciler[anahtar] = "Startkey " + resmi[anahtar][0]
        else:
            temsilciler[anahtar] = (str(uyeler[0][0]).strip() if uyeler[0][0] is not None else "(ofis adı yok)")
    bilinen = set(gruplar) | set(resmi)

    def _grup_adi(anahtar):
        # 'Ref 2', 'Altunsu 2' gibi numaralı şubeler, numarasız asıl ofisi biliniyorsa onun
        # grubuna girer (Meltem: "ofisler 1-2 ayrılsa da ilanları tek isimle çıkabiliyor").
        # 'Evka 3' gibi numarasız karşılığı olmayanlar kendi başına kalır.
        m = re.match(r"^(.+?)(\d+)$", anahtar)
        if m and m.group(1) in bilinen:
            b = m.group(1)
            return temsilciler.get(b) or ("Startkey " + resmi[b][0])
        return temsilciler[anahtar]

    harita, satir = {}, []
    for anahtar, uyeler in gruplar.items():
        temsilci = temsilciler[anahtar]
        grup_adi = _grup_adi(anahtar)
        if anahtar in resmi:
            r_il, r_ilce, r_var = resmi[anahtar][1], resmi[anahtar][2], "Evet"
        else:
            r_il, r_ilce, r_var = None, None, "Hayır"
        for ad, n in uyeler:
            harita[ad] = temsilci
            satir.append({"Birleştirilmiş ofis": temsilci, "Revy'deki yazım": ad, "İlan sayısı": n,
                          "Gruptaki yazım sayısı": len(uyeler), "Resmi listede": r_var,
                          "Ofis ili (resmi)": r_il, "Ofis ilçesi (resmi)": r_ilce,
                          "Ofis grubu (şubeler birleşik)": grup_adi})
    df = pd.DataFrame(satir)
    if len(df):
        df = df.sort_values(["Birleştirilmiş ofis", "İlan sayısı"], ascending=[True, False]).reset_index(drop=True)
    return harita, df


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


def _sayfali_anahtar(supa, tablo, kolonlar, anahtar, filtre=None):
    """Anahtar (birincil anahtar) üzerinden 'bundan büyük' sayfalaması.
    Büyük OFFSET'li sayfalamanın tetiklediği Supabase zaman aşımını önler:
    her sayfa indeksten doğrudan başlar."""
    sonuc, son = [], None
    kol = kolonlar if anahtar in kolonlar.split(",") else kolonlar + "," + anahtar
    while True:
        q = supa.table(tablo).select(kol)
        if filtre:
            q = filtre(q)
        if son is not None:
            q = q.gt(anahtar, son)
        veri = q.order(anahtar).limit(SAYFA).execute().data or []
        sonuc.extend(veri)
        if len(veri) < SAYFA:
            break
        son = veri[-1][anahtar]
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
    eski = _sayfali_anahtar(
        supa, "izmir_pazar_ilanlar", "ilce,ilan_tarihi,ilan_linki", "ilan_linki",
        filtre=lambda q: q.eq("marka", "startkey").eq("aktif", True).gte("ilan_tarihi", baslangic),
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
    harita, _esl = ofis_esleme_tablosu(satirlar)
    ofis_il_ilce = {
        r["Birleştirilmiş ofis"]: (r["Ofis ili (resmi)"], r["Ofis ilçesi (resmi)"])
        for _, r in _esl.iterrows()
    } if len(_esl) else {}
    ofis_grubu = {
        r["Birleştirilmiş ofis"]: r["Ofis grubu (şubeler birleşik)"] for _, r in _esl.iterrows()
    } if len(_esl) else {}
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
        _b = harita.get(None if r.get("ofis") is None else str(r.get("ofis")))
        ham["Ofis (birleştirilmiş)"] = _b
        ham["Ofis İli (resmi liste)"], ham["Ofis İlçesi (resmi liste)"] = ofis_il_ilce.get(_b, (None, None))
        ham["Ofis grubu (şubeler birleşik)"] = ofis_grubu.get(_b)
        kayitlar.append(ham)
    df = pd.DataFrame(kayitlar)
    sirali = [c for c in ham_kolonlar if c in df.columns] + [c for c in EK_KOLONLAR if c in df.columns]
    return df[sirali] if len(df) else pd.DataFrame(columns=EK_KOLONLAR)


def ofis_ozeti(satirlar, gruplu=False):
    """gruplu=False: birleştirilmiş ofis başına. gruplu=True: numaralı şubeler
    (Ref / Ref 2 gibi) tek ofis grubu olarak toplanır."""
    if not satirlar:
        return pd.DataFrame()
    harita, esleme = ofis_esleme_tablosu(satirlar)
    if gruplu:
        _g = dict(zip(esleme["Birleştirilmiş ofis"], esleme["Ofis grubu (şubeler birleşik)"]))
        harita = {k: _g.get(v, v) for k, v in harita.items()}
        esleme = esleme.assign(**{"Birleştirilmiş ofis": esleme["Ofis grubu (şubeler birleşik)"]})
    df = pd.DataFrame([{
        "ofis": harita.get(None if r.get("ofis") is None else str(r.get("ofis"))),
        "durum": r.get("durum"), "ilan_sahibi": r.get("ilan_sahibi"),
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
    varyantlar = esleme.groupby("Birleştirilmiş ofis")["Revy'deki yazım"].apply(
        lambda x: " | ".join(str(v) for v in x))
    out["Revy'deki yazımlar"] = [varyantlar.get(i, "") for i in out.index]
    out["Yazım sayısı"] = [int(esleme[esleme["Birleştirilmiş ofis"] == i].shape[0]) for i in out.index]
    _bilgi = esleme.drop_duplicates("Birleştirilmiş ofis").set_index("Birleştirilmiş ofis")
    out["Resmi listede"] = [_bilgi["Resmi listede"].get(i, "") for i in out.index]
    if not gruplu:   # grupta birden çok şube/ilçe olabilir; il/ilçe yalnız şube bazında anlamlı
        out["Ofis ili"] = [_bilgi["Ofis ili (resmi)"].get(i) for i in out.index]
        out["Ofis ilçesi"] = [_bilgi["Ofis ilçesi (resmi)"].get(i) for i in out.index]
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
    ("Revy sütunları", "Revy export'unun tüm sütunları olduğu gibi korunur. Sağdaki 9 sütun (Durum (sistem), İlan Tarihi (gerçek tarih), Yayından Kalkış Tarihi (hesaplanan), Ofis Eşleşme, Son Görülme, Ofis (birleştirilmiş), Ofis İli (resmi liste), Ofis İlçesi (resmi liste)) sistem tarafından eklenmiştir."),
    ("Ofis (birleştirilmiş)", "Revy'de aynı ofis farklı yazılabiliyor (büyük/küçük harf, 'GAYRİMENKUL' eki, baştaki/sondaki boşluk, 'EVKA 3' / 'EVKA3'). Bu sütun yazım farklarını tek ofis olarak birleştirir; Ofis Özeti buna göre sayar. Numaralı şubeler (MEGAPOL / MEGAPOL 2) ayrı ofistir. 'TİM' / 'TIME' gibi belirsiz olanlar birleştirilmez — 'Ofis Eşleme' sayfasından gözden geçirin. Revy'nin özgün 'Ofis' sütunu değiştirilmez. Resmi listede (startkey.com.tr/tr/ofisler, 07.10.2026'daki 85 ofis) olan ofisler için ofisin ili/ilçesi de eklenir; listede olmayanlar kapanmış, yeniden adlandırılmış ya da eski ofis olabilir (Ofis Özeti'nde 'Resmi listede = Hayır')."),
    ("Ofis grubu (şubeler birleşik)", "Numaralı şubeler (Ref / Ref 2, Altunsu / Altunsu 2, Yalı / Yalı 2…) Revy'de çoğu zaman aynı adla görünür; ayrı yazılanlar da bu sütunda tek gruba toplanır. 'Ofis Grubu Özeti' sayfası ofis grubu bazında sayar; 'Ofis Özeti' ise şube bazındadır. Numarasız karşılığı olmayan ofisler (ör. Evka 3) kendi başına kalır."),
    ("Ofis Eşleşme", "'startkey' = ofis adında 'startkey' geçiyor. 'gevsek' = adı ancak boşluk/tire/harf farkı yok sayılınca eşleşiyor (ör. 'START KEY'); sayıca azdır, analizden önce gözden geçirilmesi önerilir."),
    ("Son Görülme", "Bu ilanı en son gören çekimin zamanı. Çekimler elle çalıştırıldığı için, uzun süre güncellenmemiş verideki 'aktif' ilanlar bayat olabilir."),
    ("Çekim Raporu", "Her ilçe/mülk/işlem/durum kombinasyonunun ham ve Startkey satır sayısı, istek sayısı, hata ve uyarıları. 'Sonuç' = eksik olan kombinasyonlar tamamlanmadan veri eksiksiz sayılmamalıdır."),
]


def excel_uret(ilan_satirlari, son_kombinasyonlar):
    """Döner: xlsx bayt dizisi (sayfalar: Açıklama, İlanlar, Ofis Özeti, Ofis Grubu Özeti, Ofis Eşleme, Çekim Raporu)."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl", datetime_format="DD.MM.YYYY", date_format="DD.MM.YYYY") as xw:
        pd.DataFrame(ACIKLAMA, columns=["Konu", "Açıklama"]).to_excel(xw, sheet_name="Açıklama", index=False)
        ilanlar_dataframe(ilan_satirlari).to_excel(xw, sheet_name="İlanlar", index=False)
        ofis_ozeti(ilan_satirlari).to_excel(xw, sheet_name="Ofis Özeti", index=False)
        ofis_ozeti(ilan_satirlari, gruplu=True).to_excel(xw, sheet_name="Ofis Grubu Özeti", index=False)
        ofis_esleme_tablosu(ilan_satirlari)[1].to_excel(xw, sheet_name="Ofis Eşleme", index=False)
        cekim_raporu(son_kombinasyonlar).to_excel(xw, sheet_name="Çekim Raporu", index=False)
        for ad, genislik in (("Açıklama", {"A": 34, "B": 120}),):
            ws = xw.sheets[ad]
            for kol, w in genislik.items():
                ws.column_dimensions[kol].width = w
        for ad in ("İlanlar", "Ofis Özeti", "Ofis Grubu Özeti", "Ofis Eşleme", "Çekim Raporu"):
            ws = xw.sheets[ad]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
    return buf.getvalue()


def tum_ilanlar(supa, ilerleme=None):
    return _sayfali(supa, TABLO, "*", sirala="ilan_url", ilerleme=ilerleme)

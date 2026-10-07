# core/startkey_ofis_cek.py
# -*- coding: utf-8 -*-
"""
Startkey ofisleri analizi için Revy ilan verisini EKSİKSİZ ve DOĞRULANABİLİR
biçimde çeken motor (07.10.2026).

Meltem: "yapmak istediğim ofis yönetimi için bir Startkey ofisleri analizi...
revy excel tablosundaki tümü işime yarayabilir. senden isteğim bu veriyi
eksiksiz doğru çekebilmek." Kapsam: İzmir'in 30 ilçesi, konut/ticari/arsa,
satılık/kiralık, ilan tarihi >= 2025-01-01, hem AKTİF hem YAYINDAN KALKAN
(Revy arşiv sekmesi), yalnızca ofis adı "Startkey" olan ilanlar saklanır.

NEDEN core/revy_pazar_cek.py KULLANILMIYOR (yalnızca giriş/oturum için):
  * _parca_cek() her hatayı "0 satır" diye döndürüyor — hata ile gerçekten
    boş sonuç ayırt edilemiyor, bir parça sessizce kaybolabiliyor.
  * Bölme mantığı yalnızca günlük pazar taraması için yazılmış.
Burada AYNI Revy uç noktası ve parametreleri kullanılır, ama:
  1. Her istek hata/boş/başarılı olarak AYRI sınıflanır; hata alan istek
     yeniden denenir, oturum düşmüşse yeniden giriş yapılır, hâlâ
     başarısızsa kombinasyon "eksik" işaretlenir (sessiz kayıp yok).
  2. 1000 satır sınırına çarpan tarih aralığı, tek güne inene kadar ikiye
     bölünür; tek günde bile sınıra çarparsa bu ayrıca raporlanır.
  3. Çalışmadan önce kendi kendini sınar: bir tarih aralığının sonucu, aynı
     aralığın gün gün sonuçlarının birleşimine eşit olmalı (sınır günlerinin
     iki uçta da dahil olduğunu ve boşluk/çakışma olmadığını doğrular).
  4. Her kombinasyon için ham/tekil/Startkey satır sayısı, istek sayısı,
     hata ve belirsiz-boş yanıt sayısı kayda geçer.
Hiçbir kimlik bilgisi loglanmaz.
"""

import io
import re
import time
from datetime import date, datetime, timedelta

import pandas as pd
import requests

LIMIT = 1000                       # Revy'nin tek export'ta döndürdüğü azami satır
ENDPOINT = "https://revy.com.tr/app/portfoy/ilanlar/ajax"
CITY_ID = "41"                     # İzmir
URL_KOLONLARI = ["İlan Url", "İlan Linki"]
BEKLEME_SN = 1.0                   # isteklerin arası (Revy'yi yormamak için)

MULK_TIPLERI = {"konut": "1", "ticari": "2", "arsa": "3"}
ISLEM_TIPLERI = {"satilik": "sale", "kiralik": "rent"}
DURUM_DEGERLERI = {"aktif": "active", "pasif": "suspended"}


class OturumHatasi(RuntimeError):
    """Yeniden giriş sınırı aşıldı / giriş yapılamadı."""


# ─────────────────────────────────────────────────────────────────────────
# Oturum (giriş + gerektiğinde yenileme)
# ─────────────────────────────────────────────────────────────────────────
class RevyOturum:
    def __init__(self, giris_fonksiyonu, azami_yenileme=8, log=print, uyku=time.sleep):
        """giris_fonksiyonu: argümansız çağrılınca {cookie_adi: deger} döner."""
        self._giris = giris_fonksiyonu
        self.azami_yenileme = azami_yenileme
        self.yenileme_sayisi = 0
        self.log = log
        self.uyku = uyku
        self.session = None
        self.headers = None
        self._kur()

    def _kur(self):
        cookies = self._giris()
        if not cookies:
            raise OturumHatasi("Revy girişinde cookie alınamadı.")
        xsrf = cookies.get("XSRF-TOKEN", "")
        self.headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "X-XSRF-TOKEN": xsrf,
            "Referer": "https://revy.com.tr/app/portfoy/ilanlar",
        }
        s = requests.Session()
        for ad, deger in cookies.items():
            s.cookies.set(ad, deger, domain="revy.com.tr")
        self.session = s

    def yenile(self):
        if self.yenileme_sayisi >= self.azami_yenileme:
            raise OturumHatasi(
                f"Revy oturumu {self.yenileme_sayisi} kez yenilendi, sınır aşıldı."
            )
        self.yenileme_sayisi += 1
        self.log(f"🔐 Revy oturumu yenileniyor ({self.yenileme_sayisi}/{self.azami_yenileme})...")
        self._kur()


# ─────────────────────────────────────────────────────────────────────────
# Tek istek: hata / boş / başarılı ayrımı
# ─────────────────────────────────────────────────────────────────────────
class Sonuc:
    __slots__ = ("tur", "df", "mesaj")

    def __init__(self, tur, df=None, mesaj=""):
        self.tur = tur        # "tamam" | "bos_belirsiz" | "hata"
        self.df = df
        self.mesaj = mesaj


def _giris_sayfasi_mi(r):
    url = (getattr(r, "url", "") or "").lower()
    if "/login" in url or "/giris" in url:
        return True
    ct = (r.headers.get("Content-Type", "") or "").lower()
    if "text/html" in ct:
        govde = (r.text or "")[:6000].lower()
        if "giriş yap" in govde and "password" in govde:
            return True
    return False


def parca_getir(oturum, params, deneme=4, uyku=time.sleep):
    """Tek bir export isteğini yapar.

    "tamam"        : geçerli xlsx (0 satır da olabilir — başlık-only xlsx boş sonuçtur)
    "bos_belirsiz" : 200 ama xlsx değil ve giriş sayfası da değil, küçük gövde
                     (Revy'nin 'sonuç yok' yanıt biçimi) — sayılır ve raporlanır
    "hata"         : tüm denemeler başarısız
    """
    son_mesaj = "bilinmeyen"
    for d in range(deneme):
        try:
            r = oturum.session.get(ENDPOINT, params=params, headers=oturum.headers, timeout=90)
        except requests.RequestException as e:
            son_mesaj = f"ağ hatası: {type(e).__name__}"
            uyku(3 * (d + 1))
            continue

        if r.status_code in (401, 403, 419) or (r.status_code == 200 and _giris_sayfasi_mi(r)):
            son_mesaj = f"oturum düştü (HTTP {r.status_code})"
            try:
                oturum.yenile()
            except OturumHatasi as e:
                return Sonuc("hata", None, f"{son_mesaj}; {e}")
            continue

        if r.status_code == 429 or r.status_code >= 500:
            son_mesaj = f"HTTP {r.status_code}"
            uyku(5 * (d + 1))
            continue

        if r.status_code == 200 and r.content[:4] == b"PK\x03\x04":
            try:
                df = pd.read_excel(io.BytesIO(r.content))
            except Exception as e:
                son_mesaj = f"xlsx okunamadı: {type(e).__name__}"
                uyku(2)
                continue
            return Sonuc("tamam", df)

        if r.status_code == 200:
            ct = (r.headers.get("Content-Type", "") or "").lower()
            govde = r.content[:2000]
            # Büyük bir HTML sayfası "boş sonuç" değil, bir hata sayfasıdır.
            if "text/html" in ct and len(r.content) > 2000:
                son_mesaj = "beklenmeyen HTML yanıtı"
                uyku(3 * (d + 1))
                continue
            imza = f"{ct[:40]}|{len(r.content)}B|{govde[:120]!r}"
            return Sonuc("bos_belirsiz", None, imza)

        son_mesaj = f"HTTP {r.status_code}"
        uyku(2)
    return Sonuc("hata", None, son_mesaj)


# ─────────────────────────────────────────────────────────────────────────
# Tarih aralığı: 1000 satırda ikiye böl
# ─────────────────────────────────────────────────────────────────────────
class KombKayit:
    """Bir (ilçe, mülk, işlem, durum) kombinasyonunun çekim defteri."""

    def __init__(self):
        self.parcalar = []
        self.istek = 0
        self.hatalar = []             # [(bas, bit, mesaj)]
        self.belirsiz_bos = 0
        self.belirsiz_ornekler = []
        self.tek_gun_limit = []       # tek günde bile 1000'e çarpan günler
        self.en_derin = 0


def aralik_getir(oturum, base, bas, bit, kayit, derinlik=0, uyku=time.sleep, bekleme=BEKLEME_SN):
    params = {
        **base,
        "advertisement_first_date": bas.strftime("%Y-%m-%d"),
        "advertisement_last_date": bit.strftime("%Y-%m-%d"),
    }
    sonuc = parca_getir(oturum, params, uyku=uyku)
    kayit.istek += 1
    kayit.en_derin = max(kayit.en_derin, derinlik)
    uyku(bekleme)

    if sonuc.tur == "hata":
        kayit.hatalar.append((str(bas), str(bit), sonuc.mesaj))
        return
    if sonuc.tur == "bos_belirsiz":
        kayit.belirsiz_bos += 1
        if len(kayit.belirsiz_ornekler) < 3:
            kayit.belirsiz_ornekler.append(sonuc.mesaj)
        return

    n = len(sonuc.df)
    if n < LIMIT:
        if n:
            kayit.parcalar.append(sonuc.df)
        return

    # n >= LIMIT: sonuç kesilmiş olabilir → böl
    if bas >= bit:
        kayit.parcalar.append(sonuc.df)
        kayit.tek_gun_limit.append(str(bas))
        return
    orta = bas + timedelta(days=(bit - bas).days // 2)
    aralik_getir(oturum, base, bas, orta, kayit, derinlik + 1, uyku, bekleme)
    aralik_getir(oturum, base, orta + timedelta(days=1), bit, kayit, derinlik + 1, uyku, bekleme)


def base_parametreler(ilce_id, mulk, islem, durum):
    base = {
        "export": "1",
        "city_id": CITY_ID,
        "district_id[]": str(ilce_id),
        "advertisement_status": DURUM_DEGERLERI[durum],
        "property_type_id[]": MULK_TIPLERI[mulk],
        "transaction_type": ISLEM_TIPLERI[islem],
        # "area" verilmezse Revy hesabın kendi bölgesine düşebiliyor; her zaman tümü.
        "area": "all",
    }
    if durum == "pasif":
        base["tab"] = "archive"
    return base


# ─────────────────────────────────────────────────────────────────────────
# Kendi kendini sınama
# ─────────────────────────────────────────────────────────────────────────
def kendi_kendini_sinama(oturum, ilce_id, bitis=None, gun=30, log=print,
                         uyku=time.sleep, bekleme=BEKLEME_SN, durum="aktif"):
    """Aynı aralık tek istekle ve gün gün çekilir; URL kümeleri EŞİT olmalı.

    Döner: (basarili, mesaj). Başarısızlık = tarih sınırları beklendiği gibi
    (iki ucu dahil) çalışmıyor → veri çekimine GEÇİLMEMELİ."""
    bitis = bitis or (date.today() - timedelta(days=1))
    baslangic = bitis - timedelta(days=gun - 1)
    base = base_parametreler(ilce_id, "konut", "satilik", durum)

    k_tum = KombKayit()
    aralik_getir(oturum, base, baslangic, bitis, k_tum, uyku=uyku, bekleme=bekleme)
    if k_tum.hatalar or k_tum.belirsiz_bos or not k_tum.parcalar:
        return False, (f"Sınama ({durum}): bütün aralık alınamadı veya boş geldi "
                       f"(hatalar={k_tum.hatalar}, belirsiz_bos={k_tum.belirsiz_bos}) — sınama yapılamadı.")
    tum = pd.concat(k_tum.parcalar, ignore_index=True)
    ucol = _url_kolonu(tum)
    if not ucol:
        return False, f"Sınama ({durum}): URL kolonu bulunamadı."
    kume_tum = set(tum[ucol].dropna().astype(str))

    kume_gun = set()
    gun_i = baslangic
    while gun_i <= bitis:
        k = KombKayit()
        aralik_getir(oturum, base, gun_i, gun_i, k, uyku=uyku, bekleme=bekleme)
        if k.hatalar:
            return False, f"Sınama ({durum}): {gun_i} günü alınamadı: {k.hatalar}"
        for p in k.parcalar:
            kume_gun |= set(p[ucol].dropna().astype(str))
        gun_i += timedelta(days=1)

    if kume_tum != kume_gun:
        return False, (
            f"Sınama ({durum}) BAŞARISIZ: aralık={len(kume_tum)} ilan, gün gün={len(kume_gun)} ilan; "
            f"yalnız-aralıkta={len(kume_tum - kume_gun)}, yalnız-günlerde={len(kume_gun - kume_tum)}. "
            "Tarih sınırı davranışı varsayımla uyuşmuyor."
        )
    return True, f"Sınama ({durum}) başarılı: {baslangic}..{bitis} aralığı = gün gün birleşim ({len(kume_tum)} ilan)."


# ─────────────────────────────────────────────────────────────────────────
# Satır işleme
# ─────────────────────────────────────────────────────────────────────────
_TR = str.maketrans("İIıÖöÜüŞşÇçĞğ", "iiioouusscc" "gg")


def _url_kolonu(df):
    for c in URL_KOLONLARI:
        if c in df.columns:
            return c
    return next((c for c in df.columns if "url" in str(c).lower()), None)


def startkey_eslesmesi(ofis):
    """'startkey' | 'gevsek' | None.  startkey: ofis adında 'startkey' geçiyor.
    gevsek: boşluk/tire/nokta/Türkçe harf farkını yok sayınca eşleşiyor
    ('START KEY', 'Start-Key' gibi) — ayrı işaretlenir, sonradan gözden geçirilir."""
    if ofis is None or (isinstance(ofis, float) and pd.isna(ofis)):
        return None
    s = str(ofis)
    if "startkey" in s.lower():
        return "startkey"
    sade = re.sub(r"[^a-z0-9]", "", s.translate(_TR).lower())
    if "startkey" in sade:
        return "gevsek"
    return None


def _tarih(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    d = pd.to_datetime(v, format="%d.%m.%Y", errors="coerce")
    if pd.isna(d):
        d = pd.to_datetime(v, errors="coerce", dayfirst=True)
    return None if pd.isna(d) else d.date()


def _sayi(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(".", "").replace(",", "."))
    except Exception:
        return None


def _sade(v):
    """JSON'a girebilecek sade değer (NaN/Timestamp güvenli)."""
    if v is None:
        return None
    try:
        if pd.isna(v):          # NaN, NaT, pd.NA
            return None
    except (TypeError, ValueError):
        pass                    # liste/dizi gibi skaler olmayanlar
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    if hasattr(v, "item"):
        try:
            return v.item()
        except Exception:
            pass
    return v


def kayitlara_cevir(df, durum, ilan_basi, cekim_zamani):
    """Startkey satırlarını Supabase kayıtlarına çevirir.
    Döner: (kayitlar, istatistik)."""
    ist = {"ham": len(df), "url_yok": 0, "tekil": 0, "startkey": 0, "gevsek": 0}
    if df.empty:
        return [], ist
    ucol = _url_kolonu(df)
    if not ucol:
        ist["url_yok"] = len(df)
        return [], ist

    df = df[df[ucol].notna() & (df[ucol].astype(str).str.strip() != "")].copy()
    ist["url_yok"] = ist["ham"] - len(df)
    # Boşluk farkıyla ayrışan aynı link, upsert'te "aynı satıra iki kez" hatası verir.
    df[ucol] = df[ucol].astype(str).str.strip()
    df = df.drop_duplicates(subset=[ucol], keep="first")
    ist["tekil"] = len(df)

    kayitlar = []
    for _, satir in df.iterrows():
        es = startkey_eslesmesi(satir.get("Ofis"))
        if not es:
            continue
        ist["startkey" if es == "startkey" else "gevsek"] += 1
        ham = {str(k): _sade(v) for k, v in satir.items()}
        ilan_t = _tarih(satir.get("İlan tarihi"))
        sure = _sayi(satir.get("İlan Yayın Süresi"))
        sure_i = int(sure) if sure is not None else None
        kalkis = None
        if durum == "pasif" and ilan_t is not None and sure_i is not None:
            kalkis = ilan_t + timedelta(days=sure_i)
        kayitlar.append({
            "ilan_url": str(satir[ucol]).strip(),
            "durum": durum,
            "ofis": _sade(satir.get("Ofis")),
            "ofis_eslesme": es,
            "ilan_sahibi": _sade(satir.get("İlan sahibi")),
            "ilce": _sade(satir.get("İlçe")),
            "mahalle": _sade(satir.get("Mahalle")),
            "mulk_tipi": _sade(satir.get("Mülk tipi")),
            "islem_tipi": _sade(satir.get("İşlem tipi")),
            "ilan_tarihi": ilan_t.isoformat() if ilan_t else None,
            "yayin_suresi": sure_i,
            "kalkis_tarihi": kalkis.isoformat() if kalkis else None,
            "fiyat": _sayi(satir.get("Fiyat")),
            "m2": _sayi(satir.get("M2")),
            "ham": ham,
            "son_gorulme": cekim_zamani,
        })
    return kayitlar, ist


def kombinasyon_cek(oturum, ilce_ad, ilce_id, mulk, islem, durum, bas, bit,
                    cekim_zamani, uyku=time.sleep, bekleme=BEKLEME_SN):
    """Bir kombinasyonu çeker. Döner: dict(kayitlar=[...], ozet={...})"""
    base = base_parametreler(ilce_id, mulk, islem, durum)
    kayit = KombKayit()
    aralik_getir(oturum, base, bas, bit, kayit, uyku=uyku, bekleme=bekleme)

    df = pd.concat(kayit.parcalar, ignore_index=True) if kayit.parcalar else pd.DataFrame()
    kayitlar, ist = kayitlara_cevir(df, durum, bas, cekim_zamani)

    eksik = bool(kayit.hatalar)
    ozet = {
        "ilce": ilce_ad, "mulk": mulk, "islem": islem, "durum": durum,
        "ilan_baslangic": str(bas), "ilan_bitis": str(bit),
        "istek_sayisi": kayit.istek,
        "ham_satir": ist["ham"], "tekil_satir": ist["tekil"],
        "startkey_satir": ist["startkey"], "gevsek_satir": ist["gevsek"],
        "url_yok": ist["url_yok"],
        "en_derin_bolme": kayit.en_derin,
        "hata_sayisi": len(kayit.hatalar),
        "belirsiz_bos": kayit.belirsiz_bos,
        "tek_gun_limit": len(kayit.tek_gun_limit),
        "sonuc": "eksik" if eksik else "tamam",
        "detay": {
            "hatalar": kayit.hatalar[:20],
            "belirsiz_ornekler": kayit.belirsiz_ornekler,
            "tek_gun_limit_gunleri": kayit.tek_gun_limit[:20],
        },
    }
    return {"kayitlar": kayitlar, "ozet": ozet}

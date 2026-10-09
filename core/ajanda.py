"""
core/ajanda.py

Ajandam (09.10.2026) — danışmanın kişisel takvimi: olay verisi + Rehberim
alarmlarının takvim olayına çevrilmesi.

Olaylar iki kaynaktan gelir ve takvimde tek listede görünür:
  1. 'ajanda_olaylari' tablosu — elle eklenen olaylar (FSBO araması, yer
     gösterimi, randevu vb.)
  2. Rehberim'deki "yeniden ara" alarmları (danisman_kisiler.alarm_zamani)
     — 'kaynak' = 'alarm'; takvimde "Yeniden ara · Kişi" olarak görünür.
     Düzenleme/silme Rehberim'deki alarm fonksiyonlarıyla yapılır.

Tablo henüz oluşturulmadıysa (sql/ajanda_olaylari.sql çalıştırılmadıysa)
olaylari_cek() hata vermez: ([], hata_metni) döner, sayfa uyarı gösterir ve
Rehberim alarmları yine görünür.
"""
import uuid  # noqa: F401  (ileride kimlik üretimi gerekirse)
from datetime import datetime, date, time, timedelta, timezone

import streamlit as st

from core.supabase_client import get_client

supabase = get_client()

TURLER = {
    "fsbo": "FSBO araması",
    "gos": "Yer gösterimi",
    "ran": "Randevu / Toplantı",
    "ara": "Arama / Takip",
    "dig": "Diğer",
}

HATIRLATMA_SECENEKLERI = {
    "Hatırlatma yok": None,
    "Olay saatinde": 0,
    "30 dakika önce": 30,
    "1 saat önce": 60,
    "1 gün önce": 1440,
}

_SAYFA = 1000


def _tz():
    from zoneinfo import ZoneInfo
    return ZoneInfo("Europe/Istanbul")


def simdi_yerel():
    """Türkiye saatiyle şimdi (naive datetime)."""
    try:
        return datetime.now(_tz()).replace(tzinfo=None)
    except Exception:
        return datetime.now()


def bugun_yerel():
    return simdi_yerel().date()


def _hhmm(v):
    return str(v or "10:00")[:5]


@st.cache_data(ttl=30, show_spinner=False)
def olaylari_cek(danisman_adi):
    """Danışmanın tüm ajanda olayları. Döner: (liste, hata_metni_veya_None).
    1000 satır sınırına takılmamak için sayfalayarak okur."""
    tum = []
    try:
        bas = 0
        while True:
            r = (
                supabase.table("ajanda_olaylari").select("*")
                .eq("danisman", danisman_adi)
                .order("tarih").order("saat")
                .range(bas, bas + _SAYFA - 1)
                .execute()
            )
            veri = r.data or []
            tum.extend(veri)
            if len(veri) < _SAYFA:
                break
            bas += _SAYFA
    except Exception as e:  # tablo yok / şema önbelleği eski
        return [], str(e)
    return tum, None


def olay_ekle(danisman_adi, baslik, tur, tarih, saat, kisi_ad="", kisi_id=None,
              yer="", notlar="", hatirlat_dk=None):
    """Yeni olay yazar. hatirlat_dk: None = hatırlatma yok; 0 = olay saatinde;
    diğerleri o kadar dakika önce. Hatırlatma zamanı şimdiden önceyse
    hatırlatma kurulmaz. Döner: hatırlatma kuruldu mu (bool)."""
    tur = tur if tur in TURLER else "dig"
    hz = None
    if hatirlat_dk is not None:
        yerel = datetime.combine(tarih, saat) - timedelta(minutes=hatirlat_dk)
        if yerel > simdi_yerel():
            hz = yerel.replace(tzinfo=_tz()).astimezone(timezone.utc).isoformat()
    supabase.table("ajanda_olaylari").insert({
        "danisman": danisman_adi,
        "baslik": (baslik or "").strip() or TURLER[tur],
        "tur": tur,
        "tarih": tarih.isoformat(),
        "saat": saat.strftime("%H:%M"),
        "kisi_id": str(kisi_id) if kisi_id else None,
        "kisi_ad": (kisi_ad or "").strip() or None,
        "yer": (yer or "").strip() or None,
        "notlar": (notlar or "").strip() or None,
        "hatirlat_zamani": hz,
    }).execute()
    olaylari_cek.clear()
    return hz is not None


def olay_guncelle(olay_id, alanlar):
    alanlar = dict(alanlar)
    alanlar["guncelleme"] = datetime.now(timezone.utc).isoformat()
    supabase.table("ajanda_olaylari").update(alanlar).eq("id", olay_id).execute()
    olaylari_cek.clear()


def olay_ertele(olay):
    """Olayı bir sonraki güne alır; hatırlatma varsa yeniden kurulur."""
    yeni = (_gun(olay["tarih"]) or bugun_yerel()) + timedelta(days=1)
    alanlar = {"tarih": yeni.isoformat()}
    if olay.get("hatirlat_zamani"):
        try:
            d = datetime.fromisoformat(str(olay["hatirlat_zamani"]).replace("Z", "+00:00")) + timedelta(days=1)
            alanlar["hatirlat_zamani"] = d.isoformat()
            alanlar["hatirlat_bildirildi"] = None
        except Exception:
            pass
    olay_guncelle(olay["id"], alanlar)


def olay_tamamla(olay_id, bitti=True):
    olay_guncelle(olay_id, {"tamamlandi": bool(bitti)})


def olay_sil(olay_id):
    supabase.table("ajanda_olaylari").delete().eq("id", olay_id).execute()
    olaylari_cek.clear()


def _gun(v):
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _alarm_yerel(m):
    ham = m.get("alarm_zamani")
    if not ham:
        return None
    try:
        d = datetime.fromisoformat(str(ham).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(_tz()).replace(tzinfo=None)
    except Exception:
        return None


def takvim_olaylari(olaylar, kisiler):
    """Bileşenin çizeceği sade liste. id: ajanda olayı için tablo kimliği,
    Rehberim alarmı için 'a:<kişi id>'. Metinler bileşende kaçışlanır."""
    cikti = []
    for o in olaylar or []:
        t = _gun(o.get("tarih"))
        if not t:
            continue
        cikti.append({
            "id": str(o["id"]), "t": t.isoformat(), "s": _hhmm(o.get("saat")),
            "tur": o.get("tur") if o.get("tur") in TURLER else "dig",
            "b": o.get("baslik") or "", "k": o.get("kisi_ad") or "",
            "yer": o.get("yer") or "", "n": o.get("notlar") or "",
            "done": bool(o.get("tamamlandi")),
            "alarm": bool(o.get("hatirlat_zamani")), "src": "olay",
        })
    for m in kisiler or []:
        z = _alarm_yerel(m)
        if not z:
            continue
        cikti.append({
            "id": f"a:{m['id']}", "t": z.date().isoformat(), "s": z.strftime("%H:%M"),
            "tur": "ara", "b": "Yeniden ara", "k": m.get("ad") or "",
            "yer": "", "n": m.get("alarm_notu") or "",
            "done": False, "alarm": True, "src": "alarm",
        })
    return cikti

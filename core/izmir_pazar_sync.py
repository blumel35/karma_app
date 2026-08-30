# core/izmir_pazar_sync.py
# -*- coding: utf-8 -*-
"""
izmir_pazar_ilanlar merkezi tablosuna Revy pazar verisi yazan ortak
mantık (2026-08-30).

Bu dosya, önceden pages/startkey_portfoy_listesi.py İÇİNE gömülü olan
_mt_* yardımcıları ve merkezi_tabloya_yaz()'ı BURAYA taşıyor — amaç iki
farklı çağıranın (1) Streamlit sayfası (kullanıcı "Yeni Sorgu"ya
bastığında) ve (2) başsız/headless GitHub Actions günlük senkronizasyon
işi (izmir_pazar_sync_job.py) aynı kodu kullanması, ikisinin ayrı ayrı
bakım gerektiren birer kopyası olmaması.

merkezi_tabloya_yaz() artık isteğe bağlı bir supabase_client parametresi
alıyor: Streamlit sayfasından çağrıldığında (parametre verilmezse)
core.supabase_client.get_client() ile eskisi gibi st.secrets üzerinden
bağlanıyor; headless işten çağrıldığında ise revy_sync.py'nin ortam
değişkeni (GitHub Secrets) tabanlı istemcisi doğrudan verilir — böylece
bu modülün kendisi hiçbir kimlik bilgisi okuma/loglama mantığı
İÇERMİYOR, sadece kendisine verilen istemciyi kullanıyor.
"""

import pandas as pd


# ── Satır normalize yardımcıları ────────────────────────────────────────
def _mt_sayi(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() in ("", "nan", "None"):
        return None
    try:
        return float(str(v).replace(".", "").replace(",", "."))
    except Exception:
        return None


def _mt_tarih(v):
    if v is None or str(v).strip() in ("", "nan", "None"):
        return None
    try:
        d = pd.to_datetime(v, dayfirst=True, errors="coerce")
        return d.strftime("%Y-%m-%d") if pd.notna(d) else None
    except Exception:
        return None


def _mt_str(v):
    # NOT: pandas'tan boş gelen METİN sütunları (Ofis, Mahalle, Kullanım
    # Durumu vb.) düz bir float NaN olarak geliyor — bunu string'e çevirmeden
    # doğrudan dict'e koyunca Supabase'e JSON'a çevrilirken "Out of range
    # float values are not JSON compliant: nan" hatası veriyordu.
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    return s if s and s.lower() not in ("nan", "none", "<na>") else None


def _mt_satir_to_kayit(row, aktif: bool):
    from datetime import datetime

    url = row.get("İlan Url") or row.get("İlan Linki")
    if not url or str(url).strip() in ("", "nan"):
        return None
    fiyat = _mt_sayi(row.get("Fiyat"))
    m2 = _mt_sayi(row.get("M2"))
    birim = (fiyat / m2) if (fiyat and m2 and m2 > 0) else None
    return {
        "ilan_linki":             str(url).strip(),
        "marka":                  (_mt_str(row.get("MARKA")) or "").lower() or None,
        "ofis":                   _mt_str(row.get("Ofis")),
        "ofis_norm":              _mt_str(row.get("Ofis_norm")) or _mt_str(row.get("Ofis")),
        "talep_eden_danisan":     _mt_str(row.get("İlan sahibi")),
        "ilce":                   _mt_str(row.get("İlçe")),
        "mahalle":                _mt_str(row.get("Mahalle")),
        "mulk_tipi":              _mt_str(row.get("Mülk tipi")),
        "mulk_turu":              _mt_str(row.get("Mülk türü")),
        "islem_tipi":             _mt_str(row.get("İşlem tipi")),
        "oda_sayisi":             _mt_str(row.get("Oda sayısı")),
        "m2":                     m2,
        "fiyat":                  fiyat,
        "birim_fiyat":            birim,
        "kat":                    _mt_str(row.get("Bulunduğu kat")),
        "bina_yasi":              _mt_str(row.get("Bina Yaşı")),
        "site_icerisinde":        _mt_str(row.get("Site içerisinde")),
        "kullanim_durumu":        _mt_str(row.get("Kullanım Durumu")),
        "esyali":                 _mt_str(row.get("Eşyalı")),
        "ilan_tarihi":            _mt_tarih(row.get("İlan tarihi")),
        "ilan_suresi":            int(_mt_sayi(row.get("İlan Yayın Süresi"))) if _mt_sayi(row.get("İlan Yayın Süresi")) is not None else None,
        "aktif":                  aktif,
        "yayindan_kalkis_tarihi": _mt_tarih(row.get("Yayından Kalkış Tarihi")) if not aktif else None,
        "ilan_kaynagi":           _mt_str(row.get("İlan Kaynağı")),
        "guncelleme_tarihi":      datetime.now().isoformat(),
    }


def merkezi_tabloya_yaz(birlesik: dict, hedef_ilceler: list, progress_cb=None, supabase_client=None):
    """Startkey'e filtrelemeden önceki TÜM markaları merkezi izmir_pazar_ilanlar
    tablosuna yazar (upsert). FSBO ve Pazar Radar bu tablodan okuyacak.
    Hata olursa sessizce geçer — bu, ana Startkey akışını bozmamalı.

    supabase_client verilmezse (Streamlit sayfası çağrısı) core.supabase_client
    üzerinden st.secrets ile bağlanılır; verilmişse (headless iş) doğrudan
    kullanılır — bu fonksiyon hiçbir kimlik bilgisini kendisi okumaz.

    TUR 2A (non_destructive_sync): Otomatik pasifleştirme BİLİNÇLİ OLARAK
    KAPALI — yalnızca ekleme/güncelleme yapılıyor, hiçbir kayıt
    pasifleştirilmiyor (ayrıntı için önceki sürümdeki not korunmuştur).
    """
    if supabase_client is not None:
        supa = supabase_client
    else:
        try:
            from core.supabase_client import get_client
            supa = get_client()
        except Exception as e:
            import logging, uuid
            _takip_kodu = str(uuid.uuid4())[:8]
            logging.getLogger(__name__).exception(
                "Merkezi tabloya bağlantı hatası (takip kodu: %s): %s", _takip_kodu, e
            )
            if progress_cb:
                progress_cb(f"⚠️ Merkezi tabloya yazılamadı. Takip kodu: {_takip_kodu}")
            return {"basarili": False, "yazma_hatasi_sayisi": 0, "yazilan": 0}

    kayitlar = []
    taranan_urller = set()
    _bilinmeyen_anahtarlar = set()
    for anahtar, df_ in (birlesik or {}).items():
        if df_ is None or df_.empty:
            continue
        if anahtar not in ("aktif", "yayindan_kalkan"):
            _bilinmeyen_anahtarlar.add(anahtar)
            continue
        aktif = (anahtar == "aktif")
        for _, row in df_.iterrows():
            k = _mt_satir_to_kayit(row, aktif=aktif)
            if k:
                kayitlar.append(k)
                if aktif:
                    taranan_urller.add(k["ilan_linki"])

    if _bilinmeyen_anahtarlar and progress_cb:
        progress_cb(
            f"⚠️ Beklenmeyen sonuç anahtarı/anahtarları atlandı: "
            f"{', '.join(sorted(_bilinmeyen_anahtarlar))} — bu veri merkezi tabloya yazılmadı."
        )

    if not kayitlar:
        return {"basarili": True, "yazma_hatasi_sayisi": 0, "yazilan": 0}

    if progress_cb:
        progress_cb(f"💾 Merkezi tabloya {len(kayitlar):,} kayıt yazılıyor...")
    yazilan = 0
    yazma_hatasi_sayisi = 0
    for i in range(0, len(kayitlar), 500):
        parca = kayitlar[i:i + 500]
        try:
            supa.table("izmir_pazar_ilanlar").upsert(parca, on_conflict="ilan_linki").execute()
            yazilan += len(parca)
        except Exception as e:
            import logging, uuid
            _takip_kodu = str(uuid.uuid4())[:8]
            logging.getLogger(__name__).exception(
                "Merkezi tablo yazma hatası (parça %d, takip kodu: %s): %s",
                i, _takip_kodu, e,
            )
            yazma_hatasi_sayisi += 1
            if progress_cb:
                progress_cb(f"⚠️ Bir parça yazılamadı. Takip kodu: {_takip_kodu}")

    # ── TUR 2A: Otomatik pasifleştirme geçici olarak KAPALI ──────────────
    if hedef_ilceler:
        try:
            toplam_gorunmeyen = 0
            for ilce_ad in hedef_ilceler:
                mevcut = supa.table("izmir_pazar_ilanlar") \
                    .select("ilan_linki").eq("ilce", ilce_ad).eq("aktif", True).execute()
                eski = {r["ilan_linki"] for r in (mevcut.data or [])}
                toplam_gorunmeyen += len(eski - taranan_urller)
            if toplam_gorunmeyen and progress_cb:
                progress_cb(
                    f"ℹ️ {toplam_gorunmeyen} ilan bu taramada görünmüyor ama "
                    f"pasifleştirilmedi (otomatik pasifleştirme TUR 2B'ye kadar kapalı)."
                )
        except Exception:
            pass

    if progress_cb:
        if yazma_hatasi_sayisi == 0:
            progress_cb(
                f"✅ Merkezi tablo güncellendi: {yazilan:,} kayıt yazıldı "
                f"(pasifleştirme devre dışı — non_destructive_sync)."
            )
        else:
            progress_cb(
                f"⚠️ Merkezi tablo kısmen güncellendi: {yazilan:,} kayıt yazıldı, "
                f"{yazma_hatasi_sayisi} parça başarısız oldu "
                f"(pasifleştirme devre dışı — non_destructive_sync)."
            )

    return {
        "basarili": yazma_hatasi_sayisi == 0,
        "yazma_hatasi_sayisi": yazma_hatasi_sayisi,
        "yazilan": yazilan,
    }


def senkronize(hedef_ilceler, kullanici, sifre, giris_url, supabase_client, progress_cb=None):
    """Verilen ilçe listesini Revy'den (core/revy_pazar_cek.py üzerinden)
    tarayıp izmir_pazar_ilanlar tablosuna yazan uçtan uca akış. Hem headless
    günlük iş (izmir_pazar_sync_job.py) hem de ileride başka bir çağıran
    tarafından kullanılabilir — Streamlit'e bağımlı değildir."""
    import revy_pazar_cek as rpc
    from pathlib import Path

    if not hedef_ilceler:
        if progress_cb:
            progress_cb("ℹ️ Taranacak ilçe yok (hiçbir danışmanın seçili Uzmanlık Bölgesi bulunamadı).")
        return {"basarili": True, "yazma_hatasi_sayisi": 0, "yazilan": 0}

    if progress_cb:
        progress_cb("🌐 Revy'ye bağlanılıyor...")
    cookies = rpc.selenium_cookie_al(
        kullanici=kullanici,
        sifre=sifre,
        giris_url=giris_url or "https://revy.com.tr",
        headless=True,
        progress_cb=progress_cb,
    )

    filtre_ana = {
        "mulk": ["konut", "ticari", "arsa"],
        "islem": ["satilik", "kiralik"],
        "durum": ["aktif"],
    }

    birlesik = {}
    for i, ilce in enumerate(hedef_ilceler, 1):
        if progress_cb:
            progress_cb(f"📍 [{i}/{len(hedef_ilceler)}] {ilce} taranıyor...")
        ilce_filtre = dict(filtre_ana)
        ilce_filtre["ilce"] = [ilce]
        parca = rpc.pazar_cek(
            cookies, ilce_filtre,
            cikti_klasor=Path(__file__).parent.parent / "revy_pazar_cikti",
            progress_cb=progress_cb,
        )
        for anahtar, v in (parca or {}).items():
            if v is None or v.empty:
                continue
            birlesik[anahtar] = (
                pd.concat([birlesik[anahtar], v], ignore_index=True)
                if anahtar in birlesik else v.copy()
            )

    return merkezi_tabloya_yaz(birlesik, hedef_ilceler, progress_cb=progress_cb, supabase_client=supabase_client)

# core/bolge_secici.py
# -*- coding: utf-8 -*-
"""
Danışman FSBO İlanları ve Danışman Startkey İlanları ekranları için
ORTAK bölge-seçici mantığı (2026-08-30).

Tasarım kararı (Meltem ile konuşulup onaylandı): "Uzmanlık Bölgelerim"
ekranındaki kalıcı 5-ilçe seçim mantığı (core/danisman_ortak.py'deki
uzmanlik_bolgelerini_cek / uzmanlik_bolgelerini_kaydet) BİREBİR AYNI
desende, ama FSBO ve Startkey için BİRBİRİNDEN VE Uzmanlık
Bölgelerim'den BAĞIMSIZ iki ayrı tabloya (fsbo_bolgeleri,
startkey_ilan_bolgeleri) uygulanıyor. Sebep: bir danışmanın FSBO takip
ettiği bölgeler ile Startkey ilan ilgi alanı bazen farklı olabiliyor
("bazen fsbo bölgesi farklı olabilir müşteriye özel startkey de bölge
çalışması yapılabilir" — Meltem, 2026-08-30).

Kod tekrarını önlemek için uzmanlik_bolgelerini_cek/kaydet'i BURADA
TEKRAR YAZMAK yerine, hangi tabloya yazılacağını parametre olarak alan
GENEL (generic) bir versiyonu var — hem FSBO hem Startkey ekranı aynı
üç fonksiyonu (tablo adını vererek) çağırıyor:

    bolgelerini_cek(tablo_adi, kullanici)   -> o kullanıcının kalıcı
                                                seçtiği ilçe satırları
    bolgelerini_kaydet(tablo_adi, ilceler)  -> kalıcı seçimi TAMAMEN
                                                değiştirir (en fazla 5)
    aktif_bolgeler(tablo_adi)               -> TÜM danışmanların o
                                                tabloya kaydettiği
                                                ilçelerin tekrarsız
                                                birleşimi (otomatik
                                                senkronizasyon işi için)

Ayrıca ekranların "Uzmanlık Bölgelerim"de OLMAYAN bir desen olan geçici
(ad-hoc) bölge filtresini (kalıcı seçime EK, kaydedilmeyen, oturuma
özel) kalıcı seçimle birleştirmek için etkin_ilceler() var — bu DB'ye
hiç dokunmuyor, saf Python.

Son olarak pazar_ilanlarini_cek(marka, ilceler) — etkin_ilceler()'in
ürettiği birleşik listeyle izmir_pazar_ilanlar tablosundan AKTİF ilanları
çeker (marka='mulk_sahibi' -> FSBO, marka='startkey' -> Startkey
İlanları). ilceler boşsa sorgu hiç atılmaz, boş liste döner.

NOT (2026-08-30): aktif_bolgeler() şu an hiçbir yerden çağrılmıyor —
otomatik senkronizasyon işi (izmir_pazar_sync_job.py) hâlâ sadece
core.danisman_ortak.aktif_uzmanlik_bolgeleri()'ni kullanıyor. FSBO ve
Startkey ekranları tamamlanıp bu iki yeni tabloya gerçek veri girmeye
başlayınca, senkronizasyon kapsamını bu tabloları da içerecek şekilde
genişletmek AYRI BİR ADIM (bilerek şimdi yapılmadı — küçük, test
edilebilir adımlar halinde ilerleniyor).
"""

import streamlit as st

from core.supabase_client import get_client
from core.danisman_ortak import su_anki_danisman

supabase = get_client()

MAX_BOLGE = 5


def bolgelerini_cek(tablo_adi, kullanici):
    """uzmanlik_bolgelerini_cek(kullanici) ile birebir aynı davranış,
    sadece tablo adı parametrik. Cache'siz — çağıran ekran kaydet
    sonrası zaten st.rerun() çağırmalı."""
    resp = supabase.table(tablo_adi).select("*").eq("kullanici", kullanici).execute()
    return resp.data or []


def bolgelerini_kaydet(tablo_adi, ilceler):
    """uzmanlik_bolgelerini_kaydet(ilceler) ile birebir aynı davranış
    (delete + insert, RLS sessiz reddini tespit eden satır-sayısı
    kontrolü dahil), sadece tablo adı parametrik. En fazla MAX_BOLGE
    ilçe — UI tarafında (st.multiselect max_selections=MAX_BOLGE) zaten
    zorlanmalı, burada ikinci bir güvenlik önlemi olarak tekrar kesilir."""
    kullanici = su_anki_danisman()
    ilceler = list(ilceler)[:MAX_BOLGE]
    if not kullanici:
        raise ValueError(
            "Kaydedilemedi: giriş yapan kullanıcı tespit edilemedi "
            "(su_anki_danisman() boş döndü)."
        )
    supabase.table(tablo_adi).delete().eq("kullanici", kullanici).execute()
    if ilceler:
        insert_resp = supabase.table(tablo_adi).insert(
            [{"kullanici": kullanici, "ilce": ilce} for ilce in ilceler]
        ).execute()
        donen_sayi = len(insert_resp.data or [])
        if donen_sayi != len(ilceler):
            raise RuntimeError(
                f"{len(ilceler)} ilçe gönderildi ama Supabase yalnızca "
                f"{donen_sayi} satır döndürdü. Bu genellikle '{tablo_adi}' "
                f"tablosunun Row Level Security (RLS) politikasının INSERT "
                f"işlemini sessizce reddettiği anlamına gelir — Supabase "
                f"panelinde Authentication > Policies kısmından bu "
                f"tablonun INSERT politikasını kontrol et."
            )


def aktif_bolgeler(tablo_adi):
    """TÜM danışmanların verilen tabloya kaydettiği ilçelerin tekrarsız
    (distinct) birleşimini döndürür — aktif_uzmanlik_bolgeleri()'nin
    genel (generic) versiyonu. Otomatik senkronizasyon kapsamı
    genişletildiğinde bu fonksiyon fsbo_bolgeleri ve
    startkey_ilan_bolgeleri için de çağrılacak (bkz. modül üstü not)."""
    try:
        resp = supabase.table(tablo_adi).select("ilce").execute()
        ilceler = sorted({
            (r.get("ilce") or "").strip()
            for r in (resp.data or [])
            if (r.get("ilce") or "").strip()
        })
        return ilceler
    except Exception:
        return []


def etkin_ilceler(kalici_ilceler, gecici_ilceler=None):
    """Kalıcı (kaydedilmiş) bölge seçimi ile o anki oturuma özel geçici
    (ad-hoc, kaydedilmeyen) ek bölge filtresini birleştirip tekrarsız,
    alfabetik sıralı bir liste döndürür. FSBO/Startkey ekranlarında
    izmir_pazar_ilanlar sorgusundaki '.in_("ilce", ...)' filtresi bu
    listeden üretilir. Saf Python — Supabase'e hiç dokunmaz."""
    birlesim = set(kalici_ilceler or []) | set(gecici_ilceler or [])
    return sorted(b for b in birlesim if b)


@st.cache_data(ttl=60, show_spinner="Pazar ilanları yükleniyor...")
def pazar_ilanlarini_cek(marka, ilceler):
    """izmir_pazar_ilanlar tablosundan, verilen marka ('mulk_sahibi' ->
    Danışman FSBO İlanları, 'startkey' -> Danışman Startkey İlanları) ve
    etkin ilçe kümesine göre AKTİF ilanları çeker.

    ilceler boşsa (henüz hiçbir bölge — ne kalıcı ne geçici — seçilmemişse)
    hiç sorgu atmadan boş liste döner: hem gereksiz bir 'tüm İzmir' sorgusu
    hem de danışmanın hiç seçmediği bölgelerin yanlışlıkla görünmesi
    böylece engellenmiş olur (core/danisman_ortak.py'deki
    uzmanlik_bolgesi_filtrele'nin DAVRANIŞÇA aynı temkinli deseni).

    DÜZELTME (30.08.2026): PostgREST tek sorguda EN FAZLA 1000 satır
    döndürüyor — ilk sürüm bunu hesaba katmıyordu, tek ilçede bile tam
    1000 kayıt varsa (gerçek toplam bundan fazla olsa da) sessizce
    kırpılıyordu. core/danisman_ortak.py'deki _tum_sayfalari_cek() ile
    AYNI sayfalama (range) deseni burada da uygulanıyor."""
    if not ilceler:
        return []
    tum_kayitlar = []
    baslangic = 0
    sayfa_boyutu = 1000
    while True:
        resp = (
            supabase.table("izmir_pazar_ilanlar")
            .select("*")
            .eq("marka", marka)
            .eq("aktif", True)
            .in_("ilce", list(ilceler))
            .order("id", desc=True)
            .range(baslangic, baslangic + sayfa_boyutu - 1)
            .execute()
        )
        satirlar = resp.data or []
        tum_kayitlar.extend(satirlar)
        if len(satirlar) < sayfa_boyutu:
            break
        baslangic += sayfa_boyutu
    return tum_kayitlar

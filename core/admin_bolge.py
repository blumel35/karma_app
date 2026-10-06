# core/admin_bolge.py
# -*- coding: utf-8 -*-
"""
Yönetici (admin) bölge yönetimi için yardımcı fonksiyonlar (06.10.2026).

Meltem: "bana bir admin sayfası ekleyelim, ben orada her danışman için
onlara sorarak en fazla 5 adet olacak şekilde FSBO / Startkey ve Uzmanlık
bölgelerini kaydedeyim" — pilot grup: Ahmet Koç, Sinan Yücesoy, Ömer
Bayraktar, Turgay Özdemir, Mustafa Balcı, Erhan Yaşar.

NEDEN AYRI MODÜL: core/bolge_secici.py ve core/danisman_ortak.py'deki
kaydet/ayarla fonksiyonları KASITLI olarak "giriş yapan kullanıcı"
(su_anki_danisman()) adına yazıyor. Burada ise yönetici BAŞKA bir
danışman adına yazıyor — bu yüzden kullanıcı adı AÇIK parametre. Mevcut
dosyalara dokunulmadı (canlıdaki ekranlar etkilenmesin).

KANONİK AD: kayıtlar her zaman zeta_personel_listesi.xlsx'teki ad_soyad ile
yazılır (uygulamanın oturumda kullandığı ad ile aynı) — aynı kişinin hem
"Turgay Özdemir" hem "turgay.ozdemir" adıyla ikiye bölünmesini önler.

Üç bölge türü, üç ayrı tablo:
    fsbo      -> fsbo_bolgeleri            (ilce, mahalleler, bildirim_acik)
    startkey  -> startkey_ilan_bolgeleri   (ilce, mahalleler, bildirim_acik)
    uzmanlik  -> uzmanlik_bolgeleri        (ilce, bildirim_acik; mahalle YOK)

Servis anahtarıyla (get_client) çalıştığı için RLS'e takılmaz.
"""

from core.supabase_client import get_client

supabase = get_client()

MAX_BOLGE = 5

BOLGE_TURLERI = {
    "fsbo": {
        "tablo": "fsbo_bolgeleri",
        "marka": "mulk_sahibi",
        "etiket": "FSBO",
        "mahalle": True,
    },
    "startkey": {
        "tablo": "startkey_ilan_bolgeleri",
        "marka": "startkey",
        "etiket": "Startkey",
        "mahalle": True,
    },
    "uzmanlik": {
        "tablo": "uzmanlik_bolgeleri",
        "marka": None,
        "etiket": "Uzmanlık",
        "mahalle": False,
    },
}


def _tablo(tur):
    return BOLGE_TURLERI[tur]["tablo"]


def _kullanici_kontrol(kullanici):
    kullanici = (kullanici or "").strip()
    if not kullanici:
        raise ValueError("Kaydedilemedi: danışman adı boş.")
    return kullanici


def bolgeleri_cek(tur, kullanici):
    """Tek bir danışmanın bu türdeki ilçe satırları."""
    resp = (
        supabase.table(_tablo(tur))
        .select("*")
        .eq("kullanici", kullanici)
        .execute()
    )
    return resp.data or []


def tum_bolgeleri_cek(tur):
    """{kullanici: [satır, ...]} — genel durum tablosu için."""
    try:
        resp = supabase.table(_tablo(tur)).select("*").execute()
    except Exception:
        return {}
    sonuc = {}
    for r in (resp.data or []):
        k = (r.get("kullanici") or "").strip()
        if k:
            sonuc.setdefault(k, []).append(r)
    return sonuc


def cihaz_sayilari():
    """{kullanici: bildirim cihazı sayısı} (push_abonelikleri)."""
    try:
        resp = supabase.table("push_abonelikleri").select("kullanici").execute()
    except Exception:
        return {}
    sonuc = {}
    for r in (resp.data or []):
        k = (r.get("kullanici") or "").strip()
        if k:
            sonuc[k] = sonuc.get(k, 0) + 1
    return sonuc


def bolgeleri_kaydet(tur, kullanici, ilceler):
    """Danışmanın bu türdeki ilçe seçimini istenen listeye eşitler.

    Sil-hepsini-yeniden-ekle YAPMAZ: yalnızca çıkarılan ilçeleri siler,
    yalnızca yeni eklenen ilçeleri ekler. Hâlâ seçili kalan bir ilçenin
    mahalle alt-filtresi ve bildirim açık/kapalı tercihi böylece hiç
    dokunulmadan korunur. Sonunda tabloyu yeniden okuyup sonucu doğrular;
    beklenenle uyuşmazsa AÇIKÇA hata fırlatır (sessiz başarısızlık yok)."""
    kullanici = _kullanici_kontrol(kullanici)
    cfg = BOLGE_TURLERI[tur]
    tablo = cfg["tablo"]

    istenen = []
    for i in ilceler or []:
        i = (i or "").strip()
        if i and i not in istenen:
            istenen.append(i)
    if len(istenen) > MAX_BOLGE:
        raise ValueError(f"En fazla {MAX_BOLGE} ilçe seçilebilir.")

    mevcut = {r["ilce"] for r in bolgeleri_cek(tur, kullanici)}
    silinecek = sorted(mevcut - set(istenen))
    eklenecek = [i for i in istenen if i not in mevcut]

    if silinecek:
        (
            supabase.table(tablo)
            .delete()
            .eq("kullanici", kullanici)
            .in_("ilce", silinecek)
            .execute()
        )

    if eklenecek:
        satirlar = []
        for i in eklenecek:
            satir = {"kullanici": kullanici, "ilce": i, "bildirim_acik": True}
            if cfg["mahalle"]:
                satir["mahalleler"] = []
            satirlar.append(satir)
        resp = supabase.table(tablo).insert(satirlar).execute()
        donen = len(resp.data or [])
        if donen != len(satirlar):
            raise RuntimeError(
                f"{len(satirlar)} ilçe gönderildi ama Supabase {donen} satır "
                f"döndürdü ('{tablo}' tablosu)."
            )

    sonra = {r["ilce"] for r in bolgeleri_cek(tur, kullanici)}
    if sonra != set(istenen):
        raise RuntimeError(
            f"Kayıt doğrulanamadı. Beklenen: {sorted(istenen)}, "
            f"tabloda görülen: {sorted(sonra)}."
        )


def ilce_bildirim_ayarla(tur, kullanici, ilce, acik):
    """Tek bir ilçenin bildirim açık/kapalı durumu (seçime dokunmaz)."""
    kullanici = _kullanici_kontrol(kullanici)
    (
        supabase.table(_tablo(tur))
        .update({"bildirim_acik": bool(acik)})
        .eq("kullanici", kullanici)
        .eq("ilce", ilce)
        .execute()
    )


MIN_SIFRE_UZUNLUGU = 8


def giris_hesabi_id_bul(email):
    """E-postaya karşılık gelen Supabase Auth kullanıcısının id'sini döner
    (yoksa None). Yönetici API'sinde e-postayla doğrudan arama olmadığı için
    kullanıcılar sayfa sayfa taranır — 15 kişilik bir ekipte tek sayfa yeter,
    büyürse döngü devam eder."""
    email = (email or "").strip().lower()
    if not email:
        return None
    sayfa, sayfa_boyutu = 1, 100
    while True:
        kullanicilar = supabase.auth.admin.list_users(page=sayfa, per_page=sayfa_boyutu)
        for u in kullanicilar:
            if (getattr(u, "email", "") or "").strip().lower() == email:
                return u.id
        if len(kullanicilar) < sayfa_boyutu:
            return None
        sayfa += 1


def sifre_belirle(email, yeni_sifre):
    """YÖNETİCİ, danışmanın giriş şifresini belirler (06.10.2026, Meltem:
    "şifre değiştirmek isteyen bana müracaat etsin"). Supabase yönetici
    API'sini (servis anahtarı) kullanır; şifre HİÇBİR yere yazılmaz/loglanmaz.
    email_confirm=True: daveti hiç tamamlamamış (ör. hiç giriş yapmamış) bir
    hesap, şifre belirlenince 'e-posta onaylanmadı' hatasına takılmasın."""
    yeni_sifre = str(yeni_sifre or "")
    if len(yeni_sifre) < MIN_SIFRE_UZUNLUGU:
        raise ValueError(f"Şifre en az {MIN_SIFRE_UZUNLUGU} karakter olmalı.")
    uid = giris_hesabi_id_bul(email)
    if not uid:
        raise LookupError(f"'{email}' e-postasıyla bir giriş hesabı bulunamadı.")
    supabase.auth.admin.update_user_by_id(
        uid, {"password": yeni_sifre, "email_confirm": True}
    )


def ilce_mahallelerini_ayarla(tur, kullanici, ilce, mahalleler):
    """Tek bir ilçenin mahalle alt-filtresi (boş liste = tüm mahalleler).
    Uzmanlık tablosunda mahalle sütunu olmadığı için reddedilir."""
    if not BOLGE_TURLERI[tur]["mahalle"]:
        raise ValueError("Bu bölge türünde mahalle seçimi yok.")
    kullanici = _kullanici_kontrol(kullanici)
    (
        supabase.table(_tablo(tur))
        .update({"mahalleler": list(mahalleler or [])})
        .eq("kullanici", kullanici)
        .eq("ilce", ilce)
        .execute()
    )

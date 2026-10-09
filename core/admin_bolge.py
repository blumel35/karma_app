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


def alias_birlestirme_plani(alias, kanonik):
    """E-posta önü adıyla ('ahmet.koc') kalmış kayıtların kanonik ada
    ('Ahmet Koç') taşınması için ÖNİZLEME. Hiçbir şey yazmaz.
    Kural: kanonik adda zaten olan ilçe -> alias satırı silinir (kanonik
    kayıt, tercihleriyle birlikte korunur); olmayan ilçe -> taşınır, ancak
    toplam MAX_BOLGE'yi aşıyorsa taşınmaz (silinmez, alias'ta kalır).
    Döner: {tur: {"tasi": [...], "zaten_var": [...], "sigmayan": [...]}},
    ayrıca "cihaz": alias'a bağlı bildirim cihazı sayısı."""
    plan = {}
    for tur in BOLGE_TURLERI:
        a = bolgeleri_cek(tur, alias)
        k = {r["ilce"] for r in bolgeleri_cek(tur, kanonik)}
        tasi, var, sigmayan = [], [], []
        for r in a:
            if r["ilce"] in k:
                var.append(r["ilce"])
            elif len(k) + len(tasi) < MAX_BOLGE:
                tasi.append(r["ilce"])
            else:
                sigmayan.append(r["ilce"])
        plan[tur] = {"tasi": tasi, "zaten_var": var, "sigmayan": sigmayan}
    try:
        resp = supabase.table("push_abonelikleri").select("id").eq("kullanici", alias).execute()
        plan["cihaz"] = len(resp.data or [])
    except Exception:
        plan["cihaz"] = 0
    return plan


def alias_birlestir(alias, kanonik):
    """alias_birlestirme_plani'nın kuralıyla kayıtları gerçekten taşır.
    Satırları yeniden eklemez, yalnızca kullanici alanını günceller (mahalle
    ve bildirim tercihleri korunur). Sonunda yeni plan döner (boş olmalı)."""
    alias = _kullanici_kontrol(alias)
    kanonik = _kullanici_kontrol(kanonik)
    if alias.casefold() == kanonik.casefold():
        raise ValueError("Alias ile kanonik ad aynı.")
    plan = alias_birlestirme_plani(alias, kanonik)
    for tur, p in plan.items():
        if tur == "cihaz":
            continue
        tablo = _tablo(tur)
        if p["zaten_var"]:
            (supabase.table(tablo).delete().eq("kullanici", alias)
             .in_("ilce", p["zaten_var"]).execute())
        if p["tasi"]:
            (supabase.table(tablo).update({"kullanici": kanonik})
             .eq("kullanici", alias).in_("ilce", p["tasi"]).execute())
    if plan.get("cihaz"):
        (supabase.table("push_abonelikleri").update({"kullanici": kanonik})
         .eq("kullanici", alias).execute())
    return alias_birlestirme_plani(alias, kanonik)


def eslestirme_kodu_uret(kullanici):
    """iPhone bildirim eşleştirme kodu (09.10.2026): Supabase'deki
    eslestirme_kodu_uret() fonksiyonu 10 dk geçerli, tek kullanımlık 6 haneli
    kod üretir (aynı kişinin önceki kullanılmamış kodu iptal olur). Kod,
    danışmanın kanonik adına bağlıdır; danışman mini-PWA'da kodu yazınca
    abonelik bu ad altına kaydolur. Döner: (kod, son_kullanma_iso)."""
    kullanici = _kullanici_kontrol(kullanici)
    resp = supabase.rpc("eslestirme_kodu_uret", {"p_kullanici": kullanici}).execute()
    veri = resp.data
    if isinstance(veri, list):
        veri = veri[0] if veri else None
    if not isinstance(veri, dict) or not veri.get("kod"):
        raise RuntimeError(f"Kod üretilemedi, Supabase yanıtı: {veri!r}")
    return veri["kod"], veri.get("son_kullanma")


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


def giris_hesaplari():
    """{e-posta (küçük harf): son giriş zamanı veya None} — Supabase Auth'ta
    hesabı olan herkes. Hesabı olmayan danışmanın bölgesi yine girilebilir
    (kayıtlar ada göre tutulur) ama uygulamayı açana kadar uygulama içi
    görünüm/bildirim olmaz. Alınamazsa None döner (sayfa bozulmasın)."""
    sonuc, sayfa, sayfa_boyutu = {}, 1, 100
    try:
        while True:
            liste = supabase.auth.admin.list_users(page=sayfa, per_page=sayfa_boyutu)
            for u in liste:
                e = (getattr(u, "email", "") or "").strip().lower()
                if e:
                    sonuc[e] = getattr(u, "last_sign_in_at", None)
            if len(liste) < sayfa_boyutu:
                break
            sayfa += 1
    except Exception:
        return None
    return sonuc


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

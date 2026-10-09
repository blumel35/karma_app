# core/bildirim_tetikleyici.py
# -*- coding: utf-8 -*-
"""
Talep/Portföy eklendiğinde iki bildirim türünü tetikleyen ortak katman
(23.09.2026 — Meltem: "uzmanlık bölgelerim ilçe bazlı bildirim olsa
yeterli fikrini sevdim... zeta etkileşimleri olsun istiyorum (bölgeden
bağımsız) örneğin ömer çiğli de yeni bir portföy ilanı paylaştı. sinan
buda için bir alıcı talebi girdi gibi.").

Planlanan 4 bildirim kaynağından (A: Uzmanlık Bölgem, B: Startkey
İlanları, C: FSBO İlanları, D: Zeta Etkileşimleri) bu dosya A ve D'yi
(manuel ekleme anında, senkron) VE artık B ile C'nin "yeni ilan" kısmını
(günde bir kere, headless — bkz. pazar_yeni_ilan_bildirimleri_gonder())
kapsıyor.

FAZ 2 (27.09.2026 — Meltem onayı: "önce sadece yeni ilan bildirimi",
"ayrı bildirimler" [FSBO ve Startkey için ayrı ayrı, birleşik özet
değil]): pazar_yeni_ilan_bildirimleri_gonder(), pazar_bildirim_job.py
(yeni, headless) tarafından GÜNDE BİR KERE, core/izmir_pazar_sync.py'nin
günlük senkronizasyonu BİTTİKTEN HEMEN SONRA (aynı GitHub Actions
job'ında, aynı runner'da) çağrılır — izmir_pazar_ilanlar tablosu taze
olsun diye. Fiyat düşüşü tespiti BİLEREK bu turda YOK (Meltem: mevcut
senkronizasyon akışına eski fiyatı saklayan yeni bir adım gerektiriyor,
ayrı/daha büyük bir iş — Faz 3'e bırakıldı).

DÜZELTME (27.09.2026, Meltem: "sorunsuz çalıştı ama bildirim gelmedi.
revy de ilanlar 3 gün geriden geliyor ondan olabilir mi"): ilk sürüm
"yeni ilan" tetikleyicisi ilan_tarihi (Revy'nin kendi tarihi) == bugün
şartına bakıyordu; gerçek Supabase verisiyle bunun neredeyse hiç
eşleşmediği doğrulandı. Artık izmir_pazar_ilanlar.ilk_gorulme_tarihi
(yeni sütun, sadece gerçek İLK INSERT'te dolan, sonraki güncellemelerde
değişmeyen bir zaman damgası) kullanılıyor — bkz. _pazar_ilk_gorulme_gun.
Aynı kök sebep pages/Danisman_Secim.py'deki FSBO "+N yeni" rozetini ve
Startkey "Son 24 saat" sayısını da etkiliyordu, ikisi de aynı turda
düzeltildi.

FAZ 1 kararı (Meltem onayı — "tek anahtar, hepsi birlikte"): 4 kaynak
için AYRI AÇMA/KAPAMA tercihi YOK — mevcut tek "Telefon Bildirimlerini
Aç" anahtarını (core/push_bildirim.py) açmış olan HERKES, ilgili
olay gerçekleştiğinde otomatik olarak bildirim alır. İleride ihtiyaç
çıkarsa (Meltem'in "sırayla başlayalım" tercihiyle tutarlı) kaynak
bazlı açma/kapama ayrı bir adımda eklenebilir.

talep_portfoy_bildirim_gonder(), core/danisman_ortak.py'deki
ekle_dialog() içinde, bir kayıt Supabase'e BAŞARIYLA eklendikten HEMEN
SONRA çağrılır. BİLEREK sadece MANUEL ekleme akışını kapsıyor (temiz/
güvenilir "kim ekledi" ve "hangi ilçe" bilgisi burada var) — mail
otomasyonuyla (core/mail_job.py) otomatik ayrıştırılan kayıtlar için
aynı bildirim AYRI, sonraki bir adımda eklenebilir (oradaki "kim"
bilgisi mail başlığından geliyor, buradaki kadar güvenilir/normalize
değil — küçük adımlarla ilerleme kararına uygun, bilerek şimdi
kapsanmadı).

Bildirim gönderimi BEST-EFFORT'tur — herhangi bir hata (Supabase
sorgusu, push gönderimi) SESSİZCE yutulur; asıl kayıt ekleme akışını
ASLA bozmamalı veya kullanıcıya hata göstermemeli (kayıt zaten
başarıyla eklenmiş oluyor, bildirim ikincil bir katman).
"""

from datetime import date, datetime

from core.supabase_client import get_client
from core.push_bildirim import bildirim_gonder, KARMA_APP_URL

supabase = get_client()

# DÜZELTME (28.09.2026, Meltem: "bildirim sistemi başarılı oldu ama
# panoyu aç dediğinde bildirimin bahsettiği ekranı açmıyor ana sayfayı
# açıyor. o ekranı açmalı hatta bugün 2 yeni ilan dediyse bugün
# filtresiyle ilgili sayfa açılmalı") — KÖK SEBEP: bu dosyadaki HER
# bildirim_gonder() çağrısı url parametresini hiç geçmiyordu, bu yüzden
# core/push_bildirim.py'nin varsayılanı (KARMA_APP_URL + "/Danisman_Secim"
# — yani ana sayfa) HER bildirim türü için kullanılıyordu, bildirimin
# gerçek konusundan bağımsız olarak. Artık her bildirim türü kendi
# ekranına özel bir url gönderiyor; FSBO/Startkey ayrıca ?zaman=bugun
# ekliyor ki hedef sayfa (pages/Danisman_FSBOIlanlari.py /
# Danisman_StartkeyIlanlari.py) "Bugün" filtresiyle açılsın (bkz. o
# dosyalardaki aynı tarihli düzeltme notu).
_TALEP_URL = f"{KARMA_APP_URL}/Danisman_Talep"
_PORTFOY_URL = f"{KARMA_APP_URL}/Danisman_Portfoy"
_FSBO_BUGUN_URL = f"{KARMA_APP_URL}/Danisman_FSBOIlanlari?zaman=bugun"
_STARTKEY_BUGUN_URL = f"{KARMA_APP_URL}/Danisman_StartkeyIlanlari?zaman=bugun"


def _ilce_normalize(ilce):
    return (ilce or "").strip().casefold()


def _uzmanlik_bolgesi_eslesenler(ilceler):
    """Verilen ilçe listesinden EN AZ biriyle Uzmanlık Bölgesi'nde
    eşleşen danışmanların {kullanici: eşleşen_ilce} sözlüğünü döner.
    Bir danışmanın birden fazla ilçesi eşleşse bile tek bir bildirim
    gitsin diye sadece İLK eşleşen (VE bildirimi açık olan) ilçe
    tutulur.

    DÜZELTME (28.09.2026, Meltem: "uzmanlık bölgelerindeki ilçelere tek
    tek bildirim açık/kapalı butonu olmalı ... sadece balcova
    bildirimleri gelsin isteyebilir"): bildirim_acik=False olan bir
    ilçe artık EŞLEŞME SAYILMIYOR — o ilçe için push gönderilmez, ama
    kullanıcının başka (bildirimi açık) bir ilçesi eşleşirse yine o
    üzerinden bildirim alır. bildirim_acik sütunu henüz migration
    çalıştırılmamış eski satırlarda yoksa (None), varsayılan olarak
    açık (True) sayılır — geriye dönük davranış bozulmaz."""
    hedef = {_ilce_normalize(i) for i in (ilceler or []) if i}
    if not hedef:
        return {}
    try:
        resp = supabase.table("uzmanlik_bolgeleri").select("kullanici, ilce, bildirim_acik").execute()
    except Exception:
        return {}
    eslesenler = {}
    for row in (resp.data or []):
        kullanici = (row.get("kullanici") or "").strip()
        ilce = row.get("ilce") or ""
        bildirim_acik = row.get("bildirim_acik")
        if bildirim_acik is False:
            continue
        if not kullanici or _ilce_normalize(ilce) not in hedef:
            continue
        if kullanici not in eslesenler:
            eslesenler[kullanici] = ilce
    return eslesenler


def _push_abone_kullanicilar():
    """Telefon bildirimini açmış (en az bir cihazda kayıtlı aboneliği
    olan) TÜM danışmanların kullanıcı adlarının tekrarsız kümesini
    döner — Zeta Etkileşimleri'nin (D) hedef kitlesi budur."""
    try:
        resp = supabase.table("push_abonelikleri").select("kullanici").execute()
    except Exception:
        return set()
    return {(r.get("kullanici") or "").strip() for r in (resp.data or []) if r.get("kullanici")}


def talep_portfoy_bildirim_gonder(kayit_tipi, ilceler, olusturan, islem_tipi=None, kayit=None):
    """Yeni bir talep/portföy kaydı BAŞARIYLA eklendikten sonra çağrılır.

    kayit_tipi: "Talep" | "Portföy"
    ilceler:    o kayıtta seçilen ilçe(ler) — liste, birden fazla olabilir
    olusturan:  kaydı ekleyen danışmanın kullanıcı adı (su_anki_danisman())
                — kendi eklediği kayıt için KENDİSİNE bildirim gitmez.
    islem_tipi: "Satılık" | "Kiralık" (opsiyonel, A mesajına eklenir)

    Hiçbir şey döndürmez, hiçbir hatayı dışarı sızdırmaz (best-effort)."""
    try:
        _gonder_ic(kayit_tipi, ilceler, olusturan, islem_tipi, kayit)
    except Exception:
        pass


def _gonder_ic(kayit_tipi, ilceler, olusturan, islem_tipi, kayit=None):
    ilceler = [i for i in (ilceler or []) if i]
    if not ilceler:
        return
    olusturan_norm = (olusturan or "").strip().casefold()
    portfoy_mu = (kayit_tipi == "Portföy")
    tur_adi = "portföy" if portfoy_mu else "talep"
    ilk_ilce = ilceler[0]
    islem_ek = f"{islem_tipi} " if islem_tipi else ""
    # 28.09.2026: A/D/E bildirimleri hep AYNI kaydın (bu çağrıdaki
    # kayit_tipi) panosuna işaret eder — talep mi portföy mü olduğuna
    # göre doğru ekran.
    panosu_url = _PORTFOY_URL if portfoy_mu else _TALEP_URL

    # YENİ (09.10.2026): kayıt verildiyse, ilan-linki açık kullanıcılara
    # (_SNAPSHOT_LINK_KULLANICILARI) giriş istemeyen kayıt linki gider.
    # Link TEK kez (ilk gereken anda) üretilir, aynı kayıt için herkese
    # yeniden kullanılır; üretilemezse sessizce uygulama içi adrese düşer.
    _snap = {"url": None, "denendi": False}

    def _hedef(kullanici):
        if kayit and _snapshot_acik_mi(kullanici):
            if not _snap["denendi"]:
                _snap["denendi"] = True
                _snap["url"] = _kayit_pano_url(
                    [kayit], "portfoy" if portfoy_mu else "talep",
                    "Yeni Portföy" if portfoy_mu else "Yeni Talep", "portfoy" if portfoy_mu else "talep",
                )
            if _snap["url"]:
                return _snap["url"]
        return panosu_url

    # ── A) Uzmanlık Bölgesi eşleşenler — bölge bazlı, isimsiz/nesnel metin.
    # DEĞİŞTİ (26.09.2026, Meltem: "yazı karakteri renk değişse vs dikkat
    # çekici olsun istiyorum"): sistem bildirimlerinin yazı tipi/rengi
    # Android tarafından sabitlendiği için (platform sınırı — bkz.
    # sw.js'teki not), tek kontrol edebildiğimiz "renk" başlıktaki emoji —
    # bölge eşleşmesi 📍 ile işaretlendi, bildirim listesinde bir bakışta
    # ayırt edilsin diye.
    eslesenler = _uzmanlik_bolgesi_eslesenler(ilceler)
    bildirilenler = set()
    bildirilen_isimler = []
    for kullanici, ilce in eslesenler.items():
        if kullanici.strip().casefold() == olusturan_norm:
            continue
        bildirim_gonder(
            kullanici,
            "📍 Uzmanlık Bölgeniz",
            f"Uzmanlık bölgeniz olan {ilce} bölgesinde 1 adet {islem_ek}{tur_adi} yayınlandı.",
            url=_hedef(kullanici),
        )
        bildirilenler.add(kullanici.strip().casefold())
        bildirilen_isimler.append(kullanici)

    # ── D) Zeta Etkileşimleri — bölgeden BAĞIMSIZ, telefon bildirimini
    # açmış TÜM danışmanlara (A'da zaten bildirim alanlar HARİÇ — aynı
    # olay için aynı kişiye 2. bildirim gitmesin diye).
    if portfoy_mu:
        govde = f"{olusturan} {ilk_ilce} bölgesinde yeni bir portföy ilanı paylaştı."
    else:
        govde = f"{olusturan} {ilk_ilce} bölgesi için bir alıcı talebi girdi."

    for kullanici in _push_abone_kullanicilar():
        kullanici_norm = kullanici.strip().casefold()
        if kullanici_norm == olusturan_norm or kullanici_norm in bildirilenler:
            continue
        bildirim_gonder(kullanici, "🔔 Zeta Etkileşimleri", govde, url=_hedef(kullanici))
        bildirilen_isimler.append(kullanici)

    # ── E) Kendine ONAY bildirimi — YENİ (26.09.2026, Meltem: "ama ben
    # olduğum için bana gelmeyecek bu pek mantıklı değil, kişi kendi de
    # bildirim gitti mi görmek isteyebilir"): A/D bilerek kaydı ekleyen
    # kişiye göndermiyor (kendi paylaştığı şeyi kendine haber vermenin
    # anlamı yok) — ama kişi PIPELINE'ın gerçekten çalışıp çalışmadığını
    # görmek isteyebilir. Bu yüzden olusturan'a AYRI, farklı içerikli
    # (kaç kişiye gittiğini özetleyen) bir onay bildirimi gidiyor —
    # bildirim_gonder() zaten push gitsin gitmesin bildirim_gecmisi'ne
    # yazıyor, yani push aboneliği olmasa bile "Bildirimlerim" ekranında
    # bu onay görünür, kişi kendi paylaşımının tetiklendiğini doğrulayabilir.
    # DEĞİŞTİ (27.09.2026, Meltem: "2 danışmana bildirim gitti mesajı geldi
    # ama bu danışmanlar kim bilsem daha iyi değil mi"): sadece sayı değil,
    # bildirilen_isimler listesi de (A + D'de gerçekten push_gonder()
    # çağrılan herkesin kullanıcı adı) onay metnine ekleniyor.
    toplam_bildirilen = len(bildirilen_isimler)
    if toplam_bildirilen:
        isim_listesi = ", ".join(bildirilen_isimler)
        onay_govde = (
            f"{tur_adi.capitalize()} kaydınız paylaşıldı — {toplam_bildirilen} "
            f"danışmana bildirim gitti: {isim_listesi}."
        )
    else:
        onay_govde = f"{tur_adi.capitalize()} kaydınız paylaşıldı — şu an eşleşen/abone bir danışman yoktu."
    bildirim_gonder(olusturan, "✅ Paylaşıldı", onay_govde, url=_hedef(olusturan))


# ══════════════════════════════════════════════════════════════════════
# FAZ 2 (27.09.2026) — Startkey İlanları (B) + FSBO İlanları (C): günlük
# toplu "bugün yeni ilan çıktı" bildirimleri. bkz. modül üstü not.
#
# NOT: core.bolge_secici burada BİLEREK modül üstünde değil, fonksiyon
# içinde import ediliyor — core.danisman_ortak (bolge_secici'nin
# su_anki_danisman() için import ettiği modül) bu dosyadaki
# talep_portfoy_bildirim_gonder'i modül üstünde import ediyor
# (danisman_ortak.py satır 41); modül üstünde import edilseydi
# bildirim_tetikleyici -> bolge_secici -> danisman_ortak ->
# bildirim_tetikleyici döngüsel import hatası (ImportError) oluşurdu.
# ══════════════════════════════════════════════════════════════════════

def _pazar_ilk_gorulme_gun(v):
    """DÜZELTME (27.09.2026 — Meltem: "sorunsuz çalıştı ama bildirim
    gelmedi. revy de ilanlar 3 gün geriden geliyor ondan olabilir mi"):
    bu fonksiyon ÖNCEDEN ilan_tarihi'ne (Revy'nin kendi "İlan tarihi"
    sütunu) bakıyordu. Meltem'in verdiği Supabase sorgusuyla doğrulandı:
    bugün taranan/dokunulan ilanlar arasında ilan_tarihi'ne göre GERÇEKTEN
    "bugün" (gün farkı=0) olan pratikte YOK, dağılım 100 güne kadar
    yayılıyor — yani ilan_tarihi bizim "bunu ilk gördüğümüz tarih"imiz
    DEĞİL, Revy'nin kendi (gecikmeli/güvenilmez) tarihi; "== bugün"
    filtresi bu yüzden neredeyse hiç eşleşmiyordu.

    Artık yeni izmir_pazar_ilanlar.ilk_gorulme_tarihi sütununa bakıyor —
    bu sütun SADECE bir ilan tabloya İLK YAZILDIĞINDA (gerçek INSERT)
    Postgres'in kendi DEFAULT now()'ıyla dolar; core/izmir_pazar_sync.py
    bu alanı upsert payload'ına BİLEREK hiç eklemiyor, böylece sonraki
    güncellemelerde (aynı ilan tekrar aktif görüldüğünde) ASLA
    değişmiyor. Yani "bizim veritabanımız bunu bugün ilk kez gördü"
    sinyali — Revy'nin kendi tarihi ne olursa olsun güvenilir."""
    t = v.get("ilk_gorulme_tarihi")
    if not t:
        return None
    try:
        return datetime.strptime(str(t)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _pazar_bugun_ilanlari(tablo_adi, marka):
    """_pazar_bugun_sayilari ile AYNI hesap (kullanıcının ilçe + mahalle +
    bildirim anahtarı ayarlarına göre BUGÜN ilk kez görülen ilanlar), ama
    sayı yerine İLAN LİSTESİ döner: {kullanici: [ilan_satiri, ...]}.
    Listesi boş kullanıcılar sonuca dahil edilmez. (05.10.2026 — bildirimden
    açılan, o kullanıcının o günkü ilanlarını gösteren link için.)"""
    return _pazar_bugun_hesapla(tablo_adi, marka)


def _pazar_bugun_sayilari(tablo_adi, marka):
    """{kullanici: sayı} — _pazar_bugun_hesapla'nın sayı özeti."""
    return {k: len(v) for k, v in _pazar_bugun_hesapla(tablo_adi, marka).items()}


def _pazar_bugun_hesapla(tablo_adi, marka):
    """tablo_adi'na (fsbo_bolgeleri | startkey_ilan_bolgeleri) kayıtlı HER
    kullanıcı için, KENDİ seçtiği ilçelerde (varsa KENDİ mahalle alt-
    filtresiyle) BUGÜN veritabanına İLK KEZ yazılan (ilk_gorulme_tarihi
    = bugün — bkz. _pazar_ilk_gorulme_gun) ilan SAYISINI hesaplar. Sonuç
    {kullanici: sayı} — sayısı 0 olan kullanıcılar sonuca dahil edilmez
    (çağıran taraf zaten sadece bildirim gidecekleri dolaşıyor).

    DÜZELTME (01.10.2026, Meltem: "... mahalle seçmek istiyorlar"):
    core/bolge_secici.py:tum_kullanicilarin_bolgeleri() artık her ilçe
    için mahalleler alt-listesini de taşıyor (bkz. o fonksiyondaki aynı
    tarihli not). Paylaşılan ilan havuzu HÂLÂ sadece ilçe kümesine göre
    (eskisi gibi) bir kere çekiliyor/cache'leniyor — mahalle filtresi
    her kullanıcı için o paylaşılan havuzun ÜZERİNE, ayrıca uygulanıyor
    (iki kullanıcı aynı ilçeleri seçse bile mahalle alt-filtreleri farklı
    olabilir, bu yüzden mahalle bazında ayrıca cache'lenmiyor — ama bu
    adım saf Python/bellek içi, ekstra Supabase sorgusu gerektirmiyor)."""
    from core.bolge_secici import (
        tum_kullanicilarin_bolgeleri, pazar_ilanlarini_cek, mahalle_ile_filtrele,
    )

    kullanici_bolgeleri = tum_kullanicilarin_bolgeleri(tablo_adi)
    if not kullanici_bolgeleri:
        return {}
    bugun = date.today()
    # Aynı ilçe kümesini seçen birden fazla kullanıcı için tekrar sorgu
    # atmamak üzere (pazar_ilanlarini_cek zaten @st.cache_data(ttl=60) ile
    # cache'li olsa da) burada da basit bir sonuç-cache'i tutuluyor.
    _ilanlar_havuzu = {}
    sonuc = {}
    for kullanici, kayitlar in kullanici_bolgeleri.items():
        ilceler = [k["ilce"] for k in kayitlar]
        ilceler_key = tuple(sorted(set(ilceler)))
        if not ilceler_key:
            continue
        if ilceler_key not in _ilanlar_havuzu:
            _ilanlar_havuzu[ilceler_key] = pazar_ilanlarini_cek(marka, list(ilceler_key))
        ilanlar = _ilanlar_havuzu[ilceler_key]

        ilce_mahalle_haritasi = {k["ilce"]: (k.get("mahalleler") or []) for k in kayitlar}
        ilanlar_kullanici = mahalle_ile_filtrele(ilanlar, ilce_mahalle_haritasi)

        bugunku = [v for v in ilanlar_kullanici if _pazar_ilk_gorulme_gun(v) == bugun]
        if bugunku:
            sonuc[kullanici] = bugunku
    return sonuc


# TEST AŞAMASI (05.10.2026 — Meltem: "linkleri bildirimlerin içine
# yerleştirebilir miyiz"): bildirime dokununca, o kullanıcının O GÜNKÜ yeni
# ilanlarının donmuş bir kopyasını gösteren, oturumsuz açılan bir link
# (Pano_Goruntule) kullanılır. Şimdilik YALNIZCA bu kullanıcılar için;
# diğer herkes eskisi gibi uygulama içi "Bugün" filtreli sayfaya gider.
# Genişletmek için bu küme genişletilir ya da None yapılıp herkese açılır.
# GENİŞLETİLDİ (09.10.2026, Meltem: iPhone'da bildirime dokununca giriş
# ekranı çıkıyor, danışman ilanları linkten görmeli): pilot grup eklendi.
# Herkese açmak için bu kümeyi None yap.
_SNAPSHOT_LINK_KULLANICILARI = {
    "Meltem Bulu",
    "Ahmet Koç", "Sinan Yücesoy", "Ömer Bayraktar",
    "Turgay Özdemir", "Mustafa Balcı", "Erhan Yaşar",
}


def _bildirim_hedef_url(kullanici, ilanlar, pano_basligi, dosya_on_eki, varsayilan_url):
    """Bildirimin dokunma adresini döner. Test kümesindeki kullanıcılar için
    ilan listesinin anlık görüntüsünü üretip yükler ve onun linkini verir;
    herhangi bir hata olursa (veya kullanıcı kümede değilse)
    varsayilan_url'e (uygulama içi sayfa) düşer — bildirim ASLA gitmemezlik
    etmez."""
    if _SNAPSHOT_LINK_KULLANICILARI is not None and kullanici not in _SNAPSHOT_LINK_KULLANICILARI:
        return varsayilan_url
    try:
        from core.pano_export import pazar_ilan_pano_html_olustur, pano_yukle_ve_link_al
        html_buf = pazar_ilan_pano_html_olustur(ilanlar, pano_basligi, baslik_goster=False)
        return pano_yukle_ve_link_al(
            html_buf.getvalue(), dosya_on_eki, app_base_url=KARMA_APP_URL
        )
    except Exception as e:
        print(f"⚠️ Anlık görüntü linki üretilemedi ({kullanici}), varsayılan adres kullanılacak: {e}", flush=True)
        return varsayilan_url


def _snapshot_acik_mi(kullanici):
    """Bu kullanıcı için ilan-linkli (oturumsuz) bildirim açık mı?"""
    return _SNAPSHOT_LINK_KULLANICILARI is None or kullanici in _SNAPSHOT_LINK_KULLANICILARI


def _kayit_pano_url(kayitlar, kayit_tipi, pano_basligi, dosya_on_eki):
    """Talep/portföy kayıtlarının donmuş kopyasını Pano_Goruntule linkine
    çevirir (09.10.2026, Meltem: "aynen çevir"). kayit_tipi: "talep" |
    "portfoy". Müşteri adı/telefonu kopyadan çıkarılır (zaten kartta
    gösterilmiyor; yine de HTML'e hiç girmesin). Hata olursa None döner —
    çağıran varsayılan (uygulama içi) adrese düşer, bildirim gitmemezlik
    etmez."""
    try:
        from core.pano_export import pano_html_olustur, pano_yukle_ve_link_al
        temiz = [
            {k: v for k, v in kayit.items() if k not in ("musteri_adi", "musteri_telefon")}
            for kayit in kayitlar
        ]
        html_buf = pano_html_olustur(temiz, pano_basligi, kayit_tipi=kayit_tipi, baslik_goster=False)
        return pano_yukle_ve_link_al(
            html_buf.getvalue(), dosya_on_eki, app_base_url=KARMA_APP_URL
        )
    except Exception as e:
        print(f"⚠️ Kayıt anlık görüntü linki üretilemedi ({dosya_on_eki}): {e}", flush=True)
        return None


def _mail_kayit_taze_mi(kayit, saat=48):
    """Mail kaydının (kayit_tarihi, RFC 2822) son `saat` saat içinde olup
    olmadığı. AI kredisi bitmesi gibi bir kesintiden sonra birikmiş ESKİ
    raw kayıtlar işlenince "yeni kayıt eklendi" bildirimi yağmasın diye.
    Tarih ayrıştırılamazsa False (bildirim gitmez, kayıt zaten eklenir)."""
    try:
        from email.utils import parsedate_to_datetime
        from datetime import timezone, timedelta
        t = parsedate_to_datetime(str(kayit.get("kayit_tarihi") or ""))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - t) <= timedelta(hours=saat)
    except Exception:
        return False


def mail_kayit_ozet_bildirimleri_gonder(talepler, portfoyler):
    """YENİ (07.10.2026 — Meltem: "kesinlikle özetleme yapalım"): e-postadan
    otomatik ayrıştırılan (core/mail_job.py: run_pending_ai_parse_job) YENİ
    talep/portföy kayıtları için "📍 Uzmanlık Bölgeniz" bildirimi.

    Önceden bu bildirim yalnızca Danışman Panosu'ndaki Kaydet formundan
    girilen kayıtlar için gidiyordu (talep_portfoy_bildirim_gonder); Zeta'nın
    asıl kayıtları ise mail hattından (kaynak_klasor=INBOX) geldiği için
    bildirim hiç tetiklenmiyordu.

    ÖZET: bir çalıştırmada (30 dk'lık mail işi, en fazla ~20 kayıt) aynı
    danışmanın bölgelerine düşen kayıtlar TEK bildirimde toplanır:
    "Balçova: 3 portföy, 1 talep; Buca: 2 portföy". Eşleşme kuralları
    _uzmanlik_bolgesi_eslesenler ile aynı: ilçe adı (casefold) eşleşir,
    bildirim_acik=False olan ilçe sayılmaz, bir kayıt bir danışman için
    yalnızca İLK eşleşen ilçesinde sayılır.

    talepler / portfoyler: kayıt sözlükleri (ilce, ilceler, kayit_tarihi).
    Kayıt tarihi 48 saatten eskiyse (kesinti sonrası birikmiş) sayılmaz.
    Döner: bildirim gönderilen kullanıcı listesi. Hata fırlatmaz."""
    try:
        talepler = [k for k in (talepler or []) if _mail_kayit_taze_mi(k)]
        portfoyler = [k for k in (portfoyler or []) if _mail_kayit_taze_mi(k)]
        if not talepler and not portfoyler:
            return []

        resp = supabase.table("uzmanlik_bolgeleri").select("kullanici, ilce, bildirim_acik").execute()
        kullanici_ilceleri = {}
        for row in (resp.data or []):
            kullanici = (row.get("kullanici") or "").strip()
            ilce = (row.get("ilce") or "").strip()
            if not kullanici or not ilce or row.get("bildirim_acik") is False:
                continue
            kullanici_ilceleri.setdefault(kullanici, []).append(ilce)
        if not kullanici_ilceleri:
            return []

        def _kayit_ilceleri(k):
            ham = list(k.get("ilceler") or []) + [k.get("ilce")]
            return {_ilce_normalize(i) for i in ham if i}

        # {kullanici: {ilce: {"portföy": n, "talep": n}}} + o kullanıcının kayıtları
        sayac = {}
        kayit_listeleri = {}   # {kullanici: {"portföy": [kayıt...], "talep": [kayıt...]}}
        for tur, liste in (("portföy", portfoyler), ("talep", talepler)):
            for k in liste:
                kayit_ilceleri = _kayit_ilceleri(k)
                if not kayit_ilceleri:
                    continue
                for kullanici, ilceler in kullanici_ilceleri.items():
                    eslesen = next((i for i in ilceler if _ilce_normalize(i) in kayit_ilceleri), None)
                    if eslesen:
                        d = sayac.setdefault(kullanici, {}).setdefault(eslesen, {"portföy": 0, "talep": 0})
                        d[tur] += 1
                        kayit_listeleri.setdefault(kullanici, {"portföy": [], "talep": []})[tur].append(k)

        gonderilenler = []
        for kullanici, ilce_sayilari in sayac.items():
            toplam_portfoy = sum(d["portföy"] for d in ilce_sayilari.values())
            parcalar = []
            for ilce in sorted(ilce_sayilari):
                d = ilce_sayilari[ilce]
                alt = [f"{d[t]} {t}" for t in ("portföy", "talep") if d[t]]
                parcalar.append(f"{ilce}: " + ", ".join(alt))
            govde = "Uzmanlık bölgenizde yeni kayıt eklendi — " + "; ".join(parcalar) + "."
            hedef_url = _PORTFOY_URL if toplam_portfoy else _TALEP_URL
            # YENİ (09.10.2026): ilan-linki açık kullanıcıda link, o kullanıcının
            # kayıtlarının oturumsuz kopyasına gider. Hem portföy hem talep
            # varsa ikisi ayrı sayfa olduğundan iki ayrı bildirim gider.
            if _snapshot_acik_mi(kullanici):
                kl = kayit_listeleri.get(kullanici, {})
                turler = [(t, kl.get(t)) for t in ("portföy", "talep") if kl.get(t)]
                if turler:
                    try:
                        for tur, kayitlar in turler:
                            link = _kayit_pano_url(
                                kayitlar, "portfoy" if tur == "portföy" else "talep",
                                f"Yeni {tur}", "portfoy" if tur == "portföy" else "talep",
                            )
                            if len(turler) == 1:
                                metin = govde
                            else:
                                alt = "; ".join(
                                    f"{i}: {d[tur]} {tur}" for i, d in sorted(ilce_sayilari.items()) if d[tur]
                                )
                                metin = f"Uzmanlık bölgenizde yeni {tur} eklendi — {alt}."
                            bildirim_gonder(
                                kullanici, "📍 Uzmanlık Bölgeniz", metin,
                                url=link or (_PORTFOY_URL if tur == "portföy" else _TALEP_URL),
                            )
                        gonderilenler.append(kullanici)
                    except Exception:
                        pass
                    continue
            try:
                bildirim_gonder(kullanici, "📍 Uzmanlık Bölgeniz", govde, url=hedef_url)
                gonderilenler.append(kullanici)
            except Exception:
                pass
        return gonderilenler
    except Exception:
        return []


def pazar_yeni_ilan_bildirimleri_gonder(progress_cb=None):
    """FAZ 2 (27.09.2026 — Meltem onayı): FSBO İlanları ve Startkey
    İlanları için, HER danışmana KENDİ bölgelerinde BUGÜN yayınlanan yeni
    ilan varsa push bildirimi gönderir.

    Meltem'in AskUserQuestion ile onayladığı iki karar:
    1) "Önce sadece yeni ilan bildirimi" — fiyat düşüşü tespiti BU TURDA
       YOK (Faz 3'e bırakıldı, mevcut senkronizasyon akışına eski fiyatı
       saklayan yeni bir adım gerektiriyor).
    2) "Ayrı bildirimler" — FSBO ve Startkey için AYRI push/kayıt gider;
       aynı kullanıcıya ikisi de varsa 2 ayrı bildirim gider, birleşik
       tek bir günlük özet YOK.

    pazar_bildirim_job.py (headless) tarafından, core/izmir_pazar_sync.py
    senkronizasyonu BİTTİKTEN HEMEN SONRA, aynı GitHub Actions job'ında
    çağrılır — izmir_pazar_ilanlar tablosu o günün taze verisiyle dolu
    olsun diye. progress_cb(msg) verilirse ilerleme mesajları oraya
    (print yerine) yazılır. Best-effort: bir kullanıcı/kaynak için hata
    diğerlerini durdurmaz; hiçbir hata dışarı sızmaz.

    Döndürür: {"fsbo_bildirim_sayisi": int, "startkey_bildirim_sayisi": int}
    """

    def _bildir(msg):
        if progress_cb:
            progress_cb(msg)
        else:
            print(msg, flush=True)

    # ── C) FSBO İlanları
    try:
        fsbo_ilanlar = _pazar_bugun_ilanlari("fsbo_bolgeleri", "mulk_sahibi")
    except Exception as e:
        _bildir(f"⚠️ FSBO sayıları hesaplanamadı: {e}")
        fsbo_ilanlar = {}
    fsbo_sayilar = {k: len(v) for k, v in fsbo_ilanlar.items()}
    for kullanici, sayi in fsbo_sayilar.items():
        try:
            bildirim_gonder(
                kullanici,
                "📋 FSBO İlanları",
                f"Bölgelerinde bugün {sayi} yeni FSBO ilanı eklendi.",
                url=_bildirim_hedef_url(
                    kullanici, fsbo_ilanlar[kullanici], "FSBO İlanları", "fsbo", _FSBO_BUGUN_URL
                ),
            )
            _bildir(f"✅ FSBO bildirimi gönderildi: {kullanici} ({sayi} ilan)")
        except Exception as e:
            _bildir(f"⚠️ FSBO bildirimi gönderilemedi ({kullanici}): {e}")

    # ── B) Startkey İlanları
    try:
        startkey_ilanlar = _pazar_bugun_ilanlari("startkey_ilan_bolgeleri", "startkey")
    except Exception as e:
        _bildir(f"⚠️ Startkey sayıları hesaplanamadı: {e}")
        startkey_ilanlar = {}
    startkey_sayilar = {k: len(v) for k, v in startkey_ilanlar.items()}
    for kullanici, sayi in startkey_sayilar.items():
        try:
            bildirim_gonder(
                kullanici,
                "🏢 Startkey İlanları",
                f"Bölgelerinde bugün {sayi} yeni Startkey ilanı eklendi.",
                url=_bildirim_hedef_url(
                    kullanici, startkey_ilanlar[kullanici], "Startkey İlanları", "startkey", _STARTKEY_BUGUN_URL
                ),
            )
            _bildir(f"✅ Startkey bildirimi gönderildi: {kullanici} ({sayi} ilan)")
        except Exception as e:
            _bildir(f"⚠️ Startkey bildirimi gönderilemedi ({kullanici}): {e}")

    _bildir(
        f"🏁 Bitti: {len(fsbo_sayilar)} FSBO bildirimi, "
        f"{len(startkey_sayilar)} Startkey bildirimi gönderildi."
    )
    return {
        "fsbo_bildirim_sayisi": len(fsbo_sayilar),
        "startkey_bildirim_sayisi": len(startkey_sayilar),
    }

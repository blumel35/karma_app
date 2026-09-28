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


def talep_portfoy_bildirim_gonder(kayit_tipi, ilceler, olusturan, islem_tipi=None):
    """Yeni bir talep/portföy kaydı BAŞARIYLA eklendikten sonra çağrılır.

    kayit_tipi: "Talep" | "Portföy"
    ilceler:    o kayıtta seçilen ilçe(ler) — liste, birden fazla olabilir
    olusturan:  kaydı ekleyen danışmanın kullanıcı adı (su_anki_danisman())
                — kendi eklediği kayıt için KENDİSİNE bildirim gitmez.
    islem_tipi: "Satılık" | "Kiralık" (opsiyonel, A mesajına eklenir)

    Hiçbir şey döndürmez, hiçbir hatayı dışarı sızdırmaz (best-effort)."""
    try:
        _gonder_ic(kayit_tipi, ilceler, olusturan, islem_tipi)
    except Exception:
        pass


def _gonder_ic(kayit_tipi, ilceler, olusturan, islem_tipi):
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
            url=panosu_url,
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
        bildirim_gonder(kullanici, "🔔 Zeta Etkileşimleri", govde, url=panosu_url)
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
    bildirim_gonder(olusturan, "✅ Paylaşıldı", onay_govde, url=panosu_url)


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


def _pazar_bugun_sayilari(tablo_adi, marka):
    """tablo_adi'na (fsbo_bolgeleri | startkey_ilan_bolgeleri) kayıtlı HER
    kullanıcı için, KENDİ seçtiği ilçelerde BUGÜN veritabanına İLK KEZ
    yazılan (ilk_gorulme_tarihi = bugün — bkz. _pazar_ilk_gorulme_gun)
    ilan SAYISINI hesaplar. Sonuç {kullanici: sayı} — sayısı 0 olan
    kullanıcılar sonuca dahil edilmez (çağıran taraf zaten sadece
    bildirim gidecekleri dolaşıyor)."""
    from core.bolge_secici import tum_kullanicilarin_bolgeleri, pazar_ilanlarini_cek

    kullanici_ilceleri = tum_kullanicilarin_bolgeleri(tablo_adi)
    if not kullanici_ilceleri:
        return {}
    bugun = date.today()
    # Aynı ilçe kümesini seçen birden fazla kullanıcı için tekrar sorgu
    # atmamak üzere (pazar_ilanlarini_cek zaten @st.cache_data(ttl=60) ile
    # cache'li olsa da) burada da basit bir sonuç-cache'i tutuluyor.
    _hesaplanan = {}
    sonuc = {}
    for kullanici, ilceler in kullanici_ilceleri.items():
        ilceler_key = tuple(sorted(set(ilceler)))
        if not ilceler_key:
            continue
        if ilceler_key not in _hesaplanan:
            ilanlar = pazar_ilanlarini_cek(marka, list(ilceler_key))
            _hesaplanan[ilceler_key] = len(
                [v for v in ilanlar if _pazar_ilk_gorulme_gun(v) == bugun]
            )
        sayi = _hesaplanan[ilceler_key]
        if sayi:
            sonuc[kullanici] = sayi
    return sonuc


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
        fsbo_sayilar = _pazar_bugun_sayilari("fsbo_bolgeleri", "mulk_sahibi")
    except Exception as e:
        _bildir(f"⚠️ FSBO sayıları hesaplanamadı: {e}")
        fsbo_sayilar = {}
    for kullanici, sayi in fsbo_sayilar.items():
        try:
            bildirim_gonder(
                kullanici,
                "📋 FSBO İlanları",
                f"Bölgelerinde bugün {sayi} yeni FSBO ilanı yayınlandı.",
                url=_FSBO_BUGUN_URL,
            )
            _bildir(f"✅ FSBO bildirimi gönderildi: {kullanici} ({sayi} ilan)")
        except Exception as e:
            _bildir(f"⚠️ FSBO bildirimi gönderilemedi ({kullanici}): {e}")

    # ── B) Startkey İlanları
    try:
        startkey_sayilar = _pazar_bugun_sayilari("startkey_ilan_bolgeleri", "startkey")
    except Exception as e:
        _bildir(f"⚠️ Startkey sayıları hesaplanamadı: {e}")
        startkey_sayilar = {}
    for kullanici, sayi in startkey_sayilar.items():
        try:
            bildirim_gonder(
                kullanici,
                "🏢 Startkey İlanları",
                f"Bölgelerinde bugün {sayi} yeni Startkey ilanı yayınlandı.",
                url=_STARTKEY_BUGUN_URL,
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

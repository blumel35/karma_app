"""
core/danisman_ortak.py

Danışman Panosu ekranları (Danisman_Secim, Danisman_Talep, Danisman_Portfoy,
Danisman_Favoriler, Danisman_Kayitlarim, Danisman_Paylasimlar) arasında
paylaşılan tüm mantık burada topluyor — kod tekrarını önlemek için.

Mimari (2026-08 revizyonu, 2. güncelleme):
- Danisman_Secim.py: giriş sonrası ANA ekran. İki büyük kart (Talep/Portföy,
  sayı + tıklanabilir "+N yeni" rozeti — TÜM KAYNAKLAR: Zeta + Startkey/mail
  birlikte), Favori Listem butonu, "+ Ekle" butonu (ortak dialog), "Son 24
  saat" aktivite özeti (yine TÜM KAYNAKLAR). Sağ üstte hamburger menü:
  Kendi Kayıtlarım, Zeta Paylaşımları, Çıkış Yap.
- Danisman_Talep.py / Danisman_Portfoy.py: sadece kart listesi + A-Z
  navigasyon + filtreler. HER ZAMAN TÜM HAVUZU gösterir (Zeta + Startkey
  birlikte) — "İlan Kaynağı" filtresi YOK, çünkü Zeta'ya özel görünüm
  zaten ayrı bir sayfada (Danisman_Paylasimlar.py). "Ekle" ve
  "Kendi Kayıtlarım" burada da YOK — ana ekrana / hamburger menüye taşındı.
- Danisman_Paylasimlar.py (Zeta Paylaşımları): TEK istisna — burası hâlâ
  yalnızca Zeta kaynaklı kayıtları gösterir (ölçeklenebilirlik + "ekip
  arkadaşlarım ne yaptı" sorusuna özel cevap).
- "+N yeni" rozetine tıklanınca ilgili panoya SADECE SON 24 SAATTEKİ
  kayıtlar filtrelenmiş olarak açılır (st.session_state["dp_sadece_yeni"]
  ile taşınır, query param değil — MPA sayfa geçişlerinde daha güvenilir).
"""

import uuid
import time
import json
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import streamlit as st

from core.supabase_client import get_client
from core.pano_export import _ilce_normalize, _islem_tipi_norm, _TR_BUYUK_HARF

supabase = get_client()

ZETA_DEGERLERI = {"zeta", "zeta1", "zeta2", "ofis"}

# YENİ (12.08.2026 — İlanlarım / Kayıtlarım ayrımı): ZETA_DEGERLERI şu an
# İKİ FARKLI ŞEYİ aynı torbada tutuyor:
#   - "zeta" / "ofis"  → GD'lerin Danışman Panosu'ndan ELLE girdiği,
#     ilan sitelerinde YAYINLANMAYAN ofis-içi paylaşımlar (talep/portföy)
#   - "zeta1" / "zeta2" → revy_sync.py'nin Revy'den senkronize ettiği,
#     portallarda (sahibinden vb.) FİİLEN YAYINLANAN resmi ilanlar
# Bu ikisi KAVRAMSAL OLARAK AYRI — biri "ekip içi duyuru", diğeri "canlı
# ilan envanteri". revy_sync henüz üretime entegre değil (bu yüzden
# bugün pratik bir etkisi yok) ama entegre edildiğinde ZETA_DEGERLERI'nı
# kullanan yerler (Zeta Paylaşımları, Portföy Panosu'nun genel Zeta/
# Startkey filtresi) BİLEREK değiştirilmedi — sadece "Kendi Kayıtlarım"
# ekranındaki YENİ "İlanlarım" bölümü bu ayrı sabiti kullanıyor.
ILAN_PORTAL_DEGERLERI = {"zeta1", "zeta2"}

IZMIR_ILCELERI = [
    "Aliağa", "Balçova", "Bayındır", "Bayraklı", "Bergama", "Beydağ",
    "Bornova", "Buca", "Çeşme", "Çiğli", "Dikili", "Foça", "Gaziemir",
    "Güzelbahçe", "Karabağlar", "Karaburun", "Karşıyaka", "Kemalpaşa",
    "Kınık", "Kiraz", "Konak", "Menderes", "Menemen", "Narlıdere",
    "Ödemiş", "Seferihisar", "Selçuk", "Tire", "Torbalı", "Urla",
]


# ── OTURUM YARDIMCILARI ───────────────────────────────────────────────

def su_anki_danisman():
    return (
        st.session_state.get("user_name")
        or st.session_state.get("kullanici", {}).get("email", "")
    )


# ── TÜRKÇE METİN YARDIMCILARI ─────────────────────────────────────────

def _tr_lower(s):
    """Python'un .lower()'ı Türkçe İ/I'yı yanlış küçültüyor — önce
    Türkçe karşılıklarına çevirip sonra standart .lower() uygulanır."""
    return (s or "").replace("İ", "i").replace("I", "ı").lower()


def baslik_normalize(metin):
    """Virgülle ayrılmış serbest metin parçalarının ilk harfini
    Türkçe'ye uygun büyütür (örn. 'zeytinalanı, kalabak' → 'Zeytinalanı, Kalabak')."""
    if not metin:
        return metin
    parcalar = [p.strip() for p in metin.split(",")]
    return ", ".join(_ilce_normalize(p) for p in parcalar if p)


def _ozet_olustur(ilceler, bolge, oda, islem_tipi, mulk_tipi, kayit_tipi):
    """AI'a hiç gerek kalmadan, seçilen yapılandırılmış alanlardan
    şablonla özet cümlesi üretir — ücretsiz, anında, halüsinasyon riski yok."""
    if not ilceler:
        ilce_str = ""
    elif len(ilceler) == 1:
        ilce_str = ilceler[0]
    else:
        ilce_str = ", ".join(ilceler[:-1]) + " ve " + ilceler[-1]
    if bolge:
        ilce_str = f"{ilce_str} ({bolge})" if ilce_str else bolge

    oda_str = f"{oda} " if oda else ""
    islem_kucuk = _tr_lower(islem_tipi)
    mulk_kucuk = _tr_lower(mulk_tipi)
    eylem = "arayışı" if kayit_tipi == "talep" else "ilanı"

    parcalar = [p for p in [ilce_str, f"{oda_str}{islem_kucuk} {mulk_kucuk} {eylem}"] if p.strip()]
    return " bölgesinde ".join(parcalar) if ilce_str else " ".join(parcalar)


# ── VERİ ÇEKME (SUPABASE) ─────────────────────────────────────────────

def _son_60_gun_esigi():
    return datetime.now(timezone.utc) - timedelta(days=60)


def _tarihte_mi(kayit_tarihi_str, esik):
    """kayit_tarihi Supabase'de metin (RFC822 mail tarihi) olarak
    tutuluyor — sunucu tarafında doğru filtrelenemediği için tüm
    kayıtlar çekilip burada, Python'da gerçek tarih olarak karşılaştırılır."""
    try:
        d = parsedate_to_datetime(kayit_tarihi_str or "")
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d >= esik
    except Exception:
        return False


def kayit_tarihi_dt(kayit_tarihi_str):
    """_tarihte_mi ile aynı ayrıştırma, ama karşılaştırma değil datetime döner
    (aktivite akışını tarihe göre sıralamak için)."""
    try:
        d = parsedate_to_datetime(kayit_tarihi_str or "")
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return None


def _tum_sayfalari_cek(tablo, secim, filtreler=None):
    """PostgREST tek sorguda en fazla 1000 satır döndürür — sayfa sayfa
    (range ile) tüm kayıtlara ulaşılır. (core/mail_job.py'deki desenle aynı.)"""
    tum_kayitlar = []
    baslangic = 0
    sayfa_boyutu = 1000
    while True:
        sorgu = supabase.table(tablo).select(secim)
        for alan, deger in (filtreler or {}).items():
            sorgu = sorgu.eq(alan, deger)
        resp = (
            sorgu.order("id", desc=True)
            .range(baslangic, baslangic + sayfa_boyutu - 1)
            .execute()
        )
        satirlar = resp.data or []
        tum_kayitlar.extend(satirlar)
        if len(satirlar) < sayfa_boyutu:
            break
        baslangic += sayfa_boyutu
    return tum_kayitlar


@st.cache_data(ttl=60, show_spinner="Talepler yükleniyor...")
def talepleri_cek():
    esik = _son_60_gun_esigi()
    tumu = _tum_sayfalari_cek(
        "alici_talepleri", "*",
        filtreler={"kategori": "alici_talebi", "parse_status": "parsed"},
    )
    return [v for v in tumu if _tarihte_mi(v.get("kayit_tarihi"), esik)]


@st.cache_data(ttl=60, show_spinner="Portföyler yükleniyor...")
def portfoyleri_cek():
    esik = _son_60_gun_esigi()
    tumu = _tum_sayfalari_cek("portfoyler", "*")
    return [v for v in tumu if _tarihte_mi(v.get("kayit_tarihi"), esik)]


# ── FİLTRELER ──────────────────────────────────────────────────────────

def kaynak_filtrele(kayitlar, secim):
    if secim == "Tümü":
        return kayitlar
    if secim == "Zeta":
        return [v for v in kayitlar if str(v.get("kaynak") or "").strip().lower() in ZETA_DEGERLERI]
    return [v for v in kayitlar if str(v.get("kaynak") or "").strip().lower() not in ZETA_DEGERLERI]


def islem_tipi_filtrele(kayitlar, secim):
    if secim == "Tümü":
        return kayitlar
    return [v for v in kayitlar if _islem_tipi_norm(v) == secim]


def son_24_saat_filtrele(kayitlar):
    esik = datetime.now(timezone.utc) - timedelta(hours=24)
    return [v for v in kayitlar if _tarihte_mi(v.get("kayit_tarihi"), esik)]


def son_N_gun_filtrele(kayitlar, gun):
    esik = datetime.now(timezone.utc) - timedelta(days=gun)
    return [v for v in kayitlar if _tarihte_mi(v.get("kayit_tarihi"), esik)]


# ── YENİ KAYIT EKLEME ──────────────────────────────────────────────────

def _yeni_talep_ekle(ilceler, bolge, mulk_tipi, oda, butce, islem_tipi, ek_not, danisman_adi,
                      iliski_tipi="kendi", musteri_adi="", musteri_telefon=""):
    ozet = _ozet_olustur(ilceler, bolge, oda, islem_tipi, mulk_tipi, "talep")
    detay = ek_not.strip() if ek_not else ozet
    kayit = {
        "kayit_tarihi": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000"),
        "talep_eden_danisan": danisman_adi,
        "bolge_mahalle": bolge,
        "oda_sayisi_m2": oda,
        "max_butce": butce,
        "ozel_kriterler": detay,
        "iletisim_not": "",
        "mail_konusu": f"[Danışman Panosu] {ozet[:80]}",
        "mail_icerigi": detay,
        "message_id": f"<danisman-panel-{uuid.uuid4().hex}@karma-app>",
        "kaynak_klasor": "danisman_panel",
        "kategori": "alici_talebi",
        "ozet": ozet,
        "islem_tipi": islem_tipi,
        "mulk_tipi": mulk_tipi,
        "il": "İzmir",
        "ilce": ilceler[0] if ilceler else "",
        "ilceler": ilceler,
        "kaynak": "zeta",
        "parse_status": "parsed",
        "ai_processed_at": datetime.now(timezone.utc).isoformat(),
        # YENİ (13.08.2026): iliski_tipi paylaşılan kartta "Köprü" notu
        # olarak görünür (pano_export.py). musteri_adi/musteri_telefon
        # ASLA paylaşılan kartta gösterilmiyor — sadece Kendi
        # Kayıtlarım'da, kaydı girenin kendisine.
        "iliski_tipi": iliski_tipi,
        "musteri_adi": musteri_adi or None,
        "musteri_telefon": musteri_telefon or None,
    }
    supabase.table("alici_talepleri").insert(kayit).execute()
    # YENİ (13.08.2026): Müşteri adı girildiyse Müşterilerim'e otomatik
    # senkronize edilir — talep = "Alıcı" (bu kişi bir mülk arıyor).
    if musteri_adi.strip():
        _musteri_senkronize(danisman_adi, musteri_adi, musteri_telefon, "Alıcı")


def _yeni_portfoy_ekle(ilceler, bolge, mulk_tipi, oda, fiyat, islem_tipi, ek_not, danisman_adi,
                        iliski_tipi="kendi", musteri_adi="", musteri_telefon=""):
    ozet = _ozet_olustur(ilceler, bolge, oda, islem_tipi, mulk_tipi, "portfoy")
    detay = ek_not.strip() if ek_not else ozet
    kayit = {
        "kayit_tarihi": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000"),
        "talep_eden_danisan": danisman_adi,
        "bolge_mahalle": bolge,
        "oda_sayisi_m2": oda,
        "fiyat": fiyat,
        "ozet": ozet,
        "ozellikler": detay,
        "islem_tipi": islem_tipi,
        "mulk_tipi": mulk_tipi,
        "ilce": ilceler[0] if ilceler else "",
        "ilceler": ilceler,
        "kaynak": "zeta",
        "message_id": f"<danisman-panel-{uuid.uuid4().hex}@karma-app>",
        "iliski_tipi": iliski_tipi,
        "musteri_adi": musteri_adi or None,
        "musteri_telefon": musteri_telefon or None,
    }
    supabase.table("portfoyler").insert(kayit).execute()
    # YENİ (13.08.2026): Müşteri adı girildiyse Müşterilerim'e otomatik
    # senkronize edilir — portföy = "Satıcı" (bu kişinin mülkü satılıyor/
    # kiralanıyor).
    if musteri_adi.strip():
        _musteri_senkronize(danisman_adi, musteri_adi, musteri_telefon, "Satıcı")


def kayit_sil(tablo, kayit_id):
    supabase.table(tablo).delete().eq("id", kayit_id).execute()


def kayit_notunu_guncelle(tablo, kayit_id, alan, yeni_deger):
    """Kendi Kayıtlarım ekranından bir kaydın not alanını günceller —
    talep için 'ozel_kriterler', portföy için 'ozellikler' (aynı alanlar
    ilk oluşturmada _yeni_talep_ekle/_yeni_portfoy_ekle'nin 'Ek Not'
    girdisini yazdığı alanlar — burada da AYNI alan kullanılıyor ki
    oluşturma sırasında girilen not ile sonradan düzenlenen not
    ÇAKIŞMASIN, tek bir kaynak olsun).
    GÜVENLİK SINIRI: Bu fonksiyon kendi başına bir yetki kontrolü yapmıyor
    — çağıran ekran (Danisman_Kayitlarim.py) zaten yalnızca kaynak=Zeta
    VE talep_eden_danisan=giriş yapan kullanıcı olan kayıtları listeleyip
    bu fonksiyonu çağırıyor, dolayısıyla kullanıcı yalnızca kendi
    kayıtlarının notunu değiştirebilir."""
    supabase.table(tablo).update({alan: yeni_deger}).eq("id", kayit_id).execute()


# ── MÜŞTERİLERİM (kişi defteri) — YENİ (13.08.2026) ─────────────────────
# Talep/Portföy tablolarından TAMAMEN BAĞIMSIZ bir tablo (musteriler) —
# bilinçli tasarım: "ilanlar silinse de müşteriler kayıtlı kalsın"
# isteği, aralarında hiçbir foreign key/cascade delete olmamasıyla
# sağlanıyor. Şimdilik KİŞİSEL (danisman alanına göre filtrelenir,
# ofis geneli paylaşılmıyor) — ileride ihtiyaç olursa genişletilebilir.

@st.cache_data(ttl=30, show_spinner=False)
def musterileri_cek(danisman_adi):
    resp = (
        supabase.table("danisman_kisiler")
        .select("*")
        .eq("danisman", danisman_adi)
        .order("guncelleme_tarihi", desc=True)
        .execute()
    )
    return resp.data or []


def _isim_normalize(ad):
    """'ender böncü' -> 'Ender Böncü'. _ilce_normalize'dan farkı: birden
    fazla kelimeyi (ad+soyad) AYRI AYRI büyütür, tek kelimeyi değil.
    Python'un .title()'ı Türkçe İ/ı'yı yanlış çevirdiği için (örn.
    'ışık'.title() -> 'Işık' değil 'IŞık' gibi hatalar verir) elle,
    _TR_BUYUK_HARF eşlemesiyle yapılıyor (13.08.2026)."""
    ad = (ad or "").strip()
    if not ad:
        return ad
    kelimeler = ad.split(" ")
    duzeltilmis = []
    for k in kelimeler:
        if not k:
            continue
        ilk = k[0]
        ilk_buyuk = _TR_BUYUK_HARF.get(ilk, ilk.upper())
        geri_kalan = k[1:].lower().replace("i̇", "i")
        duzeltilmis.append(ilk_buyuk + geri_kalan)
    return " ".join(duzeltilmis)


def _tip_listele(tip_degeri):
    """Rehberim'deki 'tip' alanını HER ZAMAN temiz bir liste olarak
    döner — DÜZELTME (13.08.2026): migration çalıştırılmadan önce (veya
    eski bir kayıtta) tip alanı hâlâ DÜZ METİN olabilir ('İş Ortağı').
    Bunu doğrudan bir Python listesi gibi kullanmak (for t in tip)
    STRING'i TEK TEK KARAKTERLERİNE ayırır (Python'da string de
    iterable) — canlıda tam olarak bu hata görüldü.
    DÜZELTME (13.08.2026 — 2. tur): 'tip' sütunu Supabase'de HÂLÂ TEXT
    tipindeyse (migration çalışmadıysa/etkisi görülmediyse), Python
    listesi gönderildiğinde postgrest JSON'a çevirip metin olarak
    kaydediyor — geri okunduğunda "[\"İş Ortağı\"]" gibi köşeli
    parantez+tırnaklı DÜZ METİN olarak geliyor. Bu da artık ayrıca
    yakalanıp gerçek listeye çevriliyor (json.loads denemesi ile)."""
    if not tip_degeri:
        return []
    if isinstance(tip_degeri, list):
        return [t for t in tip_degeri if t]
    if isinstance(tip_degeri, str):
        metin = tip_degeri.strip()
        if metin.startswith("[") and metin.endswith("]"):
            try:
                cozulmus = json.loads(metin)
                if isinstance(cozulmus, list):
                    return [t for t in cozulmus if t]
            except (ValueError, TypeError):
                pass
        return [metin] if metin else []
    return []


def _telefon_normalize(t):
    """Karşılaştırma için telefon numarasını sadece rakamlara indirger,
    son 10 haneyi alır — '0542 288 16 20', '+90 542 288 16 20',
    '5422881620' gibi farklı yazımların AYNI kişi olarak eşleşmesi
    için (13.08.2026 düzeltmesi — öncesinde birebir string eşleşmesi
    arandığı için format farkı mükerrer kayıt yaratıyordu)."""
    rakamlar = "".join(ch for ch in (t or "") if ch.isdigit())
    return rakamlar[-10:] if len(rakamlar) >= 10 else rakamlar


def _musteri_senkronize(danisman_adi, ad, telefon, tip):
    """Bir talep/portföy eklenirken müşteri adı girilmişse, bu kişiyi
    Müşterilerim'e de otomatik ekler/günceller — AYRI bir işlem yapmana
    gerek kalmasın diye.

    DÜZELTME (13.08.2026 — 2. tur, iki gerçek boşluk kapatıldı):
    1) Eşleştirme artık NORMALİZE EDİLMİŞ telefona göre (format farkı
       artık mükerrer kayıt yaratmıyor) VE isim büyük/küçük harf +
       boşluk farkına duyarsız şekilde yapılıyor — ikisi de fallback
       olarak denenir (önce telefon, sonra isim), TEK bir kayıt
       bulunana kadar.
    2) tip artık TEK DEĞER değil, DİZİ — aynı kişi hem 'Alıcı' hem
       'Satıcı' olabilir. Var olan kayıt bulunursa yeni tip, mevcut
       diziye EKLENİR (zaten varsa tekrar eklenmez) — üzerine
       YAZILMAZ, önceki rolleri kaybetmez."""
    ad = _isim_normalize(ad)
    if not ad:
        return
    telefon = (telefon or "").strip() or None
    telefon_norm = _telefon_normalize(telefon)

    # Kişisel bir adres defteri için makul boyutta bir liste — tek
    # sorguda çekip Python'da normalize ederek karşılaştırmak, Supabase
    # tarafında format-duyarsız bir SQL sorgusu yazmaktan daha basit ve
    # güvenilir.
    adaylar = (
        supabase.table("danisman_kisiler")
        .select("id, ad, telefon, tip")
        .eq("danisman", danisman_adi)
        .execute()
        .data or []
    )

    eslesen = None
    if telefon_norm:
        for a in adaylar:
            if _telefon_normalize(a.get("telefon")) == telefon_norm:
                eslesen = a
                break
    if not eslesen:
        ad_norm = ad.lower()
        for a in adaylar:
            if (a.get("ad") or "").strip().lower() == ad_norm:
                eslesen = a
                break

    if eslesen:
        guncelleme = {"guncelleme_tarihi": datetime.now(timezone.utc).isoformat()}
        if telefon and not eslesen.get("telefon"):
            guncelleme["telefon"] = telefon
        # DÜZELTME: _tip_listele() ile savunmacı — eslesen kaydın 'tip'i
        # migration çalıştırılmadan önce yazılmış, hâlâ düz metin olabilir.
        mevcut_tipler = _tip_listele(eslesen.get("tip"))
        if tip not in mevcut_tipler:
            guncelleme["tip"] = mevcut_tipler + [tip]
        supabase.table("danisman_kisiler").update(guncelleme).eq("id", eslesen["id"]).execute()
    else:
        supabase.table("danisman_kisiler").insert({
            "danisman": danisman_adi,
            "ad": ad,
            "telefon": telefon,
            "tip": [tip],
            "kaynak": "otomatik",
        }).execute()
    musterileri_cek.clear()


def musteri_ekle(danisman_adi, ad, telefon, tip, notlar, uzmanlik="", bolgeler=None):
    """Müşterilerim sayfasından elle yeni kişi ekleme (iş ortağı,
    tedarikçi vb. — bir talep/portföye bağlı olması ŞART değil).
    tip artık bir LİSTE (13.08.2026) — bir kişi birden fazla rol
    taşıyabilir (örn. hem Alıcı hem Satıcı).
    uzmanlik/bolgeler (13.08.2026, 2. tur): İş Ortağı/Tedarikçi gibi
    tiplerde 'kim ne iş yapıyor, nerede çalışıyor' bilgisini notlara
    gömmeden, satırda görünür/ileride filtrelenebilir tutmak için —
    ikisi de opsiyonel."""
    supabase.table("danisman_kisiler").insert({
        "danisman": danisman_adi,
        "ad": _isim_normalize(ad),
        "telefon": (telefon or "").strip() or None,
        "tip": tip if isinstance(tip, list) else [tip],
        "notlar": (notlar or "").strip() or None,
        "uzmanlik": _isim_normalize(uzmanlik) or None,
        "bolgeler": bolgeler or [],
        "kaynak": "manuel",
    }).execute()
    musterileri_cek.clear()


def musteri_guncelle(musteri_id, alanlar):
    alanlar = dict(alanlar)
    # DÜZELTME (13.08.2026, 4. tur): "uzmanlık" alanı da isimler gibi
    # Türkçe-uyumlu büyük harfle normalize ediliyor artık ("mali müşavir"
    # -> "Mali Müşavir") — hangi ekrandan/hangi çağrıdan geldiğine
    # bakılmaksızın burada, merkezi olarak yapılıyor.
    if alanlar.get("uzmanlik"):
        alanlar["uzmanlik"] = _isim_normalize(alanlar["uzmanlik"])
    alanlar["guncelleme_tarihi"] = datetime.now(timezone.utc).isoformat()
    supabase.table("danisman_kisiler").update(alanlar).eq("id", musteri_id).execute()
    musterileri_cek.clear()


def musteri_sil(musteri_id):
    supabase.table("danisman_kisiler").delete().eq("id", musteri_id).execute()
    musterileri_cek.clear()


@st.dialog("Yeni Talep / Portföy Ekle")
def ekle_dialog(varsayilan_tip="Talep"):
    """Ana ekrandaki tek '+ Ekle' butonundan açılan ortak dialog.
    Talep Panosu / Portföy Panosu ekranlarının HİÇBİRİNDE ayrıca
    tekrarlanmaz — kayıt ekleme mantığı yalnızca burada yaşar."""
    kayit_tipi_secim = st.radio(
        "Ne eklemek istiyorsun?", ["Talep", "Portföy"],
        horizontal=True, key="ds_kayit_tipi",
        index=0 if varsayilan_tip == "Talep" else 1,
    )
    with st.form("ds_yeni_kayit_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            f_islem = st.selectbox("İşlem Tipi", ["Satılık", "Kiralık"], key="ds_islem")
            f_ilceler = st.multiselect("İlçe(ler)", IZMIR_ILCELERI, key="ds_ilceler")
            f_bolge = st.text_input(
                "Bölge / Mahalle (opsiyonel)", placeholder="örn. Alaçatı, Kalabak",
                key="ds_bolge",
            )
            f_mulk = st.selectbox(
                "Mülk Tipi", ["Konut", "Arsa", "İşyeri/Ticari", "Villa", "Diğer"],
                key="ds_mulk",
            )
        with col2:
            f_oda = st.text_input("Oda Sayısı / m²", placeholder="örn. 2+1", key="ds_oda")
            if kayit_tipi_secim == "Talep":
                f_deger = st.text_input("Max Bütçe", placeholder="örn. 5.000.000 TL", key="ds_butce")
            else:
                f_deger = st.text_input("Fiyat", placeholder="örn. 4.500.000 TL", key="ds_fiyat")
        f_ek_not = st.text_area(
            "Ek Not (opsiyonel)",
            placeholder="Otomatik özete ek olarak eklemek istediğin bir detay varsa buraya yaz.",
            key="ds_ozet", height=68,
        )

        # YENİ (13.08.2026): İlan Kaynağı — bu talep/portföy senin kendi
        # müşterinden mi (varsayılan), yoksa başka bir kaynaktan sana
        # ulaşıp havuza AKTARDIĞIN ("köprü" olduğun) bir talep/portföy
        # mü? Köprü seçilirse, havuzdaki kartta bir not olarak görünür
        # ("Köprü") — kimin doğrudan muhatap olduğu konusunda şeffaflık
        # için, kişisel bilgi paylaşmadan.
        f_iliski_tipi = st.radio(
            "İlan Kaynağı (opsiyonel)", ["Kendi Talebim", "Köprü"],
            horizontal=True, key="ds_iliski_tipi",
            help="Köprü: bu talep/portföy senin doğrudan müşterin değil, "
                 "başka bir kaynaktan sana ulaşıp havuza aktardığın bir kayıt.",
        )

        # YENİ (13.08.2026): Müşteri Adı/Telefon — TAMAMEN OPSİYONEL ve
        # GİZLİ. Bu iki alan yalnızca "Kendi Kayıtlarım"da, kaydı girenin
        # kendisine görünür — pano_export.py'deki paylaşılan kart
        # şablonuna KASITLI OLARAK hiç eklenmedi, havuzda (Talep/Portföy
        # Panosu, Zeta Paylaşımları) asla görünmez.
        with st.expander("Müşteri Bilgisi (opsiyonel, sadece sende görünür)", expanded=False):
            st.caption("Bu bilgi sadece Kendi Kayıtlarım'da sana görünür — havuzda hiçbir zaman paylaşılmaz.")
            mc1, mc2 = st.columns(2)
            with mc1:
                f_musteri_adi = st.text_input("Müşteri Adı (opsiyonel)", key="ds_musteri_adi")
            with mc2:
                f_musteri_telefon = st.text_input("Müşteri Telefonu (opsiyonel)", key="ds_musteri_tel")

        gonder = st.form_submit_button("Kaydet", type="primary", use_container_width=True)

        if gonder:
            if not f_ilceler:
                st.error("En az bir ilçe seçimi zorunlu.")
            else:
                f_bolge = baslik_normalize(f_bolge)
                danisman_adi = su_anki_danisman()
                iliski_deger = "kopru" if f_iliski_tipi == "Köprü" else "kendi"
                try:
                    if kayit_tipi_secim == "Talep":
                        _yeni_talep_ekle(
                            f_ilceler, f_bolge, f_mulk, f_oda, f_deger, f_islem, f_ek_not, danisman_adi,
                            iliski_tipi=iliski_deger, musteri_adi=f_musteri_adi.strip(),
                            musteri_telefon=f_musteri_telefon.strip(),
                        )
                    else:
                        _yeni_portfoy_ekle(
                            f_ilceler, f_bolge, f_mulk, f_oda, f_deger, f_islem, f_ek_not, danisman_adi,
                            iliski_tipi=iliski_deger, musteri_adi=f_musteri_adi.strip(),
                            musteri_telefon=f_musteri_telefon.strip(),
                        )
                    st.success("✅ Kaydedildi! Talep/Portföy Merkezi'nde ve panoda görünecek.")
                    talepleri_cek.clear()
                    portfoyleri_cek.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Kaydedilemedi: {e}")


# ── FAVORİLER ──────────────────────────────────────────────────────────

@st.cache_data(ttl=30, show_spinner=False)
def favorileri_cek(kullanici):
    resp = supabase.table("favoriler").select("*").eq("kullanici", kullanici).execute()
    return resp.data or []


def favori_ekle(kaynak_tablo, kayit_id):
    supabase.table("favoriler").upsert(
        {"kullanici": su_anki_danisman(), "kaynak_tablo": kaynak_tablo, "kayit_id": kayit_id},
        on_conflict="kullanici,kaynak_tablo,kayit_id",
    ).execute()


def favori_cikar(favori_id):
    supabase.table("favoriler").delete().eq("id", favori_id).execute()


# ── UZMANLIK BÖLGELERİ ("Favori Listem"in COĞRAFİ kardeşi) ──────────────
# Bilinçli olarak Talep/Portföy Panosu'nun içine bir filtre katmanı olarak
# EKLENMEDİ — o sayfalarda zaten birden fazla filtre katmanı birbirini
# eziyordu (08.08.2026 regresyon turu). Bunun yerine ayrı bir sayfa
# (Danisman_UzmanlikBolgeleri.py), Favoriler ile birebir aynı iskelet:
# sekmeli (Talepler/Portföyler), kendi filtre toolbar'ı, kart görünümü.
#
# Favoriler'den TEK mimari fark: "favori" durumu kayıt kartındaki ⭐'a
# tıklanarak (tekil ekle/çıkar) belirleniyordu — burada "favorilenen" şey
# bir kayıt değil bir COĞRAFİ ALAN, bu yüzden ayrı bir seçim arayüzü var
# (en fazla 5 ilçe) ve "kaydet" ile TÜM seçim tek seferde değiştiriliyor
# (düşük sıklıkla değişen bir ayar olduğu için tekil ekle/çıkar yerine
# bu daha basit).

def uzmanlik_bolgelerini_cek(kullanici):
    """NOT: favorileri_cek()'in aksine cache'siz — bu sayfa kendi
    içinde kaydet sonrası zaten st.rerun() çağırıyor, ayrıca ttl bazlı
    bir cache'e ihtiyaç yok, her zaman taze veri okunuyor."""
    resp = supabase.table("uzmanlik_bolgeleri").select("*").eq("kullanici", kullanici).execute()
    return resp.data or []


def uzmanlik_bolgelerini_kaydet(ilceler):
    """Kullanıcının uzmanlık bölgelerini TAMAMEN değiştirir (mevcut
    kayıtları silip yeni seçimi ekler). En fazla 5 ilçe — UI tarafında
    (st.multiselect max_selections=5) zaten zorlanıyor, burada ikinci
    bir güvenlik önlemi olarak tekrar kesiliyor.

    DÜZELTME (12.08.2026): Önceden insert()'in dönüş değeri hiç kontrol
    edilmiyordu. Supabase/PostgREST, tablonun Row Level Security (RLS)
    politikası INSERT'i reddettiğinde çoğu zaman Python tarafında bir
    İSTİSNA FIRLATMAZ — 200 OK + boş bir data listesiyle sessizce döner.
    Sonuç: çağıran ekran "başarılı" mesajı gösterir ama satır hiç
    eklenmemiş olur (canlıda gözlemlenen belirti tam olarak buydu).
    Artık dönen satır sayısı gönderilenle eşleşmezse AÇIKÇA hata
    fırlatılıyor — çağıran ekran bunu yakalayıp göstermeli."""
    kullanici = su_anki_danisman()
    ilceler = list(ilceler)[:5]
    if not kullanici:
        raise ValueError(
            "Kaydedilemedi: giriş yapan kullanıcı tespit edilemedi "
            "(su_anki_danisman() boş döndü)."
        )
    supabase.table("uzmanlik_bolgeleri").delete().eq("kullanici", kullanici).execute()
    if ilceler:
        insert_resp = supabase.table("uzmanlik_bolgeleri").insert(
            [{"kullanici": kullanici, "ilce": ilce} for ilce in ilceler]
        ).execute()
        donen_sayi = len(insert_resp.data or [])
        if donen_sayi != len(ilceler):
            raise RuntimeError(
                f"{len(ilceler)} ilçe gönderildi ama Supabase yalnızca "
                f"{donen_sayi} satır döndürdü. Bu genellikle "
                f"'uzmanlik_bolgeleri' tablosunun Row Level Security (RLS) "
                f"politikasının INSERT işlemini sessizce reddettiği anlamına "
                f"gelir — Supabase panelinde Authentication > Policies "
                f"kısmından bu tablonun INSERT politikasını kontrol et "
                f"(kullanılan API key'in — anon/service — bu tabloya yazma "
                f"izni olduğundan emin ol)."
            )


def _kayit_ilcesi_eslesiyor_mu(kayit, secili_ilceler_norm):
    """Bir kaydın ilceler listesindeki (yoksa tekil ilce alanındaki) HER
    HANGİ BİR ilçesi, seçili uzmanlık bölgeleriyle eşleşiyor mu?
    _ilce_normalize ile karşılaştırılıyor — core/pano_export.py'de zaten
    kullanılan aynı normalizasyon (Türkçe karakter/büyük-küçük harf
    farklarına dayanıklı), tahmin edilmiş yeni bir mantık değil."""
    kayit_ilceleri = kayit.get("ilceler") or ([kayit.get("ilce")] if kayit.get("ilce") else [])
    return any(_ilce_normalize(i) in secili_ilceler_norm for i in kayit_ilceleri if i)


def uzmanlik_bolgesi_filtrele(kayitlar, secili_ilceler):
    if not secili_ilceler:
        return []
    secili_norm = {_ilce_normalize(i) for i in secili_ilceler}
    return [v for v in kayitlar if _kayit_ilcesi_eslesiyor_mu(v, secili_norm)]


# ── SUPABASE ANON SIRLARI (kartlardaki ⭐ yıldız JS'i için) ────────────

def supabase_anon_secrets():
    try:
        return st.secrets["supabase"]["url"], st.secrets["supabase"]["publishable_key"]
    except Exception:
        return None, None


# ── AKTİVİTE ÖZETİ ("Son 24 saat") ─────────────────────────────────────

def son_24_saat_ozeti():
    """Ana ekrandaki 'Son 24 saat' widget'ı — KASITLI olarak kartlardaki
    '+N yeni' rozetlerinden (7 günlük pencere, 'haftalık yoğunluk')
    FARKLI bir zaman penceresi kullanır: 24 saat, 'en sıcak gelişme'
    sorusuna cevap verir. Bu iki farklı pencere bilerek yan yana
    gösteriliyor — biri diğerinin yerini almıyor. İkisi de aynı canlı,
    cache'lenmiş veriden (talepleri_cek/portfoyleri_cek) hesaplanıyor,
    hiçbiri statik/eski değil.

    Kapsam ayrımı (değişmedi):
    - Özet CÜMLESİ (kaç yeni talep/portföy) → TÜM havuz (Zeta + Startkey/
      mail) — kart rozetleriyle aynı KAYNAK havuzunu kullanır, sadece
      zaman penceresi farklı (24 saat vs 7 gün).
    - İSİMLİ paylaşım satırları (kim ne ekledi) → SADECE ZETA — 'ekibim
      ne yaptı' sorusuna cevap verir; tüm Startkey ağını (binlerce kişi)
      burada isim isim listelemek hem yanıltıcı hem alakasız olur.

    DÜZELTME (12.08.2026 — Zeta Portföyleri): resmi portal ilanları
    (kaynak zeta1/zeta2) artık "yeni bir portföy paylaştı" genel
    cümlesiyle KARIŞTIRILMIYOR — kendi ayrı olay türü ("yeni bir Zeta
    portföyü yayınladı") ve ayrı bir sayaç (ilan_sayisi) var. Bu, ofis-
    içi paylaşım ile portalda YAYINLANAN resmi ilan arasındaki ayrımı
    (uygulamanın geri kalanında zaten kurduğumuz) aktivite akışında da
    koruyor."""
    talepler_yeni_tumu = son_24_saat_filtrele(talepleri_cek())
    # DÜZELTME (13.08.2026 — KRİTİK, çift sayım): portfoy_sayisi ile
    # ilan_sayisi AYRI sinyaller olsun diye tasarlanmıştı ama portfoy_sayisi
    # hâlâ TÜM havuzdan (zeta1/zeta2 dahil) hesaplanıyordu — yani resmi
    # ilanlar hem "portfoy_sayisi"ye hem "ilan_sayisi"ye giriyor, iki kez
    # sayılıyordu. Artık portfoy_sayisi de resmi ilanları HARİÇ TUTUYOR —
    # tıpkı Portföy Panosu'nun artık hariç tuttuğu gibi (tutarlılık).
    portfoyler_yeni_tumu = [
        v for v in son_24_saat_filtrele(portfoyleri_cek())
        if str(v.get("kaynak") or "").strip().lower() not in ILAN_PORTAL_DEGERLERI
    ]

    talepler_yeni_zeta = son_24_saat_filtrele(kaynak_filtrele(talepleri_cek(), "Zeta"))
    portfoyler_yeni_zeta = [
        v for v in son_24_saat_filtrele(kaynak_filtrele(portfoyleri_cek(), "Zeta"))
        if str(v.get("kaynak") or "").strip().lower() not in ILAN_PORTAL_DEGERLERI
    ]
    portfoyler_yeni_ilan = [
        v for v in portfoyleri_cek()
        if str(v.get("kaynak") or "").strip().lower() in ILAN_PORTAL_DEGERLERI
    ]
    portfoyler_yeni_ilan = son_24_saat_filtrele(portfoyler_yeni_ilan)

    olaylar = []
    for v in talepler_yeni_zeta:
        olaylar.append({
            "danisman": v.get("talep_eden_danisan") or "Bilinmeyen",
            "eylem": "yeni bir talep girdi",
            "tarih": kayit_tarihi_dt(v.get("kayit_tarihi")),
        })
    for v in portfoyler_yeni_zeta:
        olaylar.append({
            "danisman": v.get("talep_eden_danisan") or "Bilinmeyen",
            "eylem": "yeni bir portföy paylaştı",
            "tarih": kayit_tarihi_dt(v.get("kayit_tarihi")),
        })
    for v in portfoyler_yeni_ilan:
        olaylar.append({
            "danisman": v.get("talep_eden_danisan") or "Bilinmeyen",
            "eylem": "yeni bir Zeta portföyü yayınladı",
            "tarih": kayit_tarihi_dt(v.get("kayit_tarihi")),
        })
    olaylar = [o for o in olaylar if o["tarih"] is not None]
    olaylar.sort(key=lambda o: o["tarih"], reverse=True)

    return {
        "talep_sayisi": len(talepler_yeni_tumu),
        "portfoy_sayisi": len(portfoyler_yeni_tumu),
        "ilan_sayisi": len(portfoyler_yeni_ilan),
        "son_olaylar": olaylar[:2],
        "toplam_olay": len(olaylar),
    }


def render_activity_bar():
    """Ana ekranda, aksiyon satırının altında tek bir kompakt blok —
    kart değil. 'Tüm Paylaşımlar' linki Danisman_Paylasimlar.py'ye gider."""
    ozet = son_24_saat_ozeti()
    if ozet["talep_sayisi"] == 0 and ozet["portfoy_sayisi"] == 0 and ozet["ilan_sayisi"] == 0:
        return

    with st.container(border=True, key="dp_activity_box"):
        # DÜZELTME (12.08.2026): "N yeni ilan" bilgisi, varsa cümleye
        # eklendi — resmi portal ilanları artık ayrı bir sinyal.
        ilan_cumle = f", {ozet['ilan_sayisi']} yeni Zeta ilanı" if ozet["ilan_sayisi"] else ""
        st.markdown(
            "<span style='display:inline-flex;align-items:center;gap:6px;'>"
            "<svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='#b8892f' stroke-width='2' "
            "stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='10'/>"
            "<polyline points='12 6 12 12 16 14'/></svg>"
            f"<span><b>Son 24 saat:</b> {ozet['talep_sayisi']} yeni talep, "
            f"{ozet['portfoy_sayisi']} yeni portföy paylaşımı{ilan_cumle}</span></span>",
            unsafe_allow_html=True,
        )
        for olay in ozet["son_olaylar"]:
            st.caption(f"• **{olay['danisman']}** {olay['eylem']}")
        if st.button("Tüm Paylaşımlar →", key="ds_tum_paylasimlar"):
            st.switch_page("pages/Danisman_Paylasimlar.py")


# ── HAMBURGER MENÜ (sağ üst) ────────────────────────────────────────────

def render_topbar(baslik, ikon="📊", geri_hedefi=None, eyebrow=None):
    """Tüm Danışman ekranlarının ortak üst barı: sol grup (hamburger +
    opsiyonel geri butonu), ortada başlık, sağda avatar.

    eyebrow (12.08.2026 — YENİ, SADECE ana ekran için): Verilirse,
    başlığın ÜSTÜNE küçük, büyük harfli, harf aralıklı bir "eyebrow
    label" eklenir (mockup'ta onaylanan "STARTKEY ZETA" + kalın
    "Danışman Panosu" ikilisi). Diğer sayfalar bu parametreyi
    kullanmıyor — bilinçli olarak sadece ana ekrana özel, alt sayfalar
    kompakt/sade kalmaya devam ediyor (daha önce kararlaştırıldığı
    gibi). Logo kutusu KASITLI OLARAK yok — mockup karşılaştırmasında
    metin-only versiyon tercih edildi.

    MİMARİ NOT (3. tur — absolute positioning TAMAMEN TERK EDİLDİ):
    İki ayrı turda position:absolute denendi, ikisinde de başlık yanlış
    bir ataya göre konumlanıp dar bir sütuna sıkışarak harf harf bölündü
    (gerçek testte iki kez doğrulandı — kabul edilemez bir regresyon).
    Kök sebep kesin olarak teşhis edilemedi (position:relative'in hangi
    atada gerçekten "tuttuğu" canlı DOM incelemesi olmadan garanti
    edilemiyor) — bu yüzden absolute'a üçüncü kez güvenmek yerine CSS
    GRID'e geçildi: `grid-template-columns: auto 1fr auto`. Bu teknik
    absolute'un aksine bir "referans atası" tahminine hiç ihtiyaç
    duymaz — grid, KENDİ doğrudan çocuklarını (nth-of-type ile) sütunlara
    yerleştirir, DOM derinliği/pozisyon belirsizliği riski yoktur.

    Grid'in 3 sütununun HER ZAMAN tutarlı kalması için üç doğrudan
    Streamlit elemanı HER ZAMAN render edilir (başlık boş olsa bile):
    1) dp_topbar_left (hamburger + opsiyonel geri butonu, TEK grup)
    2) başlık (boşsa bile boş bir <div>, sütun kaymasın diye)
    3) avatar
    """
    from core.auth import cikis_yap

    st.markdown("""
    <style>
    div[data-testid="stVerticalBlock"][class*="st-key-dp_topbar_wrap"] {
        display: grid !important;
        grid-template-columns: minmax(0, auto) minmax(0, 1fr) minmax(0, auto) !important;
        align-items: center !important;
        gap: 8px !important;
        overflow-x: hidden !important;
    }
    /* nth-of-type ile 3 doğrudan çocuğu (her zaman tam 3 tane) sütunlara
       eşliyoruz — pozisyona dayalı ama SAYI HER ZAMAN SABİT olduğu için
       (fonksiyon her çağrıda tam 3 element-container üretiyor) kırılgan
       değil, garantili. */
    div[data-testid="stVerticalBlock"][class*="st-key-dp_topbar_wrap"] > div[data-testid="element-container"]:nth-of-type(1) {
        grid-column: 1 !important;
    }
    div[data-testid="stVerticalBlock"][class*="st-key-dp_topbar_wrap"] > div[data-testid="element-container"]:nth-of-type(2) {
        grid-column: 2 !important;
        min-width: 0 !important;
        overflow: hidden !important;
        text-align: center !important;
    }
    div[data-testid="stVerticalBlock"][class*="st-key-dp_topbar_wrap"] > div[data-testid="element-container"]:nth-of-type(3) {
        grid-column: 3 !important;
    }
    /* Sol grup (hamburger + opsiyonel geri butonu) — kendi içinde yatay
       dizilsin. Class doğrudan bu stVerticalBlock'un kendisinde, torun
       bir elemanda değil (bu dosyada daha önce birkaç kez yaşanan
       yanlış varsayımı burada tekrarlamıyoruz). */
    div[class*="st-key-dp_topbar_left"] {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 8px !important;
    }

    /* Streamlit'in KENDİ bileşenlerinin (popover) kutu/gölgesini
       sıfırlıyoruz — kendi özel HTML'imize hiç dokunmuyor. */
    div[class*="st-key-dp_topbar_wrap"] [data-testid="stPopover"] > button {
        border: 1px solid #e3e1da !important;
        box-shadow: none !important;
        background: #ffffff !important;
    }
    div[class*="st-key-dp_topbar_wrap"] {
        border-bottom: 1px solid #ecebe5 !important;
        padding-bottom: 8px !important;
        margin-bottom: 8px !important;
    }
    /* "← Panoya Dön" butonu — dar konteynerlerde metni dikey bölmesin
       (Zeta Paylaşımları gibi sayfalarda gözlemlendi). Buton doğal
       genişliğini korusun, satır kırmasın. */
    div[class*="st-key-dp_geri_btn"] button {
        white-space: nowrap !important;
        width: auto !important;
    }
    /* Başlık — grid sütunu içinde ortalı, satır kırmasın, sığmazsa
       kırpılıp "..." göstersin (satır kırıp dikey bölünmek yerine).
       DÜZELTME (10.08.2026): Başlık rengi artık AÇIKÇA lacivert —
       önceden Streamlit'in varsayılan metin rengine bırakılmıştı,
       kararlaştırılan "başlık lacivert kalsın" tercihiyle tutarlı
       olsun diye netleştirildi. */
    .dp-topbar-baslik {
        margin: 0 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        color: #1b2540 !important;
        font-size: 17px !important;
        font-weight: 800 !important;
        letter-spacing: -0.01em !important;
    }
    /* Eyebrow label (12.08.2026, sadece ana ekran) — mockup'ta onaylanan
       "STARTKEY ZETA" küçük etiket stili. Logo kutusu bilinçli olarak
       yok (metin-only versiyon tercih edildi). */
    .dp-topbar-eyebrow {
        margin: 0 !important;
        font-size: 10.5px !important;
        font-weight: 700 !important;
        letter-spacing: 0.08em !important;
        color: #9aa1af !important;
        text-transform: uppercase !important;
        line-height: 1.3 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    /* Avatar rozeti — kendi sınıfıyla, üstteki reset kurallarından
       tamamen bağımsız garanti altına alınıyor.
       DÜZELTME (10.08.2026): Lacivert dolu daireden soluk/pastel gold
       zemin + koyu gold yazıya geçildi — amaç "her yer lacivert olmasın"
       (monotonluğu kırmak) ama tam doygun gold gibi göz önce buraya
       gitmesin diye BİLİNÇLİ OLARAK soluk tutuldu (mockup'ta 3 seçenek
       karşılaştırılıp bu seçildi). */
    .dp-avatar-circle {
        width: 30px !important;
        height: 30px !important;
        border-radius: 50% !important;
        background: #f0e2c4 !important;
        color: #8a6519 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 12px !important;
        font-weight: 700 !important;
        flex-shrink: 0 !important;
    }

    /* MOBİL (dar ekran) — DÜZELTME (3. tur, diğer AI'ın önerisiyle):
       Başlığı tek satırda tutmaya çalışmak (kırpma, küçültme, sarma)
       hepsi farklı derecelerde başarısız oldu — kök sorun "başlığı
       navigasyon düğmeleriyle aynı yatay yarışa sokmak". Çözüm: mobilde
       topbar'ı TAMAMEN 2 SATIRA ayırıyoruz (CSS Grid Areas ile):
         1. satır: [sol grup: hamburger+geri]  ...  [avatar]
         2. satır: [başlık] (tam genişlik, kendi satırında rahat yer)
       Grid'in 3 doğrudan çocuğu (sol grup, başlık, avatar) DOM sırası
       değişmeden, sadece grid-area atamalarıyla yeniden yerleşiyor. */
    @media (max-width: 480px) {
        .dp-avatar-name {
            display: none !important;
        }
        div[class*="st-key-dp_geri_btn"] button {
            padding: 8px 10px !important;
        }
        div[class*="st-key-dp_geri_btn"] button p {
            font-size: 0 !important;
        }
        div[class*="st-key-dp_geri_btn"] button p::before {
            content: "←";
            font-size: 16px;
        }
        div[data-testid="stVerticalBlock"][class*="st-key-dp_topbar_wrap"] {
            grid-template-columns: auto 1fr auto !important;
            grid-template-rows: auto auto !important;
            grid-template-areas: "sol . avatar" "baslik baslik baslik" !important;
            row-gap: 6px !important;
            align-items: center !important;
        }
        div[data-testid="stVerticalBlock"][class*="st-key-dp_topbar_wrap"] > div[data-testid="element-container"]:nth-of-type(1) {
            grid-area: sol !important;
        }
        div[data-testid="stVerticalBlock"][class*="st-key-dp_topbar_wrap"] > div[data-testid="element-container"]:nth-of-type(2) {
            grid-area: baslik !important;
            justify-self: center !important;
        }
        div[data-testid="stVerticalBlock"][class*="st-key-dp_topbar_wrap"] > div[data-testid="element-container"]:nth-of-type(3) {
            grid-area: avatar !important;
        }
        .dp-topbar-baslik {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: unset !important;
            font-size: 17px !important;
            font-weight: 800 !important;
            line-height: 1.25 !important;
            text-align: center !important;
            letter-spacing: -0.01em !important;
        }
        .dp-topbar-eyebrow {
            font-size: 9.5px !important;
            text-align: center !important;
            white-space: normal !important;
            overflow: visible !important;
        }

        /* Üstteki fazla boşluğu azalt — Streamlit'in varsayılan mobil
           üst dolgusu (block-container padding-top) gereğinden fazla
           boş alan bırakıyordu. DÜZELTME (11.08.2026 — 2. tur): 0.75rem
           hâlâ yetersizdi, ekran görüntülerinde üstte belirgin boşluk
           kalıyordu — 0.35rem'e düşürüldü. */
        [data-testid="stAppViewContainer"] .main .block-container {
            padding-top: 0.35rem !important;
        }
        /* Topbar'ın kendi alt boşluğu da mobilde biraz sıkılaştırıldı
           (masaüstü değeri — 8px — dokunulmadı, bu kural sadece bu
           media query içinde geçerli). */
        div[class*="st-key-dp_topbar_wrap"] {
            padding-bottom: 6px !important;
            margin-bottom: 6px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    su_kullanici = su_anki_danisman()
    baslar = (
        "".join([p[0].upper() for p in su_kullanici.split()[:2]])
        if su_kullanici and " " in su_kullanici
        else (su_kullanici[:2].upper() if su_kullanici else "?")
    )

    with st.container(key="dp_topbar_wrap"):
        # 1. GRID SÜTUNU — sol grup: hamburger + opsiyonel geri butonu,
        # TEK bir Streamlit container'ı içinde (nth-of-type(1) garantisi).
        with st.container(key="dp_topbar_left"):
            with st.popover("☰"):
                st.markdown(f"**{su_kullanici}**")
                st.caption("Danışman")
                st.divider()
                if st.button("📂 Kendi Kayıtlarım", use_container_width=True, key="dp_menu_kayitlarim"):
                    st.switch_page("pages/Danisman_Kayitlarim.py")
                if st.button("📇 Danışman Rehberim", use_container_width=True, key="dp_menu_musteriler"):
                    st.switch_page("pages/Danisman_Rehberim.py")
                if st.button("📢 Zeta Portföyleri", use_container_width=True, key="dp_menu_zeta_ilan"):
                    st.switch_page("pages/Danisman_ZetaPortfoyleri.py")
                if st.button("👥 Zeta Paylaşımları", use_container_width=True, key="dp_menu_paylasimlar"):
                    st.switch_page("pages/Danisman_Paylasimlar.py")
                st.divider()
                if st.button("🚪 Çıkış Yap", use_container_width=True, key="dp_menu_cikis"):
                    cikis_yap()
                    # DÜZELTME (08.08.2026): Girişteki aynı yarış durumu
                    # çıkışta da vardı — cikis_yap() içindeki
                    # _tarayici_oturumu_temizle() tarayıcıya "cookie'yi sil"
                    # komutu gönderiyor ama bunun işlenmesi bir an sürüyor.
                    # Hemen ardından switch_page() sayfayı terk edince, silme
                    # komutu tamamlanmadan Danisman_Giris.py açılıyor ve orada
                    # hâlâ duran (silinmemiş) cookie'yi görüp kullanıcıyı
                    # OTOMATİK OLARAK GERİ İÇERİ ALIYORDU — çıkış yapmış
                    # gibi görünüp aslında oturumda kalmış oluyordu (gerçek
                    # testte doğrulandı). Girişteki çözümün aynısı: kısa,
                    # otomatik bir bekleme ile silme komutuna gerçek zaman
                    # tanıyoruz.
                    with st.spinner("Çıkış yapılıyor..."):
                        time.sleep(1)
                    st.switch_page("pages/Danisman_Giris.py")

            if geri_hedefi:
                if st.button("← Panoya Dön", key="dp_geri_btn"):
                    st.switch_page(geri_hedefi)

        # 2. GRID SÜTUNU — başlık. HER ZAMAN render edilir (boşsa bile
        # boş bir div) — sütun sayısı/sırası hiçbir zaman kaymasın diye.
        if eyebrow:
            baslik_html = (
                f"<div class='dp-topbar-eyebrow'>{eyebrow}</div>"
                f"<h3 class='dp-topbar-baslik'>{baslik}</h3>"
            )
        elif baslik:
            baslik_html = f"<h3 class='dp-topbar-baslik'>{ikon} {baslik}</h3>"
        else:
            baslik_html = "<div></div>"
        st.markdown(baslik_html, unsafe_allow_html=True)

        # 3. GRID SÜTUNU — avatar.
        avatar_html = ""
        if su_kullanici:
            avatar_html = (
                "<div style='display:flex;align-items:center;gap:8px;flex-shrink:0;justify-content:flex-end;'>"
                f"<div class='dp-avatar-circle'>{baslar}</div>"
                f"<span class='dp-avatar-name' style='font-size:13px;color:#5b6478 !important;font-weight:600;white-space:nowrap;'>{su_kullanici}</span></div>"
            )
        st.markdown(avatar_html, unsafe_allow_html=True)


def hide_sidebar_css():
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    [data-testid="stHeader"] { display: none !important; }

    /* İçerik genişliği: app.py 'wide' layout kullanıyor ama bu, çok
       geniş ekranlarda içeriği aşırı daraltıp yanlarda baskın krem
       boşluklar bırakıyordu. Burada net bir max-width veriyoruz —
       tüm ekranı germiyor, makul bir okuma genişliğinde ortalıyor. */
    .block-container {
        max-width: 1100px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }

    /* ── TEMA (2026-08): mockup ile uyumlu sıcak kırık beyaz zemin,
       beyaz kart yüzeyleri, Segoe UI, navy başlıklar, yumuşak gri
       ikincil metin. Yalnızca CSS/tema katmanı — düzen, buton
       konumu, veri akışı DEĞİŞMEDİ. ── */

    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        background-color: #f6f5f2 !important;
    }
    /* Font Segoe UI: KASITLI olarak *, !important VE testid tahmini
       KULLANMIYORUZ. Doğal CSS kalıtımına güveniyoruz — .stApp üzerinde
       tanımlanan font-family, metin öğelerine miras yoluyla yayılır, ama
       Streamlit'in ikon glif elemanlarına (kendi font-family'sini
       doğrudan üzerinde taşıyorlar) dokunmaz. Önceki deneme (`.stApp *`
       + `!important`) tam bu yüzden ikonları bozmuştu — doğrudan
       hedeflenen bir kural, miras alınan değerden her zaman kazanır. */
    .stApp {
        font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Ana başlıklar — koyu lacivert, extra-bold, hafif sıkışık harf
       aralığı (mockup: font-weight 800, letter-spacing -0.01em) */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        color: #1b2540 !important;
        font-weight: 800 !important;
        letter-spacing: -0.01em !important;
    }

    /* İkincil metin (caption, açıklama) — yumuşak gri-lacivert */
    .stApp [data-testid="stCaptionContainer"],
    .stApp [data-testid="stCaptionContainer"] * {
        color: #5b6478 !important;
    }

    /* Çerçeve içindeki TÜM sütun/satır grupları (kartları yan yana koyan,
       Favori Listem/Ekle'yi yan yana koyan sütunlar dahil) şeffaf olsun —
       aksi halde Streamlit'in kendi sütun elemanı sayfa zemininin (krem)
       rengini miras alıp çerçevenin İÇİNDE görünür kalıyordu. Bu kural,
       aşağıdaki daha spesifik "beyaz kart" kuralından ÖNCE geliyor —
       kartların kendisi (dp_kart_talep vb.) hâlâ kaynak sırası gereği
       kendi beyaz rengini koruyor. */
    div[class*="st-key-dp_page_frame"] [data-testid="stColumn"],
    div[class*="st-key-dp_page_frame"] [data-testid="stHorizontalBlock"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }

    /* Kartlar / bordered container'lar — beyaz yüzey, sıcak açık gri
       kenarlık, çok hafif gölge, yuvarlak köşe (mockup: 12-14px —
       Streamlit varsayılanı 8px, daha sert duruyordu).
       dp_page_frame: mockup'taki .frame-desktop — sayfa başlığından
       Favori Listem'e kadar HER ŞEYİ saran dış beyaz çerçeve.
       ÖNEMLİ: Bilerek SADECE bizim açıkça key verdiğimiz kartları
       hedefliyoruz (blanket `div[data-testid="stVerticalBlockBorderWrapper"]`
       seçicisi kullanmıyoruz) — o blanket kural, Streamlit'in popover
       bileşeninin kendi iç yapısını da boyayıp header'ın yanında
       istenmeyen bir kutu/gölge oluşturuyordu. */
    div[class*="st-key-dp_page_frame"] div[data-testid="stVerticalBlockBorderWrapper"],
    div[class*="st-key-dp_kart_talep"] div[data-testid="stVerticalBlockBorderWrapper"],
    div[class*="st-key-dp_kart_portfoy"] div[data-testid="stVerticalBlockBorderWrapper"],
    div[class*="st-key-dp_activity_box"] div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff !important;
        border-color: #e3e1da !important;
        border-radius: 16px !important;
        box-shadow: 0 1px 3px rgba(27, 37, 64, 0.06) !important;
    }

    /* DÜZELTME: dp_page_frame'in KENDİ dış kutusu (görünür border/arka
       planı taşıyan gerçek eleman) yukarıdaki kuralla hiç boyanmıyordu.
       Sebep: st.container(border=True, key=...) çağrısında class,
       stVerticalBlockBorderWrapper'ın İÇİNE değil, onun ÇOCUĞU olan
       stVerticalBlock'a ekleniyor — yani wrapper, class'ı taşıyan
       elemanın torunu değil EBEVEYNİ. Yukarıdaki descendant seçici bu
       yüzden sadece İÇERİDEKİ kartların (dp_kart_talep vb., onlar
       gerçekten içeride nested olduğu için) kendi wrapper'ını
       boyuyordu, çerçevenin kendisini hiç boyamıyordu — altından krem
       zemin sızıyordu. :has() ile artık "içinde bu class'lı çocuk olan
       wrapper'ı bul" diyerek doğru (ebeveyn) yöne işaret ediyoruz. */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(> div[class*="st-key-dp_page_frame"]) {
        background-color: #ffffff !important;
        border-color: #e3e1da !important;
        border-radius: 16px !important;
        box-shadow: 0 1px 3px rgba(27, 37, 64, 0.06) !important;
    }

    /* Aktivite kutusu ("Son 24 saat") — diğer kartlardan farklı, sayfa
       zeminine yakın soft bej (mockup: #f8f7f4) — "öne çıkan panel"
       değil "sayfanın devamı" hissi için. Yukarıdaki genel beyaz kart
       kuralını, daha spesifik bu seçiciyle eziyoruz. */
    div[class*="st-key-dp_activity_box"] div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #f8f7f4 !important;
        border-color: #ecebe5 !important;
    }

    /* NOT (2. tur — regresyon giderme): Bu ekranda daha önce burada
       "Filtre kutusu" (bordered, krem tonlu) CSS'i vardı — prompt'un
       açık talebiyle (bordered/krem kutu görünmesin) kaldırıldı, yerini
       çerçevesiz minimalist toolbar aldı (bkz. render_pano_icerik ve
       _inject_filtre_pill_css). Radio/pill CSS'i de burada AYRICA
       tanımlıydı — render_pano_icerik() ve Danisman_Favoriler.py'deki
       scoped kopyalarla ÇAKIŞIYORDU (iki farklı seçici stratejisi aynı
       elemanları hedefliyordu: biri `input:checked`, diğeri
       `div[aria-checked="true"]`) — bu çakışma, varsayılan seçili
       "Tümü" pill'inin metninin görünmez olmasına (beyaz yazı + beyaz
       zemin) sebep oluyordu. Artık TEK kaynak var: _inject_filtre_pill_css()
       — her filtre grubunun render edildiği yerde bir kez çağrılıyor. */

    /* İç ayırıcı çizgiler (st.divider) — açık, sıcak gri */
    .stApp hr {
        border-color: #ecebe5 !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ── ORTAK PANO EKRANI (Talep / Portföy) ─────────────────────────────────
# Danisman_Talep.py ve Danisman_Portfoy.py bu tek fonksiyonu çağırır —
# iki ayrı dosyada aynı kart/A-Z/filtre mantığını tekrarlamamak için.

# ── ORTAK FİLTRE PILL CSS (2. tur — regresyon giderme) ──────────────────
# TEK, kanonik kaynak. Önceki turda üç ayrı yerde (hide_sidebar_css, eski
# render_pano_icerik, Danisman_Favoriler.py) benzer ama BİRBİRİYLE ÇAKIŞAN
# radio/pill CSS'i tanımlanmıştı — iki farklı "seçili mi?" tespit stratejisi
# (biri `input:checked`, diğeri `div[aria-checked="true"]`) aynı elemanlar
# için yarışınca, varsayılan seçili "Tümü" pill'i beyaz yazı + beyaz zemin
# kombinasyonuna düşüp görünmez oluyordu. Artık her filtre grubunun
# render edildiği yerde SADECE bu fonksiyon çağrılıyor, başka hiçbir yerde
# radio/pill CSS'i tekrar tanımlanmıyor.
#
# Seçili durumu tespit etmek için `div[data-baseweb="radio"]` kullanılıyor
# — bu, dosyada daha önce zaten ÇALIŞTIĞI DOĞRULANMIŞ bir seçici (seçili
# göstergeyi navy'ye boyayan eski kural buna dayanıyordu). Aynı elemanı artık
# TAMAMEN GİZLİYORUZ (dairesel gösterge hiç görünmesin) — bu eleman SADECE
# göstergenin kendisi, etiket metnini (p) İÇERMİYOR, bu yüzden metni
# yanlışlıkla gizleme riski yok (önceki `label > div:first-child` gibi
# konuma dayalı, kırılgan bir tahmin değil).
def _inject_filtre_pill_css():
    st.markdown("""
    <style>
    div[data-testid="stRadio"] div[role="radiogroup"] {
        gap: 6px !important;
        flex-wrap: wrap !important;
    }
    /* DÜZELTME (4. tur — yapısal çözüm, diğer AI'ın önerisiyle):
       Önceki iki deneme (parametreye güvenme, sonra :not() ile hariç
       tutma) DOM'daki bir özniteliğin "olmadığını" doğrulamaya
       dayanıyordu — kırılgan. Gerçek DOM incelemesi doğruladı ki
       stWidgetLabel (grup başlığı, örn. "İşlem Tipi"), radiogroup
       div'inin İÇİNDE DEĞİL, ONUNLA KARDEŞ bir eleman:
         <div class="stRadio">
           <label data-testid="stWidgetLabel">İşlem Tipi</label>
           <div role="radiogroup"> ...pill seçenekleri... </div>
         </div>
       Bu yüzden pill stilini SADECE "div[role=radiogroup] label"
       seçicisiyle uygulamak YAPISAL olarak grup başlığını asla
       eşleştiremez — hiçbir öznitelik tahminine/hariç tutmaya gerek
       kalmadan kesin bir ayrım. Grup başlığı ayrıca (ekstra güvence
       için) doğrudan da gizleniyor. */
    div[data-testid="stRadio"] [data-testid="stWidgetLabel"] {
        display: none !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label {
        display: inline-flex !important;
        align-items: center !important;
        border: 1px solid #e3e1da !important;
        border-radius: 999px !important;
        padding: 4px 14px !important;
        margin: 0 !important;
        min-height: unset !important;
        background: #ffffff !important;
    }
    /* Dairesel göstergeyi gizle — data-baseweb="radio" SADECE göstergenin
       kendisi (metin değil), :has() bu eleman display:none olsa bile DOM
       yapısını okumaya devam eder, seçili tespiti bozulmaz. */
    div[data-testid="stRadio"] div[role="radiogroup"] div[data-baseweb="radio"] {
        display: none !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label p {
        font-size: 12.5px !important;
        font-weight: 600 !important;
        margin: 0 !important;
        white-space: nowrap !important;
        color: #5b6478 !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(div[aria-checked="true"]) {
        background: #1b2540 !important;
        border-color: #1b2540 !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(div[aria-checked="true"]) p {
        color: #ffffff !important;
    }

    /* DÜZELTME (09.08.2026 — mobil pill taşması): Zaman Aralığı grubunda
       ("Tümü / Son 24 saat / Son 7 gün") ve bazı 3'lü İşlem Tipi
       gruplarında, filtre satırı mobilde Yenile butonuyla aynı satırı
       paylaşınca daralan genişlik yüzünden SON pill (Son 7 gün / Kiralık)
       bir alt satıra taşıyordu. Kök sebep pill'lerin masaüstü boyutunda
       kalması (padding 4px 14px, font 12.5px) — mobilde daha küçük
       pill'lerle aynı satıra üçü de rahatça sığıyor. */
    @media (max-width: 480px) {
        div[data-testid="stRadio"] div[role="radiogroup"] {
            gap: 4px !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label {
            padding: 4px 8px !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label p {
            font-size: 11px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)


# ── ORTAK PANO İÇERİĞİ (filtre + A-Z + kart) ────────────────────────────
# render_pano_icerik: kayıt havuzu DIŞARIDAN verilir. Talep/Portföy Panosu
# tüm havuzu geçirir, Zeta Paylaşımları sadece Zeta'ya filtrelenmiş havuzu
# geçirir — böylece iki farklı ekran (tüm havuz / Zeta-only) AYNI filtre +
# A-Z + kart görselini, kod tekrarı olmadan paylaşır.

def render_pano_icerik(kayitlar_havuzu, kayit_tipi, baslik, key_prefix, zaman_varsayilan="Tümü"):
    """
    kayitlar_havuzu: zaten istenen kaynağa göre süzülmüş liste (tüm havuz
                      ya da Zeta-only — çağıran belirler).
    kayit_tipi: 'talep' | 'portfoy'
    key_prefix: aynı sayfada birden fazla çağrı varsa (örn. sekmeli Zeta
                Paylaşımları) widget key çakışmasını önlemek için benzersiz
                bir önek (örn. 'zt_talep', 'zt_portfoy').
    zaman_varsayilan: 'Tümü' | 'Son 24 saat' | 'Son 7 gün' — radio'nun
                       varsayılan seçili değeri (rozetten geldiyse
                       'Son 24 saat' olarak zorlanır).
    """
    import streamlit.components.v1 as components
    from core.pano_export import pano_html_olustur

    ZAMAN_SECENEKLERI = ["Tümü", "Son 24 saat", "Son 7 gün"]
    zaman_index = ZAMAN_SECENEKLERI.index(zaman_varsayilan) if zaman_varsayilan in ZAMAN_SECENEKLERI else 0

    _inject_filtre_pill_css()

    # NOT (teknik sınır — değişmedi): "(Canlı)" paneli (başlık, "Toplam
    # kayıt", A-Z, kartlar) core.pano_export.pano_html_olustur() ile
    # üretilen BAĞIMSIZ bir HTML dokümanı — components.html ile iframe
    # içinde render ediliyor. Native Streamlit filtreleri bu yüzden
    # iframe'in GERÇEKTEN içine gömülemez. DÜZELTME (2. tur): önceki
    # turda bu sınırı "krem tonlu, bordered bir kutu" ile telafi etmeye
    # çalışmıştık — talep edilen yön bu değildi (ayrı dev panel hissi
    # veriyordu). Artık ÇERÇEVESİZ, minimalist bir toolbar satırı:
    # bordered container yok, krem kutu yok, sadece kompakt pill'ler +
    # küçük Yenile ikonu, dikey alan minimum.
    # DÜZELTME (3. tur — dikey alan sıkılaştırma): Talep edilen şey,
    # filtrelerin iframe'in İÇİNE gömülmesi değil (bu teknik olarak
    # imkansız, yukarıdaki not) — asıl istenen, topbar + filtre alanının
    # kapladığı TOPLAM dikey boşluğun minimuma inmesi, ki asıl içerik
    # (alfabe + kartlar) daha yukarıda başlasın. Bu tamamen CSS ile
    # yapılabilir: filtre satırını kendi dar key'li konteynerine alıp,
    # SADECE bu bölgenin üst/alt boşluğunu sıkılaştırıyoruz (global
    # spacing'e dokunmadan, sadece bu alanı hedefleyerek).
    st.markdown(f"""
    <style>
    div[class*="st-key-dp_filtre_toolbar_{key_prefix}"] {{
        margin-top: -8px !important;
        margin-bottom: -8px !important;
    }}
    div[class*="st-key-dp_filtre_toolbar_{key_prefix}"] div[data-testid="stHorizontalBlock"] {{
        gap: 0.5rem !important;
    }}
    div[class*="st-key-dp_yenile_{key_prefix}"] button {{
        width: 38px !important;
        min-width: 38px !important;
        padding: 0 !important;
        min-height: 38px !important;
        height: 38px !important;
        font-size: 15px !important;
        border-radius: 8px !important;
        border-color: #e3e1da !important;
        background: #ffffff !important;
        color: #5b6478 !important;
    }}

    /* DÜZELTME (mobil filtre+yenile kompaktlama, 09.08.2026, GÜNCELLEME
       11.08.2026 — 2. tur): İlk halinde 1. satır = İşlem Tipi (tam
       genişlik), 2. satır = Zaman Aralığı + Yenile yan yana idi — ama
       canlıda "Son 24 saat"/"Son 7 gün" pill'leri Yenile ile aynı dar
       satırı paylaşınca hâlâ 3. satıra taşıyordu (metinleri İşlem
       Tipi'nden uzun: "Son 24 saat", "Son 7 gün"). Çözüm: SATIRLAR
       DEĞİŞTİRİLDİ — artık 1. satır = İşlem Tipi (kısa: Tümü/Satılık/
       Kiralık) + Yenile yan yana, 2. satır = Zaman Aralığı TEK BAŞINA
       tam genişlikte, taşmasın diye ihtiyacı olan tüm alanı alıyor. */
    @media (max-width: 480px) {{
        div[class*="st-key-dp_filtre_toolbar_{key_prefix}"] div[data-testid="stHorizontalBlock"] {{
            display: grid !important;
            grid-template-columns: 1fr auto !important;
            grid-template-areas: "islem yenile" "zaman zaman" !important;
            row-gap: 6px !important;
            align-items: center !important;
        }}
        div[class*="st-key-dp_filtre_toolbar_{key_prefix}"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-of-type(1) {{
            grid-area: islem !important;
            width: auto !important;
            min-width: 0 !important;
        }}
        div[class*="st-key-dp_filtre_toolbar_{key_prefix}"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-of-type(2) {{
            grid-area: zaman !important;
            width: auto !important;
            min-width: 0 !important;
        }}
        div[class*="st-key-dp_filtre_toolbar_{key_prefix}"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-of-type(3) {{
            grid-area: yenile !important;
            width: auto !important;
            min-width: 0 !important;
        }}
        /* Yenile sütunundaki üstteki boş st.write("") boşluğu mobilde
           artık gerekmiyor — buton zaten filtre pilleriyle aynı satırda
           dikey ortalı (align-items:center yukarıda). */
        div[class*="st-key-dp_filtre_toolbar_{key_prefix}"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-of-type(3) [data-testid="stElementContainer"]:first-child {{
            display: none !important;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)

    with st.container(key=f"dp_filtre_toolbar_{key_prefix}"):
        fcol1, fcol2, fcol3 = st.columns([2, 2, 1])
        with fcol1:
            islem_secim = st.radio(
                "İşlem Tipi", ["Tümü", "Satılık", "Kiralık"],
                horizontal=True, key=f"dp_islem_filtre_{key_prefix}",
                label_visibility="collapsed",
            )
        with fcol2:
            zaman_secim = st.radio(
                "Zaman Aralığı", ZAMAN_SECENEKLERI,
                horizontal=True, index=zaman_index, key=f"dp_zaman_filtre_{key_prefix}",
                label_visibility="collapsed",
            )
        with fcol3:
            st.write("")
            if st.button("↻", key=f"dp_yenile_{key_prefix}", help="Yenile"):
                talepleri_cek.clear()
                portfoyleri_cek.clear()
                favorileri_cek.clear()
                st.rerun()

    kayitlar = islem_tipi_filtrele(kayitlar_havuzu, islem_secim)
    if zaman_secim == "Son 24 saat":
        kayitlar = son_24_saat_filtrele(kayitlar)
    elif zaman_secim == "Son 7 gün":
        kayitlar = son_N_gun_filtrele(kayitlar, 7)

    if not kayitlar:
        st.info("Bu filtrede kayıt yok.")
        return

    su_kullanici = su_anki_danisman()
    try:
        favori_kayitlari = favorileri_cek(su_kullanici)
    except Exception:
        favori_kayitlari = []
    favori_set = {(f["kaynak_tablo"], f["kayit_id"]) for f in favori_kayitlari}
    supabase_url, supabase_anon = supabase_anon_secrets()

    html_buf = pano_html_olustur(
        kayitlar, f"{baslik} (Canlı)", kayit_tipi=kayit_tipi,
        favori_destekli=True, favori_set=favori_set,
        supabase_url=supabase_url, supabase_anon_key=supabase_anon,
        mevcut_kullanici=su_kullanici,
        baslik_goster=False,
    )
    components.html(html_buf.getvalue().decode("utf-8"), height=1800, scrolling=True)


# ── ORTAK PANO EKRANI (Talep / Portföy) ─────────────────────────────────
# Danisman_Talep.py ve Danisman_Portfoy.py bu tek fonksiyonu çağırır —
# iki ayrı dosyada aynı kart/A-Z/filtre mantığını tekrarlamamak için.

def render_pano_ekrani(kayit_tipi):
    """kayit_tipi: 'talep' | 'portfoy'
    'TÜM HAVUZU' gösterir (Zeta + Startkey/mail birlikte) — kaynağa göre
    ayrı filtre yok, çünkü Zeta'ya özel görünüm zaten ayrı bir sayfada
    (Danisman_Paylasimlar.py).

    DÜZELTME (13.08.2026 — KRİTİK): 'portfoy' için TÜM HAVUZ artık
    ILAN_PORTAL_DEGERLERİ (zeta1/zeta2 — Revy'den senkronize, portallarda
    YAYINLANAN resmi ilanlar) İÇERMİYOR. revy_sync.py aktif olmadan önce
    bu ayrım gerekmiyordu (portfoyler tablosunda sadece ofis-içi/mail
    kaynaklı paylaşımlar vardı) — ama artık resmi ilanlar da AYNI tabloya
    yazılıyor, ve bu fonksiyon hiçbir filtre uygulamadığı için o ilanlar
    sessizce Portföy Panosu'na (TÜM ~30 danışmanın gördüğü ORTAK pano)
    karışmaya başlamıştı. Resmi ilanların TEK gösterileceği yer artık
    'Zeta Portföyleri' (Danisman_ZetaPortfoyleri.py) — burada değil, iki
    yapı kesinlikle karıştırılmamalı (bilinçli tasarım kararı)."""
    if kayit_tipi == "talep":
        veri_cek = talepleri_cek
        baslik = "Talep Panosu"
        ikon = "⬇️"
    else:
        veri_cek = portfoyleri_cek
        baslik = "Portföy Panosu"
        ikon = "🏘️"

    # DÜZELTME (12.08.2026 — başlık hiyerarşisi birleştirmesi): Önceden
    # BİLİNÇLİ olarak boş bırakılıyordu (iframe'in kendi büyük başlığı
    # vardı, iki başlık üst üste görünmesin diye). Artık TERSİ kararlaştı:
    # topbar TEK ve ANA başlık kaynağı, iframe'in kendi h1'i küçük bir
    # özet satırına indirildi (pano_export.py → _kart_html üstündeki
    # header). Bu yüzden buraya artık gerçek başlık geliyor.
    render_topbar(baslik, ikon=ikon, geri_hedefi="pages/Danisman_Secim.py")

    # "+N yeni" rozetinden geldiyse, zaman filtresi varsayılan olarak
    # 'Son 24 saat' açık başlar — tek seferlik: sayfa render olduktan
    # sonra bayrak sıfırlanır ki kullanıcı manuel değiştirdiğinde tekrar
    # geri gelmesin.
    rozetten_geldi = st.session_state.pop("dp_sadece_yeni", False)
    zaman_varsayilan = "Son 7 gün" if rozetten_geldi else "Tümü"

    kayitlar = veri_cek()
    if kayit_tipi == "portfoy":
        kayitlar = [
            v for v in kayitlar
            if str(v.get("kaynak") or "").strip().lower() not in ILAN_PORTAL_DEGERLERI
        ]

    render_pano_icerik(
        kayitlar, kayit_tipi, baslik, key_prefix=kayit_tipi,
        zaman_varsayilan=zaman_varsayilan,
    )

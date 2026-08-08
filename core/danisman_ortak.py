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
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import streamlit as st

from core.supabase_client import get_client
from core.pano_export import _ilce_normalize, _islem_tipi_norm

supabase = get_client()

ZETA_DEGERLERI = {"zeta", "zeta1", "zeta2", "ofis"}

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

def _yeni_talep_ekle(ilceler, bolge, mulk_tipi, oda, butce, islem_tipi, ek_not, danisman_adi):
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
    }
    supabase.table("alici_talepleri").insert(kayit).execute()


def _yeni_portfoy_ekle(ilceler, bolge, mulk_tipi, oda, fiyat, islem_tipi, ek_not, danisman_adi):
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
    }
    supabase.table("portfoyler").insert(kayit).execute()


def kayit_sil(tablo, kayit_id):
    supabase.table(tablo).delete().eq("id", kayit_id).execute()


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

        gonder = st.form_submit_button("Kaydet", type="primary", use_container_width=True)

        if gonder:
            if not f_ilceler:
                st.error("En az bir ilçe seçimi zorunlu.")
            else:
                f_bolge = baslik_normalize(f_bolge)
                danisman_adi = su_anki_danisman()
                try:
                    if kayit_tipi_secim == "Talep":
                        _yeni_talep_ekle(f_ilceler, f_bolge, f_mulk, f_oda, f_deger, f_islem, f_ek_not, danisman_adi)
                    else:
                        _yeni_portfoy_ekle(f_ilceler, f_bolge, f_mulk, f_oda, f_deger, f_islem, f_ek_not, danisman_adi)
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
      burada isim isim listelemek hem yanıltıcı hem alakasız olur."""
    talepler_yeni_tumu = son_24_saat_filtrele(talepleri_cek())
    portfoyler_yeni_tumu = son_24_saat_filtrele(portfoyleri_cek())

    talepler_yeni_zeta = son_24_saat_filtrele(kaynak_filtrele(talepleri_cek(), "Zeta"))
    portfoyler_yeni_zeta = son_24_saat_filtrele(kaynak_filtrele(portfoyleri_cek(), "Zeta"))

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
    olaylar = [o for o in olaylar if o["tarih"] is not None]
    olaylar.sort(key=lambda o: o["tarih"], reverse=True)

    return {
        "talep_sayisi": len(talepler_yeni_tumu),
        "portfoy_sayisi": len(portfoyler_yeni_tumu),
        "son_olaylar": olaylar[:2],
        "toplam_olay": len(olaylar),
    }


def render_activity_bar():
    """Ana ekranda, aksiyon satırının altında tek bir kompakt blok —
    kart değil. 'Tüm Paylaşımlar' linki Danisman_Paylasimlar.py'ye gider."""
    ozet = son_24_saat_ozeti()
    if ozet["talep_sayisi"] == 0 and ozet["portfoy_sayisi"] == 0:
        return

    with st.container(border=True, key="dp_activity_box"):
        st.markdown(
            "<span style='display:inline-flex;align-items:center;gap:6px;'>"
            "<svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='#b8892f' stroke-width='2' "
            "stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='10'/>"
            "<polyline points='12 6 12 12 16 14'/></svg>"
            f"<span><b>Son 24 saat:</b> {ozet['talep_sayisi']} yeni talep, "
            f"{ozet['portfoy_sayisi']} yeni portföy paylaşımı</span></span>",
            unsafe_allow_html=True,
        )
        for olay in ozet["son_olaylar"]:
            st.caption(f"• **{olay['danisman']}** {olay['eylem']}")
        if st.button("Tüm Paylaşımlar →", key="ds_tum_paylasimlar"):
            st.switch_page("pages/Danisman_Paylasimlar.py")


# ── HAMBURGER MENÜ (sağ üst) ────────────────────────────────────────────

def render_topbar(baslik, ikon="📊", geri_hedefi=None):
    """Tüm Danışman ekranlarının ortak üst barı: sol grup (hamburger +
    opsiyonel geri butonu), ortada başlık, sağda avatar.

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
        grid-template-columns: auto 1fr auto !important;
        align-items: center !important;
        gap: 14px !important;
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
       kırpılıp "..." göstersin (satır kırıp dikey bölünmek yerine). */
    .dp-topbar-baslik {
        margin: 0 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    /* Avatar rozeti — kendi sınıfıyla, üstteki reset kurallarından
       tamamen bağımsız garanti altına alınıyor. */
    .dp-avatar-circle {
        width: 30px !important;
        height: 30px !important;
        border-radius: 50% !important;
        background: #1b2540 !important;
        color: #ffffff !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 12px !important;
        font-weight: 700 !important;
        flex-shrink: 0 !important;
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
        st.markdown(
            f"<h3 class='dp-topbar-baslik'>{ikon} {baslik}</h3>" if baslik else "<div></div>",
            unsafe_allow_html=True,
        )

        # 3. GRID SÜTUNU — avatar.
        avatar_html = ""
        if su_kullanici:
            avatar_html = (
                "<div style='display:flex;align-items:center;gap:8px;flex-shrink:0;justify-content:flex-end;'>"
                f"<div class='dp-avatar-circle'>{baslar}</div>"
                f"<span style='font-size:13px;color:#5b6478 !important;font-weight:600;white-space:nowrap;'>{su_kullanici}</span></div>"
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
    div[data-testid="stRadio"] label {
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
    div[data-testid="stRadio"] div[data-baseweb="radio"] {
        display: none !important;
    }
    div[data-testid="stRadio"] label p {
        font-size: 12.5px !important;
        font-weight: 600 !important;
        margin: 0 !important;
        white-space: nowrap !important;
        color: #5b6478 !important;
    }
    div[data-testid="stRadio"] label:has(div[aria-checked="true"]) {
        background: #1b2540 !important;
        border-color: #1b2540 !important;
    }
    div[data-testid="stRadio"] label:has(div[aria-checked="true"]) p {
        color: #ffffff !important;
    }
    div[data-testid="stWidgetLabel"] p {
        font-size: 11px !important;
        color: #8a8271 !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: .04em !important;
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
    div[class*="st-key-dp_filtre_toolbar_{key_prefix}"] div[data-testid="stWidgetLabel"] {{
        margin-bottom: 2px !important;
    }}
    div[class*="st-key-dp_filtre_toolbar_{key_prefix}"] div[data-testid="stHorizontalBlock"] {{
        gap: 0.5rem !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    with st.container(key=f"dp_filtre_toolbar_{key_prefix}"):
        fcol1, fcol2, fcol3 = st.columns([2, 2, 1])
        with fcol1:
            islem_secim = st.radio(
                "İşlem Tipi", ["Tümü", "Satılık", "Kiralık"],
                horizontal=True, key=f"dp_islem_filtre_{key_prefix}",
            )
        with fcol2:
            zaman_secim = st.radio(
                "Zaman Aralığı", ZAMAN_SECENEKLERI,
                horizontal=True, index=zaman_index, key=f"dp_zaman_filtre_{key_prefix}",
            )
        with fcol3:
            st.markdown(f"""
            <style>
            div[class*="st-key-dp_yenile_{key_prefix}"] button {{
                padding: 4px 10px !important;
                min-height: 30px !important;
                height: 30px !important;
                font-size: 13px !important;
                border-radius: 8px !important;
                border-color: #e3e1da !important;
                background: #ffffff !important;
                color: #5b6478 !important;
            }}
            </style>
            """, unsafe_allow_html=True)
            st.write("")
            if st.button("↻", key=f"dp_yenile_{key_prefix}", help="Yenile", use_container_width=True):
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
    )
    components.html(html_buf.getvalue().decode("utf-8"), height=1800, scrolling=True)


# ── ORTAK PANO EKRANI (Talep / Portföy) ─────────────────────────────────
# Danisman_Talep.py ve Danisman_Portfoy.py bu tek fonksiyonu çağırır —
# iki ayrı dosyada aynı kart/A-Z/filtre mantığını tekrarlamamak için.

def render_pano_ekrani(kayit_tipi):
    """kayit_tipi: 'talep' | 'portfoy'
    HER ZAMAN TÜM HAVUZU gösterir (Zeta + Startkey/mail birlikte) —
    kaynağa göre ayrı filtre yok, çünkü Zeta'ya özel görünüm zaten
    ayrı bir sayfada (Danisman_Paylasimlar.py)."""
    if kayit_tipi == "talep":
        veri_cek = talepleri_cek
        baslik = "Talep Panosu"
        ikon = "⬇️"
    else:
        veri_cek = portfoyleri_cek
        baslik = "Portföy Panosu"
        ikon = "🏘️"

    render_topbar("", geri_hedefi="pages/Danisman_Secim.py")

    # "+N yeni" rozetinden geldiyse, zaman filtresi varsayılan olarak
    # 'Son 24 saat' açık başlar — tek seferlik: sayfa render olduktan
    # sonra bayrak sıfırlanır ki kullanıcı manuel değiştirdiğinde tekrar
    # geri gelmesin.
    rozetten_geldi = st.session_state.pop("dp_sadece_yeni", False)
    zaman_varsayilan = "Son 7 gün" if rozetten_geldi else "Tümü"

    render_pano_icerik(
        veri_cek(), kayit_tipi, baslik, key_prefix=kayit_tipi,
        zaman_varsayilan=zaman_varsayilan,
    )

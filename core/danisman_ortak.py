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
    """Ana ekrandaki 'Son 24 saat' widget'ında iki farklı kapsam bilinçli
    olarak ayrı tutulur:
    - Özet CÜMLESİ (kaç yeni talep/portföy) → TÜM havuz (Zeta + Startkey/
      mail) — 'genel olarak ne kadar yeni var' sorusuna cevap verir, kart
      rozetleriyle ('+N yeni') aynı sayıyı göstermeli.
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
    """Tüm Danışman ekranlarının ortak üst barı: (opsiyonel) geri butonu +
    başlık solda, hamburger menü sağda. Hamburger içinde: Kendi Kayıtlarım,
    Zeta Paylaşımları, Çıkış Yap."""
    from core.auth import cikis_yap

    st.markdown("""
    <style>
    /* Radio butonlarının seçili rengi — Streamlit varsayılan kırmızısı
       yerine Karma App navy'si */
    div[data-baseweb="radio"] div[aria-checked="true"] {
        background-color: #1b2540 !important;
        border-color: #1b2540 !important;
    }
    div[data-baseweb="radio"] div[aria-checked="true"] div {
        background-color: #1b2540 !important;
    }

    /* HEADER: hiçbir alt eleman kutu/gölge/arka plan taşımasın — kaynağı
       ne olursa olsun (Karma App'in genel temasından miras kalan bir
       kural da olabilir) zorla sıfırlıyoruz. Sadece dış wrapper'ın
       altında ince bir çizgi olacak (mockup: border-bottom). */
    div[class*="st-key-dp_topbar_wrap"],
    div[class*="st-key-dp_topbar_wrap"] *,
    div[class*="st-key-dp_topbar_wrap"] [data-testid="stVerticalBlockBorderWrapper"] {
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }
    div[class*="st-key-dp_topbar_wrap"] {
        border-bottom: 1px solid #ecebe5 !important;
        padding-bottom: 14px !important;
        margin-bottom: 14px !important;
    }
    /* Mobilde de başlık ve hamburger AYNI satırda kalsın — Streamlit
       dar ekranda columns'ı varsayılan olarak alt alta yığar, bunu
       zorla engelliyoruz. */
    div[class*="st-key-dp_topbar_wrap"] [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        align-items: flex-start !important;
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
        col_baslik, col_menu = st.columns([6, 1])
        with col_baslik:
            if geri_hedefi:
                if st.button("← Panoya Dön", key="dp_geri_btn"):
                    st.switch_page(geri_hedefi)
            baslik_metni = f"{ikon} {baslik}" if ikon else baslik
            st.markdown(f"### {baslik_metni}")
            if su_kullanici:
                st.markdown(
                    "<div style='display:flex;align-items:center;gap:8px;margin-top:2px;'>"
                    f"<div style='width:24px;height:24px;border-radius:50%;background:#1b2540;"
                    "color:#fff;display:flex;align-items:center;justify-content:center;"
                    f"font-size:11px;font-weight:700;flex-shrink:0;'>{baslar}</div>"
                    f"<span style='font-size:13px;color:#5b6478;font-weight:600;'>{su_kullanici}</span></div>",
                    unsafe_allow_html=True,
                )
        with col_menu:
            # NOT: st.popover'ı önceden bir st.container(key=...) ve özel CSS
            # ile sarmalamaya çalışmıştık — bu kombinasyon üst barın tamamen
            # bozulmasına yol açmıştı (başlık kayboldu, 'Çıkış Yap' popover
            # dışında göründü). Bu sefer dış wrapper (dp_topbar_wrap) ayrı
            # tutuluyor, popover'ın kendisi hâlâ sade/doğrudan kullanılıyor.
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
                    st.switch_page("pages/Danisman_Giris.py")


def hide_sidebar_css():
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    [data-testid="stHeader"] { display: none !important; }

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

    /* Kartlar / bordered container'lar — beyaz yüzey, sıcak açık gri
       kenarlık, çok hafif gölge, yuvarlak köşe (mockup: 12-14px —
       Streamlit varsayılanı 8px, daha sert duruyordu).
       ÖNEMLİ: Bilerek SADECE bizim açıkça key verdiğimiz kartları
       hedefliyoruz (blanket `div[data-testid="stVerticalBlockBorderWrapper"]`
       seçicisi kullanmıyoruz) — o blanket kural, Streamlit'in popover
       bileşeninin kendi iç yapısını da boyayıp header'ın yanında
       istenmeyen bir kutu/gölge oluşturuyordu. */
    div[class*="st-key-dp_kart_talep"] div[data-testid="stVerticalBlockBorderWrapper"],
    div[class*="st-key-dp_kart_portfoy"] div[data-testid="stVerticalBlockBorderWrapper"],
    div[class*="st-key-dp_activity_box"] div[data-testid="stVerticalBlockBorderWrapper"] {
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

    /* İç ayırıcı çizgiler (st.divider) — açık, sıcak gri */
    .stApp hr {
        border-color: #ecebe5 !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ── ORTAK PANO EKRANI (Talep / Portföy) ─────────────────────────────────
# Danisman_Talep.py ve Danisman_Portfoy.py bu tek fonksiyonu çağırır —
# iki ayrı dosyada aynı kart/A-Z/filtre mantığını tekrarlamamak için.

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

    fcol1, fcol2 = st.columns([1, 1])
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

    if st.button("🔄 Yenile", key=f"dp_yenile_{key_prefix}"):
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

    render_topbar(baslik, ikon=ikon, geri_hedefi="pages/Danisman_Secim.py")

    # "+N yeni" rozetinden geldiyse, zaman filtresi varsayılan olarak
    # 'Son 24 saat' açık başlar — tek seferlik: sayfa render olduktan
    # sonra bayrak sıfırlanır ki kullanıcı manuel değiştirdiğinde tekrar
    # geri gelmesin.
    rozetten_geldi = st.session_state.pop("dp_sadece_yeni", False)
    zaman_varsayilan = "Son 24 saat" if rozetten_geldi else "Tümü"

    render_pano_icerik(
        veri_cek(), kayit_tipi, baslik, key_prefix=kayit_tipi,
        zaman_varsayilan=zaman_varsayilan,
    )

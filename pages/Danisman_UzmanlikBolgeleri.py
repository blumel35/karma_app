"""
pages/Danisman_UzmanlikBolgeleri.py

Uzmanlık Bölgelerim ekranı — "Favori Listem"in COĞRAFİ kardeşi. Danışman
en fazla 5 ilçe seçip, Talep/Portföy havuzunu kendi ilgi alanına göre
daraltabiliyor ("28 ilçelik kalabalık yerine sadece Karşıyaka'yı takip
ediyorum" senaryosu, 09.08.2026'da netleşen ihtiyaç).

BİLİNÇLİ OLARAK AYRI BİR AKIŞ — Talep/Portföy Panosu'nun içine bir
filtre katmanı olarak eklenmedi, çünkü o sayfalarda zaten birden fazla
filtre katmanı birbirini eziyordu (08.08.2026 regresyon turu). Yeni bir
katman daha eklemek yerine, Favoriler ile birebir aynı iskelet (sekmeli,
kendi filtre toolbar'ı, kart görünümü) kullanan bağımsız bir sayfa.

Kart tasarımı diğer panolarla BİREBİR AYNI (pano_html_olustur) — sadece
beslenen liste, tüm kayıtlar yerine seçili ilçelerdeki kayıtlarla sınırlı.
"""

import streamlit as st
import streamlit.components.v1 as components

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.pano_export import pano_html_olustur
from core.danisman_ortak import (
    talepleri_cek, portfoyleri_cek, islem_tipi_filtrele,
    favorileri_cek, su_anki_danisman, supabase_anon_secrets, IZMIR_ILCELERI,
    uzmanlik_bolgelerini_cek, uzmanlik_bolgelerini_kaydet, uzmanlik_bolgesi_filtrele,
    render_topbar, hide_sidebar_css, _inject_filtre_pill_css,
)

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Uzmanlık Bölgelerim", ikon="📍", geri_hedefi="pages/Danisman_Secim.py")

su_kullanici = su_anki_danisman()
mevcut_kayitlar = uzmanlik_bolgelerini_cek(su_kullanici)
mevcut_ilceler = [k["ilce"] for k in mevcut_kayitlar]

# ── İLÇE SEÇİM ALANI ─────────────────────────────────────────────────
# Hiç seçim yoksa açık başlar (kullanıcıyı doğrudan seçime yönlendirir),
# seçim varsa kapalı başlar (sayfa açılışında hemen kayıtlara odaklanır).
with st.expander(
    f"📍 İlçelerini seç (en fazla 5) — şu an {len(mevcut_ilceler)} seçili",
    expanded=not mevcut_ilceler,
):
    secim = st.multiselect(
        "Uzmanlık bölgelerin",
        options=IZMIR_ILCELERI,
        default=mevcut_ilceler,
        max_selections=5,
        key="ub_secim",
        label_visibility="collapsed",
        placeholder="İlçe seç (en fazla 5)...",
    )
    if st.button("Kaydet", key="ub_kaydet", type="primary"):
        uzmanlik_bolgelerini_kaydet(secim)
        st.success("Uzmanlık bölgelerin kaydedildi.")
        st.rerun()

if not mevcut_ilceler:
    st.info("Henüz uzmanlık bölgesi seçmedin — yukarıdan en fazla 5 ilçe seçip kaydet.")
    st.stop()

supabase_url, supabase_anon = supabase_anon_secrets()

bolge_talepler = uzmanlik_bolgesi_filtrele(talepleri_cek(), mevcut_ilceler)
bolge_portfoyler = uzmanlik_bolgesi_filtrele(portfoyleri_cek(), mevcut_ilceler)

sekme_talep, sekme_portfoy = st.tabs([
    f"Talepler ({len(bolge_talepler)})",
    f"Portföyler ({len(bolge_portfoyler)})",
])


def _bolge_sekme_icerik(havuz, kayit_tipi, key_prefix, baslik_iframe):
    """Her iki sekme de aynı çerçevesiz toolbar + filtre mantığını
    paylaşır — Danisman_Favoriler.py'deki aynı desen."""
    _inject_filtre_pill_css()
    st.markdown(f"""
    <style>
    div[class*="st-key-ub_filtre_toolbar_{key_prefix}"] {{
        margin-top: -8px !important;
        margin-bottom: -8px !important;
    }}
    div[class*="st-key-ub_filtre_toolbar_{key_prefix}"] div[data-testid="stHorizontalBlock"] {{
        gap: 0.5rem !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    with st.container(key=f"ub_filtre_toolbar_{key_prefix}"):
        fcol1, fcol2 = st.columns([4, 1])
        with fcol1:
            islem_secim = st.radio(
                "İşlem Tipi", ["Tümü", "Satılık", "Kiralık"],
                horizontal=True, key=f"ub_islem_{key_prefix}",
                label_visibility="collapsed",
            )
        with fcol2:
            st.markdown(f"""
            <style>
            div[class*="st-key-ub_yenile_{key_prefix}"] button {{
                padding: 4px 10px !important; min-height: 30px !important; height: 30px !important;
                font-size: 13px !important; border-radius: 8px !important;
                border-color: #e3e1da !important; background: #ffffff !important; color: #5b6478 !important;
            }}
            </style>
            """, unsafe_allow_html=True)
            if st.button("↻", key=f"ub_yenile_{key_prefix}", help="Yenile", use_container_width=True):
                talepleri_cek.clear()
                portfoyleri_cek.clear()
                st.rerun()

    kayitlar = islem_tipi_filtrele(havuz, islem_secim)
    if not kayitlar:
        st.info("Bu filtrede uzmanlık bölgelerinde kayıt yok.")
        return

    # Favori durumu (⭐) diğer panolarla tutarlı kalsın diye GERÇEK
    # favori setini çekiyoruz — boş bir set geçmek, burada favorilenmiş
    # bir kaydın yıldızını yanlışlıkla boş göstermesine sebep olurdu.
    try:
        favori_kayitlari = favorileri_cek(su_kullanici)
    except Exception:
        favori_kayitlari = []
    favori_set = {(f["kaynak_tablo"], f["kayit_id"]) for f in favori_kayitlari}

    html_buf = pano_html_olustur(
        kayitlar, baslik_iframe, kayit_tipi=kayit_tipi,
        favori_destekli=True, favori_set=favori_set,
        supabase_url=supabase_url, supabase_anon_key=supabase_anon,
        mevcut_kullanici=su_kullanici,
    )
    components.html(html_buf.getvalue().decode("utf-8"), height=1800, scrolling=True)


with sekme_talep:
    _bolge_sekme_icerik(bolge_talepler, "talep", "ub_talep", "Uzmanlık Bölgem Talepleri")

with sekme_portfoy:
    _bolge_sekme_icerik(bolge_portfoyler, "portfoy", "ub_portfoy", "Uzmanlık Bölgem Portföyleri")

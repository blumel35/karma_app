"""
pages/Danisman_Favoriler.py

Favori Listem ekranı. Eski Danisman_Pano.py içindeki "Takip Listem"
sekmesinin ayrı bir sayfaya çıkarılmış hali — isim "Favori Listem" olarak
sabitlendi (mockup'ta da bu isimle netleşti).

Kart tasarımı diğer panolarla BİREBİR AYNI (pano_html_olustur) — sadece
beslenen liste, tüm kayıtlar yerine favorilenmiş kayıtlarla sınırlı.
"""

import streamlit as st
import streamlit.components.v1 as components

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.pano_export import pano_html_olustur
from core.danisman_ortak import (
    talepleri_cek, portfoyleri_cek, kaynak_filtrele, islem_tipi_filtrele,
    favorileri_cek, su_anki_danisman, supabase_anon_secrets,
    render_topbar, hide_sidebar_css,
)

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Favori Listem", ikon="⭐", geri_hedefi="pages/Danisman_Secim.py")

su_kullanici = su_anki_danisman()

# KOMPAKT FİLTRE GÖRÜNÜMÜ (bu tur revizyonu) — Talep/Portföy panolarındaki
# (core/danisman_ortak.py → render_pano_icerik) aynı pill-buton CSS deseni,
# aynı kompakt kutuya taşındı. Etkileşim mantığına (st.radio state'i)
# dokunulmadı — sadece görünüm.
st.markdown("""
<style>
div[class*="st-key-dp_favori_filtre_box"] div[data-testid="stRadio"] > label { display: none !important; }
div[class*="st-key-dp_favori_filtre_box"] div[data-testid="stRadio"] div[role="radiogroup"] { gap: 6px !important; }
div[class*="st-key-dp_favori_filtre_box"] div[data-testid="stRadio"] div[role="radiogroup"] > label {
    display: inline-flex !important; align-items: center !important;
    border: 1px solid #e3e1da !important; border-radius: 999px !important;
    padding: 4px 12px !important; margin: 0 !important;
    min-height: unset !important; background: #ffffff !important;
}
div[class*="st-key-dp_favori_filtre_box"] div[data-testid="stRadio"] div[role="radiogroup"] > label:has(div[aria-checked="true"]) {
    background: #1b2540 !important; border-color: #1b2540 !important;
}
div[class*="st-key-dp_favori_filtre_box"] div[data-testid="stRadio"] div[role="radiogroup"] > label:has(div[aria-checked="true"]) p {
    color: #ffffff !important;
}
div[class*="st-key-dp_favori_filtre_box"] div[data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child {
    display: none !important;
}
div[class*="st-key-dp_favori_filtre_box"] div[data-testid="stRadio"] p {
    font-size: 12.5px !important; font-weight: 600 !important; margin: 0 !important; white-space: nowrap !important;
}
div[class*="st-key-dp_favori_filtre_box"] div[data-testid="stWidgetLabel"] p {
    font-size: 11px !important; color: #8a8271 !important; font-weight: 600 !important;
    text-transform: uppercase !important; letter-spacing: .04em !important;
}
div[class*="st-key-dp_favori_yenile"] button {
    padding: 4px 12px !important; min-height: 30px !important; height: 30px !important;
    font-size: 12.5px !important; border-radius: 8px !important;
    border-color: #e3e1da !important; background: #ffffff !important; color: #5b6478 !important;
}
div[class*="st-key-dp_favori_filtre_box"] { padding: 10px 14px !important; }
</style>
""", unsafe_allow_html=True)

with st.container(border=True, key="dp_favori_filtre_box"):
    fcol1, fcol2, fcol3 = st.columns([2, 2, 1])
    with fcol1:
        kaynak_secim = st.radio("İlan Kaynağı", ["Tümü", "Zeta", "Startkey"], horizontal=True, key="df_kaynak")
    with fcol2:
        islem_secim = st.radio("İşlem Tipi", ["Tümü", "Satılık", "Kiralık"], horizontal=True, key="df_islem")
    with fcol3:
        st.write("")
        if st.button("🔄 Yenile", key="dp_favori_yenile", use_container_width=True):
            favorileri_cek.clear()
            st.rerun()

favori_kayitlari = favorileri_cek(su_kullanici)

if not favori_kayitlari:
    st.info("Henüz favori eklemedin — panodaki kartların üzerindeki ☆ yıldıza tıklayarak ekleyebilirsin.")
else:
    favori_talep_idler = {f["kayit_id"] for f in favori_kayitlari if f["kaynak_tablo"] == "alici_talepleri"}
    favori_portfoy_idler = {f["kayit_id"] for f in favori_kayitlari if f["kaynak_tablo"] == "portfoyler"}
    favori_set = {(f["kaynak_tablo"], f["kayit_id"]) for f in favori_kayitlari}
    supabase_url, supabase_anon = supabase_anon_secrets()

    takip_talepler = islem_tipi_filtrele(
        kaynak_filtrele([v for v in talepleri_cek() if v["id"] in favori_talep_idler], kaynak_secim),
        islem_secim,
    )
    takip_portfoyler = islem_tipi_filtrele(
        kaynak_filtrele([v for v in portfoyleri_cek() if v["id"] in favori_portfoy_idler], kaynak_secim),
        islem_secim,
    )

    if not takip_talepler and not takip_portfoyler:
        st.info("Bu filtrede favori listende kayıt yok.")

    if takip_talepler:
        html_buf = pano_html_olustur(
            takip_talepler, "Favori Taleplerim", kayit_tipi="talep",
            favori_destekli=True, favori_set=favori_set,
            supabase_url=supabase_url, supabase_anon_key=supabase_anon,
            mevcut_kullanici=su_kullanici,
        )
        components.html(html_buf.getvalue().decode("utf-8"), height=1200, scrolling=True)

    if takip_portfoyler:
        html_buf = pano_html_olustur(
            takip_portfoyler, "Favori Portföylerim", kayit_tipi="portfoy",
            favori_destekli=True, favori_set=favori_set,
            supabase_url=supabase_url, supabase_anon_key=supabase_anon,
            mevcut_kullanici=su_kullanici,
        )
        components.html(html_buf.getvalue().decode("utf-8"), height=1200, scrolling=True)

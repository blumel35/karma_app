"""
pages/Danisman_Secim.py

Danışman Panosu'nun giriş sonrası ANA ekranı (2026-08 revizyonu).

Önceki mimaride (Danisman_Pano.py) tek sayfada form + kayıtlarım +
filtreler + 3 sekme birlikteydi — bu sayfa onun yerine, kullanıcının
ilk gördüğü şeyin sade bir "nereye gitmek istiyorum" seçimi olmasını
sağlıyor:

- İki büyük kart: Talep Panosu / Portföy Panosu (ana sayı + tıklanabilir
  "+N yeni" rozeti — rozete tıklayınca ilgili panoya SADECE SON 24
  SAATTEKİ kayıtlar filtrelenmiş halde açılır).
- Favori Listem butonu.
- "+ Ekle" butonu — ortak dialog (core.danisman_ortak.ekle_dialog),
  Talep Panosu / Portföy Panosu ekranlarının hiçbirinde ayrıca YOK.
- "Son 24 saat" aktivite özeti (kim ne ekledi, kısa liste + tüm
  paylaşımlar linki).
- Sağ üstte hamburger menü: Kendi Kayıtlarım, Zeta Paylaşımları, Çıkış Yap.
"""

import streamlit as st

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.danisman_ortak import (
    talepleri_cek, portfoyleri_cek, kaynak_filtrele, son_24_saat_filtrele,
    ekle_dialog, render_activity_bar, render_topbar, hide_sidebar_css,
)

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()

st.markdown("""
<style>
/* Seçim kartları — Karma App navy/gold kimliğine bağlı, sade beyaz kart */
div[class*="st-key-dp_kart_talep"] > div[data-testid="stVerticalBlockBorderWrapper"] {
    border-top: 3px solid #1b2540 !important;
}
div[class*="st-key-dp_kart_portfoy"] > div[data-testid="stVerticalBlockBorderWrapper"] {
    border-top: 3px solid #b8892f !important;
}
</style>
""", unsafe_allow_html=True)

render_topbar("Danışman Panosu")
st.caption("Talep ve portföyleri canlı takip edin, hızlıca yeni kayıt ekleyin.")
st.write("")

talepler = talepleri_cek()
portfoyler = portfoyleri_cek()
talep_yeni = son_24_saat_filtrele(kaynak_filtrele(talepler, "Zeta"))
portfoy_yeni = son_24_saat_filtrele(kaynak_filtrele(portfoyler, "Zeta"))

col_talep, col_portfoy = st.columns(2, gap="medium")

with col_talep:
    with st.container(border=True, key="dp_kart_talep"):
        st.markdown(":material/download: **Talep Panosu**")
        st.caption("Alıcı taleplerini görüntüle ve yönet")
        st.markdown(f"### {len(talepler)} aktif talep")
        if talep_yeni:
            if st.button(f"🟢 +{len(talep_yeni)} yeni", key="dp_talep_yeni_rozet", use_container_width=True):
                st.session_state["dp_sadece_yeni"] = True
                st.switch_page("pages/Danisman_Talep.py")
        if st.button("Talep Panosuna Git →", key="dp_talep_git", type="primary", use_container_width=True):
            st.session_state["dp_sadece_yeni"] = False
            st.switch_page("pages/Danisman_Talep.py")

with col_portfoy:
    with st.container(border=True, key="dp_kart_portfoy"):
        st.markdown(":material/home_work: **Portföy Panosu**")
        st.caption("Portföyleri görüntüle ve yönet")
        st.markdown(f"### {len(portfoyler)} aktif portföy")
        if portfoy_yeni:
            if st.button(f"🟠 +{len(portfoy_yeni)} yeni", key="dp_portfoy_yeni_rozet", use_container_width=True):
                st.session_state["dp_sadece_yeni"] = True
                st.switch_page("pages/Danisman_Portfoy.py")
        if st.button("Portföy Panosuna Git →", key="dp_portfoy_git", type="primary", use_container_width=True):
            st.session_state["dp_sadece_yeni"] = False
            st.switch_page("pages/Danisman_Portfoy.py")

st.write("")

col_favori, col_ekle = st.columns([1, 1])
with col_favori:
    if st.button(":material/star: Favori Listem", key="dp_favori_btn", use_container_width=True):
        st.switch_page("pages/Danisman_Favoriler.py")
with col_ekle:
    if st.button(":material/add: Ekle", key="dp_ekle_btn", use_container_width=True):
        ekle_dialog()

st.write("")
render_activity_bar()

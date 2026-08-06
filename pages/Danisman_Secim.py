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
    talepleri_cek, portfoyleri_cek, son_24_saat_filtrele,
    ekle_dialog, render_activity_bar, render_topbar, hide_sidebar_css,
)

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()

st.markdown("""
<style>
div[class*="st-key-dp_talep_git"] button,
div[class*="st-key-dp_portfoy_git"] button {
    background-color: #1b2540 !important;
    border-color: #1b2540 !important;
    color: #ffffff !important;
}
div[class*="st-key-dp_talep_git"] button:hover,
div[class*="st-key-dp_portfoy_git"] button:hover {
    background-color: #28345a !important;
    border-color: #28345a !important;
    color: #ffffff !important;
}
.dp-icon-box {
    width: 38px; height: 38px; border-radius: 9px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; margin-bottom: 8px;
}
.dp-icon-box.talep { background: rgba(27,37,64,.08); color: #1b2540; }
.dp-icon-box.portfoy { background: rgba(184,137,47,.12); color: #b8892f; }
.dp-stat-row {
    display: flex; align-items: center; justify-content: space-between;
    gap: 8px; padding-top: 10px; margin-top: 8px;
    border-top: 1px solid #ecebe5;
}
.dp-stat-num { font-size: 22px; font-weight: 800; color: #1b2540; }
.dp-stat-num.portfoy { color: #b8892f; }
</style>
""", unsafe_allow_html=True)

render_topbar("Danışman Panosu")
st.caption("Talep ve portföyleri canlı takip edin, hızlıca yeni kayıt ekleyin.")
st.write("")

talepler = talepleri_cek()
portfoyler = portfoyleri_cek()
# "+N yeni" rozeti ve sayaçlar TÜM KAYNAKLARI kapsar (Zeta + Startkey/mail
# birlikte) — Talep/Portföy Panosu zaten her zaman tüm havuzu gösteriyor,
# bu yüzden rozet de aynı kapsamda tutarlı olmalı. Yalnızca Zeta'ya özel
# görünüm için: hamburger menü → Zeta Paylaşımları.
talep_yeni = son_24_saat_filtrele(talepler)
portfoy_yeni = son_24_saat_filtrele(portfoyler)

col_talep, col_portfoy = st.columns(2, gap="medium")

with col_talep:
    with st.container(border=True, key="dp_kart_talep"):
        st.markdown(
            "<div style='height:4px;background:#1b2540;border-radius:3px;margin:-1px 0 12px 0;'></div>"
            "<div class='dp-icon-box talep'>⬇️</div>",
            unsafe_allow_html=True,
        )
        st.markdown("**Talep Panosu**")
        st.caption("Alıcı taleplerini görüntüle ve yönet")

        stat_col, badge_col = st.columns([2, 1])
        with stat_col:
            st.markdown(f"<div class='dp-stat-row'><span class='dp-stat-num'>{len(talepler)}</span>"
                        f"<span style='color:#5b6478;font-size:13px;'>aktif talep</span></div>",
                        unsafe_allow_html=True)
        with badge_col:
            if talep_yeni:
                st.write("")
                if st.button(f"🟢 +{len(talep_yeni)} yeni", key="dp_talep_yeni_rozet", use_container_width=True):
                    st.session_state["dp_sadece_yeni"] = True
                    st.switch_page("pages/Danisman_Talep.py")

        st.write("")
        if st.button("Talep Panosuna Git →", key="dp_talep_git", type="primary", use_container_width=True):
            st.session_state["dp_sadece_yeni"] = False
            st.switch_page("pages/Danisman_Talep.py")

with col_portfoy:
    with st.container(border=True, key="dp_kart_portfoy"):
        st.markdown(
            "<div style='height:4px;background:#b8892f;border-radius:3px;margin:-1px 0 12px 0;'></div>"
            "<div class='dp-icon-box portfoy'>🏠</div>",
            unsafe_allow_html=True,
        )
        st.markdown("**Portföy Panosu**")
        st.caption("Portföyleri görüntüle ve yönet")

        stat_col, badge_col = st.columns([2, 1])
        with stat_col:
            st.markdown(f"<div class='dp-stat-row'><span class='dp-stat-num portfoy'>{len(portfoyler)}</span>"
                        f"<span style='color:#5b6478;font-size:13px;'>aktif portföy</span></div>",
                        unsafe_allow_html=True)
        with badge_col:
            if portfoy_yeni:
                st.write("")
                if st.button(f"🟠 +{len(portfoy_yeni)} yeni", key="dp_portfoy_yeni_rozet", use_container_width=True):
                    st.session_state["dp_sadece_yeni"] = True
                    st.switch_page("pages/Danisman_Portfoy.py")

        st.write("")
        if st.button("Portföy Panosuna Git →", key="dp_portfoy_git", type="primary", use_container_width=True):
            st.session_state["dp_sadece_yeni"] = False
            st.switch_page("pages/Danisman_Portfoy.py")

st.write("")

col_favori, col_ekle = st.columns([1, 1])
with col_favori:
    if st.button("⭐ Favori Listem", key="dp_favori_btn", use_container_width=True):
        st.switch_page("pages/Danisman_Favoriler.py")
with col_ekle:
    if st.button("➕ Ekle", key="dp_ekle_btn", use_container_width=True):
        ekle_dialog()

st.write("")
render_activity_bar()

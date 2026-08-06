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

# NOT: Önceki sürümde kart üst kenarındaki renkli çizgi, Streamlit'in
# internal container testid'ine (stVerticalBlockBorderWrapper) bağlı bir
# CSS seçicisiyle uygulanmaya çalışılmıştı — bu, Streamlit sürümüne göre
# DOM yapısı değiştiği için render olmadı. Bunun yerine, kartın İÇİNDE,
# ilk eleman olarak düz bir renkli <div> çubuğu ekleniyor (aşağıda) —
# Streamlit'in internal yapısına bağımlı değil, her sürümde çalışır.
#
# Buton rengi: "Talep Panosuna Git" / "Portföy Panosuna Git" butonları
# type="primary" ile Streamlit'in varsayılan temasını (kırmızı) alıyordu.
# Karma App navy kimliğine bağlamak için, buton key'i üzerinden CSS ile
# rengi zorluyoruz — bu, kodda zaten kanıtlanmış bir desen (bkz. eski
# dp_toolbar_row seçicisi).
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
            "<div style='height:4px;background:#1b2540;border-radius:3px;margin:-1px 0 14px 0;'></div>",
            unsafe_allow_html=True,
        )
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
        st.markdown(
            "<div style='height:4px;background:#b8892f;border-radius:3px;margin:-1px 0 14px 0;'></div>",
            unsafe_allow_html=True,
        )
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

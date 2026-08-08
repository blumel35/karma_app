"""
pages/Danisman_Kayitlarim.py

Kendi Kayıtlarım ekranı — eski Danisman_Pano.py içindeki "Kayıtlarım"
expander'ının ayrı sayfaya çıkarılmış hali. Artık ana ekranda değil,
hamburger menüden erişiliyor (düşük frekanslı bir yönetim eylemi).

GÜVENLİK SINIRI (değişmedi): yalnız "kaynak" alanı Zeta değerlerinden
biri (Danışman Panosu'ndan girilmiş) VE "talep_eden_danisan" şu an
giriş yapmış kullanıcıyla eşleşen kayıtlar silinebilir. Startkey/mail
kaynaklı hiçbir kayıda bu ekrandan asla dokunulamaz.
"""

import streamlit as st

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.danisman_ortak import (
    talepleri_cek, portfoyleri_cek, kaynak_filtrele, su_anki_danisman,
    kayit_sil, render_topbar, hide_sidebar_css,
)

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Kendi Kayıtlarım", ikon="📂", geri_hedefi="pages/Danisman_Secim.py")

# KART GÖRÜNÜMÜ (bu tur revizyonu): önceki hâlde her kayıt çıplak bir
# st.columns satırıydı, hiçbir çerçeve/kart içinde değildi — "Sil" butonu
# görsel olarak kayıttan kopuk duruyordu. Şimdi her kayıt kendi bordered
# container'ında, diğer danışman ekranlarındaki (Talep/Portföy kartları)
# aynı görsel dille (beyaz kart, ince kenarlık) — Sil butonu artık aynı
# kartın içinde, kayıtla fiziksel olarak bütünleşik.
st.markdown("""
<style>
div[class*="st-key-dp_kayit_card_"] {
    padding: 14px 16px !important;
    margin-bottom: 10px !important;
}
div[class*="st-key-dp_kayit_sil_"] button {
    border-color: #e3e1da !important;
    color: #b3261e !important;
    font-size: 12.5px !important;
}
</style>
""", unsafe_allow_html=True)

su_kullanici = su_anki_danisman()

kendi_talepler = [
    v for v in kaynak_filtrele(talepleri_cek(), "Zeta")
    if v.get("talep_eden_danisan") == su_kullanici
]
kendi_portfoyler = [
    v for v in kaynak_filtrele(portfoyleri_cek(), "Zeta")
    if v.get("talep_eden_danisan") == su_kullanici
]

if not kendi_talepler and not kendi_portfoyler:
    st.info("Henüz Danışman Panosu'ndan eklediğin bir kayıt yok.")

if kendi_talepler:
    st.markdown("##### 📥 Taleplerim")
    for v in kendi_talepler:
        with st.container(border=True, key=f"dp_kayit_card_talep_{v['id']}"):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"**Talep:** {v.get('ozet', '')}")
            with c2:
                if st.button("Sil", key=f"dp_kayit_sil_talep_{v['id']}", use_container_width=True):
                    kayit_sil("alici_talepleri", v["id"])
                    talepleri_cek.clear()
                    st.rerun()

if kendi_portfoyler:
    st.markdown("##### 🏘️ Portföylerim")
    for v in kendi_portfoyler:
        with st.container(border=True, key=f"dp_kayit_card_portfoy_{v['id']}"):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"**Portföy:** {v.get('ozet', '')}")
            with c2:
                if st.button("Sil", key=f"dp_kayit_sil_portfoy_{v['id']}", use_container_width=True):
                    kayit_sil("portfoyler", v["id"])
                    portfoyleri_cek.clear()
                    st.rerun()

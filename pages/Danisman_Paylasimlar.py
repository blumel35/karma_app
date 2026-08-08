"""
pages/Danisman_Paylasimlar.py

Zeta Paylaşımları ekranı — ana ekrandaki "Son 24 saat" özet çubuğundaki
"Tüm Paylaşımlar" linkinin gittiği yer. Hamburger menüden de erişilebilir.

GÖRSEL: Talep/Portföy Panosu ile BİREBİR AYNI çerçeve (core.danisman_ortak.
render_pano_icerik) — filtre (İşlem Tipi + Zaman Aralığı), Yenile butonu,
kart + A-Z navigasyon. Sekmeli: Talep / Portföy. TEK FARK: kayıt havuzu
tüm Startkey değil, SADECE ZETA kaynaklı kayıtlarla sınırlı — ölçeklenebilirlik
ve "ekibim ne paylaştı" sorusuna özel cevap için bilinçli sınır.
"""

import streamlit as st

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.danisman_ortak import (
    talepleri_cek, portfoyleri_cek, kaynak_filtrele,
    render_pano_icerik, render_topbar, hide_sidebar_css,
)

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Zeta Paylaşımları", ikon="👥", geri_hedefi="pages/Danisman_Secim.py")
st.caption("Sadece Zeta ofisi kaynaklı kayıtlar — filtre ve zaman aralığıyla daraltabilirsin.")

zeta_talep_havuzu = kaynak_filtrele(talepleri_cek(), "Zeta")
zeta_portfoy_havuzu = kaynak_filtrele(portfoyleri_cek(), "Zeta")

sekme_talep, sekme_portfoy = st.tabs([
    f"Talepler ({len(zeta_talep_havuzu)})",
    f"Portföyler ({len(zeta_portfoy_havuzu)})",
])

with sekme_talep:
    render_pano_icerik(
        zeta_talep_havuzu, "talep", "Zeta Talepleri",
        key_prefix="zeta_talep", zaman_varsayilan="Tümü",
    )

with sekme_portfoy:
    render_pano_icerik(
        zeta_portfoy_havuzu, "portfoy", "Zeta Portföyleri",
        key_prefix="zeta_portfoy", zaman_varsayilan="Tümü",
    )

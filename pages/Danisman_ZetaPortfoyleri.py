"""
pages/Danisman_ZetaPortfoyleri.py

Zeta Portföyleri ekranı — Revy'den senkronize, portallarda (sahibinden vb.)
FİİLEN YAYINLANAN, tüm ofisin resmi ilanları. Hamburger menüden erişilir.

GÖRSEL: Talep/Portföy Panosu ile BİREBİR AYNI çerçeve (render_pano_icerik)
— tek fark kayıt havuzu: kaynak zeta1/zeta2 (ILAN_PORTAL_DEGERLERI) ile
sınırlı. Talep sekmesi YOK — portal ilanları kavramsal olarak her zaman
portföy, alıcı talebi değil.

AYRIM (önemli, karıştırılmamalı — 12.08.2026'da netleşti):
- "Zeta Paylaşımları" (Danisman_Paylasimlar.py) → GD'lerin ELLE girdiği,
  ilan sitelerinde OLMAYAN ofis-içi paylaşımlar (kaynak zeta/ofis).
- "Zeta Portföyleri" (BU SAYFA) → Revy'den senkronize, portallarda
  YAYINLANAN resmi ilanlar (kaynak zeta1/zeta2). İkisi bağımsız, birbirini
  içermiyor.
"""

import streamlit as st

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.danisman_ortak import (
    portfoyleri_cek, render_pano_icerik, render_topbar, hide_sidebar_css,
    ILAN_PORTAL_DEGERLERI,
)

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Zeta Portföyleri", ikon="📢", geri_hedefi="pages/Danisman_Secim.py")
st.caption("Portallarda (sahibinden vb.) yayınlanan, tüm ofisin aktif resmi ilanları.")

zeta_ilan_havuzu = [
    v for v in portfoyleri_cek()
    if str(v.get("kaynak") or "").strip().lower() in ILAN_PORTAL_DEGERLERI
]

render_pano_icerik(
    zeta_ilan_havuzu, "portfoy", "Zeta Portföyleri",
    key_prefix="zeta_ilan", zaman_varsayilan="Tümü",
)

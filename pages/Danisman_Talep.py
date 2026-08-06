"""
pages/Danisman_Talep.py

Talep Panosu ekranı. "Ekle" ve "Kendi Kayıtlarım" burada YOK — ana ekrana
(Danisman_Secim.py) ve hamburger menüye taşındı. Gerçek render mantığı
core.danisman_ortak.render_pano_ekrani içinde — Danisman_Portfoy.py ile
kod tekrarı olmasın diye.
"""

import streamlit as st

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.danisman_ortak import render_pano_ekrani, hide_sidebar_css

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_pano_ekrani("talep")

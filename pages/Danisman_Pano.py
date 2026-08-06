"""
pages/Danisman_Pano.py

ESKİ giriş noktası — geriye dönük uyumluluk için tutuluyor (bu URL'e
işaret eden eski bir kısayol/bookmark varsa "Page not found" almasın).
Gerçek arayüz artık Danisman_Secim.py (ana seçim ekranı) ve oradan
açılan Danisman_Talep.py / Danisman_Portfoy.py / Danisman_Favoriler.py /
Danisman_Kayitlarim.py / Danisman_Paylasimlar.py sayfalarında yaşıyor.

Bu dosya SADECE yönlendirme yapar, kendi mantığı yoktur.
"""

import streamlit as st

st.switch_page("pages/Danisman_Secim.py")

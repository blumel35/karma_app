# core/yeni_ana_sayfa.py
# -*- coding: utf-8 -*-
"""
YENİ Danışman Panosu ana sayfası — İSKELET (Faz 0).

pages/Danisman_Secim.py bu modülü SADECE core.ozellik_erisim.ozellik_acik_mi
("yeni_ana_sayfa") True döndürürse çağırır. Diğer herkes eski ekranı görür.

Planlanan yapı (mockup v13): iki sayfa — "Ana sayfa" (mevcut ana ekran,
Telefon bildirimleri ve Startkey İlanları kaldırılmış, Son 24 saat
Bildirimlerim içinde) ve "Radarım" (Portföylerim / Taleplerim akışları).
Şimdilik sadece iskelet: sekme seçimi + yer tutucular.

Sekme seçimi st.tabs ile DEĞİL st.radio ile yapılıyor: st.tabs her
çalıştırmada TÜM sekmelerin kodunu çalıştırır, Radarım'ın ağır sorguları
ana sayfayı da yavaşlatırdı. Burada yalnızca seçili sayfa çizilecek.
"""

import streamlit as st

from core.danisman_ortak import hide_sidebar_css, render_topbar


def render_yeni_ana_sayfa():
    hide_sidebar_css()
    with st.container(border=True, key="dp_page_frame"):
        render_topbar("Danışman Panosu", eyebrow="Startkey Zeta")

        st.info(
            "🧪 Yeni arayüz (deneme) — bu ekranı yalnızca yetkili kullanıcılar "
            "görüyor. Eski ekranı görmek için adres sonuna ?eski=1 ekle."
        )

        sayfa = st.radio(
            "Sayfa",
            ["Ana sayfa", "Radarım"],
            horizontal=True,
            key="ya_sayfa",
            label_visibility="collapsed",
        )

        if sayfa == "Ana sayfa":
            st.caption("Ana sayfa içeriği bir sonraki adımda buraya taşınacak.")
        else:
            st.caption("Radarım (Portföylerim / Taleplerim akışları) sonraki adımlarda eklenecek.")

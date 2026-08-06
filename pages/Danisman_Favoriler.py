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

fcol1, fcol2 = st.columns(2)
with fcol1:
    kaynak_secim = st.radio("İlan Kaynağı", ["Tümü", "Zeta", "Startkey"], horizontal=True, key="df_kaynak")
with fcol2:
    islem_secim = st.radio("İşlem Tipi", ["Tümü", "Satılık", "Kiralık"], horizontal=True, key="df_islem")

if st.button("🔄 Yenile", key="df_yenile"):
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
        st.markdown("##### 📥 Favori Taleplerim")
        html_buf = pano_html_olustur(
            takip_talepler, "Favori Taleplerim", kayit_tipi="talep",
            favori_destekli=True, favori_set=favori_set,
            supabase_url=supabase_url, supabase_anon_key=supabase_anon,
            mevcut_kullanici=su_kullanici,
        )
        components.html(html_buf.getvalue().decode("utf-8"), height=1200, scrolling=True)

    if takip_portfoyler:
        st.markdown("##### 🏘️ Favori Portföylerim")
        html_buf = pano_html_olustur(
            takip_portfoyler, "Favori Portföylerim", kayit_tipi="portfoy",
            favori_destekli=True, favori_set=favori_set,
            supabase_url=supabase_url, supabase_anon_key=supabase_anon,
            mevcut_kullanici=su_kullanici,
        )
        components.html(html_buf.getvalue().decode("utf-8"), height=1200, scrolling=True)

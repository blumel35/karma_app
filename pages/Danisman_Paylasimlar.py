"""
pages/Danisman_Paylasimlar.py

Zeta Paylaşımları ekranı — ana ekrandaki "Son 24 saat" özet çubuğundaki
"Tüm Paylaşımlar" linkinin gittiği yer. Hamburger menüden de erişilebilir.

Son 24 saatle sınırlı değil — son 7 günün tüm Zeta kaynaklı talep/portföy
paylaşımlarını, kim/ne/ne zaman ekledi şeklinde listeler. Yalnızca kendi
ofisi (Zeta) kapsıyor, tüm Startkey ağını değil — ölçeklenebilirlik için
bilinçli sınır (bkz. core.danisman_ortak.son_24_saat_ozeti).
"""

import streamlit as st

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.danisman_ortak import (
    talepleri_cek, portfoyleri_cek, kaynak_filtrele, kayit_tarihi_dt,
    render_topbar, hide_sidebar_css,
)
from datetime import datetime, timezone, timedelta

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Zeta Paylaşımları", ikon=":material/groups:", geri_hedefi="pages/Danisman_Secim.py")
st.caption("Son 7 gün · sadece Zeta ofisi kaynaklı paylaşımlar")

esik = datetime.now(timezone.utc) - timedelta(days=7)

talepler = kaynak_filtrele(talepleri_cek(), "Zeta")
portfoyler = kaynak_filtrele(portfoyleri_cek(), "Zeta")

olaylar = []
for v in talepler:
    tarih = kayit_tarihi_dt(v.get("kayit_tarihi"))
    if tarih and tarih >= esik:
        olaylar.append({
            "danisman": v.get("talep_eden_danisan") or "Bilinmeyen",
            "eylem": "yeni bir talep girdi",
            "ozet": v.get("ozet", ""),
            "tarih": tarih,
        })
for v in portfoyler:
    tarih = kayit_tarihi_dt(v.get("kayit_tarihi"))
    if tarih and tarih >= esik:
        olaylar.append({
            "danisman": v.get("talep_eden_danisan") or "Bilinmeyen",
            "eylem": "yeni bir portföy paylaştı",
            "ozet": v.get("ozet", ""),
            "tarih": tarih,
        })

olaylar.sort(key=lambda o: o["tarih"], reverse=True)

if not olaylar:
    st.info("Son 7 günde Zeta ofisinden paylaşım yok.")
else:
    gun_gruplari = {}
    for o in olaylar:
        gun = o["tarih"].strftime("%d.%m.%Y")
        gun_gruplari.setdefault(gun, []).append(o)

    for gun, gun_olaylari in gun_gruplari.items():
        st.markdown(f"**{gun}**")
        for o in gun_olaylari:
            st.markdown(f"• **{o['danisman']}** {o['eylem']} — _{o['ozet']}_")
        st.write("")

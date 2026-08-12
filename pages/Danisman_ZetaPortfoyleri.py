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

# YENİ (13.08.2026): Bu sayfaya özel ek filtreler — render_pano_icerik'in
# paylaşılan İşlem Tipi/Zaman Aralığı filtresine EK olarak, sadece bu
# sayfada anlamlı olan Revy-özel alanlara göre. Paylaşılan çekirdek
# fonksiyona DOKUNULMADI — filtreleme burada, render_pano_icerik'e
# geçmeden ÖNCE, Python tarafında yapılıyor. Seçenekler HARDCODE
# edilmedi — havuzdaki gerçek verilerden dinamik olarak çıkarılıyor
# (örn. "asansörlü mü" filtresi EKLENMEDİ çünkü Revy export'unda böyle
# bir sütun hiç yok — "ilan yaşı" da AYRICA eklenmedi, gerçek veriyle
# doğrulandı: İlan Yayın Süresi ile birebir aynı metrik, tekrar olurdu).
#
# Mülk analizi için hedeflenen tam set: kat, site içinde mi, kullanım
# durumu (kiracılı/mülk sahibi oturuyor/boş), piyasada kalma süresi,
# m², fiyat.
def _sayisal_degerler(havuz, alan):
    degerler = []
    for v in havuz:
        try:
            degerler.append(float(v.get(alan)))
        except (TypeError, ValueError):
            continue
    return degerler


def _sayisal_slider(havuz, alan, etiket, anahtar, tam_sayi=True):
    """Havuzdaki gerçek min/max'a göre slider kurar. Kullanıcı slider'ı
    dokunmadan (varsayılan tam aralıkta) bırakırsa None döner — böylece
    bu alanı boş olan kayıtlar sessizce elenmez."""
    degerler = _sayisal_degerler(havuz, alan)
    if not degerler:
        st.caption(f"{etiket}: veri yok")
        return None
    d_min, d_max = min(degerler), max(degerler)
    if tam_sayi:
        d_min, d_max = int(d_min), int(d_max)
    if d_min == d_max:
        st.caption(f"{etiket}: tüm ilanlar {d_min:,.0f}".replace(",", "."))
        return None
    secim = st.slider(etiket, d_min, d_max, (d_min, d_max), key=anahtar)
    return None if secim == (d_min, d_max) else secim


with st.expander("Detaylı Filtreler (kat, site, kullanım, süre, m², fiyat)", expanded=False):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        kat_secenekleri = sorted({
            str(v.get("kat")) for v in zeta_ilan_havuzu
            if v.get("kat") not in (None, "", "None")
        })
        kat_secim = st.multiselect("Bulunduğu kat", kat_secenekleri, key="zeta_ilan_kat")
    with fc2:
        site_secim = st.radio(
            "Site içerisinde", ["Tümü", "Evet", "Hayır"],
            horizontal=True, key="zeta_ilan_site",
        )
    with fc3:
        kullanim_secenekleri = sorted({
            str(v.get("kullanim_durumu")) for v in zeta_ilan_havuzu
            if v.get("kullanim_durumu") not in (None, "", "None")
        })
        kullanim_secim = st.multiselect(
            "Kullanım durumu (kiracılı / mülk sahibi / boş)",
            kullanim_secenekleri, key="zeta_ilan_kullanim",
        )

    fc4, fc5, fc6 = st.columns(3)
    with fc4:
        sure_araligi = _sayisal_slider(
            zeta_ilan_havuzu, "ilan_suresi", "Piyasada kalma süresi (gün)", "zeta_ilan_sure"
        )
    with fc5:
        m2_araligi = _sayisal_slider(zeta_ilan_havuzu, "m2", "m²", "zeta_ilan_m2")
    with fc6:
        fiyat_araligi = _sayisal_slider(zeta_ilan_havuzu, "fiyat", "Fiyat (TL)", "zeta_ilan_fiyat")

if kat_secim:
    zeta_ilan_havuzu = [v for v in zeta_ilan_havuzu if str(v.get("kat")) in kat_secim]
if site_secim != "Tümü":
    zeta_ilan_havuzu = [
        v for v in zeta_ilan_havuzu
        if str(v.get("site_icerisinde") or "").strip().lower() == site_secim.lower()
    ]
if kullanim_secim:
    zeta_ilan_havuzu = [v for v in zeta_ilan_havuzu if str(v.get("kullanim_durumu")) in kullanim_secim]


def _araliga_gore_sirala(havuz, alan, aralik):
    if not aralik:
        return havuz
    sonuc = []
    for v in havuz:
        try:
            deger = float(v.get(alan))
        except (TypeError, ValueError):
            continue
        if aralik[0] <= deger <= aralik[1]:
            sonuc.append(v)
    return sonuc


zeta_ilan_havuzu = _araliga_gore_sirala(zeta_ilan_havuzu, "ilan_suresi", sure_araligi)
zeta_ilan_havuzu = _araliga_gore_sirala(zeta_ilan_havuzu, "m2", m2_araligi)
zeta_ilan_havuzu = _araliga_gore_sirala(zeta_ilan_havuzu, "fiyat", fiyat_araligi)

render_pano_icerik(
    zeta_ilan_havuzu, "portfoy", "Zeta Portföyleri",
    key_prefix="zeta_ilan", zaman_varsayilan="Tümü",
)

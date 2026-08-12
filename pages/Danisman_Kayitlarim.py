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
from html import escape as _esc

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.danisman_ortak import (
    talepleri_cek, portfoyleri_cek, kaynak_filtrele, su_anki_danisman,
    kayit_sil, kayit_notunu_guncelle, render_topbar, hide_sidebar_css,
    ILAN_PORTAL_DEGERLERI,
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
/* Not kaydet butonu — Sil ile karışmasın diye nötr (kırmızı değil) */
div[class*="st-key-dp_not_kaydet_"] button {
    border-color: #e3e1da !important;
    color: #1b2540 !important;
    font-size: 12.5px !important;
}
/* YENİ (12.08.2026 — İlanlarım bölümü): "↗ İlana Git" linki — Portföy
   Panosu'ndaki kart içi linkle (pano_export.py .kart-ilan-link) aynı
   görsel dil, burada Streamlit-native markdown içinde. */
.dp-ilan-link {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 11.5px;
    font-weight: 700;
    color: #1b2540;
    background: #eef0f3;
    border: 1px solid #dde1e6;
    padding: 4px 11px;
    border-radius: 20px;
    text-decoration: none;
    margin-top: 6px;
}
</style>
""", unsafe_allow_html=True)

su_kullanici = su_anki_danisman()

# YENİ (12.08.2026 — İlanlarım / Kayıtlarım ayrımı):
#   "Zeta Portföylerim" → Revy'den senkronize, portallarda (sahibinden
#                  vb.) FİİLEN YAYINLANAN resmi ilanların — SALT OKUNUR
#                  (kaynağı Revy/portal, buradan silinmesi/düzenlenmesi
#                  anlamlı değil), sadece "↗ İlana Git" linkiyle referans.
#   "Taleplerim" / "Portföylerim" → Danışman Panosu'ndan elle girilmiş,
#                  ilan sitelerinde BULUNMAYAN kayıtlar (kaynak zeta/ofis).
#                  Silinebilir/notu düzenlenebilir — değişmedi.
# revy_sync.py artık üretime entegre — "Zeta Portföylerim" gerçek veriyle
# dolmaya başlamış olmalı.
#
# DÜZELTME (12.08.2026 — 2. tur): Üç bölüm artık ALT ALTA koşullu
# başlıklar yerine SEKME (st.tabs) olarak gösteriliyor — Favoriler ve
# Uzmanlık Bölgelerim'deki aynı desen, tutarlılık için.
kendi_ilanlarim = [
    v for v in portfoyleri_cek()
    if str(v.get("kaynak") or "").strip().lower() in ILAN_PORTAL_DEGERLERI
    and v.get("talep_eden_danisan") == su_kullanici
]
kendi_talepler = [
    v for v in kaynak_filtrele(talepleri_cek(), "Zeta")
    if v.get("talep_eden_danisan") == su_kullanici
]
kendi_portfoyler = [
    v for v in kaynak_filtrele(portfoyleri_cek(), "Zeta")
    if v.get("talep_eden_danisan") == su_kullanici
    # "zeta1"/"zeta2" (resmi ilanlar) burada DEĞİL, "Zeta Portföylerim"
    # sekmesinde — ikisi birbirine karışmasın diye.
    and str(v.get("kaynak") or "").strip().lower() not in ILAN_PORTAL_DEGERLERI
]

if not kendi_ilanlarim and not kendi_talepler and not kendi_portfoyler:
    st.info("Henüz Danışman Panosu'ndan eklediğin bir kayıt yok.")
    st.stop()

sekme_ilan, sekme_talep, sekme_portfoy = st.tabs([
    f"Zeta Portföylerim ({len(kendi_ilanlarim)})",
    f"Taleplerim ({len(kendi_talepler)})",
    f"Portföylerim ({len(kendi_portfoyler)})",
])

with sekme_ilan:
    if not kendi_ilanlarim:
        st.caption("Henüz Revy'den senkronize edilmiş bir ilanın yok.")
    else:
        st.caption("Portallarda (sahibinden vb.) yayınlanan aktif ilanların — salt okunur.")
        for v in kendi_ilanlarim:
            with st.container(border=True, key=f"dp_kayit_card_ilan_{v['id']}"):
                st.markdown(f"**İlan:** {v.get('ozet', '')}")
                ilan_linki = v.get("ilan_linki")
                if ilan_linki:
                    st.markdown(
                        f"<a class='dp-ilan-link' href='{_esc(ilan_linki)}' target='_blank' "
                        f"rel='noopener noreferrer'>↗ İlana Git</a>",
                        unsafe_allow_html=True,
                    )

# NOT ALANI (09.08.2026): Kayıt oluşturulurken girilen "Ek Not" daha önce
# sadece o an yazılabiliyordu, sonradan hiçbir yerden düzenlenemiyordu.
# Şimdi her kartın altında aynı alan (talep: ozel_kriterler, portföy:
# ozellikler) görünür ve düzenlenebilir — "Notu Kaydet" ile Supabase'e
# yazılır. Boş bırakılıp kaydedilirse not temizlenmiş olur (bilinçli;
# ayrı bir "notu sil" eylemi eklemeye gerek yok).

with sekme_talep:
    if not kendi_talepler:
        st.caption("Henüz Danışman Panosu'ndan eklediğin bir talep yok.")
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
            yeni_not = st.text_area(
                "Not", value=v.get("ozel_kriterler") or "",
                key=f"dp_not_talep_{v['id']}", height=68,
                label_visibility="collapsed",
                placeholder="Bu talep için not ekle (opsiyonel)...",
            )
            if st.button("Notu Kaydet", key=f"dp_not_kaydet_talep_{v['id']}"):
                kayit_notunu_guncelle("alici_talepleri", v["id"], "ozel_kriterler", yeni_not.strip())
                talepleri_cek.clear()
                st.success("Not kaydedildi.")
                st.rerun()

with sekme_portfoy:
    if not kendi_portfoyler:
        st.caption("Henüz Danışman Panosu'ndan eklediğin bir portföy yok.")
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
            yeni_not = st.text_area(
                "Not", value=v.get("ozellikler") or "",
                key=f"dp_not_portfoy_{v['id']}", height=68,
                label_visibility="collapsed",
                placeholder="Bu portföy için not ekle (opsiyonel)...",
            )
            if st.button("Notu Kaydet", key=f"dp_not_kaydet_portfoy_{v['id']}"):
                kayit_notunu_guncelle("portfoyler", v["id"], "ozellikler", yeni_not.strip())
                portfoyleri_cek.clear()
                st.success("Not kaydedildi.")
                st.rerun()

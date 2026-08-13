"""
pages/Danisman_Musterilerim.py

Müşterilerim — kişisel kişi defteri (13.08.2026). Hamburger menüden
erişilir. Talep/Portföy tablolarından TAMAMEN BAĞIMSIZ — "Yeni Talep/
Portföy Ekle" formunda müşteri adı girildiğinde buraya OTOMATİK
senkronize edilir (core.danisman_ortak._musteri_senkronize), ama bu
sayfadan elle de kişi eklenebilir (emlakçı, tedarikçi vb. — bir talep/
portföye bağlı olmak zorunda değil).

BİLİNÇLİ TASARIM: Şimdilik KİŞİSEL — sadece kaydı ekleyen danışmana
görünür, ofis geneli paylaşılmıyor (ileride ihtiyaç olursa
genişletilebilir). "İlanlar silinse de müşteriler kayıtlı kalsın"
isteği, bu tablonun talep/portföy ile hiçbir foreign key/cascade
ilişkisi olmamasıyla sağlanıyor.
"""

import streamlit as st

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.danisman_ortak import (
    su_anki_danisman, musterileri_cek, musteri_ekle, musteri_guncelle,
    musteri_sil, render_topbar, hide_sidebar_css,
)

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Müşterilerim", ikon="📇", geri_hedefi="pages/Danisman_Secim.py")
st.caption("Kişisel kişi defterin — sadece sana görünür, ofis geneli paylaşılmaz.")

TIP_SECENEKLERI = ["Alıcı", "Satıcı", "Emlakçı", "Tedarikçi", "Diğer"]

st.markdown("""
<style>
div[class*="st-key-dp_mus_kart_"] {
    padding: 14px 16px !important;
    margin-bottom: 10px !important;
}
div[class*="st-key-dp_mus_sil_"] button {
    border-color: #e3e1da !important;
    color: #b3261e !important;
    font-size: 12.5px !important;
}
.dp-mus-tip {
    display: inline-block;
    font-size: 11px; font-weight: 700;
    padding: 3px 10px; border-radius: 999px;
    background: rgba(27,37,64,.08); color: #1b2540;
    margin-left: 8px;
}
</style>
""", unsafe_allow_html=True)

su_kullanici = su_anki_danisman()

with st.expander("+ Yeni Kişi Ekle", expanded=False):
    with st.form("dp_mus_yeni_form", clear_on_submit=True):
        mc1, mc2 = st.columns(2)
        with mc1:
            f_ad = st.text_input("Ad Soyad", key="dp_mus_ad")
            f_tip = st.selectbox("Tip", TIP_SECENEKLERI, key="dp_mus_tip")
        with mc2:
            f_telefon = st.text_input("Telefon (opsiyonel)", key="dp_mus_telefon")
        f_not = st.text_area("Not (opsiyonel)", key="dp_mus_not", height=68)
        if st.form_submit_button("Kaydet", type="primary", use_container_width=True):
            if not f_ad.strip():
                st.error("Ad Soyad zorunlu.")
            else:
                musteri_ekle(su_kullanici, f_ad, f_telefon, f_tip, f_not)
                st.success("✅ Eklendi.")
                st.rerun()

st.write("")

tum_musteriler = musterileri_cek(su_kullanici)

tip_filtre = st.radio(
    "Tip", ["Tümü"] + TIP_SECENEKLERI, horizontal=True,
    key="dp_mus_filtre", label_visibility="collapsed",
)
if tip_filtre != "Tümü":
    gosterilecek = [m for m in tum_musteriler if m.get("tip") == tip_filtre]
else:
    gosterilecek = tum_musteriler

st.caption(f"{len(gosterilecek)} kişi")

if not gosterilecek:
    st.info("Bu filtrede kayıtlı kişi yok. Yukarıdan yeni kişi ekleyebilir, ya da bir talep/portföy eklerken müşteri bilgisi girerek otomatik ekleyebilirsin.")

for m in gosterilecek:
    with st.container(border=True, key=f"dp_mus_kart_{m['id']}"):
        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown(
                f"**{m.get('ad', '')}**"
                f"<span class='dp-mus-tip'>{m.get('tip', 'Diğer')}</span>",
                unsafe_allow_html=True,
            )
            if m.get("telefon"):
                st.caption(f"📞 {m['telefon']}")
            if m.get("kaynak") == "otomatik":
                st.caption("↻ Talep/Portföy eklerken otomatik senkronize edildi")
        with c2:
            if st.button("Sil", key=f"dp_mus_sil_{m['id']}", use_container_width=True):
                musteri_sil(m["id"])
                st.rerun()
        yeni_not = st.text_area(
            "Not", value=m.get("notlar") or "",
            key=f"dp_mus_not_duzenle_{m['id']}", height=68,
            label_visibility="collapsed",
            placeholder="Bu kişi için not ekle (opsiyonel)...",
        )
        if st.button("Notu Kaydet", key=f"dp_mus_not_kaydet_{m['id']}"):
            musteri_guncelle(m["id"], {"notlar": yeni_not.strip() or None})
            st.success("Not kaydedildi.")
            st.rerun()

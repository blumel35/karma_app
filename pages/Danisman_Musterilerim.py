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

TIP_SECENEKLERI = ["Alıcı", "Satıcı", "İş Ortağı", "Tedarikçi", "Diğer"]

st.markdown("""
<style>
/* DÜZELTME (13.08.2026): Büyük, her zaman açık kartlar bir adres
   defteri için fazla yer kaplıyordu (her kişi ~250px). Kompakt, tek
   satırlık listeye çevrildi — not/sil işlemleri artık bir expander
   içinde, ihtiyaç olmadıkça hiç yer kaplamıyor. */
div[class*="st-key-dp_mus_satir_"] {
    padding: 2px 0 !important;
}
.dp-mus-tip {
    display: inline-block;
    font-size: 10px; font-weight: 700;
    padding: 2px 8px; border-radius: 999px;
    background: rgba(27,37,64,.08); color: #1b2540;
    margin-left: 8px; vertical-align: middle;
}
.dp-mus-harf-baslik {
    font-size: 13px; font-weight: 800; color: #b8892f;
    margin: 14px 0 4px 0; padding-bottom: 3px;
    border-bottom: 1px solid #ecebe5;
}
div[class*="st-key-dp_mus_islem_"] {
    margin-top: -6px !important;
    margin-bottom: 4px !important;
}
div[class*="st-key-dp_mus_sil_"] button {
    border-color: #e3e1da !important;
    color: #b3261e !important;
    font-size: 12px !important;
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

# DÜZELTME (13.08.2026): Alfabetik gruplu, kompakt liste — her kişi tek
# satır (ad + tip rozeti + telefon), not/sil işlemleri bir expander
# içinde saklı. Büyük, her zaman açık kartlar yerine gerçek bir adres
# defteri hissi versin diye.
gosterilecek_sirali = sorted(gosterilecek, key=lambda m: (m.get("ad") or "").strip().lower())

su_anki_harf = None
for m in gosterilecek_sirali:
    ad = m.get("ad", "").strip()
    ilk_harf = ad[0].upper() if ad else "#"
    if ilk_harf != su_anki_harf:
        su_anki_harf = ilk_harf
        st.markdown(f"<div class='dp-mus-harf-baslik'>{ilk_harf}</div>", unsafe_allow_html=True)

    telefon_metni = f" · 📞 {m['telefon']}" if m.get("telefon") else ""
    st.markdown(
        f"<div style='padding:6px 0;'>"
        f"<b>{ad}</b><span class='dp-mus-tip'>{m.get('tip', 'Diğer')}</span>"
        f"<span style='color:#7a8194;font-size:13px;'>{telefon_metni}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    with st.expander("Not / Sil", expanded=False):
        with st.container(key=f"dp_mus_islem_{m['id']}"):
            if m.get("kaynak") == "otomatik":
                st.caption("↻ Talep/Portföy eklerken otomatik senkronize edildi")
            yeni_not = st.text_area(
                "Not", value=m.get("notlar") or "",
                key=f"dp_mus_not_duzenle_{m['id']}", height=68,
                label_visibility="collapsed",
                placeholder="Bu kişi için not ekle (opsiyonel)...",
            )
            b1, b2 = st.columns([3, 1])
            with b1:
                if st.button("Notu Kaydet", key=f"dp_mus_not_kaydet_{m['id']}", use_container_width=True):
                    musteri_guncelle(m["id"], {"notlar": yeni_not.strip() or None})
                    st.success("Not kaydedildi.")
                    st.rerun()
            with b2:
                if st.button("Sil", key=f"dp_mus_sil_{m['id']}", use_container_width=True):
                    musteri_sil(m["id"])
                    st.rerun()

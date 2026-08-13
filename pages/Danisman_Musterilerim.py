"""
pages/Danisman_Musterilerim.py

Rehberim — kişisel kişi defteri (13.08.2026). Hamburger menüden
erişilir. Talep/Portföy tablolarından TAMAMEN BAĞIMSIZ — "Yeni Talep/
Portföy Ekle" formunda müşteri adı girildiğinde buraya OTOMATİK
senkronize edilir (core.danisman_ortak._musteri_senkronize), ama bu
sayfadan elle de kişi eklenebilir (iş ortağı, tedarikçi vb. — bir
talep/portföye bağlı olmak zorunda değil).

BİLİNÇLİ TASARIM: Şimdilik KİŞİSEL — sadece kaydı ekleyen danışmana
görünür, ofis geneli paylaşılmıyor (ileride ihtiyaç olursa
genişletilebilir). "İlanlar silinse de müşteriler kayıtlı kalsın"
isteği, bu tablonun talep/portföy ile hiçbir foreign key/cascade
ilişkisi olmamasıyla sağlanıyor.

DÜZELTME (13.08.2026 — 3. tur, kompaktlaştırma): Büyük her-zaman-açık
kartlar yerine gerçek bir adres defteri hissi: üstte Talep/Portföy
panolarındaki A-Z hızlı gezinme çubuğuyla AYNI görsel dil (aktif harf
koyu/tıklanabilir link, boş harf soluk), her kişi TEK satırda (ad +
tip + telefon + not/sil aksiyonu aynı satırda st.popover ile — expander
gibi ayrı bir satır işgal etmiyor), "+ Yeni Kişi Ekle" filtre satırının
sağına, kompakt bir popover butonu olarak taşındı.
"""

import streamlit as st

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.danisman_ortak import (
    su_anki_danisman, musterileri_cek, musteri_ekle, musteri_guncelle,
    musteri_sil, render_topbar, hide_sidebar_css, IZMIR_ILCELERI, _tip_listele,
)

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Rehberim", ikon="📇", geri_hedefi="pages/Danisman_Secim.py")
st.caption("Kişisel kişi defterin — sadece sana görünür, ofis geneli paylaşılmaz.")

TIP_SECENEKLERI = ["Alıcı", "Satıcı", "İş Ortağı", "Tedarikçi", "Diğer"]
TUM_HARFLER = list("ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ")

st.markdown("""
<style>
.dp-mus-tip {
    display: inline-block;
    font-size: 10px; font-weight: 700;
    padding: 2px 8px; border-radius: 999px;
    background: rgba(27,37,64,.08); color: #1b2540;
    margin-left: 8px; vertical-align: middle;
}
.dp-mus-satir {
    padding: 7px 0; border-bottom: 1px solid #f2f0ea;
}
.dp-mus-harf-baslik {
    font-size: 13px; font-weight: 800; color: #b8892f;
    margin: 16px 0 2px 0; padding-bottom: 3px;
    border-bottom: 1px solid #ecebe5;
}
.dp-mus-az {
    display: flex; flex-wrap: wrap; gap: 4px; margin: 6px 0 14px 0;
}
.dp-mus-az a {
    font-size: 12.5px; font-weight: 700; color: #1b2540;
    text-decoration: none; padding: 3px 6px; border-radius: 5px;
}
.dp-mus-az a:hover { background: rgba(27,37,64,.08); }
.dp-mus-az span { font-size: 12.5px; color: #cfcabf; padding: 3px 6px; }
div[class*="st-key-dp_mus_ekle_pop_"] button { white-space: nowrap !important; }
</style>
""", unsafe_allow_html=True)

su_kullanici = su_anki_danisman()
tum_musteriler = musterileri_cek(su_kullanici)

# ── FİLTRE SATIRI + "+ Yeni Kişi Ekle" (aynı satırda, sağda kompakt) ────
col_filtre, col_ekle = st.columns([5, 1.3])
with col_filtre:
    tip_filtre = st.radio(
        "Tip", ["Tümü"] + TIP_SECENEKLERI, horizontal=True,
        key="dp_mus_filtre", label_visibility="collapsed",
    )
with col_ekle:
    with st.popover("+ Yeni Kişi", use_container_width=True):
        with st.form("dp_mus_yeni_form", clear_on_submit=True):
            f_ad = st.text_input("Ad Soyad", key="dp_mus_ad")
            f_tip = st.multiselect(
                "Tip (birden fazla seçilebilir)", TIP_SECENEKLERI,
                default=["Alıcı"], key="dp_mus_tip",
            )
            f_telefon = st.text_input("Telefon (opsiyonel)", key="dp_mus_telefon")
            # YENİ (13.08.2026, 2. tur): "kim ne iş yapıyor, nerede
            # çalışıyor" sorusuna notları açmadan cevap verebilmek için
            # — özellikle İş Ortağı/Tedarikçi'de fark yaratıyor (örn.
            # "Ender Böncü — Gayrimenkul Değerleme Uzmanı — Bornova").
            f_uzmanlik = st.text_input(
                "Uzmanlık / Meslek (opsiyonel)", key="dp_mus_uzmanlik",
                placeholder="örn. Gayrimenkul Değerleme Uzmanı, Boyacı, Nakliyeci",
            )
            f_bolgeler = st.multiselect(
                "Çalıştığı Bölge(ler) (opsiyonel)", IZMIR_ILCELERI, key="dp_mus_bolgeler",
            )
            f_not = st.text_area("Not (opsiyonel)", key="dp_mus_not", height=68)
            if st.form_submit_button("Kaydet", type="primary", use_container_width=True):
                if not f_ad.strip():
                    st.error("Ad Soyad zorunlu.")
                elif not f_tip:
                    st.error("En az bir tip seçimi zorunlu.")
                else:
                    musteri_ekle(su_kullanici, f_ad, f_telefon, f_tip, f_not, f_uzmanlik, f_bolgeler)
                    st.success("✅ Eklendi.")
                    st.rerun()

if tip_filtre != "Tümü":
    gosterilecek = [m for m in tum_musteriler if tip_filtre in _tip_listele(m.get("tip"))]
else:
    gosterilecek = tum_musteriler

gosterilecek_sirali = sorted(gosterilecek, key=lambda m: (m.get("ad") or "").strip().lower())
st.caption(f"{len(gosterilecek_sirali)} kişi")

# ── A-Z HIZLI GEZİNME — Talep/Portföy panolarındaki AYNI görsel dil:
# içinde kayıt olan harf koyu/tıklanabilir link (aynı sayfa içi #çapaya
# atlıyor), boş harf soluk/tıklanamaz. ───────────────────────────────
mevcut_harfler = {
    (m.get("ad") or "").strip()[0].upper()
    for m in gosterilecek_sirali if (m.get("ad") or "").strip()
}
az_parcalari = []
for harf in TUM_HARFLER:
    if harf in mevcut_harfler:
        az_parcalari.append(f'<a href="#dp-mus-harf-{harf}">{harf}</a>')
    else:
        az_parcalari.append(f'<span>{harf}</span>')
st.markdown(f'<div class="dp-mus-az">{"".join(az_parcalari)}</div>', unsafe_allow_html=True)

if not gosterilecek_sirali:
    st.info("Bu filtrede kayıtlı kişi yok. Yukarıdan yeni kişi ekleyebilir, ya da bir talep/portföy eklerken müşteri bilgisi girerek otomatik ekleyebilirsin.")

su_anki_harf = None
for m in gosterilecek_sirali:
    ad = m.get("ad", "").strip()
    ilk_harf = ad[0].upper() if ad else "#"
    if ilk_harf != su_anki_harf:
        su_anki_harf = ilk_harf
        st.markdown(
            f"<div id='dp-mus-harf-{ilk_harf}' class='dp-mus-harf-baslik'>{ilk_harf}</div>",
            unsafe_allow_html=True,
        )

    # DÜZELTME: ad + tip + telefon + not/sil aksiyonu ARTIK AYNI SATIRDA.
    # st.popover, expander'ın aksine kapalıyken de açıkken de sayfada
    # yeni bir satır İŞGAL ETMİYOR — küçük bir buton olarak satırın
    # sağında duruyor, tıklanınca üstte kayan bir kutu açılıyor.
    r1, r2 = st.columns([6, 1])
    with r1:
        telefon_metni = f" · 📞 {m['telefon']}" if m.get("telefon") else ""
        rozetler = "".join(f"<span class='dp-mus-tip'>{t}</span>" for t in (_tip_listele(m.get("tip")) or ["Diğer"]))
        # YENİ (13.08.2026, 2. tur): uzmanlık + bölgeler satırda, notu
        # açmaya gerek kalmadan görünür — "Ender Böncü İş Ortağı ·
        # Gayrimenkul Değerleme Uzmanı · 📍 Bornova, Karşıyaka" gibi.
        alt_satir_parcalari = []
        if m.get("uzmanlik"):
            alt_satir_parcalari.append(m["uzmanlik"])
        if m.get("bolgeler"):
            alt_satir_parcalari.append("📍 " + ", ".join(m["bolgeler"]))
        alt_satir = f"<div style='color:#7a8194;font-size:12px;margin-top:1px;'>{' · '.join(alt_satir_parcalari)}</div>" if alt_satir_parcalari else ""
        st.markdown(
            f"<div class='dp-mus-satir'><b>{ad}</b>{rozetler}"
            f"<span style='color:#7a8194;font-size:13px;'>{telefon_metni}</span>{alt_satir}</div>",
            unsafe_allow_html=True,
        )
    with r2:
        with st.popover("⋮", use_container_width=True):
            if m.get("kaynak") == "otomatik":
                st.caption("↻ Talep/Portföy eklerken otomatik senkronize edildi")
            yeni_tipler = st.multiselect(
                "Tip", TIP_SECENEKLERI,
                default=[t for t in _tip_listele(m.get("tip")) if t in TIP_SECENEKLERI],
                key=f"dp_mus_tip_duzenle_{m['id']}",
            )
            yeni_uzmanlik = st.text_input(
                "Uzmanlık / Meslek", value=m.get("uzmanlik") or "",
                key=f"dp_mus_uzmanlik_duzenle_{m['id']}",
            )
            yeni_bolgeler = st.multiselect(
                "Çalıştığı Bölge(ler)", IZMIR_ILCELERI, default=m.get("bolgeler") or [],
                key=f"dp_mus_bolgeler_duzenle_{m['id']}",
            )
            yeni_not = st.text_area(
                "Not", value=m.get("notlar") or "",
                key=f"dp_mus_not_duzenle_{m['id']}", height=68,
                label_visibility="collapsed",
                placeholder="Bu kişi için not ekle (opsiyonel)...",
            )
            bp1, bp2 = st.columns(2)
            with bp1:
                if st.button("Kaydet", key=f"dp_mus_not_kaydet_{m['id']}", use_container_width=True):
                    musteri_guncelle(m["id"], {
                        "notlar": yeni_not.strip() or None,
                        "tip": yeni_tipler or ["Diğer"],
                        "uzmanlik": yeni_uzmanlik.strip() or None,
                        "bolgeler": yeni_bolgeler,
                    })
                    st.success("Kaydedildi.")
                    st.rerun()
            with bp2:
                if st.button("Sil", key=f"dp_mus_sil_{m['id']}", use_container_width=True):
                    musteri_sil(m["id"])
                    st.rerun()

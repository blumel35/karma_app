"""
pages/Danisman_SenaryoOlustur.py

Danışmanın "Üç Olası Yol" senaryo hesaplayıcısı için müşteriye özel
veri girip, benzersiz bir link ürettiği ekran (14.08.2026). Hamburger
menüden erişilir, GİRİŞ GEREKTİRİR (Rehberim ile aynı kişisel-kapsam
deseni — sadece kaydeden danışman kendi listesini görür).

Ürettiği link (?kod=...) pages/Senaryo_Hesaplayici.py'ye gider — o
sayfa GİRİŞSİZDİR, müşteri hesabı olmadan açabilir.
"""

import streamlit as st

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from urllib.parse import quote
from core.auth import oturum_kontrol
from core.danisman_ortak import (
    su_anki_danisman, senaryolari_cek, senaryo_kaydet, senaryo_guncelle,
    senaryo_sil, render_topbar, hide_sidebar_css,
)

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Senaryo Hesaplayıcı", ikon="🧮", geri_hedefi="pages/Danisman_Secim.py")
st.caption(
    "Müşteriye özel bir link üret — elindeki veriyi doldur, boş bıraktığın alanlar "
    "aracın kendi varsayılan değerleriyle açılır. Tüm alanlar opsiyonel, sadece "
    "Müşteri Adı zorunlu."
)

su_kullanici = su_anki_danisman()

_TEMEL_URL = "https://startkey-zeta.streamlit.app/Senaryo_Hesaplayici"


def _link_olustur(kod, musteri_adi=""):
    # YENİ (14.08.2026): müşteri adı da linkte — hem okunurluk için
    # (kopyalarken/paylaşırken kime ait olduğu belli olsun) hem de
    # Senaryo_Hesaplayici.py'nin sayfada ismiyle karşılama yapabilmesi
    # için. URL-encode edilmiş — Türkçe karakter/boşluk güvenli.
    url = f"{_TEMEL_URL}?kod={kod}"
    if musteri_adi and musteri_adi.strip():
        url += f"&musteri={quote(musteri_adi.strip())}"
    return url


with st.expander("+ Yeni Senaryo Oluştur", expanded=True):
    with st.form("dp_senaryo_form", clear_on_submit=True):
        f_musteri = st.text_input("Müşteri Adı *", key="dp_sn_musteri")

        st.markdown("**Evine Ait Bilgiler** (opsiyonel)")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            f_konum = st.text_input("Konum", key="dp_sn_konum", placeholder="örn. Bornova, İzmir")
        with c2:
            f_oda = st.text_input("Oda Sayısı", key="dp_sn_oda", placeholder="örn. 3+1")
        with c3:
            f_yas = st.text_input("Bina Yaşı", key="dp_sn_yas", placeholder="örn. 8")
        with c4:
            f_m2 = st.text_input("m²", key="dp_sn_m2", placeholder="örn. 120")
        f_ozellik = st.text_input(
            "Diğer Özellikler", key="dp_sn_ozellik",
            placeholder="örn. Asansör, Otopark, Balkon",
        )

        st.markdown("**Değerleme Raporu Sonuçları** (opsiyonel — bilgi amaçlı, hesaplamayı etkilemez)")
        v1, v2, v3 = st.columns(3)
        with v1:
            f_kisa = st.text_input(
                "Kısa Vade / Hızlı Satış (TL)", key="dp_sn_kisa", placeholder="örn. 16000000",
                help="Hiçbir öneri/teklif girilmezse \"Bugün Satarsanız\" hesaplaması BUNU baz alır (ofis kararı).",
            )
        with v2:
            f_orta = st.text_input("Orta Vade (TL)", key="dp_sn_orta", placeholder="örn. 17500000")
        with v3:
            f_uzun = st.text_input("Uzun Vade (TL)", key="dp_sn_uzun", placeholder="örn. 19000000")

        st.markdown("**Önerilen Fiyat / Gelen Teklif** (opsiyonel — doluysa hesaplamayı ezer)")
        o1, o2, o3 = st.columns(3)
        with o1:
            f_oneri = st.text_input(
                "Önerilen Fiyat (TL)", key="dp_sn_oneri", placeholder="Doluysa kısa vadeyi ezer",
            )
        with o2:
            f_teklif = st.text_input(
                "Gelen Teklif Tutarı (TL)", key="dp_sn_teklif", placeholder="Doluysa her şeyi ezer",
                help="Öncelik sırası: Gelen Teklif > Önerilen Fiyat > Kısa Vade.",
            )
        with o3:
            f_hedef = st.text_input(
                "Hedef Satış Fiyatı (TL)", key="dp_sn_hedef",
                placeholder="Biliyorsan doldur, yoksa boş bırak",
            )

        st.markdown("**Piyasa Varsayımları** (opsiyonel — müşteri kendi tarafında oynatabilir)")
        p1, p2, p3, p4 = st.columns(4)
        with p1:
            f_sure = st.text_input(
                "Piyasada Satış Süresi (ay)", key="dp_sn_sure", placeholder="örn. 6",
                help="\"Ne kadar bekleyebilirsiniz?\" kaydırıcısının başlangıç noktası olur.",
            )
        with p2:
            f_m2fiyat = st.text_input("Ort. m² Fiyatı (TL)", key="dp_sn_m2fiyat", placeholder="örn. 145000")
        with p3:
            f_faiz = st.text_input(
                "Piyasa Faiz Oranı (%)", key="dp_sn_faiz", placeholder="örn. 45",
                help="%10-70 arası bir kaydırıcının başlangıç noktası olur.",
            )
        with p4:
            f_aylik = st.text_input(
                "Aylık Maliyet (TL)", key="dp_sn_aylik", placeholder="örn. 2500",
                help="Aidat/abonelik gibi bekleme süresince devam eden giderler (opsiyonel).",
            )

        if st.form_submit_button("Link Oluştur", type="primary", use_container_width=True):
            if not f_musteri.strip():
                st.error("Müşteri Adı zorunlu.")
            else:
                kod = senaryo_kaydet(su_kullanici, {
                    "musteri_adi": f_musteri, "konum": f_konum, "oda_sayisi": f_oda,
                    "bina_yasi": f_yas, "m2": f_m2, "ozellikler": f_ozellik,
                    "deger_kisa": f_kisa, "deger_orta": f_orta, "deger_uzun": f_uzun,
                    "oneri_fiyat": f_oneri, "teklif_tutari": f_teklif,
                    "hedef_fiyat": f_hedef, "piyasa_satis_suresi": f_sure,
                    "ort_m2_fiyati": f_m2fiyat, "piyasa_faiz_orani": f_faiz,
                    "aylik_maliyet": f_aylik,
                })
                st.success(f"✅ Link hazır: {_link_olustur(kod, f_musteri)}")
                st.code(_link_olustur(kod, f_musteri), language=None)
                st.rerun()

st.write("")
st.markdown("##### Önceki Senaryoların")

senaryolar = senaryolari_cek(su_kullanici)
if not senaryolar:
    st.info("Henüz bir senaryo oluşturmadın.")

for s in senaryolar:
    with st.container(border=True, key=f"dp_sn_kart_{s['id']}"):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(f"**{s.get('musteri_adi', '')}**")
            link = _link_olustur(s["kod"], s.get("musteri_adi", ""))
            st.code(link, language=None)
        with c2:
            if st.button("Sil", key=f"dp_sn_sil_{s['id']}", use_container_width=True):
                senaryo_sil(s["id"])
                st.rerun()

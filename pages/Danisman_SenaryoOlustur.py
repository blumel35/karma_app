"""
pages/Danisman_SenaryoOlustur.py

Danışmanın "Üç Olası Yol" senaryo hesaplayıcısı için müşteriye özel
veri girip, benzersiz bir link ürettiği ekran (14.08.2026). Hamburger
menüden erişilir, GİRİŞ GEREKTİRİR (Rehberim ile aynı kişisel-kapsam
deseni — sadece kaydeden danışman kendi listesini görür).

Ürettiği link (?kod=...) pages/Senaryo_Hesaplayici.py'ye gider — o
sayfa GİRİŞSİZDİR, müşteri hesabı olmadan açabilir.

DÜZELTME (22.08.2026): Para birimi alanları büyük rakamlar (17500000
gibi) içerdiği için okuması/takip etmesi zordu. st.form KULLANILMIYOR
artık — Streamlit formları içindeki alanlar sadece gönderim anında
işlenir, "yazarken" hiçbir şey tetiklenmez; bu yüzden HTML aracındaki
gibi anlık (her tuşta) biçimlendirme burada MÜMKÜN DEĞİL. Bunun yerine
her para birimi alanı bir alandan diğerine geçildiğinde (on_change,
odak kaybı) otomatik olarak binlik ayraçla yeniden yazılıyor — "canlı"
değil ama gerçek bir iyileştirme. Kaydetme sırasında ayraçlar tekrar
temizlenip ham rakam olarak saklanıyor (veritabanı/enjeksiyon tarafı
etkilenmiyor).
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

# DÜZELTME (22.08.2026): Streamlit, bir widget key'ine o widget BU
# ÇALIŞMADA zaten oluşturulduktan SONRA doğrudan değer atanmasına izin
# vermiyor (StreamlitAPIException). Bu yüzden alanları temizleme işlemi
# artık widget'lar oluşturulmadan ÖNCE, bir bayrak üzerinden yapılıyor —
# "Link Oluştur" butonu bayrağı set edip rerun ediyor, bir SONRAKİ
# çalıştırmada (widget'lar henüz oluşmadan) bu blok bayrağı görüp
# alanları temizliyor.
if st.session_state.pop("_dp_sn_temizle", False):
    for _k in ["dp_sn_musteri", "dp_sn_konum", "dp_sn_oda", "dp_sn_yas", "dp_sn_m2",
               "dp_sn_ozellik", "dp_sn_kisa", "dp_sn_orta", "dp_sn_uzun", "dp_sn_oneri",
               "dp_sn_teklif", "dp_sn_hedef", "dp_sn_m2fiyat", "dp_sn_aylik",
               "dp_sn_sure", "dp_sn_faiz"]:
        st.session_state[_k] = ""

# DÜZELTME (22.08.2026): st.rerun() hemen çalıştığı için, "Link Oluştur"
# butonunun ANINDA gösterdiği başarı mesajı/link, rerun ile birlikte
# gözden kaybolurdu (kullanıcı hiç göremezdi). Şimdi link session_state'te
# saklanıp BİR SONRAKİ çalıştırmada burada, en üstte gösteriliyor —
# gösterildikten sonra kendini temizliyor (bir daha tekrar etmesin diye).
if st.session_state.get("_dp_sn_son_link"):
    st.success(f"✅ Link hazır: {st.session_state['_dp_sn_son_link']}")
    st.code(st.session_state["_dp_sn_son_link"], language=None)
    del st.session_state["_dp_sn_son_link"]

_TEMEL_URL = "https://startkey-zeta.streamlit.app/Senaryo_Hesaplayici"

# Para birimi (TL) alanlarının key'leri — otomatik binlik ayraç bu
# alanlara uygulanıyor. "dp_sn_faiz" (yüzde) ve "dp_sn_sure" (ay) küçük
# rakamlar olduğu için bilerek dışarıda bırakıldı.
_TL_ALANLARI = [
    "dp_sn_kisa", "dp_sn_orta", "dp_sn_uzun", "dp_sn_oneri",
    "dp_sn_teklif", "dp_sn_hedef", "dp_sn_m2fiyat", "dp_sn_aylik",
]


def _tl_bicimlendir(key):
    """on_change ile çağrılır — alandan çıkılınca (odak kaybı/Enter),
    yazılan rakamları binlik ayraçla yeniden yazar (17500000 -> 17.500.000)."""
    ham = st.session_state.get(key, "") or ""
    rakamlar = "".join(ch for ch in ham if ch.isdigit())
    st.session_state[key] = f"{int(rakamlar):,}".replace(",", ".") if rakamlar else ""


def _tl_temizle(deger):
    """Kaydetmeden önce ayraçları temizler — veritabanına/HTML enjeksiyonuna
    her zaman ham rakam gider, ayraçlı metin değil."""
    if not deger:
        return deger
    return "".join(ch for ch in deger if ch.isdigit()) or None


def _link_olustur(kod, musteri_adi=""):
    # YENİ (14.08.2026): müşteri adı da linkte — hem okunurluk için
    # (kopyalarken/paylaşırken kime ait olduğu belli olsun) hem de
    # Senaryo_Hesaplayici.py'nin sayfada ismiyle karşılama yapabilmesi
    # için. URL-encode edilmiş — Türkçe karakter/boşluk güvenli.
    url = f"{_TEMEL_URL}?kod={kod}"
    if musteri_adi and musteri_adi.strip():
        # DÜZELTME (22.08.2026): quote() boşlukları "%20" olarak kodluyordu
        # — linki kopyalayıp paylaşırken çirkin/karışık görünüyordu.
        # Boşluklar yerine "-" kullanılıyor (linkte temiz görünür),
        # Senaryo_Hesaplayici.py karşılama metninde "-"yı tekrar boşluğa
        # çeviriyor.
        url += f"&musteri={quote(musteri_adi.strip().replace(' ', '-'))}"
    return url


with st.expander("+ Yeni Senaryo Oluştur", expanded=True):
    # DÜZELTME (22.08.2026): st.form KALDIRILDI — on_change ile anlık
    # biçimlendirme, form içinde çalışmıyordu (form yalnızca gönderim
    # anında işlenir).
    f_musteri = st.text_input("Müşteri Adı *", key="dp_sn_musteri")

    # YENİ (23.08.2026): iki farklı arayüz şablonu — Klasik (tek sayfa,
    # tüm alanlar bir arada) ve Sihirbaz (8 adımlı, "İleri/Geri" ile
    # ilerlenen, hikaye akışı gibi hissettiren versiyon). İkisi de AYNI
    # alan ID'lerini kullanıyor, bu yüzden veri girişi/kaydetme tarafı
    # değişmiyor — sadece müşteriye hangi görselin gideceği değişiyor.
    f_surum = st.radio(
        "Arayüz Şablonu", ["Klasik (Tek Sayfa)", "Sihirbaz (Adım Adım)"],
        key="dp_sn_surum", horizontal=True,
        help="Sihirbaz, bilgileri 8 adıma bölüp tek tek gösterir — mobilde daha az kalabalık görünür.",
    )

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
            "Kısa Vade / Hızlı Satış (TL)", key="dp_sn_kisa", placeholder="örn. 16.000.000",
            help="Hiçbir öneri/teklif girilmezse \"Bugün Satarsanız\" hesaplaması BUNU baz alır (ofis kararı).",
            on_change=_tl_bicimlendir, args=("dp_sn_kisa",),
        )
    with v2:
        f_orta = st.text_input(
            "Orta Vade (TL)", key="dp_sn_orta", placeholder="örn. 17.500.000",
            on_change=_tl_bicimlendir, args=("dp_sn_orta",),
        )
    with v3:
        f_uzun = st.text_input(
            "Uzun Vade (TL)", key="dp_sn_uzun", placeholder="örn. 19.000.000",
            on_change=_tl_bicimlendir, args=("dp_sn_uzun",),
        )

    st.markdown("**Önerilen Fiyat / Gelen Teklif** (opsiyonel — doluysa hesaplamayı ezer)")
    o1, o2, o3 = st.columns(3)
    with o1:
        f_oneri = st.text_input(
            "Önerilen Fiyat (TL)", key="dp_sn_oneri", placeholder="Doluysa kısa vadeyi ezer",
            on_change=_tl_bicimlendir, args=("dp_sn_oneri",),
        )
    with o2:
        f_teklif = st.text_input(
            "Gelen Teklif Tutarı (TL)", key="dp_sn_teklif", placeholder="Doluysa her şeyi ezer",
            help="Öncelik sırası: Gelen Teklif > Önerilen Fiyat > Kısa Vade.",
            on_change=_tl_bicimlendir, args=("dp_sn_teklif",),
        )
    with o3:
        f_hedef = st.text_input(
            "Hedef Satış Fiyatı (TL)", key="dp_sn_hedef",
            placeholder="Biliyorsan doldur, yoksa boş bırak",
            on_change=_tl_bicimlendir, args=("dp_sn_hedef",),
        )

    st.markdown("**Piyasa Varsayımları** (opsiyonel — müşteri kendi tarafında oynatabilir)")
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        f_sure = st.text_input(
            "Piyasada Satış Süresi (ay)", key="dp_sn_sure", placeholder="örn. 6",
            help="\"Ne kadar bekleyebilirsiniz?\" kaydırıcısının başlangıç noktası olur.",
        )
    with p2:
        f_m2fiyat = st.text_input(
            "Ort. m² Fiyatı (TL)", key="dp_sn_m2fiyat", placeholder="örn. 145.000",
            on_change=_tl_bicimlendir, args=("dp_sn_m2fiyat",),
        )
    with p3:
        f_faiz = st.text_input(
            "Piyasa Faiz Oranı (%)", key="dp_sn_faiz", placeholder="örn. 45",
            help="%10-70 arası bir kaydırıcının başlangıç noktası olur.",
        )
    with p4:
        f_aylik = st.text_input(
            "Aylık Maliyet (TL)", key="dp_sn_aylik", placeholder="örn. 2.500",
            help="Aidat/abonelik gibi bekleme süresince devam eden giderler (opsiyonel).",
            on_change=_tl_bicimlendir, args=("dp_sn_aylik",),
        )

    if st.button("Link Oluştur", type="primary", use_container_width=True, key="dp_sn_kaydet_btn"):
        if not f_musteri.strip():
            st.error("Müşteri Adı zorunlu.")
        else:
            kod = senaryo_kaydet(su_kullanici, {
                "musteri_adi": f_musteri, "konum": f_konum, "oda_sayisi": f_oda,
                "bina_yasi": f_yas, "m2": f_m2, "ozellikler": f_ozellik,
                "deger_kisa": _tl_temizle(f_kisa), "deger_orta": _tl_temizle(f_orta),
                "deger_uzun": _tl_temizle(f_uzun),
                "oneri_fiyat": _tl_temizle(f_oneri), "teklif_tutari": _tl_temizle(f_teklif),
                "hedef_fiyat": _tl_temizle(f_hedef), "piyasa_satis_suresi": f_sure,
                "ort_m2_fiyati": _tl_temizle(f_m2fiyat), "piyasa_faiz_orani": f_faiz,
                "aylik_maliyet": _tl_temizle(f_aylik),
                "surum": "sihirbaz" if f_surum.startswith("Sihirbaz") else "klasik",
            })
            st.session_state["_dp_sn_son_link"] = _link_olustur(kod, f_musteri)
            st.session_state["_dp_sn_temizle"] = True
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
            _surum_etiket = "🧙 Sihirbaz" if s.get("surum") == "sihirbaz" else "📄 Klasik"
            st.markdown(f"**{s.get('musteri_adi', '')}**  ·  `{_surum_etiket}`")
            link = _link_olustur(s["kod"], s.get("musteri_adi", ""))
            st.code(link, language=None)
        with c2:
            if st.button("Sil", key=f"dp_sn_sil_{s['id']}", use_container_width=True):
                senaryo_sil(s["id"])
                st.rerun()

"""
pages/Danisman_OfisPano.py

Ofis Panosu — YENİ (17.09.2026, 2. TUR — Meltem: "ofis panosunda sadece
senaryo hesaplayıcı olmayacaktı, o bir bölüm olacaktı ve link oluştur
diyerek göndermeyi düşünüyordum"). Danışman Panosu'na hamburger menüden
erişilen, OTURUM GEREKTİREN bir HUB sayfası — ileride ofis geneli başka
araçlar da (birer "bölüm" olarak) buraya eklenebilir diye kartlı/
genişletilebilir bir yapı olarak kuruldu. Şimdilik tek kart: Prim
Sistemi Senaryo Hesaplayıcı.

MİMARİ — pages/Danisman_SenaryoOlustur.py (oturumlu "oluştur" ekranı) /
pages/Senaryo_Hesaplayici.py (girişsiz "göster" sayfası) ikilisiyle AYNI
desen: bu hub oturum gerektirir, her kartın "🔗 Link Oluştur" aksiyonu
ise İLGİLİ ARACIN kendi girişsiz/paylaşılabilir sayfasının (örn.
pages/Prim_Hesaplayici.py) SABİT URL'sini gösterir. Prim Hesaplayıcı'da
kişiye özel bir "kod" olmadığı için (tüm girdiler sayfanın kendi JS'i
tarafından yönetiliyor) burada bir DB kaydı ÜRETİLMİYOR — "Link Oluştur"
sadece o aracın hazır, sabit linkini görünür kılıp panoya kopyalanabilir
hale getiriyor.

Yeni bir bölüm eklemek için: BOLUMLER listesine {"baslik", "aciklama",
"sayfa"} şeklinde bir sözlük daha eklemek yeterli — kart/link mantığı
otomatik çalışır.

DİKKAT: "4_Ofis_Paneli.py" (admin tarafındaki, oturum gerektiren, farklı
bir sayfa — ofis performans/portföy paneli) ile KARIŞTIRILMASIN diye
bilerek "Ofis Panosu" (bu sayfa) / "Ofis Paneli" (var olan) adları
birbirinden ayrı tutuldu.
"""

import streamlit as st

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.danisman_ortak import render_topbar, hide_sidebar_css

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Ofis Panosu", ikon="🏢", geri_hedefi="pages/Danisman_Secim.py")

# YETKİ KONTROLÜ (21.09.2026 — Meltem: "danısman panosunda ofis panosu
# ekranını sadece admin ve yönetici ve brokerlara açık hale getirir
# misin"). DESEN: core/danisman_ortak.py'deki senaryolari_cek()
# docstring'inde belirtildiği gibi bu kod tabanında yetki kontrolü
# MERKEZİ bir helper'da değil, HER SAYFANIN KENDİSİNDE yapılıyor — burada
# da pages/5_Mail_Islem.py'de kullanılan AYNI desen izlendi:
# st.session_state["kullanici"] sözlüğündeki "rol" alanı okunup izinli
# roller listesiyle karşılaştırılıyor. render_topbar() BİLİNÇLİ OLARAK bu
# kontrolden ÖNCE çağrılıyor — yetkisi olmayan biri "yetkin yok" mesajını
# görse bile üst bar (ve "← Panoya Dön" butonu) çizili kalsın, boş/çıkışsız
# bir sayfada mahsur kalmasın diye (5_Mail_Islem.py'deki aynı gerekçe).
_rol = st.session_state.get("kullanici", {}).get("rol", "")
if _rol not in ("admin", "broker", "yonetici"):
    st.error(
        "Bu sayfaya erişim yetkiniz yok — Ofis Panosu yalnızca admin, "
        "yönetici ve broker rolleri içindir."
    )
    st.stop()

st.caption("Ofis genelinde kullanılan araçlar — paylaşılabilir linkleriyle birlikte.")

# Uygulamanın canlı adresi — Senaryo Hesaplayıcı linklerinde de kullanılan
# AYNI sabit taban (startkey-zeta.streamlit.app). Değişirse tek yerden
# güncellenir diye burada, en üstte tutuluyor.
_UYGULAMA_TABAN_URL = "https://startkey-zeta.streamlit.app"

BOLUMLER = [
    {
        "baslik": "🧮 Prim Sistemi Senaryo Hesaplayıcı",
        "aciklama": (
            "Önümüzdeki 12 ay için öngörülen çalışma senaryosuna göre "
            "Kademeli 27, Girişimci 27 ve MAX prim modellerinin "
            "karşılaştırmasını gösterir."
        ),
        "sayfa": "Prim_Hesaplayici",
    },
]

for bolum in BOLUMLER:
    with st.container(border=True):
        st.subheader(bolum["baslik"])
        st.write(bolum["aciklama"])
        link_key = f"ofis_link_ac_{bolum['sayfa']}"
        if st.button("🔗 Link Oluştur", key=link_key):
            st.session_state[f"{link_key}_goster"] = True
        if st.session_state.get(f"{link_key}_goster"):
            url = f"{_UYGULAMA_TABAN_URL}/{bolum['sayfa']}"
            st.code(url, language=None)
            st.caption("Bu link oturum açmadan da çalışır — doğrudan paylaşabilirsin.")

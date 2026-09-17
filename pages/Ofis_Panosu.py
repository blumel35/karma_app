"""
pages/Ofis_Panosu.py

Ofis Panosu — YENİ (17.09.2026, Meltem: "claude üzerinden değil senaryo
hesaplayıcı gibi ... hamburger menüye ofis sayfası ekleyelim. içinde bu
prim hesaplama tablosu da olsun"). Şimdilik tek içeriği Zeta Prim Sistemi
Senaryo Hesaplayıcı — ileride ofis geneli başka araçlar da buraya
eklenebilir diye ayrı bir sayfa olarak kuruldu (Danışman Panosu'nun
içine bir sekme olarak GÖMÜLMEDİ).

BİLİNÇLİ TASARIM — pages/Senaryo_Hesaplayici.py ile AYNI desen (ve aynı
gerekçeyle "Danisman_" ÖN EKİ YOK — bu isimlendirme kod tabanında
"girişsiz, paylaşılabilir sayfa" anlamına geliyor):
- oturum_kontrol() KASITLI OLARAK ÇAĞRILMIYOR — linki bilen herkes
  (örn. işe alım sürecindeki bir aday) girişsiz açabilsin diye.
- Danışman Panosu'nun kendi topbar'ı (render_topbar vb.) BİLEREK
  kullanılmıyor — sadece temiz, bağımsız bir araç sayfası.
- İçerik assets/zeta_prim_sistemi_senaryo_hesaplayici.html'den OLDUĞU
  GİBİ okunup gömülüyor — kişiye özel bir veri enjeksiyonu YOK (Senaryo
  Hesaplayıcı'nın aksine bu araç genel/kişiselleştirilmemiş, tüm
  girdiler sayfanın kendi JS'i tarafından yönetiliyor).

DİKKAT: "4_Ofis_Paneli.py" (admin tarafındaki, oturum gerektiren, farklı
bir sayfa — ofis performans/portföy paneli) ile KARIŞTIRILMASIN diye
bilerek "Ofis Panosu" (bu sayfa) / "Ofis Paneli" (var olan) adları
birbirinden ayrı tutuldu.

Danışmanların bu linki BULMASI için hamburger menüde bir giriş var
(core/danisman_ortak.py, render_topbar()) — ama sayfanın kendisi girişsiz.
"""

import streamlit as st
import streamlit.components.v1 as components

import os

# Streamlit'in kendi arayüz izlerini (sidebar, hamburger menü, "Deploy"
# butonu) gizle — Senaryo_Hesaplayici.py ile AYNI, bilerek burada,
# minimal ve core/danisman_ortak.py'ye bağımlı olmadan yazıldı.
st.markdown("""
<style>
[data-testid="stSidebar"], [data-testid="stSidebarNav"],
header[data-testid="stHeader"], #MainMenu, footer,
[data-testid="stToolbar"] { display: none !important; }
.block-container { padding-top: 0.5rem !important; max-width: 100% !important; }
</style>
""", unsafe_allow_html=True)

_ASSETS_DIZINI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
_HTML_YOLU = os.path.join(_ASSETS_DIZINI, "zeta_prim_sistemi_senaryo_hesaplayici.html")

try:
    with open(_HTML_YOLU, "r", encoding="utf-8") as f:
        _html_icerik = f.read()
    components.html(_html_icerik, height=1900, scrolling=True)
except FileNotFoundError:
    st.error(
        "Prim Sistemi Senaryo Hesaplayıcı dosyası bulunamadı "
        "(assets/zeta_prim_sistemi_senaryo_hesaplayici.html) — "
        "deploy'un bu dosyayı içerdiğinden emin ol."
    )

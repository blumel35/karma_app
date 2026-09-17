"""
pages/Prim_Hesaplayici.py

Zeta Prim Sistemi Senaryo Hesaplayıcı — GİRİŞSİZ, PAYLAŞILABİLİR tek araç
sayfası. YENİ (17.09.2026), 2. TUR (Meltem: "ofis panosunda sadece
senaryo hesaplayıcı olmayacaktı, o bir bölüm olacaktı ve link oluştur
diyerek göndermeyi düşünüyordum"): İlk turda bu içerik "pages/
Ofis_Panosu.py" adıyla, hem hub hem tek link olarak tek dosyada
kurulmuştu — Meltem'in asıl niyetinin şu olduğu netleşti:
  - "Ofis Panosu" = Danışman Panosu'na hamburger menüden erişilen,
    OTURUM GEREKTİREN bir HUB sayfası — ileride birden fazla "bölüm"
    (araç) barındıracak, bunlardan biri de bu Prim Hesaplayıcı.
  - Bu dosya (Prim_Hesaplayici.py) ise sadece TEK bir aracın kendisi —
    hub'daki "🔗 Link Oluştur" aksiyonunun gösterdiği/paylaştığı GERÇEK
    hedef. Bkz. pages/Danisman_OfisPano.py (hub) ve
    core/danisman_ortak.py (hamburger menü artık hub'a gidiyor, bu
    sayfaya değil).
Bu ayrım BİLEREK pages/Danisman_SenaryoOlustur.py (oturumlu, "oluştur")
/ pages/Senaryo_Hesaplayici.py (girişsiz, "göster") ikilisiyle AYNI
mimari desen — tek fark, bu araçta kişiye özel bir "kod" YOK (tüm
girdiler sayfanın kendi JS'i tarafından yönetiliyor, kişiselleştirme
gerekmiyor), bu yüzden hub'daki "Link Oluştur" bir DB kaydı üretmiyor,
sadece bu sayfanın SABİT URL'sini gösteriyor.

BİLİNÇLİ TASARIM — pages/Senaryo_Hesaplayici.py ile AYNI desen (ve aynı
gerekçeyle "Danisman_" ÖN EKİ YOK — bu isimlendirme kod tabanında
"girişsiz, paylaşılabilir sayfa" anlamına geliyor):
- oturum_kontrol() KASITLI OLARAK ÇAĞRILMIYOR — linki bilen herkes
  (örn. işe alım sürecindeki bir aday) girişsiz açabilsin diye.
- Danışman Panosu'nun kendi topbar'ı (render_topbar vb.) BİLEREK
  kullanılmıyor — sadece temiz, bağımsız bir araç sayfası.
- İçerik assets/zeta_prim_sistemi_senaryo_hesaplayici.html'den OLDUĞU
  GİBİ okunup gömülüyor — kişiye özel bir veri enjeksiyonu YOK.

DİKKAT (GitHub'a yapıştırırken): Bu dosya, ilk turda eklenen
"pages/Ofis_Panosu.py"nin YERİNİ ALIYOR — o dosya GitHub'dan SİLİNMELİ,
yerine bu dosya + pages/Danisman_OfisPano.py eklenmeli.
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

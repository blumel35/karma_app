"""
pages/Yatirim_Formu.py

"Yatırım Alıcısı İhtiyaç Formu" — MÜŞTERİYE gönderilmek üzere, bağımsız/
paylaşılabilir bir link (01.10.2026, hızlı test turu).

DÜZELTME (01.10.2026, 2. tur): İlk denemede bu form static/ klasörüne
(Streamlit'in enableStaticServing mekanizması, manifest.json/icons ile
AYNI yol) konulmuştu — ama Meltem'in canlı testinde o link SÜREKLİ
"yükleniyor" durumunda takılı kaldı (hem normal hem gizli pencerede,
hem de zaten çalışan manifest.json linki de AYNI şekilde takıldı — yani
sorun bu dosyaya özel değil, static dosya sunumunun bu deploy'da
GENEL OLARAK güvenilir çalışmadığını gösterdi). Bunun yerine Senaryo
Hesaplayıcı'nın (pages/Senaryo_Hesaplayici.py) ZATEN CANLIDA ÇALIŞTIĞI
KANITLANMIŞ deseni kopyalandı: oturumsuz bir Streamlit sayfası, HTML
içeriği components.html() ile gömülü render ediliyor, kişiselleştirme
(advisor/wa/danisman) query param'ları TARAYICIDA değil BURADA, Python
tarafında okunup HTML'e enjekte ediliyor.

BİLİNÇLİ TASARIM — Senaryo_Hesaplayici.py ile AYNI desen:
- oturum_kontrol() KASITLI OLARAK ÇAĞRILMIYOR — linki bilen herkes
  (müşteri, Karma App hesabı olmadan) açabilsin diye.
- Danışman Panosu'nun kendi topbar'ı BİLEREK kullanılmıyor — müşteri bu
  linki açtığında hiçbir dahili yönetim arayüzü izi görmemeli.
- İçerik assets/yatirim-formu.html'den OLDUĞU GİBİ okunup gömülüyor.

ÖNEMLİ: app.py'de hem st.Page olarak TANIMLANMASI hem de st.navigation()
listesine EKLENMESİ gerekiyor — aksi halde "Could not find page" hatası
verir (bu kod tabanında birkaç kez tekrarlanmış, bilinen bir tuzak).

Meltem'in isteği (01.10.2026, hızlı test turu): "şimdilik bu sayfa
sadece bende görülsün" — bu yüzden hamburger menüde/navigasyonda HİÇBİR
YERE eklenmedi, sadece doğrudan linki bilen açabilir (Senaryo
Hesaplayıcı/Hesap Aktivasyonu ile AYNI "listede ama görünmez" deseni —
bkz. app.py'deki hide_sidebar_css() çağrısı, aşağıda).
"""

import streamlit as st
import streamlit.components.v1 as components

import os
import re
import json

st.markdown("""
<style>
[data-testid="stSidebar"], [data-testid="stSidebarNav"],
header[data-testid="stHeader"], #MainMenu, footer,
[data-testid="stToolbar"] { display: none !important; }
.block-container { padding-top: 0.5rem !important; max-width: 100% !important; }
</style>
""", unsafe_allow_html=True)

_HTML_YOLU = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "yatirim-formu.html",
)


def _js_const_enjekte(html, const_adi, deger):
    """<script> içindeki `const ADI=...;` satırının sağ tarafını,
    Python tarafında okunan query param değeriyle BİREBİR değiştirir.
    Form bu sayfada bir iframe (components.html) içinde render edildiği
    için kendi `location.search`'ü BOŞ gelir (iframe'in gerçek bir
    URL'i/sorgu dizesi yok) — bu yüzden ?advisor=/?wa=/?danisman=
    okuma işi artık TARAYICIDA değil, BURADA (Python) yapılıyor.
    json.dumps ile güvenli bir JS string literal'i üretiliyor (tırnak/
    özel karakter kaçışı otomatik)."""
    desen = re.compile(rf"const {re.escape(const_adi)}=[^;]*;")
    return desen.sub(f"const {const_adi}={json.dumps(deger)};", html, count=1)


_advisor = st.query_params.get("advisor", "Gayrimenkul Danışmanınız")
_wa_ham = st.query_params.get("wa", "")
_wa = "".join(ch for ch in _wa_ham if ch.isdigit())
_danisman = st.query_params.get("danisman", "")

try:
    with open(_HTML_YOLU, "r", encoding="utf-8") as f:
        _html_icerik = f.read()

    _html_icerik = _js_const_enjekte(_html_icerik, "ADVISOR", _advisor)
    _html_icerik = _js_const_enjekte(_html_icerik, "WA", _wa)
    _html_icerik = _js_const_enjekte(_html_icerik, "DANISMAN", _danisman)

    components.html(_html_icerik, height=2400, scrolling=True)
except FileNotFoundError:
    st.error(
        "Form dosyası bulunamadı (assets/yatirim-formu.html) — "
        "deploy'un bu dosyayı içerdiğinden emin ol."
    )

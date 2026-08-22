"""
pages/Senaryo_Hesaplayici.py

"Üç Olası Yol" satış senaryoları hesaplayıcısı — MÜŞTERİYE gönderilmek
üzere tasarlanmış, bağımsız/paylaşılabilir bir link (14.08.2026).

BİLİNÇLİ TASARIM — Pano_Goruntule.py'nin AYNI deseni:
- oturum_kontrol() KASITLI OLARAK ÇAĞRILMIYOR — linki bilen herkes
  (müşteri, Karma App hesabı olmadan) açabilsin diye.
- Danışman Panosu'nun kendi topbar'ı (render_topbar, "Panoya Dön" vb.)
  BİLEREK kullanılmıyor — müşteri bu linki açtığında hiçbir dahili
  yönetim arayüzü izi görmemeli, sadece temiz, bağımsız bir araç.
- İçerik assets/satis_senaryolari_basit.html'den OLDUĞU GİBİ okunup
  gömülüyor — dosyanın kendi CSS/JS'i tamamen bağımsız (dış bağımlılık
  yok), Streamlit tarafında yeniden inşa edilmedi.

Danışmanların bu linki BULMASI için hamburger menüde bir giriş var
(core/danisman_ortak.py) — ama sayfanın kendisi girişsiz.
"""

import streamlit as st
import streamlit.components.v1 as components

import os
import re

# Streamlit'in kendi arayüz izlerini (sidebar, hamburger menü, "Deploy"
# butonu) gizle — müşteri bu linki açtığında sadece temiz aracı görsün,
# hiçbir dahili yönetim izi olmasın. core/danisman_ortak.py'den DEĞİL,
# bilerek burada, minimal ve bağımsız yazıldı — bu sayfa Supabase
# bağlantısına ihtiyaç duymadan, mümkün olduğunca dayanıklı kalsın diye.
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
    "assets", "satis_senaryolari_basit.html",
)

# YENİ (14.08.2026): ?kod=... ile kişiye özel veri enjeksiyonu. kod
# yoksa/bulunamazsa HTML'in kendi genel varsayılan değerleriyle açılır
# (geriye dönük uyumlu — daha önce paylaşılan genel link hâlâ çalışır).
_ALAN_ESLEME = {
    "konum": "inLocation", "oda_sayisi": "inRooms", "bina_yasi": "inAge",
    "m2": "inM2", "ozellikler": "inFeatures",
    "deger_kisa": "inShort", "deger_orta": "inMid", "deger_uzun": "inLong",
    "oneri_fiyat": "inOneri", "teklif_tutari": "inTeklif",
    "hedef_fiyat": "inP1",
    "ort_m2_fiyati": "inMarketM2",
    "piyasa_faiz_orani": "inRate",
    "aylik_maliyet": "inMonthlyCost",
}


def _deger_enjekte(html, alan_id, deger):
    """<input ... id="alanId" ...> etiketinin İÇİNE value="deger" yazar
    — zaten bir value="..." varsa üzerine yazar, yoksa (metin alanları
    gibi) ekler. Sadece o TEK etiketi hedefler (id benzersiz kabul
    edilir), HTML'in geri kalanına dokunmaz."""
    if deger in (None, ""):
        return html
    deger_str = str(deger).replace('"', "&quot;")
    desen = re.compile(rf'(<input[^>]*\bid="{re.escape(alan_id)}"[^>]*?)(\s*/?>)')

    def _degistir(m):
        etiket = m.group(1)
        if 'value="' in etiket:
            etiket = re.sub(r'value="[^"]*"', f'value="{deger_str}"', etiket)
        else:
            etiket = etiket + f' value="{deger_str}"'
        return etiket + m.group(2)

    return desen.sub(_degistir, html, count=1)


try:
    with open(_HTML_YOLU, "r", encoding="utf-8") as f:
        _html_icerik = f.read()

    kod = st.query_params.get("kod")
    # YENİ (14.08.2026): URL'deki ?musteri=... — kod ile veri
    # çekilemese bile (Supabase erişim sorunu vb.) en azından isimle
    # karşılama yapılabilsin diye ayrı, öncelikli bir kaynak. Aşağıda,
    # kod başarıyla çözülürse DB'deki musteri_adi bunu güncel tutar.
    _musteri_adi = st.query_params.get("musteri", "").replace("-", " ")

    if kod:
        try:
            from core.supabase_client import get_client
            _sb = get_client()
            _sonuc = (
                _sb.table("danisman_senaryolari")
                .select("*")
                .eq("kod", kod)
                .limit(1)
                .execute()
            )
            if _sonuc.data:
                _kayit = _sonuc.data[0]
                if not _musteri_adi:
                    _musteri_adi = _kayit.get("musteri_adi") or ""
                for _alan, _html_id in _ALAN_ESLEME.items():
                    _html_icerik = _deger_enjekte(_html_icerik, _html_id, _kayit.get(_alan))

                # "Piyasada satış süresi" (inMarketAvg) hem bilgi kutusuna
                # hem de "Ne kadar bekleyebilirsiniz?" kaydırıcısının
                # (inT, 1-12 tamsayı) başlangıcına yazılıyor — kaydırıcı
                # ondalık kabul etmediği için burada yuvarlanıp
                # sınırlanıyor.
                _sure_ham = _kayit.get("piyasa_satis_suresi")
                if _sure_ham not in (None, ""):
                    _html_icerik = _deger_enjekte(_html_icerik, "inMarketAvg", _sure_ham)
                    try:
                        _sure_int = max(1, min(12, round(float(_sure_ham))))
                        _html_icerik = _deger_enjekte(_html_icerik, "inT", _sure_int)
                    except (TypeError, ValueError):
                        pass

                # inRate kaydırıcısı %10-70 arası — bu aralığın dışında
                # bir değer gelirse sınırlanıyor (aksi halde slider
                # bozuk görünür).
                _faiz_ham = _kayit.get("piyasa_faiz_orani")
                if _faiz_ham not in (None, ""):
                    try:
                        _faiz_sinirli = max(10, min(70, float(_faiz_ham)))
                        _html_icerik = _deger_enjekte(_html_icerik, "inRate", _faiz_sinirli)
                    except (TypeError, ValueError):
                        pass
        except Exception:
            # Supabase'e ulaşılamazsa ya da kod bulunamazsa SESSİZCE genel
            # (varsayılan) araca düşülür — müşteri hiçbir hata görmez.
            pass

    # YENİ (14.08.2026): Sayfada isimle karşılama — "Eviniz İçin Üç Olası
    # Yol" başlığı "{Ad}, Eviniz İçin Üç Olası Yol" olur. _musteri_adi
    # ?musteri=... parametresinden VEYA (o yoksa) kod ile bulunan
    # kayıttaki musteri_adi'den geliyor — kod bulunamasa/Supabase'e
    # ulaşılamasa BİLE en azından ?musteri= varsa karşılama çalışır.
    # HTML'de bu başlık TEK bir yerde, sabit metin olarak geçiyor —
    # basit bir string replace yeterli, regex'e gerek yok.
    if _musteri_adi.strip():
        from html import escape as _esc
        _html_icerik = _html_icerik.replace(
            "<h1>Eviniz İçin Üç Olası Yol</h1>",
            f"<h1>{_esc(_musteri_adi.strip())}, Eviniz İçin Üç Olası Yol</h1>",
        )

    components.html(_html_icerik, height=2400, scrolling=True)
except FileNotFoundError:
    st.error(
        "Senaryo hesaplayıcı dosyası bulunamadı "
        "(assets/satis_senaryolari_basit.html) — deploy'un bu dosyayı "
        "içerdiğinden emin ol."
    )

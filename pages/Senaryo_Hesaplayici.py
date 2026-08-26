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
- İçerik assets/*.html'den OLDUĞU GİBİ okunup gömülüyor — dosyanın
  kendi CSS/JS'i tamamen bağımsız, Streamlit tarafında yeniden inşa
  edilmedi.

DÜZELTME (23.08.2026): İki farklı arayüz şablonu desteği eklendi —
"klasik" (satis_senaryolari_basit.html, tek sayfa) ve "sihirbaz"
(satis_senaryolari_sihirbaz.html, 8 adımlı, "İleri/Geri" ile ilerlenen
versiyon). Hangi şablonun kullanılacağı, kaydın "surum" alanından
okunuyor — ikisi de AYNI input ID'lerini kullandığı için (inShort,
inMid, inOneri... vb.) veri enjeksiyon mantığı (_ALAN_ESLEME) HİÇ
DEĞİŞMEDEN ikisinde de çalışıyor. Tek fark kişiselleştirme (karşılama)
enjeksiyonu — sihirbaz'da ayrı, düzenlenebilir bir #greetingInput
alanı var, klasik'te ise başlığın (h1) kendisi değiştiriliyor.

Danışmanların bu linki BULMASI için hamburger menüde bir giriş var
(core/danisman_ortak.py) — ama sayfanın kendisi girişsiz.
"""

import streamlit as st
import streamlit.components.v1 as components

import os
import re
from html import escape as _esc

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

_VARSAYILAN_DOSYA = "satis_senaryolari_basit.html"
_SURUM_DOSYALARI = {
    "klasik": "satis_senaryolari_basit.html",
    # DÜZELTME (23.08.2026): "sihirbaz" anahtarı artık 8 adımlı gerçek
    # sihirbaz dosyasına değil, ondan türetilen 3 sayfalık HİBRİT
    # dosyaya işaret ediyor — "tek tek adım adım" değil, 3 büyük sayfa
    # (Veri Girişi / Üç Olası Yol / Detaylı İnceleme), İleri-Geri ile
    # ilerleniyor. Anahtar adı (kod/veritabanı tarafında) değişmedi,
    # sadece hangi dosyaya baktığı değişti — mevcut kayıtlar bozulmaz.
    "sihirbaz": "satis_senaryolari_hibrit.html",
}

# YENİ (14.08.2026): ?kod=... ile kişiye özel veri enjeksiyonu. kod
# yoksa/bulunamazsa HTML'in kendi genel varsayılan değerleriyle açılır
# (geriye dönük uyumlu — daha önce paylaşılan genel link hâlâ çalışır).
# Her iki şablon (klasik/sihirbaz) da AYNI ID'leri kullandığı için bu
# eşleme ikisinde de değişmeden geçerli.
_ALAN_ESLEME = {
    "konum": "inLocation", "oda_sayisi": "inRooms", "bina_yasi": "inAge",
    "m2": "inM2", "ozellikler": "inFeatures",
    "mulk_turu": "inPropertyType", "imar_durumu": "inImar", "kaks_emsal": "inKaks",
    "deger_kisa": "inShort", "deger_orta": "inMid", "deger_uzun": "inLong",
    # DÜZELTME (26.08.2026): "teklif_tutari": "inTeklif" eşlemesi
    # kaldırıldı — inTeklif id'si sadece ölü sihirbaz şablonunda vardı
    # (bkz. assets/satis_senaryolari_sihirbaz.html), aktif iki şablonda
    # (basit/hibrit) hiç yok. Bu satır zaten sessizce hiçbir yere
    # yazmıyordu; danışman formundaki karşılığı da (dp_sn_teklif) aynı
    # gerekçeyle kaldırıldı (Danisman_SenaryoOlustur.py). Önerilen Fiyat
    # ve Gelen Teklif artık tek alanda (oneri_fiyat -> inOneri).
    "oneri_fiyat": "inOneri",
    "hedef_fiyat": "inP1",
    "ort_m2_fiyati": "inMarketM2",
    "piyasa_faiz_orani": "inRate",
    "aylik_maliyet": "inMonthlyCost", "tek_seferlik_maliyet": "inOneTimeCost",
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


def _link_enjekte(html, alan_id, href, yeni_metin=None):
    """<a ... id="alanId" href="...">Metin</a> etiketinin href'ini (ve
    istenirse görünen metnini) değiştirir. _deger_enjekte'nin <input>
    için yaptığını <a> etiketleri için yapar — bylineContact gibi
    tıklanabilir iletişim linkleri için (23.08.2026)."""
    if not href:
        return html
    href_str = str(href).replace('"', "&quot;")
    desen = re.compile(
        rf'(<a\b[^>]*\bid="{re.escape(alan_id)}"[^>]*?)(>)([^<]*)(</a>)'
    )

    def _degistir(m):
        etiket = m.group(1)
        etiket = re.sub(r'href="[^"]*"', f'href="{href_str}"', etiket)
        metin = _esc(yeni_metin) if yeni_metin else m.group(3)
        return etiket + m.group(2) + metin + m.group(4)

    return desen.sub(_degistir, html, count=1)


def _telefon_e164(telefon):
    """Rehberim'de kullanılan AYNI normalize mantığı — hangi formatta
    girilmiş olursa olsun (boşluklu, '0'lı, '+90'lı) son 10 haneyi alıp
    başına 90 ekler."""
    if not telefon:
        return None
    rakamlar = "".join(ch for ch in str(telefon) if ch.isdigit())
    son10 = rakamlar[-10:] if len(rakamlar) >= 10 else rakamlar
    return "90" + son10 if son10 else None


_ASSETS_DIZINI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

kod = st.query_params.get("kod")
# YENİ (14.08.2026): URL'deki ?musteri=... — kod ile veri çekilemese
# bile (Supabase erişim sorunu vb.) en azından isimle karşılama
# yapılabilsin diye ayrı, öncelikli bir kaynak. Aşağıda, kod başarıyla
# çözülürse DB'deki musteri_adi bunu güncel tutar.
_musteri_adi = st.query_params.get("musteri", "").replace("-", " ")
_kayit = None

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
    except Exception:
        # Supabase'e ulaşılamazsa ya da kod bulunamazsa SESSİZCE genel
        # (varsayılan) araca düşülür — müşteri hiçbir hata görmez.
        pass

_surum = (_kayit or {}).get("surum") or "klasik"
_dosya_adi = _SURUM_DOSYALARI.get(_surum, _VARSAYILAN_DOSYA)
_HTML_YOLU = os.path.join(_ASSETS_DIZINI, _dosya_adi)

try:
    with open(_HTML_YOLU, "r", encoding="utf-8") as f:
        _html_icerik = f.read()

    if _kayit:
        for _alan, _html_id in _ALAN_ESLEME.items():
            _html_icerik = _deger_enjekte(_html_icerik, _html_id, _kayit.get(_alan))

        # "Piyasada satış süresi" (inMarketAvg) hem bilgi kutusuna hem
        # de "Ne kadar bekleyebilirsiniz?" kaydırıcısının (inT, 1-12
        # tamsayı) başlangıcına yazılıyor — kaydırıcı ondalık kabul
        # etmediği için burada yuvarlanıp sınırlanıyor.
        _sure_ham = _kayit.get("piyasa_satis_suresi")
        if _sure_ham not in (None, ""):
            _html_icerik = _deger_enjekte(_html_icerik, "inMarketAvg", _sure_ham)
            try:
                _sure_int = max(1, min(12, round(float(_sure_ham))))
                _html_icerik = _deger_enjekte(_html_icerik, "inT", _sure_int)
            except (TypeError, ValueError):
                pass

        # inRate kaydırıcısı %10-70 arası — bu aralığın dışında bir
        # değer gelirse sınırlanıyor (aksi halde slider bozuk görünür).
        _faiz_ham = _kayit.get("piyasa_faiz_orani")
        if _faiz_ham not in (None, ""):
            try:
                _faiz_sinirli = max(10, min(70, float(_faiz_ham)))
                _html_icerik = _deger_enjekte(_html_icerik, "inRate", _faiz_sinirli)
            except (TypeError, ValueError):
                pass

    # YENİ (14.08.2026, 23.08.2026'da şablona göre ayrıştırıldı):
    # Sihirbaz şablonunda ayrı, düzenlenebilir bir #greetingInput alanı
    # var ("Sayın Müşterimiz," gibi) — kişiselleştirme oraya yazılıyor.
    # Klasik şablonda böyle bir alan yok, başlığın (h1) kendisi
    # değiştiriliyor (sabit metin, tek yerde geçiyor — basit string
    # replace yeterli).
    if _musteri_adi.strip():
        if _surum == "sihirbaz":
            _html_icerik = _deger_enjekte(_html_icerik, "greetingInput", f"Sayın {_musteri_adi.strip()},")
        else:
            _html_icerik = _html_icerik.replace(
                "<h1>Eviniz İçin Üç Olası Yol</h1>",
                f"<h1>{_esc(_musteri_adi.strip())}, Eviniz İçin Üç Olası Yol</h1>",
            )

    # DÜZELTME (23.08.2026, 2. tur): "İletişim bilgisi" artık eklenebiliyor
    # — core/personel_manager.py'nin zaten okuduğu zeta_personel_listesi.xlsx
    # üzerinden (Supabase'de ayrı bir tablo YOK, sistem zaten bu Excel'i
    # kullanıyor), kaydı oluşturan danışmanın GERÇEK e-posta/telefonunu
    # bularak "İletişime Geç" butonuna (bylineContact) yazıyoruz. Telefon
    # varsa WhatsApp'a, yoksa e-postaya yönlendiriyor. Bulunamazsa
    # (Excel yoksa, isim eşleşmezse vb.) buton HTML'in kendi jenerik
    # varsayılan mailto'sunda sessizce kalır — hata göstermiyoruz.
    # DÜZELTME (24.08.2026): Artık HER İKİ şablonda da (Klasik + Bölümlü)
    # bylineInput/bylineContact elemanları var, bu yüzden "sadece
    # sihirbaz" kısıtı kaldırıldı — ikisinde de danışman adı/iletişim
    # bilgisi doğru enjekte ediliyor.
    if _kayit and _kayit.get("danisman"):
        _html_icerik = _deger_enjekte(
            _html_icerik, "bylineInput", f"Hazırlayan: {_kayit['danisman']}"
        )
        try:
            from core.personel_manager import load_personel_listesi
            _personel_df = load_personel_listesi()
            _danisman_adi_norm = _kayit["danisman"].strip().lower()
            _eslesen = _personel_df[
                _personel_df["ad_soyad"].str.strip().str.lower() == _danisman_adi_norm
            ]
            if not _eslesen.empty:
                _satir = _eslesen.iloc[0]
                _tel = _telefon_e164(_satir.get("telefon"))
                _eposta = (_satir.get("email") or "").strip()
                if _tel:
                    _html_icerik = _link_enjekte(
                        _html_icerik, "bylineContact",
                        f"https://wa.me/{_tel}", "WhatsApp ile İletişime Geç ↗",
                    )
                elif _eposta:
                    _html_icerik = _link_enjekte(
                        _html_icerik, "bylineContact",
                        f"mailto:{_eposta}", "İletişime Geç ↗",
                    )
        except Exception:
            # Excel okunamazsa/eşleşme bulunamazsa SESSİZCE jenerik
            # varsayılana düşülür — müşteri hiçbir hata görmez.
            pass

    components.html(_html_icerik, height=2400, scrolling=True)
except FileNotFoundError:
    st.error(
        f"Senaryo hesaplayıcı dosyası bulunamadı (assets/{_dosya_adi}) — "
        "deploy'un bu dosyayı içerdiğinden emin ol."
    )

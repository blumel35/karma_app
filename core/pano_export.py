"""
core/pano_export.py

Talep/Portföy kayıtlarını tek dosyalık, bağımsız (offline açılabilen) bir
HTML "ilan panosu"na dönüştürür:

- Üstte sabit (sticky) A-Z ilçe indeksi — sadece o an listede karşılığı
  olan harfler tıklanabilir, diğerleri soluk/pasif görünür.
- Bir harfe tıklayınca sayfa o ilçe grubuna kayar (native #anchor, JS yok).
- Her ilan bir kart: İşlem Tipi rozeti (Satılık/Kiralık renk kodlu),
  özet, bütçe/fiyat, danışman, tarih.
- Karta tıklayınca (<details>/<summary>, JS gerektirmez) mail konusu ve
  temizlenmiş mail içeriği açılır.
- Tek HTML dosyası — CSS gömülü, dış bağımlılık yok, mail eki olarak da
  gönderilebilir, WhatsApp/Drive ile paylaşılabilir, tarayıcıda açılır.

rapor_export.py ile aynı yardımcı fonksiyonları (HTML temizleme, işlem
tipi normalize etme, isim/tarih kısaltma) paylaşır — mantık tekrarını
önlemek için oradan import edilir.
"""

from io import BytesIO
from datetime import datetime
from html import escape as _esc
import uuid

import streamlit as st

from core.rapor_export import (
    _islem_tipi_norm,
    _isim_ayikla,
    _tarih_kisalt,
    _html_temizle,
)

TURK_ALFABE = list("ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ")

# İlan Vitrini uygulamasının paletinden ilham alındı (krem zemin, navy/
# gold/sage vurgular, Montserrat+Inter yazı ikilisi) — Karma App'in Excel
# çıktısındaki navy/gold kimliğiyle de uyumlu, ama daha sıcak ve ferah.
CREAM = "#FBF7F0"
CREAM_2 = "#F5EFE4"
CARD_BG = "#FFFFFF"
INK = "#2B271F"
MUTED = "#8A8271"
NAVY = "#1C2B47"
NAVY_SOFT = "#4B5A76"
RED = "#C23B32"
GOLD = "#B98A2C"
SAGE = "#5F8266"
BORDER = "#E7DFCF"
BORDER_STRONG = "#D8CDB4"

SATILIK_BG = "#EFE6DA"
SATILIK_FG = GOLD
KIRALIK_BG = "#E4EEE6"
KIRALIK_FG = SAGE
BELIRSIZ_BG = "#EEE9E1"
BELIRSIZ_FG = MUTED

# İlçe kartlarının sol renk şeridi için — İlan Vitrini'ndeki districtColor
# hash mantığının Python karşılığı.
ILCE_PALET = ["#C23B32", "#1C2B47", "#B98A2C", "#5F8266", "#7A5C8E", "#3E7C8A", "#A4522E", "#5A6B4E", "#8A4A66"]


def _ilce_renk(ilce_adi):
    metin = str(ilce_adi or "")
    h = 0
    for ch in metin:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return ILCE_PALET[h % len(ILCE_PALET)]


_TR_BUYUK_HARF = {"i": "İ", "ı": "I", "ç": "Ç", "ş": "Ş", "ö": "Ö", "ü": "Ü", "ğ": "Ğ"}


def _ilce_normalize(isim):
    """
    'urla' ve 'Urla' gibi büyük/küçük harf farklılıklarının panoda AYRI
    ilçe grupları olarak görünmesini engeller — ilk harfi Türkçe'ye
    uygun büyütüp gerisini küçültür (Python'un varsayılan .capitalize()
    metodu Türkçe İ/I ayrımını doğru yapmadığı için elle yapılıyor).
    """
    isim = (isim or "").strip()
    if not isim:
        return isim
    ilk = isim[0]
    ilk_buyuk = _TR_BUYUK_HARF.get(ilk, ilk.upper())
    geri_kalan = isim[1:].lower().replace("i̇", "i")
    return ilk_buyuk + geri_kalan


def _ilce_al(v):
    ilceler = v.get("ilceler") or []
    if ilceler and ilceler[0]:
        ilce = ilceler[0]
    else:
        ilce = (v.get("ilce") or "").strip()
    if not ilce or ilce == "Diğer Bölge":
        return "Diğer"
    return _ilce_normalize(ilce)


def _harf_al(ilce_adi):
    if not ilce_adi:
        return "#"
    ilk = ilce_adi.strip()[0].upper()
    return ilk if ilk in TURK_ALFABE else "#"


def _rozet_renk(islem_tipi):
    if islem_tipi == "Satılık":
        return SATILIK_BG, SATILIK_FG
    if islem_tipi == "Kiralık":
        return KIRALIK_BG, KIRALIK_FG
    return BELIRSIZ_BG, BELIRSIZ_FG


def _kaynak_etiket(v):
    """
    İlanın nereden geldiğini gösterir:
    - 'danisman_panel' → Danışman Panosu'ndan elle girilmiş → "Zeta"
    - diğer her şey (startkey_mail, boş, vb.) → mail sisteminden gelen
      gerçek Startkey trafiği → "Startkey"
    """
    kaynak = str(v.get("kaynak") or "").strip().lower()
    if kaynak == "danisman_panel":
        return "Zeta"
    return "Startkey"


def _kart_html(v, kayit_tipi):
    islem = _islem_tipi_norm(v)
    bg, fg = _rozet_renk(islem)
    danisman = _esc(_isim_ayikla(v.get("talep_eden_danisan", "")) or "-")
    tarih = _esc(_tarih_kisalt(v.get("kayit_tarihi", "")))
    mulk = _esc(v.get("mulk_tipi") or "Belirsiz")
    oda = _esc(v.get("oda_sayisi_m2") or "-")
    ozet = _esc(v.get("ozet") or v.get("ozel_kriterler") or v.get("ozellikler") or "")
    bolge = _esc(v.get("bolge_mahalle") or "")
    ilce_rengi = _ilce_renk(_ilce_al(v))
    kaynak_etiketi = _esc(_kaynak_etiket(v))
    kaynak_sinif = "kart-kaynak kart-kaynak-zeta" if kaynak_etiketi == "Zeta" else "kart-kaynak"

    if kayit_tipi == "talep":
        deger = _esc(v.get("max_butce") or "-")
        deger_etiket = "Bütçe"
    else:
        deger = _esc(v.get("fiyat") or "-")
        deger_etiket = "Fiyat"

    konu = _esc(_html_temizle(v.get("mail_konusu", "")))
    icerik = _esc(_html_temizle(v.get("mail_icerigi", ""))).replace("\n", "<br>")

    return f"""
    <div class="kart" style="--dist-color:{ilce_rengi}">
      <div class="kart-ust">
        <span class="rozet" style="background:{bg};color:{fg}">{_esc(islem)}</span>
        <span class="kart-tarih">{tarih}</span>
      </div>
      <div class="kart-baslik">{ozet or mulk}</div>
      <div class="kart-alt">{bolge + ' · ' if bolge else ''}{mulk} · {oda}</div>
      <div class="kart-deger">{deger_etiket}: <b>{deger}</b></div>
      <div class="kart-alt-satir">
        <span class="kart-danisman">👤 {danisman}</span>
        <span class="{kaynak_sinif}">{kaynak_etiketi}</span>
      </div>
      <details class="kart-detay">
        <summary>✉ Mail içeriğini gör</summary>
        <div class="detay-konu">{konu}</div>
        <div class="detay-icerik">{icerik}</div>
      </details>
    </div>
    """


def pano_html_olustur(kayitlar, pano_basligi, kayit_tipi="talep"):
    """
    kayitlar: dict listesi (Supabase satırları)
    kayit_tipi: "talep" | "portfoy"
    Döner: BytesIO (tek dosyalık HTML içeriği)
    """
    gruplar = {}
    for v in kayitlar:
        ilce = _ilce_al(v)
        gruplar.setdefault(ilce, []).append(v)

    sirali_ilceler = sorted(gruplar.keys(), key=lambda x: (x == "Diğer", x))
    mevcut_harfler = {_harf_al(ilce) for ilce in sirali_ilceler}

    nav_parcalari = []
    for harf in TURK_ALFABE:
        if harf in mevcut_harfler:
            nav_parcalari.append(
                f'<a href="javascript:void(0)" class="harf aktif" '
                f'onclick="panoyaKaydir(\'{harf}\'); return false;">{harf}</a>'
            )
        else:
            nav_parcalari.append(f'<span class="harf pasif">{harf}</span>')
    nav_html = "\n".join(nav_parcalari)

    bolumler = []
    onceki_harf = None
    for ilce in sirali_ilceler:
        harf = _harf_al(ilce)
        veri_harf = f'data-harf-ilk="{harf}"' if harf != onceki_harf else ""
        onceki_harf = harf
        kayitlar_bu_ilce = gruplar[ilce]
        kartlar = "\n".join(_kart_html(v, kayit_tipi) for v in kayitlar_bu_ilce)
        bolumler.append(f"""
        <div class="ilce-bolum" {veri_harf}>
          <h2 class="ilce-baslik">{_esc(ilce)} <span class="ilce-sayi">({len(kayitlar_bu_ilce)})</span></h2>
          <div class="kart-grid">{kartlar}</div>
        </div>
        """)
    bolumler_html = "\n".join(bolumler)

    tarih_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    toplam = len(kayitlar)

    html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(pano_basligi)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --cream:{CREAM}; --cream-2:{CREAM_2}; --card:{CARD_BG}; --ink:{INK}; --ink-soft:{MUTED};
    --navy:{NAVY}; --navy-soft:{NAVY_SOFT}; --gold:{GOLD}; --sage:{SAGE};
    --border:{BORDER}; --border-strong:{BORDER_STRONG};
    --shadow:0 1px 2px rgba(43,39,31,.04),0 8px 22px rgba(43,39,31,.07);
    --shadow-hover:0 3px 8px rgba(43,39,31,.07),0 18px 36px rgba(43,39,31,.12);
  }}
  * {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  body {{
    margin: 0; font-family: 'Inter', sans-serif;
    background: var(--cream); color: var(--ink); min-height: 100vh;
  }}
  header {{
    max-width: 1280px; margin: 0 auto; padding: 30px 26px 18px;
  }}
  header h1 {{
    font-family: 'Montserrat', sans-serif; font-size: 27px; font-weight: 800;
    color: var(--navy); margin: 0; letter-spacing: -.01em;
  }}
  header .meta {{ margin-top: 6px; color: var(--ink-soft); font-size: 13px; }}
  nav.harfler {{
    position: sticky; top: 0; z-index: 10;
    background: rgba(251,247,240,0.92); backdrop-filter: blur(6px);
    border-bottom: 1px solid var(--border);
    padding: 10px 26px; display: flex; flex-wrap: wrap; gap: 4px;
  }}
  nav.harfler .harf {{
    display: inline-flex; align-items:center; justify-content:center;
    width: 27px; height: 27px; border-radius: 8px; font-size: 12.5px;
    font-weight: 700; font-family: 'Montserrat', sans-serif;
  }}
  nav.harfler .harf.aktif {{
    background: var(--card); color: var(--navy); text-decoration: none;
    cursor: pointer; border: 1px solid var(--border-strong); box-shadow: var(--shadow);
    transition: transform .12s ease, box-shadow .12s ease, background .12s ease;
  }}
  nav.harfler .harf.aktif:hover {{ background: var(--gold); color: #fff; transform: translateY(-1px); box-shadow: var(--shadow-hover); }}
  nav.harfler .harf.pasif {{ color: var(--border-strong); }}
  main {{ max-width: 1280px; margin: 0 auto; padding: 24px 26px 70px; }}
  .ilce-bolum {{ margin-bottom: 36px; scroll-margin-top: 76px; }}
  .ilce-baslik {{
    font-family: 'Montserrat', sans-serif; font-size: 16px; font-weight: 700;
    color: var(--navy); display: flex; align-items: baseline; gap: 8px;
    border-bottom: 2px solid var(--gold); padding-bottom: 8px; margin-bottom: 16px;
  }}
  .ilce-sayi {{ font-weight: 500; color: var(--ink-soft); font-size: 13px; font-family: 'Inter', sans-serif; }}
  .kart-grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
  }}
  .kart {{
    background: var(--card); border: 1px solid var(--border);
    border-left: 5px solid var(--dist-color, var(--navy));
    border-radius: 14px; padding: 16px 18px; box-shadow: var(--shadow);
    transition: transform .15s ease, box-shadow .15s ease;
  }}
  .kart:hover {{ transform: translateY(-3px); box-shadow: var(--shadow-hover); }}
  .kart-ust {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 9px; }}
  .rozet {{ font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 99px; }}
  .kart-tarih {{ font-size: 11px; color: var(--ink-soft); }}
  .kart-baslik {{
    font-family: 'Montserrat', sans-serif; font-weight: 700; font-size: 14.5px;
    color: var(--navy); margin-bottom: 5px; line-height: 1.35;
  }}
  .kart-alt {{ font-size: 12.5px; color: var(--ink-soft); margin-bottom: 7px; }}
  .kart-deger {{ font-size: 13.5px; margin-bottom: 4px; }}
  .kart-deger b {{ color: var(--navy); }}
  .kart-alt-satir {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 9px;
  }}
  .kart-danisman {{ font-size: 12.5px; color: var(--ink-soft); }}
  .kart-kaynak {{
    font-size: 10px; font-weight: 700; color: var(--ink-soft);
    background: var(--cream-2); border: 1px solid var(--border);
    padding: 2px 8px; border-radius: 20px; letter-spacing: .02em;
  }}
  .kart-kaynak-zeta {{
    color: var(--navy); border-color: var(--navy);
    background: #EAF0FB;
  }}
  .kart-detay summary {{
    cursor: pointer; font-size: 12.5px; color: var(--navy); font-weight: 600;
    padding-top: 8px; border-top: 1px dashed var(--border);
    list-style: none;
  }}
  .kart-detay summary::-webkit-details-marker {{ display: none; }}
  .kart-detay summary:hover {{ color: var(--gold); }}
  .kart-detay[open] summary {{ margin-bottom: 8px; }}
  .detay-konu {{ font-size: 12.5px; font-weight: 700; margin-bottom: 5px; color: var(--navy); }}
  .detay-icerik {{
    font-size: 12.5px; color: var(--ink); line-height: 1.55;
    background: var(--cream-2); border-radius: 8px; padding: 10px 12px;
  }}
  @media (max-width: 640px) {{
    header, main, nav.harfler {{ padding-left: 16px; padding-right: 16px; }}
  }}
</style>
</head>
<body>
<header>
  <h1>{_esc(pano_basligi)}</h1>
  <div class="meta">Oluşturulma: {tarih_str} &middot; Toplam kayıt: {toplam} &middot; {len(sirali_ilceler)} ilçe</div>
</header>
<nav class="harfler">{nav_html}</nav>
<main>
{bolumler_html}
</main>
<script>
function panoyaKaydir(harf) {{
  var hedef = document.querySelector('[data-harf-ilk="' + harf + '"]');
  if (!hedef) return;
  var nav = document.querySelector('nav.harfler');
  var navYuksekligi = nav ? nav.offsetHeight : 0;
  var hedefKonum = hedef.getBoundingClientRect().top + window.pageYOffset - navYuksekligi - 12;
  window.scrollTo({{ top: hedefKonum, behavior: 'smooth' }});
}}
</script>
</body>
</html>"""

    buffer = BytesIO(html.encode("utf-8"))
    buffer.seek(0)
    return buffer


PANO_BUCKET = "pano-paylasim"


def pano_yukle_ve_link_al(html_bytes, dosya_on_eki="pano"):
    """
    Üretilen HTML panoyu Supabase Storage'daki public bucket'a yükler ve
    kalıcı, tahmin edilmesi güç (rastgele token'lı) bir public URL döner.

    Bucket'ın "public=true" olması, link'i bilen herkesin dosyayı
    açabilmesini sağlar — ekstra bir giriş/şifre gerekmez. Yükleme işlemi
    ise sadece bu backend (service key ile) yapabilir, dışarıdan biri
    bucket'a dosya ekleyemez.

    NOT: supabase-py'nin storage.upload() metodundaki file_options
    (Content-Type) parametresi kütüphane sürümüne göre farklı anahtar
    isimleri bekleyebiliyor ve sessizce yok sayılabiliyor — bu da
    tarayıcının HTML'i render etmek yerine ham kaynak kod olarak
    göstermesine yol açar. Bunu kesin garanti altına almak için burada
    kütüphane yerine doğrudan Supabase Storage REST API'sine HTTP
    isteği atılıyor, Content-Type başlığı elle set ediliyor.
    """
    import requests

    supabase_url = st.secrets["supabase"]["url"].rstrip("/")
    service_key = st.secrets["supabase"]["secret_key"]

    token = uuid.uuid4().hex[:16]
    tarih_klasoru = datetime.now().strftime("%Y%m")
    dosya_yolu = f"{tarih_klasoru}/{dosya_on_eki}_{token}.html"

    yukleme_url = f"{supabase_url}/storage/v1/object/{PANO_BUCKET}/{dosya_yolu}"
    yanit = requests.post(
        yukleme_url,
        headers={
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            "Content-Type": "text/html; charset=utf-8",
            "x-upsert": "true",
        },
        data=html_bytes,
        timeout=30,
    )
    yanit.raise_for_status()

    # ÖNEMLİ: Supabase Storage, public bucket'lardaki HTML dosyalarını
    # güvenlik amaçlı "text/plain" olarak sunuyor (Content-Type'ı biz ne
    # gönderirsek gönderelim) — tarayıcı doğrudan bu linke giderse sayfa
    # render olmaz, ham kaynak kod görünür. Bu yüzden kullanıcıya Storage
    # linkini değil, Karma App içindeki Pano_Goruntule sayfasının linkini
    # veriyoruz — o sayfa dosyayı backend'de çekip kendi içinde render
    # ediyor, Supabase'in kısıtlamasını by-pass ediyor.
    try:
        app_base_url = st.secrets["app"]["base_url"].rstrip("/")
    except Exception:
        app_base_url = None

    if not app_base_url:
        st.warning(
            "⚠️ secrets.toml'da [app] bölümüne `base_url` eklenmemiş — "
            "paylaşım linki yerel adresle (localhost) üretilecek, bu link "
            "sadece bu bilgisayardan açılır, telefondan AÇILMAZ. Canlı "
            "linkin çalışması için secrets.toml'a şunu ekle:\n\n"
            '[app]\nbase_url = "https://startkey-zeta.streamlit.app"'
        )
        app_base_url = "http://localhost:8501"

    goruntuleme_url = f"{app_base_url}/Pano_Goruntule?p={dosya_yolu}"
    return goruntuleme_url


def pano_export_butonu_goster(kayitlar, pano_basligi, kayit_tipi="talep", dosya_on_eki="pano", key_prefix="pano"):
    """Sayfaya '🗂️ İlan Panosu' üretme, indirme ve paylaşım linki alma
    seçeneklerini ekler."""
    toplam = len(kayitlar)
    uret = st.button(
        f"🗂️ İlan Panosu Oluştur ({toplam} kayıt)",
        key=f"{key_prefix}_pano_btn",
        use_container_width=False,
    )
    if uret:
        if toplam == 0:
            st.warning("Panoya eklenecek kayıt yok — filtreyi genişletmeyi deneyin.")
        else:
            with st.spinner("İlan panosu hazırlanıyor..."):
                dosya = pano_html_olustur(kayitlar, pano_basligi, kayit_tipi)
            html_bytes = dosya.getvalue()
            st.session_state[f"{key_prefix}_pano_hazir"] = html_bytes

    hazir_dosya = st.session_state.get(f"{key_prefix}_pano_hazir")
    if hazir_dosya:
        dosya_adi = f"{dosya_on_eki}_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="⬇️ Bilgisayara indir",
                data=hazir_dosya,
                file_name=dosya_adi,
                mime="text/html",
                key=f"{key_prefix}_pano_download",
                use_container_width=True,
            )
        with col2:
            link_uret = st.button(
                "🔗 Paylaşım Linki Oluştur",
                key=f"{key_prefix}_pano_link_btn",
                use_container_width=True,
            )
        if link_uret:
            with st.spinner("Link oluşturuluyor..."):
                try:
                    url = pano_yukle_ve_link_al(hazir_dosya, dosya_on_eki)
                    st.session_state[f"{key_prefix}_pano_url"] = url
                except Exception as e:
                    st.error(f"Link oluşturulamadı: {e}")

        url = st.session_state.get(f"{key_prefix}_pano_url")
        if url:
            st.success("Link hazır — ofis ekibiyle paylaşabilirsin (telefon dahil, her cihazda açılır):")
            st.code(url, language=None)
            st.caption(
                "⚠️ Bu link'i bilen herkes (şifre/giriş gerekmeden) panoyu görebilir — "
                "sadece güvendiğin kişilerle paylaş."
            )

"""
pages/Danisman_StartkeyIlanlari.py

Danışman Startkey İlanları ekranı (23.09.2026) — Danışman FSBO İlanları
(pages/Danisman_FSBOIlanlari.py) ile BİREBİR AYNI iskelet, sadece kalıcı
bölge tablosu ve marka filtresi farklı. core/bolge_secici.py bu ikizliği
zaten öngörüp GENEL (tablo adı parametreli) yazılmıştı — bu ekran o
altyapının tamamlanmasıyla eklendi (bkz. core/bolge_secici.py modül üstü
not: "FSBO ve Startkey ekranları tamamlanıp...").

Meltem'in isteği (23.09.2026): "startkey ilanlarının da seçilen max 5
bölge dahilinde fsbo ilanları gibi otomatik çekilmesi." Ardından netleşen
KASITLI tasarım kararı: Startkey ilgi bölgeleri, Uzmanlık Bölgelerim'den
VE FSBO bölgelerinden TAMAMEN BAĞIMSIZ — "ben balçovada çalışırım ama bir
müşterim için karşıyaka da kiralık arayabilirim" (Meltem). Bu yüzden
KENDİ ayrı tablosunu (startkey_ilan_bolgeleri) kullanıyor, fsbo_bolgeleri
veya uzmanlik_bolgeleri ile hiç kesişmiyor.

Veri kaynağı, FSBO ile AYNI merkezi tablo — core/izmir_pazar_sync.py'nin
(günlük GitHub Actions işi ile) doldurduğu izmir_pazar_ilanlar, burada
marka='startkey' (core/revy_pazar_cek.py'deki marka_tespit() ofis adından
otomatik tespit ediyor) ile filtrelenmiş hali. Kart görünümü FSBO/Talep/
Portföy panolarıyla GÖRSEL olarak aynı — bkz. core/pano_export.py:
pazar_ilan_pano_html_olustur().

NOT: Revy'nin back-office'inden keyword="startkey" ile doğrudan çeken
daha kesin bir fonksiyon da (core/revy_pazar_cek.py: startkey_ilan_cek())
kodda hazır duruyor ama BİLEREK bağlanmadı — mevcut genel pazar taraması
(marka tespiti) FSBO ile aynı, hızlı/az riskli bir başlangıç için yeterli.
Fiyat düşüşü bildirimi gibi daha kesin takip gerektiren bir ihtiyaç
çıkarsa (planlanan 3 bildirim sisteminden biri) o zaman değerlendirilebilir.
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import date, datetime, timedelta

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.pano_export import pazar_ilan_pano_html_olustur, pazar_pano_paylasim_blogu
from core.danisman_ortak import (
    su_anki_danisman, IZMIR_ILCELERI, render_topbar, hide_sidebar_css,
    islem_tipi_filtrele, mulk_tipi_filtrele, ilce_ile_filtrele,
)
from core.bolge_secici import (
    bolgelerini_cek, bolgelerini_kaydet, etkin_ilceler, pazar_ilanlarini_cek,
    ilcenin_mahalleleri, ilce_mahallelerini_ayarla, mahalle_ile_filtrele,
    ilce_bildirim_ayarla,
)

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Startkey İlanları", ikon="🏠", geri_hedefi="pages/Danisman_Secim.py")

TABLO_ADI = "startkey_ilan_bolgeleri"
MARKA = "startkey"

su_kullanici = su_anki_danisman()
mevcut_kayitlar = bolgelerini_cek(TABLO_ADI, su_kullanici)
kalici_ilceler = [k["ilce"] for k in mevcut_kayitlar]

# ── KALICI İLÇE SEÇİMİ ───────────────────────────────────────────────
# FSBO İlanları'ndaki AYNI desen — sadece tablo adı farklı, Uzmanlık
# Bölgelerim'den ve fsbo_bolgeleri'nden BAĞIMSIZ.
secili_ozet = ", ".join(kalici_ilceler) if kalici_ilceler else "henüz seçim yok"
with st.expander(
    f"Startkey ilgi bölgelerini seç (en fazla 5) — {secili_ozet}",
    expanded=not kalici_ilceler,
):
    secim = st.multiselect(
        "Startkey bölgelerin",
        options=IZMIR_ILCELERI,
        default=kalici_ilceler,
        max_selections=5,
        key="startkey_kalici_secim",
        label_visibility="collapsed",
        placeholder="İlçe seç (en fazla 5)...",
    )
    if st.button("Kaydet", key="startkey_kalici_kaydet", type="primary"):
        try:
            bolgelerini_kaydet(TABLO_ADI, secim)
            st.success("Startkey ilgi bölgelerin kaydedildi.")
            st.rerun()
        except Exception as e:
            st.error(f"Kaydedilemedi: {e}")

# ── İLÇE BAZLI BİLDİRİMLER — FSBO İlanları'ndaki AYNI ekleme (bkz. o
# dosyadaki 01.10.2026, 2. tur notu), sadece tablo farklı.
if kalici_ilceler:
    with st.expander("İlçe bazlı bildirimler", expanded=False):
        st.caption(
            "Kapattığın bir ilçe için ilanları görmeye devam edersin — "
            "sadece o ilçe için 'yeni ilan' bildirimi gelmez."
        )
        _bildirim_durumu = {k["ilce"]: k.get("bildirim_acik", True) for k in mevcut_kayitlar}
        for _ilce in kalici_ilceler:
            _onceki_durum = _bildirim_durumu.get(_ilce, True)
            _yeni_durum = st.toggle(_ilce, value=_onceki_durum, key=f"startkey_bildirim_{_ilce}")
            if _yeni_durum != _onceki_durum:
                try:
                    ilce_bildirim_ayarla(TABLO_ADI, _ilce, _yeni_durum)
                    st.rerun()
                except Exception as e:
                    st.error(f"Kaydedilemedi: {e}")

# ── MAHALLE BAZLI DARALTMA — FSBO İlanları'ndaki AYNI düzeltme (bkz. o
# dosyadaki 01.10.2026 tarihli not), sadece tablo/marka farklı.
if kalici_ilceler:
    with st.expander("Mahalle bazlı daraltma (isteğe bağlı)", expanded=False):
        st.caption(
            "Bir ilçede mahalle seçmezsen o ilçedeki tüm mahalleler geçerli "
            "olmaya devam eder — hem listede hem bildirimlerde."
        )
        for _ilce in kalici_ilceler:
            _onceki_secim = next(
                (k.get("mahalleler") or [] for k in mevcut_kayitlar if k["ilce"] == _ilce), []
            )
            _secenekler = ilcenin_mahalleleri(_ilce, MARKA)
            if not _secenekler:
                st.caption(f"{_ilce}: bu ilçede henüz mahalle verisi yok.")
                continue
            _yeni_secim = st.multiselect(
                _ilce, options=_secenekler, default=_onceki_secim,
                key=f"startkey_mahalle_{_ilce}",
                placeholder="Tüm mahalleler (daraltma yok)",
            )
            if set(_yeni_secim) != set(_onceki_secim):
                try:
                    ilce_mahallelerini_ayarla(TABLO_ADI, _ilce, _yeni_secim)
                    st.rerun()
                except Exception as e:
                    st.error(f"Kaydedilemedi: {e}")

# ── GEÇİCİ (AD-HOC) EK BÖLGE FİLTRESİ ────────────────────────────────
# Kaydedilmez — sadece bu oturumda, kalıcı 5'liğe EK olarak ilçe(ler)
# görmek için. "bugün sadece Çeşme'ye de bakayım" senaryosu.
with st.expander("Bu oturuma özel ek ilçe göster (kaydedilmez)", expanded=False):
    gecici_secim = st.multiselect(
        "Geçici ek ilçeler",
        options=[i for i in IZMIR_ILCELERI if i not in kalici_ilceler],
        default=st.session_state.get("startkey_gecici_secim", []),
        key="startkey_gecici_secim",
        label_visibility="collapsed",
        placeholder="Kalıcı seçime ek olarak görmek istediğin ilçe(ler)...",
    )

aktif_ilceler = etkin_ilceler(kalici_ilceler, gecici_secim)

if not aktif_ilceler:
    st.info("Henüz Startkey ilgi bölgesi seçmedin — yukarıdan en fazla 5 ilçe seçip kaydet.")
    st.stop()

# ── İLAN LİSTESİ ──────────────────────────────────────────────────────
toolbar_col1, toolbar_col2 = st.columns([5, 1])
with toolbar_col1:
    st.caption(
        f"📍 Gösterilen bölgeler: {', '.join(aktif_ilceler)}"
        + (" *(geçici ek dahil)*" if gecici_secim else "")
    )
with toolbar_col2:
    if st.button("↻ Yenile", key="startkey_yenile", use_container_width=True):
        pazar_ilanlarini_cek.clear()
        st.rerun()

ilanlar_ham = pazar_ilanlarini_cek(MARKA, aktif_ilceler)

# DÜZELTME (01.10.2026) — FSBO İlanları'ndaki AYNI uygulama.
_ilce_mahalle_haritasi = {k["ilce"]: (k.get("mahalleler") or []) for k in mevcut_kayitlar}
ilanlar_ham = mahalle_ile_filtrele(ilanlar_ham, _ilce_mahalle_haritasi)

if not ilanlar_ham:
    st.info("Seçili bölge(ler)de şu an aktif Startkey ilanı yok.")
    st.stop()

# ── İŞLEM TİPİ + ZAMAN + SIRALAMA FİLTRESİ ── FSBO İlanları'ndaki AYNI
# desen — bkz. o dosyadaki NOT: otomatik pasifleştirme (TUR 2B) burada
# da aynı şekilde geçerli, "Son 7 Gün" bu yüzden varsayılan.
def _ilan_tarihi_gun(v):
    t = v.get("ilan_tarihi")
    if not t:
        return None
    try:
        return datetime.strptime(str(t)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None

# DÜZELTME (27.09.2026) — FSBO İlanları'ndaki AYNI düzeltme, bkz. o
# dosyadaki not: "Bugün" artık ilk_gorulme_tarihi'ne (tabloya İLK
# YAZILDIĞI an dolan, sonraki güncellemelerde değişmeyen zaman damgası)
# bakıyor — ilan_tarihi (Revy'nin kendi tarihi) Supabase'te doğrulandığı
# gibi güvenilmezdi. "Son 7 Gün" BİLEREK ilan_tarihi'nde bırakıldı.
def _ilk_gorulme_gun(v):
    t = v.get("ilk_gorulme_tarihi")
    if not t:
        return None
    try:
        return datetime.strptime(str(t)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None

# DÜZELTME (28.09.2026, Meltem: "bildirim sistemi başarılı oldu ama
# panoyu aç dediğinde bildirimin bahsettiği ekranı açmıyor ana sayfayı
# açıyor... hatta bugün 2 yeni ilan dediyse bugün filtresiyle ilgili
# sayfa açılmalı") — FSBO İlanları'ndaki AYNI düzeltme, bkz. o dosyadaki
# not: core/bildirim_tetikleyici.py artık Startkey "bugün X yeni ilan"
# bildirimini bu sayfaya ?zaman=bugun ile bağlıyor.
if st.query_params.get("zaman") == "bugun" and "startkey_zaman" not in st.session_state:
    st.session_state["startkey_zaman"] = "Bugün"

ilce_filtre_secim = st.multiselect(
    "İlçe (gösterilen bölgeler içinden)", aktif_ilceler,
    key="startkey_ilce_filtre", placeholder="Tüm gösterilen bölgeler",
)

islem_col, zaman_col, siralama_col, mulk_col = st.columns([1, 1, 1, 1])
with islem_col:
    islem_secim = st.radio(
        "İşlem Tipi",
        ["Tümü", "Satılık", "Kiralık"],
        horizontal=True,
        key="startkey_islem",
        label_visibility="collapsed",
    )
with mulk_col:
    mulk_secim = st.radio(
        "Mülk Tipi",
        ["Tümü", "Konut", "Ticari", "Arsa"],
        horizontal=True,
        key="startkey_mulk",
        label_visibility="collapsed",
    )
with zaman_col:
    # DÜZELTME (01.10.2026, Meltem'in ekran görüntüsünde görülen Streamlit
    # uyarısı: "widget with key 'startkey_zaman' was created with a default
    # value but also had its value set via the Session State API") — kök
    # sebep: yukarıdaki query-param bloğu (ve artık Bildirimlerim.py'den
    # gelen st.session_state["startkey_zaman"]="Bugün" ataması) widget
    # OLUŞTURULMADAN ÖNCE session_state'i dolduruyor; aynı anda index=1
    # vermek Streamlit'in "ikisini birden verme" kuralını ihlal ediyordu.
    # index artık SADECE session_state'te henüz değer yokken veriliyor.
    zaman_secim = st.radio(
        "Zaman aralığı",
        ["Tümü", "Son 7 Gün", "Bugün"],
        index=None if "startkey_zaman" in st.session_state else 1,
        horizontal=True,
        key="startkey_zaman",
        help=(
            "'Bugün', bu ilanın sistemimize İLK KEZ bugün eklendiği "
            "anlamına geliyor (ilanın kendi 'İlan tarihi'ne göre değil "
            "— o bilgi kaynağa göre gecikmeli/güvenilmez çıktı)."
        ),
    )
with siralama_col:
    siralama_secim = st.selectbox(
        "Sıralama",
        ["En Yeni İlan", "En Eski İlan", "Fiyat: Düşükten Yükseğe", "Fiyat: Yüksekten Düşüğe"],
        key="startkey_siralama",
    )

ilanlar = islem_tipi_filtrele(ilanlar_ham, islem_secim)
ilanlar = mulk_tipi_filtrele(ilanlar, mulk_secim)
ilanlar = ilce_ile_filtrele(ilanlar, ilce_filtre_secim)
if zaman_secim == "Son 7 Gün":
    esik = date.today() - timedelta(days=7)
    ilanlar = [v for v in ilanlar if (_ilan_tarihi_gun(v) or date.min) >= esik]
elif zaman_secim == "Bugün":
    bugun = date.today()
    ilanlar = [v for v in ilanlar if _ilk_gorulme_gun(v) == bugun]

if siralama_secim == "En Yeni İlan":
    ilanlar = sorted(ilanlar, key=lambda v: v.get("ilan_tarihi") or "", reverse=True)
elif siralama_secim == "En Eski İlan":
    ilanlar = sorted(ilanlar, key=lambda v: v.get("ilan_tarihi") or "")
elif siralama_secim == "Fiyat: Düşükten Yükseğe":
    ilanlar = sorted(ilanlar, key=lambda v: (v.get("fiyat") is None, v.get("fiyat") or 0))
elif siralama_secim == "Fiyat: Yüksekten Düşüğe":
    ilanlar = sorted(ilanlar, key=lambda v: (v.get("fiyat") is None, -(v.get("fiyat") or 0)))

st.caption(f"{len(ilanlar)} / {len(ilanlar_ham)} ilan gösteriliyor")

if not ilanlar:
    st.info("Bu zaman aralığında ilan yok — 'Zaman aralığı' filtresinden 'Tümü'nü dene.")
    st.stop()

# YENİ (05.10.2026 — Meltem): ekrandaki listeyi WhatsApp'ta paylaşılabilir
# bir linke çevirir (bkz. core/pano_export.py: pazar_pano_paylasim_blogu).
_n = len(ilanlar)
if zaman_secim == "Bugün":
    _mesaj = f"Bölgenizde bugün {_n} yeni Startkey ilanı eklendi."
else:
    _mesaj = f"Bölgenizde {_n} Startkey ilanı:"
pazar_pano_paylasim_blogu(ilanlar, "Startkey İlanları", _mesaj, key_prefix="startkey", dosya_on_eki="startkey")

html_buf = pazar_ilan_pano_html_olustur(ilanlar, "Startkey İlanları", baslik_goster=False)
components.html(html_buf.getvalue().decode("utf-8"), height=1800, scrolling=True)

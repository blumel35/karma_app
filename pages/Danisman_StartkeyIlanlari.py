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
from core.pano_export import pazar_ilan_pano_html_olustur
from core.danisman_ortak import (
    su_anki_danisman, IZMIR_ILCELERI, render_topbar, hide_sidebar_css,
    islem_tipi_filtrele, mulk_tipi_filtrele, ilce_ile_filtrele,
)
from core.bolge_secici import (
    bolgelerini_cek, bolgelerini_kaydet, etkin_ilceler, pazar_ilanlarini_cek,
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
    zaman_secim = st.radio(
        "Zaman aralığı",
        ["Tümü", "Son 7 Gün", "Bugün"],
        index=1,
        horizontal=True,
        key="startkey_zaman",
        help=(
            "İlan tarihi alanında saat bilgisi yok, bu yüzden 'Bugün' "
            "pratikte 'ilan tarihi bugün olanlar' anlamına geliyor."
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
    ilanlar = [v for v in ilanlar if _ilan_tarihi_gun(v) == bugun]

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

html_buf = pazar_ilan_pano_html_olustur(ilanlar, "Startkey İlanları", baslik_goster=False)
components.html(html_buf.getvalue().decode("utf-8"), height=1800, scrolling=True)

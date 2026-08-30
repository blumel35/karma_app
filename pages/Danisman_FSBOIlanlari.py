"""
pages/Danisman_FSBOIlanlari.py

Danışman FSBO İlanları ekranı (30.08.2026) — Uzmanlık Bölgelerim ile AYNI
"kalıcı 5-ilçe seçimi" iskeletini kullanır, ama FSBO'ya özel iki farkla:

1) Kalıcı seçim KENDİ tablosunda (fsbo_bolgeleri) tutulur — Uzmanlık
   Bölgelerim'den ve (ileride gelecek) Startkey İlanları ekranından
   TAMAMEN BAĞIMSIZ (core/bolge_secici.py'de gerekçesi var).
2) Kalıcı seçime EK, bu ekrana özel bir "geçici bölge" filtresi var —
   oturum boyunca geçerli, hiçbir yere kaydedilmeyen, "bugün sadece bakmak
   istediğim" bir ilçeyi kalıcı 5'liği bozmadan görmeye yarar. Meltem'in
   isteği: "sırayla başlayalım. özellikle fsbo ekranında kullanım
   pratiğine göre eklemeler yapabiliriz" — bu yüzden bu ekran BİLEREK
   basit tutuldu, gerçek kullanımdan gelecek geri bildirime göre
   genişletilecek.

Veri kaynağı, danışmanın kendi girdiği talep/portföy kayıtları DEĞİL —
core/izmir_pazar_sync.py'nin (günlük GitHub Actions işi ile) doldurduğu
izmir_pazar_ilanlar merkezi tablosu, marka='mulk_sahibi' (mülk sahibinden
/ FSBO) ile filtrelenmiş hali. Kart görünümü Talep/Portföy panolarıyla
GÖRSEL olarak aynı ama favori/danışman-sahipliği kavramı yok — bkz.
core/pano_export.py: pazar_ilan_pano_html_olustur().
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import date, datetime, timedelta

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.pano_export import pazar_ilan_pano_html_olustur
from core.danisman_ortak import su_anki_danisman, IZMIR_ILCELERI, render_topbar, hide_sidebar_css
from core.bolge_secici import (
    bolgelerini_cek, bolgelerini_kaydet, etkin_ilceler, pazar_ilanlarini_cek,
)

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("FSBO İlanları", ikon="🏷️", geri_hedefi="pages/Danisman_Secim.py")

TABLO_ADI = "fsbo_bolgeleri"
MARKA = "mulk_sahibi"

su_kullanici = su_anki_danisman()
mevcut_kayitlar = bolgelerini_cek(TABLO_ADI, su_kullanici)
kalici_ilceler = [k["ilce"] for k in mevcut_kayitlar]

# ── KALICI İLÇE SEÇİMİ ───────────────────────────────────────────────
# Uzmanlık Bölgelerim'deki AYNI desen (09.08.2026'da netleşen, 12.08.2026'da
# düzeltilen expander başlığı deseni) — sadece tablo adı farklı.
secili_ozet = ", ".join(kalici_ilceler) if kalici_ilceler else "henüz seçim yok"
with st.expander(
    f"FSBO takip ettiğin ilçeleri seç (en fazla 5) — {secili_ozet}",
    expanded=not kalici_ilceler,
):
    secim = st.multiselect(
        "FSBO bölgelerin",
        options=IZMIR_ILCELERI,
        default=kalici_ilceler,
        max_selections=5,
        key="fsbo_kalici_secim",
        label_visibility="collapsed",
        placeholder="İlçe seç (en fazla 5)...",
    )
    if st.button("Kaydet", key="fsbo_kalici_kaydet", type="primary"):
        try:
            bolgelerini_kaydet(TABLO_ADI, secim)
            st.success("FSBO bölgelerin kaydedildi.")
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
        default=st.session_state.get("fsbo_gecici_secim", []),
        key="fsbo_gecici_secim",
        label_visibility="collapsed",
        placeholder="Kalıcı seçime ek olarak görmek istediğin ilçe(ler)...",
    )

aktif_ilceler = etkin_ilceler(kalici_ilceler, gecici_secim)

if not aktif_ilceler:
    st.info("Henüz FSBO bölgesi seçmedin — yukarıdan en fazla 5 ilçe seçip kaydet.")
    st.stop()

# ── İLAN LİSTESİ ──────────────────────────────────────────────────────
toolbar_col1, toolbar_col2 = st.columns([5, 1])
with toolbar_col1:
    st.caption(
        f"📍 Gösterilen bölgeler: {', '.join(aktif_ilceler)}"
        + (" *(geçici ek dahil)*" if gecici_secim else "")
    )
with toolbar_col2:
    if st.button("↻ Yenile", key="fsbo_yenile", use_container_width=True):
        pazar_ilanlarini_cek.clear()
        st.rerun()

ilanlar_ham = pazar_ilanlarini_cek(MARKA, aktif_ilceler)

if not ilanlar_ham:
    st.info("Seçili bölge(ler)de şu an aktif FSBO ilanı yok.")
    st.stop()

# ── ZAMAN + SIRALAMA FİLTRESİ (30.08.2026 — Meltem'in geri bildirimi) ──
# NOT: izmir_pazar_sync.py'de otomatik pasifleştirme BİLİNÇLİ OLARAK
# kapalı (TUR 2A) — yani "aktif" alanı, bir ilan piyasadan gerçekten
# kalksa bile şu an güvenilir şekilde değişmiyor. Bu yüzden tek başına
# "aktif=True" filtresi hâlâ çok eski ilanları da getirebiliyor. Zaman
# filtresi bunu TAM çözmüyor (o, ayrı bir senkronizasyon işi — TUR 2B),
# ama pratikte listeyi güncel/anlamlı ilanlara indirgemenin en basit yolu
# — bu yüzden varsayılan "Son 7 Gün" seçili geliyor, "Tümü" her zaman
# bir tık uzakta.
def _ilan_tarihi_gun(v):
    t = v.get("ilan_tarihi")
    if not t:
        return None
    try:
        return datetime.strptime(str(t)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None

zaman_col, siralama_col = st.columns([1, 1])
with zaman_col:
    zaman_secim = st.radio(
        "Zaman aralığı",
        ["Tümü", "Son 7 Gün", "Bugün"],
        index=1,
        horizontal=True,
        key="fsbo_zaman",
        help=(
            "İlan tarihi alanında saat bilgisi yok, bu yüzden 'Bugün' "
            "pratikte 'ilan tarihi bugün olanlar' anlamına geliyor."
        ),
    )
with siralama_col:
    siralama_secim = st.selectbox(
        "Sıralama",
        ["En Yeni İlan", "En Eski İlan", "Fiyat: Düşükten Yükseğe", "Fiyat: Yüksekten Düşüğe"],
        key="fsbo_siralama",
    )

ilanlar = ilanlar_ham
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

html_buf = pazar_ilan_pano_html_olustur(ilanlar, "FSBO İlanları", baslik_goster=False)
components.html(html_buf.getvalue().decode("utf-8"), height=1800, scrolling=True)

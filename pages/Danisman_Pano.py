"""
pages/Danisman_Pano.py

Karma App'e entegre, canlı (statik export DEĞİL) bir sayfa:
- Mevcut Karma App giriş sistemini kullanır (core.auth.oturum_kontrol) —
  ayrı bir kimlik doğrulama sistemi yok, danışmanlar zaten sahip
  oldukları hesapla girer.
- Talep Panosu ve Portföy Panosu'nu SUPABASE'DEN HER AÇILIŞTA CANLI
  çeker — statik pano (core/pano_export.py + Pano_Goruntule.py) gibi
  "anlık görüntü" değil, her zaman güncel.
- GÖRSEL TASARIM: core/pano_export.py'deki (krem zemin, A-Z indeks,
  ilçeye göre renkli kartlar) aynı üretici fonksiyon (pano_html_olustur)
  burada da kullanılıyor — sadece statik export listesi yerine CANLI
  Supabase sorgusu besleniyor. Kod tekrarı yok, tasarım birebir aynı.
- Danışman kendi talebini/portföyünü küçük bir formla doğrudan
  Supabase'e ekleyebilir (AI/mail işleme adımına hiç girmeden — zaten
  yapılandırılmış, temiz veri). Eklenen kayıt hem bu sayfada hem Karma
  App'in Talep Merkezi / Portföy Merkezi'nde ANINDA görünür, çünkü aynı
  tabloları kullanıyorlar.
"""

import uuid
from datetime import datetime, timezone

import streamlit as st
import streamlit.components.v1 as components

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol, cikis_yap
from core.supabase_client import get_client
from core.pano_export import pano_html_olustur

# NOT: Bu sayfa BİLEREK core.ui_helpers.render_navbar() ÇAĞIRMIYOR —
# Karma App'in kalabalık menüsü/navbar'ı burada hiç görünmesin diye.
# Bu, "Karma App'ten bağımsız, sade bir mini-arayüz" hedefinin
# görsel/mimari karşılığı. Giriş yapılmamışsa da Karma App'in ana
# giriş ekranına (pages/giris.py) DEĞİL, kendi sade giriş ekranına
# (pages/Danisman_Giris.py) yönlendiriyor.
if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

st.markdown("""
<style>
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stHeader"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

_baslik_col, _cikis_col = st.columns([5, 1])
with _baslik_col:
    st.title("📋 Danışman Panosu")
    st.caption("Talep ve portföyleri canlı takip edin, kendi talep/portföyünüzü hızlıca ekleyin.")
with _cikis_col:
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if st.button("Çıkış Yap", use_container_width=True):
        cikis_yap()
        st.switch_page("pages/Danisman_Giris.py")

supabase = get_client()


@st.cache_data(ttl=60, show_spinner=False)
def _talepleri_cek():
    resp = (
        supabase.table("alici_talepleri")
        .select("*")
        .eq("kategori", "alici_talebi")
        .eq("parse_status", "parsed")
        .order("kayit_tarihi", desc=True)
        .limit(200)
        .execute()
    )
    return resp.data or []


@st.cache_data(ttl=60, show_spinner=False)
def _portfoyleri_cek():
    resp = (
        supabase.table("portfoyler")
        .select("*")
        .order("kayit_tarihi", desc=True)
        .limit(200)
        .execute()
    )
    return resp.data or []


def _yeni_talep_ekle(ilce, mulk_tipi, oda, butce, islem_tipi, ozet, danisman_adi):
    kayit = {
        "kayit_tarihi": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000"),
        "talep_eden_danisan": danisman_adi,
        "bolge_mahalle": "",
        "oda_sayisi_m2": oda,
        "max_butce": butce,
        "ozel_kriterler": ozet,
        "iletisim_not": "",
        "mail_konusu": f"[Danışman Panosu] {ozet[:80]}",
        "mail_icerigi": ozet,
        "message_id": f"<danisman-panel-{uuid.uuid4().hex}@karma-app>",
        "kaynak_klasor": "danisman_panel",
        "kategori": "alici_talebi",
        "ozet": ozet,
        "islem_tipi": islem_tipi,
        "mulk_tipi": mulk_tipi,
        "il": "İzmir",
        "ilce": ilce,
        "ilceler": [ilce] if ilce else [],
        "kaynak": "danisman_panel",
        "parse_status": "parsed",
        "ai_processed_at": datetime.now(timezone.utc).isoformat(),
    }
    supabase.table("alici_talepleri").insert(kayit).execute()


def _yeni_portfoy_ekle(ilce, mulk_tipi, oda, fiyat, islem_tipi, ozet, danisman_adi):
    kayit = {
        "kayit_tarihi": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000"),
        "talep_eden_danisan": danisman_adi,
        "bolge_mahalle": "",
        "oda_sayisi_m2": oda,
        "fiyat": fiyat,
        "ozet": ozet,
        "ozellikler": ozet,
        "islem_tipi": islem_tipi,
        "mulk_tipi": mulk_tipi,
        "ilce": ilce,
        "ilceler": [ilce] if ilce else [],
        "kaynak": "danisman_panel",
        "message_id": f"<danisman-panel-{uuid.uuid4().hex}@karma-app>",
    }
    supabase.table("portfoyler").insert(kayit).execute()


# ── YENİ KAYIT EKLEME ────────────────────────────────────────────────
with st.expander("➕ Yeni Talep / Portföy Ekle", expanded=False):
    kayit_tipi_secim = st.radio(
        "Ne eklemek istiyorsun?", ["Talep", "Portföy"],
        horizontal=True, key="dp_kayit_tipi",
    )
    with st.form("dp_yeni_kayit_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            f_islem = st.selectbox("İşlem Tipi", ["Satılık", "Kiralık"], key="dp_islem")
            f_ilce = st.text_input("İlçe", key="dp_ilce")
            f_mulk = st.selectbox(
                "Mülk Tipi", ["Konut", "Arsa", "İşyeri/Ticari", "Villa", "Diğer"],
                key="dp_mulk",
            )
        with col2:
            f_oda = st.text_input("Oda Sayısı / m²", placeholder="örn. 2+1", key="dp_oda")
            if kayit_tipi_secim == "Talep":
                f_deger = st.text_input("Max Bütçe", placeholder="örn. 5.000.000 TL", key="dp_butce")
            else:
                f_deger = st.text_input("Fiyat", placeholder="örn. 4.500.000 TL", key="dp_fiyat")
        f_ozet = st.text_area("Özet / Açıklama", key="dp_ozet", height=80)

        gonder = st.form_submit_button("Kaydet", type="primary", use_container_width=True)

        if gonder:
            if not f_ilce or not f_ozet:
                st.error("İlçe ve Özet alanları zorunlu.")
            else:
                danisman_adi = (
                    st.session_state.get("user_name")
                    or st.session_state.get("kullanici", {}).get("email", "")
                )
                try:
                    if kayit_tipi_secim == "Talep":
                        _yeni_talep_ekle(f_ilce, f_mulk, f_oda, f_deger, f_islem, f_ozet, danisman_adi)
                    else:
                        _yeni_portfoy_ekle(f_ilce, f_mulk, f_oda, f_deger, f_islem, f_ozet, danisman_adi)
                    st.success("✅ Kaydedildi! Talep/Portföy Merkezi'nde ve aşağıdaki panoda görünecek.")
                    _talepleri_cek.clear()
                    _portfoyleri_cek.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Kaydedilemedi: {e}")

st.divider()

# ── CANLI PANO — pano_export.py'nin tasarımı, canlı veriyle ─────────
sekme_talep, sekme_portfoy = st.tabs(["📥 Talep Panosu", "🏘️ Portföy Panosu"])

with sekme_talep:
    if st.button("🔄 Yenile", key="dp_yenile_talep"):
        _talepleri_cek.clear()
        st.rerun()
    talepler = _talepleri_cek()
    if not talepler:
        st.info("Henüz kayıt yok.")
    else:
        html_buf = pano_html_olustur(talepler, "Talep Panosu (Canlı)", kayit_tipi="talep")
        components.html(html_buf.getvalue().decode("utf-8"), height=1800, scrolling=True)

with sekme_portfoy:
    if st.button("🔄 Yenile", key="dp_yenile_portfoy"):
        _portfoyleri_cek.clear()
        st.rerun()
    portfoyler = _portfoyleri_cek()
    if not portfoyler:
        st.info("Henüz kayıt yok.")
    else:
        html_buf = pano_html_olustur(portfoyler, "Portföy Panosu (Canlı)", kayit_tipi="portfoy")
        components.html(html_buf.getvalue().decode("utf-8"), height=1800, scrolling=True)

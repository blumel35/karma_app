import base64
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.ui_helpers import render_navbar

render_navbar(
    user_role=st.session_state.get("user_role", "danisan"),
    user_name=st.session_state.get("user_name", ""),
    user_initials=st.session_state.get("user_initials", ""),
)

ROOT_DIR = Path(__file__).resolve().parent.parent
PAGE_DIR  = Path(__file__).resolve().parent

HERO_CANDIDATES = [
    PAGE_DIR / "bostanli_hero.jpeg",
    PAGE_DIR / "bostanli_gunbatimi.jpg",
    PAGE_DIR / "bostanli_gunbatimi.jpeg",
    PAGE_DIR / "bostanlı_gunbatimi.jpg",
    PAGE_DIR / "bostanlı_gunbatimi.jpeg",
]
HERO_IMAGE = next((p for p in HERO_CANDIDATES if p.exists()), None)

ROUTES = {
    "taleplerim":     "pages/taleplerim.py",
    "portfoylerim":   "pages/portfoylerím.py",
    "sunum":          "pages/Sunum_Merkezi_V2_Demo.py",
    "ajandam":        "pages/ajandam.py",
    "talep_havuzu":   "pages/2_Talep_Tablosu.py",
    "portfoy_havuzu": "pages/3_Portfoy_Tablosu.py",
    "arsiv":          "pages/2_Talep_Arsiv.py",
    "ofis":           "pages/4_Ofis_Paneli.py",
    "operasyon":      "pages/operasyon_merkezi.py",
    "sozlesme":       "pages/sozlesmeler_ve_formlar.py",
    "eslestirme":     "pages/eslestirme_motoru.py",
}

# ── query_param ile navigasyon ────────────────────────────────────────────────
nav_target = st.query_params.get("nav")
if nav_target and nav_target in ROUTES:
    st.query_params.clear()
    page_path = ROUTES[nav_target]
    if (ROOT_DIR / page_path).exists():
        st.switch_page(page_path)
    else:
        st.toast("Bu modül henüz aktif değil.", icon="ℹ️")


def _image_data_uri(path) -> str:
    if path is None:
        return ""
    try:
        ext = path.suffix.lower().lstrip(".")
        mime = "jpeg" if ext in ("jpg", "jpeg") else ext
        data = base64.b64encode(path.read_bytes()).decode("utf-8")
        return f"data:image/{mime};base64,{data}"
    except Exception:
        return ""


hero_uri = _image_data_uri(HERO_IMAGE)
hero_bg_css = f"""
    background-image:
        linear-gradient(90deg,
            rgba(255,255,255,.88) 0%,
            rgba(255,255,255,.62) 30%,
            rgba(255,255,255,.10) 58%,
            rgba(255,255,255,.00) 100%
        ),
        url('{hero_uri}');
    background-size: cover;
    background-position: center 38%;
""" if hero_uri else "background: linear-gradient(135deg,#183153,#2563A8);"

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
.stApp {{ background: #F5F3EE !important; }}
[data-testid="stHeader"] {{ display: none !important; }}
[data-testid="stAppViewContainer"] > .main .block-container {{
    max-width: 1360px !important;
    padding: 1.2rem 2rem 3rem 2rem !important;
}}

/* ── Hero ── */
.hero {{
    position: relative;
    height: 210px;
    border-radius: 20px;
    overflow: hidden;
    border: 1px solid #E7E2D9;
    box-shadow: 0 4px 18px rgba(24,49,83,.09);
    margin-bottom: 18px;
    {hero_bg_css}
}}
.hero-content {{
    position: relative; z-index: 2;
    padding: 28px 36px;
}}
.hero-eyebrow {{
    font-size: .70rem; letter-spacing: .18em;
    text-transform: uppercase; color: #8A7A60;
    font-weight: 700; margin-bottom: 8px;
}}
.hero-title {{
    font-size: 2rem; font-weight: 800;
    color: #183153; letter-spacing: -.035em;
    line-height: 1.08; margin-bottom: 6px;
}}
.hero-subtitle {{ font-size: .92rem; color: #5F6775; line-height: 1.5; }}
.hero-location {{
    position: absolute; right: 22px; bottom: 16px; z-index: 2;
    font-size: .78rem; font-weight: 600;
    color: rgba(255,255,255,.93);
    text-shadow: 0 1px 6px rgba(0,0,0,.55);
}}

/* ── Hızlı İşlemler üst bar ── */
.quick-bar {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 24px;
}}
.quick-item {{
    background: #FFFFFF;
    border: 1px solid #E7E2D9;
    border-radius: 12px;
    padding: 13px 18px;
    display: flex; align-items: center; gap: 10px;
    cursor: pointer;
    text-decoration: none !important;
    transition: background .13s, box-shadow .13s;
    box-shadow: 0 1px 4px rgba(24,49,83,.05);
}}
.quick-item:hover {{
    background: #F5F1EA;
    box-shadow: 0 3px 10px rgba(24,49,83,.09);
}}
.quick-item-icon {{ font-size: 1.1rem; line-height: 1; }}
.quick-item-label {{
    font-size: .88rem; font-weight: 600; color: #183153;
}}

/* ── Bölüm başlığı ── */
.sec-head {{
    font-size: 1.1rem; font-weight: 700;
    color: #183153; letter-spacing: -.02em;
    margin: 0 0 14px 0;
}}

/* ── Kokpit grid ── */
.kokpit-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 24px;
}}
.kokpit-card {{
    background: #FFFFFF;
    border: 1px solid #E7E2D9;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(24,49,83,.05);
}}
.kokpit-card-head {{
    padding: 18px 20px 14px 20px;
    border-bottom: 1px solid #F0EDE6;
    display: flex; align-items: flex-start; gap: 12px;
}}
.kokpit-badge {{
    width: 38px; height: 38px; border-radius: 10px;
    background: #EEF1F6;
    display: flex; align-items: center; justify-content: center;
    font-size: .95rem; font-weight: 800; color: #183153;
    flex: 0 0 38px;
}}
.kokpit-card-title {{ font-size: .97rem; font-weight: 700; color: #183153; }}
.kokpit-card-desc  {{ font-size: .77rem; color: #87909E; margin-top: 3px; line-height: 1.4; }}

/* ── Kokpit satır ── */
.kokpit-row {{
    display: flex; align-items: center;
    padding: 11px 20px;
    border-bottom: 1px solid #F5F2EC;
    cursor: pointer;
    text-decoration: none !important;
    transition: background .12s;
}}
.kokpit-row:last-child {{ border-bottom: none; }}
.kokpit-row:hover {{ background: #FAFAF7; }}
.kokpit-row-icon {{
    width: 28px; height: 28px; border-radius: 8px;
    background: #F2F4F7;
    display: flex; align-items: center; justify-content: center;
    font-size: .85rem; flex: 0 0 28px; margin-right: 12px;
}}
.kokpit-row-label {{ font-size: .875rem; font-weight: 600; color: #2C3E55; flex: 1; }}
.kokpit-row-arrow {{ font-size: .8rem; color: #C0C8D2; }}

/* ── Alt grid ── */
.alt-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr 0.85fr;
    gap: 16px;
}}
.alt-card {{
    background: #FFFFFF;
    border: 1px solid #E7E2D9;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(24,49,83,.05);
}}
.alt-card-head {{
    padding: 16px 20px 12px 20px;
    border-bottom: 1px solid #F0EDE6;
}}
.alt-card-title {{ font-size: .92rem; font-weight: 700; color: #183153; }}
.alt-card-body {{ padding: 18px 20px; }}
.empty-state {{
    display: flex; flex-direction: column;
    align-items: center; gap: 10px;
    padding: 18px 0;
    color: #B0B8C4; font-size: .83rem;
}}
.empty-icon {{ font-size: 2rem; opacity: .45; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-content">
    <div class="hero-eyebrow">STARTKEY ZETA</div>
    <div class="hero-title">Merhaba Meltem</div>
    <div class="hero-subtitle">Bugünün fırsatlarını ve çalışma alanlarını buradan yönetin.</div>
  </div>
  <div class="hero-location">Bostanlı • İzmir</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# HIZLI İŞLEMLER — HTML anchor + ?nav= query param
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="quick-bar">
  <a class="quick-item" href="?nav=taleplerim">
    <span class="quick-item-icon">➕</span>
    <span class="quick-item-label">Yeni Talep</span>
  </a>
  <a class="quick-item" href="?nav=portfoylerim">
    <span class="quick-item-icon">🏠</span>
    <span class="quick-item-label">Yeni Portföy</span>
  </a>
  <a class="quick-item" href="?nav=sunum">
    <span class="quick-item-icon">📊</span>
    <span class="quick-item-label">Sunum Oluştur</span>
  </a>
  <a class="quick-item" href="?nav=eslestirme">
    <span class="quick-item-icon">🔗</span>
    <span class="quick-item-label">Eşleşmeleri Kontrol Et</span>
  </a>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ÇALIŞMA KOKPİTİ — tam HTML, sıfır st.button
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-head">Çalışma Kokpiti</div>', unsafe_allow_html=True)

st.markdown("""
<div class="kokpit-grid">

  <!-- Çalışma Alanım -->
  <div class="kokpit-card">
    <div class="kokpit-card-head">
      <div class="kokpit-badge">W</div>
      <div>
        <div class="kokpit-card-title">Çalışma Alanım</div>
        <div class="kokpit-card-desc">Kendi taleplerinizi, portföylerinizi ve günlük planınızı yönetin.</div>
      </div>
    </div>
    <a class="kokpit-row" href="?nav=taleplerim">
      <div class="kokpit-row-icon">📋</div>
      <span class="kokpit-row-label">Taleplerim</span>
      <span class="kokpit-row-arrow">›</span>
    </a>
    <a class="kokpit-row" href="?nav=portfoylerim">
      <div class="kokpit-row-icon">🏠</div>
      <span class="kokpit-row-label">Portföylerim</span>
      <span class="kokpit-row-arrow">›</span>
    </a>
    <a class="kokpit-row" href="?nav=sunum">
      <div class="kokpit-row-icon">📊</div>
      <span class="kokpit-row-label">Sunum Merkezi</span>
      <span class="kokpit-row-arrow">›</span>
    </a>
    <a class="kokpit-row" href="?nav=ajandam">
      <div class="kokpit-row-icon">📅</div>
      <span class="kokpit-row-label">Ajandam</span>
      <span class="kokpit-row-arrow">›</span>
    </a>
  </div>

  <!-- Ortak Havuzlar -->
  <div class="kokpit-card">
    <div class="kokpit-card-head">
      <div class="kokpit-badge">P</div>
      <div>
        <div class="kokpit-card-title">Ortak Havuzlar</div>
        <div class="kokpit-card-desc">Paylaşılan talepler ve portföyleri inceleyin.</div>
      </div>
    </div>
    <a class="kokpit-row" href="?nav=talep_havuzu">
      <div class="kokpit-row-icon">📥</div>
      <span class="kokpit-row-label">Talep Havuzu</span>
      <span class="kokpit-row-arrow">›</span>
    </a>
    <a class="kokpit-row" href="?nav=portfoy_havuzu">
      <div class="kokpit-row-icon">🏘️</div>
      <span class="kokpit-row-label">Portföy Havuzu</span>
      <span class="kokpit-row-arrow">›</span>
    </a>
    <a class="kokpit-row" href="?nav=arsiv">
      <div class="kokpit-row-icon">🗄️</div>
      <span class="kokpit-row-label">Arşiv Merkezi</span>
      <span class="kokpit-row-arrow">›</span>
    </a>
  </div>

  <!-- Zeta Paneli -->
  <div class="kokpit-card">
    <div class="kokpit-card-head">
      <div class="kokpit-badge">Z</div>
      <div>
        <div class="kokpit-card-title">Zeta Paneli</div>
        <div class="kokpit-card-desc">Ofis ve operasyon süreçlerini takip edin.</div>
      </div>
    </div>
    <a class="kokpit-row" href="?nav=ofis">
      <div class="kokpit-row-icon">📈</div>
      <span class="kokpit-row-label">Ofis Paneli</span>
      <span class="kokpit-row-arrow">›</span>
    </a>
    <a class="kokpit-row" href="?nav=operasyon">
      <div class="kokpit-row-icon">🔧</div>
      <span class="kokpit-row-label">Operasyon Merkezi</span>
      <span class="kokpit-row-arrow">›</span>
    </a>
    <a class="kokpit-row" href="?nav=sozlesme">
      <div class="kokpit-row-icon">📄</div>
      <span class="kokpit-row-label">Sözleşmeler ve Formlar</span>
      <span class="kokpit-row-arrow">›</span>
    </a>
  </div>

</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ALT BÖLÜM
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-head">Bugünün Akışı</div>', unsafe_allow_html=True)

st.markdown("""
<div class="alt-grid">

  <!-- Bugün Neler Oluyor -->
  <div class="alt-card">
    <div class="alt-card-head">
      <div class="alt-card-title">Bugün Neler Oluyor?</div>
    </div>
    <div class="alt-card-body">
      <div class="empty-state">
        <div class="empty-icon">📭</div>
        <span>Henüz kayıt bulunmuyor.</span>
      </div>
    </div>
  </div>

  <!-- Ajandam -->
  <div class="alt-card">
    <div class="alt-card-head">
      <div class="alt-card-title">Ajandam</div>
    </div>
    <div class="alt-card-body">
      <div class="empty-state">
        <div class="empty-icon">📆</div>
        <span>Henüz kayıt bulunmuyor.</span>
      </div>
    </div>
  </div>

  <!-- Hızlı İşlemler -->
  <div class="alt-card">
    <div class="alt-card-head">
      <div class="alt-card-title">Hızlı İşlemler</div>
    </div>
    <a class="kokpit-row" href="?nav=taleplerim">
      <div class="kokpit-row-icon">➕</div>
      <span class="kokpit-row-label">Yeni Talep</span>
      <span class="kokpit-row-arrow">›</span>
    </a>
    <a class="kokpit-row" href="?nav=portfoylerim">
      <div class="kokpit-row-icon">🏠</div>
      <span class="kokpit-row-label">Yeni Portföy</span>
      <span class="kokpit-row-arrow">›</span>
    </a>
    <a class="kokpit-row" href="?nav=sunum">
      <div class="kokpit-row-icon">📊</div>
      <span class="kokpit-row-label">Sunum Oluştur</span>
      <span class="kokpit-row-arrow">›</span>
    </a>
    <a class="kokpit-row" href="?nav=eslestirme">
      <div class="kokpit-row-icon">🔗</div>
      <span class="kokpit-row-label">Eşleşmeleri Kontrol Et</span>
      <span class="kokpit-row-arrow">›</span>
    </a>
  </div>

</div>
""", unsafe_allow_html=True)

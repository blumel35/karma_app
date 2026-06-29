# pages/ana_sayfa.py
# Startkey Zeta — Ana Sayfa (Hero layout, tam ekran arka plan)

import streamlit as st
import base64, sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Ana sayfa — sidebar yok, tam ekran hero

# ── Arka plan fotoğrafını base64'e çevir ─────────────────────────────────────
def _img_b64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""

# Fotoğraf yolu — pages/ içindeyse veya assets/ içindeyse
_img_paths = [
    os.path.join(os.path.dirname(__file__), "izmir_zeytin.jpg"),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "izmir_zeytin.jpg"),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "izmir_zeytin.jpg"),
]
_b64 = ""
for p in _img_paths:
    if os.path.exists(p):
        _b64 = _img_b64(p)
        break

_bg_style = (
    f'background-image: url("data:image/jpeg;base64,{_b64}");'
    if _b64 else
    "background: linear-gradient(135deg, #0D1B2A 0%, #1E3A5F 50%, #2D1B00 100%);"
)

# ── Kullanıcı bilgisi ─────────────────────────────────────────────────────────
_kullanici = st.session_state.get("kullanici", {})
_ad = (_kullanici.get("ad_soyad") or _kullanici.get("ad") or
       st.session_state.get("user_name", ""))
_ad_goster = _ad.split()[0] if _ad else "Danışman"

# ── Menü kartları ─────────────────────────────────────────────────────────────
KARTLAR = [
    [
        {"icon": "🏠", "baslik": "Portföylerim",    "aciklama": "Portföylerinizi yönetin",    "path": "pages/3_Portfoy_Tablosu.py"},
        {"icon": "🗄",  "baslik": "Portföy Havuzu",  "aciklama": "Havuzdaki tüm portföyler",   "path": "pages/3_Portfoy_Tablosu.py"},
    ],
    [
        {"icon": "👥", "baslik": "Taleplerim",       "aciklama": "Taleplerinizi yönetin",      "path": "pages/2_Talep_Tablosu.py"},
        {"icon": "🔍", "baslik": "Talep Havuzu",     "aciklama": "Havuzdaki tüm talepler",     "path": "pages/2_Talep_Tablosu.py"},
    ],
    [
        {"icon": "🎯", "baslik": "Eşleştirme",       "aciklama": "Akıllı eşleştirmeleri gör", "path": "pages/eslestirme_motoru.py"},
        {"icon": "📢", "baslik": "Sunum Merkezi",    "aciklama": "Hazır ve paylaşılan sunumlar","path": "pages/Sunum_Merkezi_V2_Demo.py"},
    ],
    [
        {"icon": "📊", "baslik": "Ofis Paneli",      "aciklama": "Ofisin performansını izleyin","path": "pages/4_Ofis_Paneli.py"},
        {"icon": "⚙️", "baslik": "Operasyon",        "aciklama": "İş akışlarınızı yönetin",   "path": "pages/operasyon_paneli.py"},
    ],
]

# ── CSS + HTML ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
/* Tüm Streamlit padding'i kaldır */
[data-testid="stAppViewContainer"] > .main {{
    padding: 0 !important;
    margin: 0 !important;
}}
[data-testid="stAppViewContainer"] > .main > .block-container {{
    padding: 0 !important;
    max-width: 100% !important;
}}
[data-testid="stVerticalBlock"] {{
    gap: 0 !important;
}}
[data-testid="stHeader"] {{ display: none !important; }}

/* Sidebar bu sayfada gizli */
[data-testid="stSidebar"] {{ display: none !important; }}
[data-testid="collapsedControl"] {{ display: none !important; }}
[data-testid="stAppViewContainer"] > .main {{ margin-left: 0 !important; }}

/* Hero container */
.sk-hero {{
    {_bg_style}
    background-size: cover;
    background-position: center 40%;
    min-height: 100vh;
    position: relative;
    display: flex;
    flex-direction: column;
}}

/* Koyu overlay */
.sk-overlay {{
    position: absolute;
    inset: 0;
    background: linear-gradient(
        to bottom,
        rgba(0,0,0,0.45) 0%,
        rgba(0,0,0,0.25) 35%,
        rgba(0,0,0,0.70) 100%
    );
}}

/* Üst nav bar */
.sk-topbar {{
    position: relative;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 36px;
}}
.sk-logo {{
    display: flex;
    align-items: center;
    gap: 10px;
}}
.sk-logo-icon {{
    font-size: 24px;
}}
.sk-logo-text {{
    font-size: 18px;
    font-weight: 800;
    color: #fff;
    letter-spacing: 0.05em;
}}
.sk-logo-text span {{
    color: #E87722;
}}
.sk-topbar-right {{
    display: flex;
    align-items: center;
    gap: 20px;
}}
.sk-notif {{
    position: relative;
    cursor: pointer;
    font-size: 20px;
    color: rgba(255,255,255,0.85);
}}
.sk-notif-badge {{
    position: absolute;
    top: -4px; right: -6px;
    background: #E87722;
    color: #fff;
    border-radius: 999px;
    font-size: 9px;
    font-weight: 700;
    padding: 1px 5px;
    line-height: 1.4;
}}
.sk-avatar {{
    width: 38px; height: 38px;
    border-radius: 50%;
    background: rgba(232,119,34,0.3);
    border: 2px solid #E87722;
    display: flex; align-items: center;
    justify-content: center;
    font-size: 13px; font-weight: 700;
    color: #E87722;
    cursor: pointer;
}}

/* Hero metin */
.sk-hero-body {{
    position: relative;
    z-index: 10;
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: 0 36px 24px;
}}
.sk-greeting {{
    font-size: 14px;
    color: #E87722;
    font-weight: 600;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
    font-family: 'Segoe UI', sans-serif;
}}
.sk-name {{
    font-size: 42px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.02em;
    line-height: 1.1;
    margin-bottom: 10px;
    font-family: 'Segoe UI', sans-serif;
}}
.sk-sub {{
    font-size: 14px;
    color: rgba(255,255,255,0.65);
    font-family: 'Segoe UI', sans-serif;
    margin-bottom: 28px;
}}
.sk-accent-line {{
    width: 48px; height: 3px;
    background: #E87722;
    border-radius: 2px;
    margin-bottom: 28px;
}}

/* Kart grid */
.sk-cards {{
    position: relative;
    z-index: 10;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    padding: 0 36px 32px;
}}
.sk-col {{
    display: flex;
    flex-direction: column;
    gap: 10px;
}}
.sk-kart {{
    background: rgba(255, 248, 240, 0.92);
    backdrop-filter: blur(12px);
    border-radius: 14px;
    padding: 16px 18px;
    display: flex;
    align-items: center;
    gap: 14px;
    cursor: pointer;
    transition: all 0.2s ease;
    border: 1px solid rgba(232,119,34,0.15);
    text-decoration: none;
}}
.sk-kart:hover {{
    background: rgba(255, 255, 255, 0.98);
    transform: translateY(-2px);
    box-shadow: 0 8px 28px rgba(232,119,34,0.2);
    border-color: rgba(232,119,34,0.4);
}}
.sk-kart-icon {{
    width: 42px; height: 42px;
    border-radius: 12px;
    background: rgba(232,119,34,0.12);
    display: flex; align-items: center;
    justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
}}
.sk-kart-text {{}}
.sk-kart-baslik {{
    font-size: 13px;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 2px;
    font-family: 'Segoe UI', sans-serif;
}}
.sk-kart-aciklama {{
    font-size: 11px;
    color: #64748b;
    font-family: 'Segoe UI', sans-serif;
}}
.sk-kart-arrow {{
    margin-left: auto;
    font-size: 16px;
    color: #E87722;
    flex-shrink: 0;
    opacity: 0.7;
}}
</style>

<div class="sk-hero">
  <div class="sk-overlay"></div>

  <div class="sk-topbar">
    <div class="sk-logo">
      <span class="sk-logo-icon">🔑</span>
      <span class="sk-logo-text">STARTKEY <span>ZETA</span></span>
    </div>
    <div class="sk-topbar-right">
      <div class="sk-notif">
        🔔
        <span class="sk-notif-badge">3</span>
      </div>
      <div class="sk-notif">
        ✉️
        <span class="sk-notif-badge" style="background:#1E3A5F;">12</span>
      </div>
      <div class="sk-avatar">
        {(_ad[:2].upper() if _ad else "SK")}
      </div>
    </div>
  </div>

  <div class="sk-hero-body">
    <div class="sk-greeting">Hoş Geldiniz,</div>
    <div class="sk-name">{_ad_goster} Hanım</div>
    <div class="sk-accent-line"></div>
    <div class="sk-sub">Gayrimenkul operasyonlarınızı tek merkezden yönetin.</div>

    <div class="sk-cards">
""", unsafe_allow_html=True)

# ── Kart sütunları (Streamlit butonlarıyla) ───────────────────────────────────
cols = st.columns(4, gap="small")
for ci, (col, col_kartlar) in enumerate(zip(cols, KARTLAR)):
    with col:
        for kart in col_kartlar:
            st.markdown(f"""
            <div class="sk-kart">
              <div class="sk-kart-icon">{kart['icon']}</div>
              <div class="sk-kart-text">
                <div class="sk-kart-baslik">{kart['baslik']}</div>
                <div class="sk-kart-aciklama">{kart['aciklama']}</div>
              </div>
              <div class="sk-kart-arrow">›</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(kart["baslik"], key=f"krt_{ci}_{kart['baslik']}",
                        use_container_width=True):
                st.switch_page(kart["path"])

st.markdown("</div></div></div>", unsafe_allow_html=True)

# ── Kart butonlarını gizle (sadece HTML kartlar görünsün) ─────────────────────
st.markdown("""
<style>
/* Ana sayfa kart butonlarını gizle */
[data-testid="stMain"] [data-testid="stButton"] > button {
    position: absolute !important;
    opacity: 0 !important;
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    pointer-events: none !important;
}
/* Kart div'lerini tıklanabilir hale getir için overlay */
.sk-kart {{
    position: relative;
    z-index: 1;
}}
</style>
""", unsafe_allow_html=True)

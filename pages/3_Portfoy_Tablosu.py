import streamlit as st
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from core.ui_helpers import render_navbar, render_page_title_selector, render_page_header
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.supabase_client import get_client
import pandas as pd
import re
from datetime import date, timedelta, datetime
from email.utils import parsedate_to_datetime


# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────

def fmt_gonderen(g):
    if not g: return ""
    m = re.match(r'^([^<]+)', g)
    return m.group(1).strip().strip('"') if m else g

def isim_ayikla(g):
    return fmt_gonderen(g)

# ── SAYFA UX / STATE BAŞLANGIÇ ────────────────────────────────────────────

def safe_key(value):
    return re.sub(r"[^a-zA-Z0-9_ğüşöçıİĞÜŞÖÇ-]", "_", str(value or ""))




PORTFOY_UI_DEFAULTS = {
    "pft_hizli": "Son 7 gün",
    "aktif_portfoy_workspace": "Tümü",
    "pft_gorunum": "Tablo",
    "show_portfoy_filters_panel": False,
}

st.markdown("""
<style>
:root {
    --bg: #F4F7FB;
    --card: #FFFFFF;
    --text: #0F172A;
    --muted: #64748B;
    --primary: #355C7D;
    --primary-hover: #446B8B;
    --accent: #E85D75;
    --success: #22C55E;
    --warning: #F59E0B;
    --border: #DCE4EE;
    --chip-bg: #EEF4FA;
    --hover-bg: #F8FBFF;
}

.stApp { background: var(--bg); }

.block-container {
    padding-top: 0.5rem;
    padding-bottom: 2rem;
    max-width: 1520px;
}

div[data-testid="stButton"] > button {
    white-space: normal;
    line-height: 1.2;
    border-radius: 8px;
    border: 1px solid var(--border);
    min-height: 30px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
    background: var(--chip-bg);
    color: var(--text);
    transition: all 0.16s ease-in-out;
}

div[data-testid="stButton"] > button p {
    font-size: 12px !important;
    line-height: 1.2 !important;
    margin: 0 !important;
}

div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stButton"] > button[kind="primary"]:focus {
    background: var(--primary) !important;
    border-color: var(--primary) !important;
    color: #ffffff !important;
    box-shadow: 0 2px 8px rgba(53, 92, 125, 0.18) !important;
}

div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: var(--primary-hover) !important;
    border-color: var(--primary-hover) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 12px rgba(53, 92, 125, 0.16) !important;
}

div[data-testid="stButton"] > button[kind="secondary"] {
    background: var(--hover-bg) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
}

div[data-testid="stButton"] > button[kind="secondary"]:hover {
    background: #f4f8fd !important;
    border-color: #cad7e7 !important;
    box-shadow: 0 2px 8px rgba(53, 92, 125, 0.08) !important;
}

div[data-testid="stButton"] > button:hover {
    border-color: #c8d7e5;
    box-shadow: 0 1px 4px rgba(53, 92, 125, 0.08);
}

[data-testid="stContainer"] {
    border-radius: 10px;
    border-color: var(--border) !important;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
    background: #ffffff;
}

.stCaption { color: var(--muted) !important; }

h1 {
    color: var(--text);
    letter-spacing: -0.7px;
    font-size: 1.4rem !important;
    margin-bottom: 0.1rem !important;
}

h2, h3, h4 { color: #1f2937; letter-spacing: -0.2px; }

div[data-baseweb="select"] > div {
    border-radius: 6px !important;
    border-color: var(--border) !important;
    min-height: 32px !important;
    font-size: 12px !important;
}

input { border-radius: 6px !important; font-size: 12px !important; }
input::placeholder { color: #94a3b8 !important; opacity: 1 !important; }
label, .stSelectbox label, .stTextInput label {
    color: #475569 !important; font-weight: 600 !important; font-size: 11px !important;
}

.red-badge {
    display: inline-block; background: #faeeda; color: #633806;
    border: 1px solid #f5d9a0; padding: 1px 6px; border-radius: 999px;
    font-size: 10px; font-weight: 700; margin-left: 3px;
}

.fav-section-title {
    font-size: 10px; font-weight: 750; color: #8a6124;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;
}

.firsat-row {
    display: flex; gap: 8px; align-items: center;
    flex-wrap: wrap; padding: 6px 0 4px 0; margin-bottom: 8px;
}
.fchip {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 6px 14px; border-radius: 999px;
    font-size: 12.5px; font-weight: 700; cursor: pointer;
    white-space: nowrap; border: none;
    transition: all 0.15s ease; font-family: inherit; line-height: 1;
}
.fchip-tumu { background: #f1f5f9; color: #475569; border: 1px solid #dce4ee; }
.fchip-tumu.active { background: linear-gradient(135deg,#1E3A5F,#355C7D); color:#fff; border-color:transparent; }
.fchip-ilce { background: linear-gradient(135deg,#fff1f3 0%,#fff8f0 100%); color:#b91c1c; border:1px solid #fca5a5; }
.fchip-ilce:hover { background: linear-gradient(135deg,#ffe4e6 0%,#fff0e6 100%); box-shadow:0 2px 8px rgba(220,38,38,0.18); }
.fchip-ilce.active { background: linear-gradient(135deg,#b91c1c,#dc2626); color:#fff; border-color:transparent; box-shadow:0 3px 10px rgba(185,28,28,0.25); }
.fchip-yeni { background:#16a34a; color:white; border-radius:999px; font-size:10px; font-weight:750; padding:1px 6px; margin-left:3px; }
.fchip-ekle { background:transparent; color:#94a3b8; border:1px dashed #dce4ee; font-weight:600; }
.fchip-ekle:hover { border-color:#b91c1c; color:#b91c1c; }

.kart-kriter { font-size:11.5px; font-style:italic; color:#94a3b8; line-height:1.45; margin-bottom:6px;
    display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }

.nkart {
    background: var(--color-background-primary, #fff);
    border: 0.5px solid #e2e8f0; border-radius: 12px;
    overflow: hidden; display: flex; flex-direction: column;
    transition: border-color 0.15s, box-shadow 0.15s; margin-bottom: 10px;
}
.nkart:hover { border-color: #b0c4d8; box-shadow: 0 4px 16px rgba(15,23,42,0.08); }
.nkart-topbar { height: 3px; width: 100%; }
.nkart-body { padding: 12px 14px 8px; flex: 1; display: flex; flex-direction: column; gap: 6px; }
.nkart-district { font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; }
.nkart-title { font-size: 13px; font-weight: 700; color: #0F172A; line-height: 1.4; margin: 0; }
.nkart-desc { font-size: 11px; color: #64748B; line-height: 1.5; flex: 1;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.nkart-meta { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
.nkart-price { font-size: 14px; font-weight: 600; color: #0F172A; }
.nkart-price-empty { font-size: 11px; color: #94a3b8; font-style: italic; }
.nkart-date { font-size: 10px; color: #94a3b8; }
.nkart-footer {
    border-top: 0.5px solid #e9eef5; padding: 8px 14px;
    background: #f8fafc; display: flex; align-items: center;
    justify-content: space-between; gap: 6px;
}
.nkart-avatar {
    width: 22px; height: 22px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 9px; font-weight: 700; flex-shrink: 0;
}
.nkart-agent { font-size: 11px; color: #64748B; display: flex; align-items: center; gap: 5px; }

.nbadge-yeni {
    background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; font-weight: 700;
    display: inline-flex; align-items: center; gap: 4px;
    padding: 2px 8px; border-radius: 999px; font-size: 10px;
}
.dot-live {
    width: 5px; height: 5px; border-radius: 50%; background: #16a34a;
    display: inline-block; animation: pulse-dot 1.4s infinite;
}
@keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:0.3} }
.nbadge-goruldu {
    background: #f1f5f9; color: #94a3b8; border: 1px solid #e2e8f0;
    font-size: 10px; padding: 2px 7px; border-radius: 999px; font-weight: 600;
}

.zt-dot {
    display: inline-block; width: 7px; height: 7px;
    border-radius: 50%; margin-right: 6px; flex-shrink: 0; margin-top: 3px;
}
.zt-dot-yeni { background: #16a34a; box-shadow: 0 0 0 2px rgba(22,163,74,0.15); }
.zt-dot-aktif { background: #ca8a04; }
.zt-dot-bekle { background: #f59e0b; }
.zt-row-title {
    font-size: 12px; font-weight: 600; color: #1e293b;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    max-width: 95%; display: block;
}
.zt-row-desc {
    font-size: 10.5px; color: #64748b; margin-left: 13px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block;
}
.zt-ilce-tag { display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: 600; white-space: nowrap; }
.zt-tip-satilik { background: #fef2f2; color: #991b1b; }
.zt-tip-kiralik { background: #f0fdf4; color: #166534; }
.zt-tip-belirsiz { background: #f8fafc; color: #64748b; }
.zt-butce { font-size: 11.5px; font-weight: 600; color: #0f172a; }
.zt-avatar {
    width: 22px; height: 22px; border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 8px; font-weight: 600; color: #fff;
    vertical-align: middle; margin-right: 5px; flex-shrink: 0;
}
.zt-agent { display: flex; align-items: center; overflow: hidden; }
.zt-agent-name { font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.zt-tarih { font-size: 10.5px; color: #94a3b8; line-height: 1.4; }
.zt-fav-star { color: #f59e0b; }

.filtre-badge {
    display: inline-block; background: #ff4d4f; color: white;
    border-radius: 999px; font-size: 10px; font-weight: 700;
    padding: 0 5px; margin-left: 4px; vertical-align: middle;
    line-height: 16px; height: 16px;
}
.kart-wrapper { position: relative; }

</style>
""", unsafe_allow_html=True)

for _k, _v in PORTFOY_UI_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── SIDEBAR — erken çağır (collapsed sorunu önler) ───────────────────────────
render_navbar(
    user_role=st.session_state.get("user_role", "danisan"),
    user_name=st.session_state.get("user_name", ""),
    user_initials=st.session_state.get("user_initials", ""),
)

def portfoy_secim_butonu(label, value, state_key, key_prefix):
    aktif = st.session_state.get(state_key) == value
    if st.button(
        label,
        key=f"{key_prefix}_{safe_key(value)}",
        use_container_width=True,
        type="primary" if aktif else "secondary"
    ):
        st.session_state[state_key] = value
        st.rerun()


def html_temizle(text):
    if not text: return ""
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.DOTALL|re.IGNORECASE)
    text = re.sub(r"<script.*?>.*?</script>", " ", text, flags=re.DOTALL|re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&#x[0-9a-fA-F]+;|&[a-zA-Z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()

# ── Standart badge paleti (talep tablosu ile aynı) ───────────────────────────
BADGE_PALETTE = {
    "Satılık": ("#FCEBEB", "#A32D2D", "#f5c0c0"),
    "Kiralık": ("#FAEEDA", "#854F0B", "#f0d0a0"),
    "Konut":   ("#f1f5f9", "#475569", "#e2e8f0"),
    "İşyeri":  ("#f1f5f9", "#475569", "#e2e8f0"),
    "Arsa":    ("#f1f5f9", "#475569", "#e2e8f0"),
}

def etiket_html(etiket):
    if not etiket or etiket in ("Belirsiz", "Belirtilmemiş"):
        return ""
    cfg = BADGE_PALETTE.get(etiket, ("#f1f5f9", "#475569", "#e2e8f0"))
    bg, fg, border = cfg
    return (
        f'<span style="background:{bg};color:{fg};border:1px solid {border};'
        f'padding:2px 8px;border-radius:20px;font-size:10.5px;font-weight:600;'
        f'margin-right:4px;display:inline-block;">{etiket}</span>'
    )

def nbadge(etiket, cls=None):
    if not etiket or etiket in ("Belirsiz","Belirtilmemiş"):
        return ""
    cfg = BADGE_PALETTE.get(etiket, ("#f1f5f9", "#475569", "#e2e8f0"))
    bg, fg, border = cfg
    return (
        f'<span style="background:{bg};color:{fg};border:1px solid {border};'
        f'padding:2px 7px;border-radius:20px;font-size:10.5px;font-weight:600;'
        f'margin-right:3px;display:inline-block;">{etiket}</span>'
    )

def avatar_html(isim, aks_r):
    if not isim:
        return '<div style="width:22px;height:22px;border-radius:50%;background:#f1f5f9;color:#94a3b8;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;flex-shrink:0;">?</div>'
    harfler = "".join(p[0].upper() for p in isim.split()[:2] if p)
    return (
        f'<div style="width:22px;height:22px;border-radius:50%;background:{aks_r["bg"]};'
        f'color:{aks_r["text"]};display:flex;align-items:center;justify-content:center;'
        f'font-size:9px;font-weight:700;flex-shrink:0;">{harfler}</div>'
    )

def tarih_parse(s):
    if not s: return None
    try: return parsedate_to_datetime(str(s))
    except: pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try: return datetime.strptime(str(s)[:len(fmt)], fmt)
        except: continue
    return None

def en_iyi_tarih(v):
    return (
        v.get("ilan_tarihi")
        or v.get("mail_tarihi")
        or v.get("paylasim_tarihi")
        or v.get("gonderim_tarihi")
        or v.get("tarih")
        or v.get("kayit_tarihi")
        or v.get("olusturma_tarihi")
        or ""
    )

def tarih_gun_farki(s):
    d = tarih_parse(s)
    if not d: return 9999
    _d = d.date() if hasattr(d, 'date') and callable(d.date) else d
    return (date.today() - _d).days

def fiyat_sayisal(s):
    if not s: return float('inf')
    t = re.sub(r'[^\d]', '', str(s))
    try: return float(t) if t else float('inf')
    except: return float('inf')

def il_grubu(v):
    il = (v.get("il") or "").strip()
    return il if il not in ("","Diğer",None) else ""

def ilce_grubu(v):
    ilceler = v.get("ilceler") or []
    for i in ilceler:
        if i and i not in ("","Diğer Bölge"):
            return i
    ilce = (v.get("ilce") or "").strip()
    return ilce if ilce not in ("","Diğer Bölge") else ""

def ilce_istatistik(ilce, kayitlar):
    k = [v for v in kayitlar if ilce in (v.get("ilceler") or [])]
    yeni = [v for v in k if tarih_gun_farki(en_iyi_tarih(v)) <= 7]
    return len(k), len(yeni)

def siralama_uygula(liste, siralama):
    if   siralama == "Tarih ↓": return sorted(liste, key=lambda v: tarih_gun_farki(en_iyi_tarih(v)))
    elif siralama == "Tarih ↑": return sorted(liste, key=lambda v: tarih_gun_farki(en_iyi_tarih(v)), reverse=True)
    elif siralama == "İlçe A→Z": return sorted(liste, key=lambda v: (ilce_grubu(v) or "").lower())
    elif siralama == "İlçe Z→A": return sorted(liste, key=lambda v: (ilce_grubu(v) or "").lower(), reverse=True)
    elif siralama == "Fiyat ↑": return sorted(liste, key=lambda v: fiyat_sayisal(v.get("fiyat","")))
    elif siralama == "Fiyat ↓": return sorted(liste, key=lambda v: fiyat_sayisal(v.get("fiyat","")), reverse=True)
    return liste


# ── İzmir Aks UX yardımcıları ──────────────────────────────────────────────
# Aks renk paleti
AKS_RENK = {
    "Yarımada":  {"bar": "#D85A30", "text": "#993C1D", "bg": "#FAECE7", "light": "#fdf2ef"},
    "Kuzey Aksı":{"bar": "#378ADD", "text": "#185FA5", "bg": "#E6F1FB", "light": "#eff6ff"},
    "Merkez Aks":{"bar": "#1D9E75", "text": "#0F6E56", "bg": "#E1F5EE", "light": "#f0fdf9"},
    "Güney Aksı":{"bar": "#8B5CF6", "text": "#5B21B6", "bg": "#EDE9FE", "light": "#f5f3ff"},
    "Diğer":     {"bar": "#94a3b8", "text": "#475569", "bg": "#f1f5f9", "light": "#f8fafc"},
}

IZMIR_AKS_MAP = {
    "Yarımada": ["Güzelbahçe", "Narlıdere", "Balçova", "Urla", "Çeşme", "Karaburun", "Seferihisar"],
    "Kuzey Aksı": ["Karşıyaka", "Çiğli", "Menemen", "Foça", "Aliağa", "Dikili", "Bergama", "Kınık"],
    "Merkez Aks": ["Konak", "Bayraklı", "Bornova", "Buca", "Karabağlar", "Gaziemir"],
    "Güney Aksı": ["Menderes", "Torbalı", "Selçuk", "Tire", "Ödemiş", "Bayındır", "Kiraz", "Beydağ"],
}


def aks_adi_bul(ilce):
    for aks, ilceler in IZMIR_AKS_MAP.items():
        if ilce in ilceler:
            return aks
    return "Diğer İzmir"



def aks_renk_bul(ilce_listesi):
    if not ilce_listesi:
        return AKS_RENK["Diğer"]
    for ilce in ilce_listesi:
        for aks, ilceler in IZMIR_AKS_MAP.items():
            if ilce in ilceler:
                return AKS_RENK[aks]
    return AKS_RENK["Diğer"]

def aks_bar_gradient(ilce_listesi):
    if not ilce_listesi:
        return AKS_RENK["Diğer"]["bar"]
    akslar = []
    for ilce in ilce_listesi:
        for aks, ilceler in IZMIR_AKS_MAP.items():
            if ilce in ilceler and aks not in akslar:
                akslar.append(aks)
    if not akslar:
        return AKS_RENK["Diğer"]["bar"]
    if len(akslar) == 1:
        return AKS_RENK[akslar[0]]["bar"]
    renkler = [AKS_RENK[a]["bar"] for a in akslar[:3]]
    pct = 100 // len(renkler)
    stops = []
    for i, r in enumerate(renkler):
        stops.append(f"{r} {i*pct}%")
        stops.append(f"{r} {(i+1)*pct}%")
    return f"linear-gradient(90deg, {', '.join(stops)})"

def kayit_ilce_listesi(v):
    ilceler = v.get("ilceler") or []
    temiz = [i for i in ilceler if i and i != "Diğer Bölge"]
    if temiz:
        return temiz
    tek = ilce_grubu(v)
    return [tek] if tek else []


def kayit_ilce_listesi(v):
    ilceler = v.get("ilceler") or []
    temiz = [i for i in ilceler if i and i != "Diğer Bölge"]
    if temiz:
        return temiz
    tek = ilce_grubu(v)
    return [tek] if tek else []


def ilce_kayit_sayisi(kayitlar, ilce):
    ilgili = [v for v in kayitlar if ilce in kayit_ilce_listesi(v)]
    yeni = [v for v in ilgili if tarih_gun_farki(en_iyi_tarih(v)) <= 7]
    return len(ilgili), len(yeni)


def render_compact_aks_haritasi(kayitlar, state_key, key_prefix, entity_label="kayıt"):
    """İzmir ilçelerini aks bazlı, kompakt chip/card görünümünde gösterir."""
    st.markdown(
        """
        <div style="font-size:12px;font-weight:800;color:#475569;letter-spacing:.8px;text-transform:uppercase;margin:8px 0 6px 0;">
            İzmir Aks Haritası
        </div>
        """,
        unsafe_allow_html=True,
    )

    secili_ilce = st.session_state.get(state_key)
    aks_items = list(IZMIR_AKS_MAP.items())
    cols = st.columns(4)

    for idx, (aks, ilceler) in enumerate(aks_items):
        with cols[idx % 4]:
            with st.container(border=True):
                st.markdown(
                    f"<div style='font-size:13px;font-weight:800;color:#0f172a;margin-bottom:6px;'>{aks}</div>",
                    unsafe_allow_html=True,
                )
                for ilce in ilceler:
                    toplam, yeni = ilce_kayit_sayisi(kayitlar, ilce)
                    if toplam <= 0:
                        continue
                    badge = f" · 🔴 {yeni} yeni" if yeni > 0 else ""
                    aktif = secili_ilce == ilce
                    label = f"{ilce} · {toplam} {entity_label}{badge}"
                    if st.button(
                        label,
                        key=f"{key_prefix}_aks_{safe_key(ilce)}",
                        use_container_width=True,
                        type="primary" if aktif else "secondary",
                    ):
                        st.session_state[state_key] = None if aktif else ilce
                        st.rerun()

    if secili_ilce:
        if st.button(f"Seçili ilçeyi temizle: {secili_ilce}", key=f"{key_prefix}_aks_clear", use_container_width=True):
            st.session_state[state_key] = None
            st.rerun()

# ── DB işlemleri ──────────────────────────────────────────────────────────

def favori_guncelle(kid, mevcut):
    try:
        get_client().table("portfoyler").update({"favori": not mevcut}).eq("id", kid).execute()
        st.cache_data.clear(); st.rerun()
    except Exception as e: st.error(f"Hata: {e}")

def not_kaydet(kid, metin):
    try:
        get_client().table("portfoyler").update({"not_alani": metin}).eq("id", kid).execute()
        st.cache_data.clear(); st.rerun()
    except Exception as e: st.error(f"Hata: {e}")

def kayit_guncelle(kid, data):
    try:
        get_client().table("portfoyler").update(data).eq("id", kid).execute()
        st.session_state.pop(f"duzen_{kid}", None)
        st.session_state[f"guncellendi_{kid}"] = True
        st.cache_data.clear(); st.rerun()
    except Exception as e: st.error(f"Hata: {e}")

def belirtilmemise_tasi(kid):
    try:
        get_client().table("portfoyler").update(
            {"il":"","ilce":"","ilceler":[],"mahalle":"","bolge":""}
        ).eq("id", kid).execute()
        st.session_state[f"guncellendi_{kid}"] = True
        st.cache_data.clear(); st.rerun()
    except Exception as e: st.error(f"Hata: {e}")


def portfoy_sil(kid):
    """Sadece manuel girilen portföyleri sil."""
    try:
        get_client().table("portfoyler").delete().eq("id", kid).execute()
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Silme hatası: {e}")

def kayit_gizle(kid):
    try:
        get_client().table("portfoyler").update({"gizli": True}).eq("id", kid).execute()
        st.cache_data.clear(); st.rerun()
    except Exception as e: st.error(f"Hata: {e}")

@st.cache_data(ttl=3600)
def ilce_listesi_cek():
    try:
        r = get_client().table("ilceler").select("ilce").execute()
        return sorted([x["ilce"] for x in r.data if x.get("ilce")])
    except: return []

@st.cache_data(ttl=60)
def favori_ilceleri_cek():
    try:
        r = get_client().table("kullanici_tercihleri")\
            .select("favori_ilceler").eq("kullanici_ad","varsayilan").execute()
        if r.data: return r.data[0].get("favori_ilceler") or []
        return []
    except: return []

def favori_ilce_guncelle(ilceler):
    try:
        get_client().table("kullanici_tercihleri")\
            .update({"favori_ilceler": ilceler})\
            .eq("kullanici_ad","varsayilan").execute()
        st.cache_data.clear()
    except Exception as e: st.error(f"Hata: {e}")

@st.cache_data(ttl=30)
def verileri_yukle(kaynak_filtre=None):
    """
    ÖNEMLİ DÜZELTME: Eskiden `.limit(500)` vardı — tablo 500 satırı geçince
    en eski kayıtlar bu sayfadan görünmez oluyordu (veri kaybı yok, sadece
    erişim yok). Artık `.range()` ile tüm kayıtlar sayfa sayfa çekiliyor.
    """
    def _sayfali_cek(builder_fn):
        tum = []
        sayfa_boyu = 1000
        bas = 0
        while True:
            r = builder_fn().range(bas, bas + sayfa_boyu - 1).execute()
            parca = r.data or []
            tum.extend(parca)
            if len(parca) < sayfa_boyu:
                break
            bas += sayfa_boyu
        return tum

    try:
        if kaynak_filtre == "startkey_mail":
            def _b1():
                return (
                    get_client().table("portfoyler").select("*")
                    .order("olusturma_tarihi", desc=True)
                    .eq("kaynak", "startkey_mail")
                )

            def _b2():
                return (
                    get_client().table("portfoyler").select("*")
                    .order("olusturma_tarihi", desc=True)
                    .is_("kaynak", "null")
                )
            return _sayfali_cek(_b1) + _sayfali_cek(_b2)

        def _builder():
            q = get_client().table("portfoyler").select("*").order("olusturma_tarihi", desc=True)
            if kaynak_filtre:
                if isinstance(kaynak_filtre, list):
                    q = q.in_("kaynak", kaynak_filtre)
                else:
                    q = q.eq("kaynak", kaynak_filtre)
            return q

        return _sayfali_cek(_builder)
    except Exception as e:
        st.error(f"Veri yüklenemedi: {e}")
        return []


@st.cache_data(ttl=3600)
def gd_listesi_cek_portfoy():
    try:
        r = get_client().table("portfoyler").select("talep_eden_danisan").execute()
        isimler = sorted(set(
            isim_ayikla(v.get("talep_eden_danisan",""))
            for v in r.data if v.get("talep_eden_danisan","")
        ))
        return [i for i in isimler if i]
    except Exception:
        return []


def ai_parse_portfoy(metin: str) -> dict:
    import requests, json
    prompt = f"""Aşağıdaki gayrimenkul portföy açıklamasını analiz et ve JSON olarak döndür.
Sadece JSON döndür, başka hiçbir şey yazma.

Portföy:
{metin}

JSON formatı:
{{
  "il": "İzmir",
  "ilce": "birincil ilçe veya boş",
  "ilceler": ["ilçe1", "ilçe2"],
  "mulk_tipi": "Konut/İşyeri/Arsa/Belirsiz",
  "islem_tipi": "Satılık/Kiralık/Belirsiz",
  "oda_sayisi_m2": "3+1 veya 120 m² gibi",
  "fiyat": "rakam ve para birimi",
  "mahalle": "mahalle/semt bilgisi",
  "ozel_kriterler": "özellikler, notlar",
  "ozet": "mülk tipini ve özelliklerini özetleyen kısa cümle (şehir adı yazma, sadece mülk özelliği)",
  "ilan_linki": "varsa ilan linki veya boş"
}}"""
    try:
        api_key = st.secrets["anthropic"]["api_key"].strip()
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        data = resp.json()
        if "error" in data:
            return {"_parse_hatasi": data["error"].get("message", str(data["error"]))}
        text = data["content"][0]["text"].strip()
        text = text.replace("```json","").replace("```","").strip()
        return json.loads(text)
    except Exception as e:
        return {"ozet": metin, "_parse_hatasi": str(e)}


def portfoy_kaydet(veri: dict):
    try:
        get_client().table("portfoyler").insert(veri).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")
        return False


def yeni_portfoy_modal(kaynak: str, kaynak_etiket: str, ilce_sec: list):
    modal_key = f"yeni_portfoy_{kaynak}"
    if not st.session_state.get(modal_key, False):
        if st.button(f"+ Yeni Portföy Ekle", key=f"btn_{modal_key}"):
            st.session_state[modal_key] = True
            st.rerun()
        return

    ILLER = ["İzmir","Aydın","Manisa","Balıkesir","Muğla","İstanbul","Ankara","Diğer"]

    st.markdown(
        '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:20px;margin-bottom:12px;">',
        unsafe_allow_html=True
    )
    st.markdown(f"### Yeni Portföy Ekle — {kaynak_etiket}")

    gd_list_z1 = sorted(set(
        v.get("talep_eden_danisan","")
        for v in (get_client().table("portfoyler").select("talep_eden_danisan")
                  .in_("kaynak",["zeta1"]).execute().data or [])
        if v.get("talep_eden_danisan","")
    ))
    gd_list_z2 = sorted(set(
        v.get("talep_eden_danisan","")
        for v in (get_client().table("portfoyler").select("talep_eden_danisan")
                  .in_("kaynak",["zeta2"]).execute().data or [])
        if v.get("talep_eden_danisan","")
    ))
    gd_list_tum = sorted(set(gd_list_z1 + gd_list_z2))

    if kaynak == "dis_kaynak":
        gc1, gc2, gc3 = st.columns(3)
        with gc1:
            st.caption("Portföy Sahibi GD (Dış Kaynak)")
            portfoy_sahibi = st.text_input(
                "Portföy sahibinin adı ve ofisi",
                placeholder="Örn: Ahmet Yılmaz - RE/MAX Bornova",
                key=f"pgd_sahip_{kaynak}"
            )
        with gc2:
            st.caption("Sisteme Giren Ofis")
            zeta_ofis = st.selectbox(
                "Hangi ofis giriyor?",
                ["Seç...", "ZETA 1", "ZETA 2"],
                key=f"pgd_ofis_{kaynak}"
            )
        with gc3:
            st.caption("Sisteme Giren Zeta GD")
            gd_kaynak = gd_list_z1 if zeta_ofis == "ZETA 1" else gd_list_z2 if zeta_ofis == "ZETA 2" else gd_list_tum
            zeta_gd = st.selectbox(
                "Hangi Zeta danışmanı giriyor?",
                ["Seç..."] + gd_kaynak,
                key=f"pgd_zeta_{kaynak}"
            )
        gd_ad = portfoy_sahibi
        giren_gd = zeta_gd if zeta_gd != "Seç..." else ""
    else:
        gc1, gc2, gc3 = st.columns(3)
        with gc1:
            st.caption("Ofis Seçin")
            zeta_ofis_sec = st.selectbox(
                "Ofis",
                ["Seç...", "ZETA 1", "ZETA 2"],
                key=f"pgd_ofis_sec_{kaynak}"
            )
        with gc2:
            st.caption("Portföyü Paylaşan Zeta GD")
            gd_kaynak2 = gd_list_z1 if zeta_ofis_sec == "ZETA 1" else gd_list_z2 if zeta_ofis_sec == "ZETA 2" else gd_list_tum
            gd_sec = st.selectbox(
                "Danışman seçin",
                ["Seç..."] + gd_kaynak2 + ["Diğer (manuel gir)"],
                key=f"pgd_sec_{kaynak}"
            )
        with gc3:
            if gd_sec == "Diğer (manuel gir)":
                gd_manuel = st.text_input("Danışman adı", key=f"pgd_manuel_{kaynak}")
            else:
                gd_manuel = ""
        gd_ad = gd_manuel if gd_sec == "Diğer (manuel gir)" else (gd_sec if gd_sec != "Seç..." else "")
        giren_gd = gd_ad

    st.markdown("---")

    yontem = st.radio(
        "Portföy bilgilerini nasıl girmek istersiniz?",
        ["Metin Yaz → Sistem Doldursun", "Formu Kendim Doldurayım"],
        horizontal=True, key=f"pyontem_{kaynak}"
    )

    parse_sonuc = st.session_state.get(f"pparse_{kaynak}", {})

    if yontem == "Metin Yaz → Sistem Doldursun":
        st.info("💡 Portföy hakkında bildiğiniz her şeyi yazın. Sistem otomatik olarak ilgili alanları dolduracak.")
        metin = st.text_area(
            "Portföy açıklaması",
            placeholder="Örn: Bornova Erzene'de 3+1 satılık daire, 120 m², 3. kat, asansörlü bina, güney cepheli, 4.5 milyon TL...",
            height=120, key=f"pmetin_{kaynak}"
        )
        pa, pb = st.columns([1,5])
        with pa:
            if st.button("Metni Yorumla", key=f"pparse_btn_{kaynak}", type="primary"):
                if metin.strip():
                    with st.spinner("Analiz ediliyor..."):
                        sonuc = ai_parse_portfoy(metin)
                        if "_parse_hatasi" in sonuc:
                            st.error(f"Yorumlama hatası: {sonuc['_parse_hatasi']}")
                        else:
                            # Mahalle lookup — her zaman çalıştır
                            # AI mahalle bulmuşsa ilçeyi ondan al
                            mahalle_metin = sonuc.get("mahalle","") or metin
                            lookup = mahalle_ile_ilce_bul(mahalle_metin)
                            if not lookup and mahalle_metin != metin:
                                lookup = mahalle_ile_ilce_bul(metin)
                            if lookup:
                                sonuc["il"] = lookup.get("il","")
                                sonuc["ilce"] = lookup.get("ilce","")
                                if not sonuc.get("mahalle"):
                                    sonuc["mahalle"] = lookup.get("mahalle","")
                            st.session_state[f"pparse_{kaynak}"] = sonuc
                            st.success("Bilgiler dolduruldu, kontrol edin.")
                            st.rerun()
                else:
                    st.warning("Lütfen portföy açıklaması yazın.")
        with pb:
            if parse_sonuc:
                st.caption("✅ Aşağıdaki bilgileri kontrol edip düzenleyebilirsiniz.")

    if yontem == "Formu Kendim Doldurayım" or parse_sonuc:
        st.markdown("**Portföy Bilgileri**")
        f1, f2, f3 = st.columns(3)
        with f1:
            ozet = st.text_input("Özet / Başlık",
                value=parse_sonuc.get("ozet",""),
                placeholder="Kısa portföy tanımı",
                key=f"pf_ozet_{kaynak}")
            il = st.selectbox("İl", ILLER,
                index=ILLER.index(parse_sonuc.get("il","İzmir"))
                if parse_sonuc.get("il","") in ILLER else 0,
                key=f"pf_il_{kaynak}")
            ilce_opts = ["İzmir Genel"] + ilce_sec
            ilce_raw = parse_sonuc.get("ilce","")
            ilce_idx = ilce_opts.index(ilce_raw) if ilce_raw in ilce_opts else 0
            ilce_sec2 = st.selectbox("Birincil İlçe", ilce_opts, index=ilce_idx, key=f"pf_ilce_{kaynak}")
            ilce_val = "" if ilce_sec2 == "İzmir Genel" else ilce_sec2
        with f2:
            mulk = st.selectbox("Mülk Tipi", ["Konut","İşyeri","Arsa","Belirsiz"],
                index=["Konut","İşyeri","Arsa","Belirsiz"].index(parse_sonuc.get("mulk_tipi","Belirsiz"))
                if parse_sonuc.get("mulk_tipi","") in ["Konut","İşyeri","Arsa","Belirsiz"] else 3,
                key=f"pf_mulk_{kaynak}")
            islem = st.selectbox("İşlem Tipi", ["Satılık","Kiralık","Belirsiz"],
                index=["Satılık","Kiralık","Belirsiz"].index(parse_sonuc.get("islem_tipi","Belirsiz"))
                if parse_sonuc.get("islem_tipi","") in ["Satılık","Kiralık","Belirsiz"] else 2,
                key=f"pf_islem_{kaynak}")
            fiyat = st.text_input("Fiyat",
                value=parse_sonuc.get("fiyat",""),
                placeholder="Örn: 4.500.000 TL",
                key=f"pf_fiyat_{kaynak}")
        with f3:
            oda = st.text_input("Oda / M²",
                value=parse_sonuc.get("oda_sayisi_m2",""),
                placeholder="Örn: 3+1 / 120 m²",
                key=f"pf_oda_{kaynak}")
            mahalle = st.text_input("Mahalle / Semt",
                value=parse_sonuc.get("mahalle",""),
                placeholder="Örn: Erzene Mahallesi",
                key=f"pf_mahalle_{kaynak}")
            link = st.text_input("İlan Linki",
                value=parse_sonuc.get("ilan_linki",""),
                placeholder="https://revy.com.tr/...",
                key=f"pf_link_{kaynak}")

        ilceler_default = [i for i in (parse_sonuc.get("ilceler") or []) if i in ilce_sec]
        ilceler = st.multiselect("Tüm İlçeler / Bölgeler", ilce_sec,
            default=ilceler_default, key=f"pf_ilceler_{kaynak}")

        ozel = st.text_area("Özellikler / Notlar",
            value=parse_sonuc.get("ozel_kriterler",""),
            placeholder="Asansör, otopark, güney cephe, tapu durumu, krediye uygunluk...",
            height=70, key=f"pf_ozel_{kaynak}")

        st.markdown("**Fotoğraflar** *(isteğe bağlı)*")
        yuklenen = st.file_uploader(
            "Fotoğraf yükle",
            type=["jpg","jpeg","png","webp"],
            accept_multiple_files=True,
            key=f"pf_foto_{kaynak}",
            help="Maksimum 5 MB, JPG/PNG/WEBP. Birden fazla seçebilirsiniz."
        )
        if yuklenen:
            st.caption(f"✅ {len(yuklenen)} fotoğraf seçildi — kaydet butonuna basınca yüklenecek")
            import base64
            imgs_html = ""
            for dosya in yuklenen:
                b64 = base64.b64encode(dosya.read()).decode()
                dosya.seek(0)
                mime = "image/jpeg" if dosya.name.lower().endswith(("jpg","jpeg")) else "image/png"
                imgs_html += (
                    f'<img src="data:{mime};base64,{b64}" '
                    f'style="width:150px;height:110px;object-fit:cover;'
                    f'border-radius:8px;margin:4px;" />'
                )
            st.markdown(
                f'<div style="display:flex;flex-wrap:wrap;gap:4px;margin:6px 0;">{imgs_html}</div>',
                unsafe_allow_html=True
            )

        st.markdown("---")
        ka, kb = st.columns([1,5])
        with ka:
            if st.button("Kaydet", key=f"pkaydet_{kaynak}", type="primary"):
                if not gd_ad:
                    st.warning("Danışman bilgisi girin.")
                elif kaynak == "dis_kaynak" and not giren_gd:
                    st.warning("Sisteme giren Zeta GD'yi seçin.")
                else:
                    with st.spinner("Kaydediliyor..."):
                        # Önce portföyü kaydet, ID al
                        import uuid as _uuid
                        portfoy_id = str(_uuid.uuid4())
                        foto_urls_list = []
                        if yuklenen:
                            foto_urls_list = foto_yukle(portfoy_id, yuklenen)
                        
                        veri = {
                            "talep_eden_danisan": gd_ad,
                            "kaynak": kaynak,
                            "giren_gd": giren_gd,
                            "il": il,
                            "ilce": ilce_val,
                            "ilceler": ilceler if ilceler else ([ilce_val] if ilce_val else []),
                            "mulk_tipi": mulk,
                            "islem_tipi": islem,
                            "fiyat": fiyat,
                            "oda_sayisi_m2": oda,
                            "mahalle": mahalle,
                            "ilan_linki": link,
                            "ozet": ozet,
                            "ozel_kriterler": ozel,
                            "foto_url": ",".join(foto_urls_list) if foto_urls_list else "",
                            "olusturma_tarihi": datetime.now().isoformat(),
                        }
                        if portfoy_kaydet(veri):
                            st.session_state.pop(f"pparse_{kaynak}", None)
                            st.session_state[modal_key] = False
                            st.success(f"✅ Portföy kaydedildi! {len(foto_urls_list)} fotoğraf yüklendi.")
                            st.rerun()
        with kb:
            if st.button("İptal", key=f"piptal_{kaynak}"):
                st.session_state.pop(f"pparse_{kaynak}", None)
                st.session_state[modal_key] = False
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)




# ── Fotoğraf Yükleme ─────────────────────────────────────────────────────

BUCKET = "portfoy-fotograflari"  # Supabase bucket adı (küçük harf)

def foto_yukle(portfoy_id: str, dosyalar: list) -> list:
    """Fotoğrafları Supabase Storage'a yükle, URL listesi döndür."""
    import uuid, mimetypes
    client = get_client()
    urls = []
    for dosya in dosyalar:
        try:
            ext = dosya.name.split(".")[-1].lower()
            dosya_adi = f"{portfoy_id}/{uuid.uuid4()}.{ext}"
            mime = mimetypes.guess_type(dosya.name)[0] or "image/jpeg"
            
            client.storage.from_(BUCKET).upload(
                path=dosya_adi,
                file=dosya.getvalue(),
                file_options={"content-type": mime, "upsert": "true"}
            )
            
            url = client.storage.from_(BUCKET).get_public_url(dosya_adi)
            urls.append(url)
        except Exception as e:
            st.warning(f"{dosya.name} yüklenemedi: {e}")
    return urls


def foto_sil(url: str):
    """Storage'dan fotoğraf sil."""
    try:
        client = get_client()
        # URL'den path çıkar
        path = url.split(f"/{BUCKET}/")[-1]
        client.storage.from_(BUCKET).remove([path])
    except Exception as e:
        st.warning(f"Silme hatası: {e}")


def foto_goster(foto_urls: list, max_cols: int = 4):
    """Fotoğrafları grid olarak göster."""
    if not foto_urls:
        return
    urls = [u.strip() for u in foto_urls if u.strip()]
    if not urls:
        return
    # HTML ile kontrollü boyut
    img_tags = "".join(
        f'<img src="{u}" style="width:100%;max-width:220px;height:160px;'
        f'object-fit:cover;border-radius:8px;margin:4px;" />'
        for u in urls
    )
    st.markdown(
        f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin:8px 0;">{img_tags}</div>',
        unsafe_allow_html=True
    )


@st.cache_data(ttl=3600)
def mahalle_lookup_cek():
    """Mahalle → (il, ilce) eşleştirme tablosu."""
    try:
        r = get_client().table("mahalleler").select("il,ilce,mahalle").execute()
        lookup = {}
        for row in r.data:
            mh = row["mahalle"].strip().lower()
            lookup[mh] = (row["il"], row["ilce"])
        return lookup
    except Exception:
        return {}


def mahalle_ile_ilce_bul(metin: str) -> dict:
    """Metindeki mahalle/semt adını bulup il/ilçe döndür."""
    if not metin:
        return {}
    lookup = mahalle_lookup_cek()
    metin_lower = metin.lower()
    # En uzun eşleşmeyi bul (Erzene → Erzene Mahallesi olmaması için)
    eslesme = {}
    for mh_lower, (il, ilce) in lookup.items():
        if mh_lower in metin_lower:
            if not eslesme or len(mh_lower) > len(list(eslesme.keys())[0]):
                eslesme = {mh_lower: (il, ilce, mh_lower)}
    if eslesme:
        _, (il, ilce, mh) = list(eslesme.items())[0]
        return {"il": il, "ilce": ilce, "mahalle": mh}
    return {}

def filtre_temizle():
    for k in ["pft_ara","pft_il","pft_ilce","pft_danisan","pft_mulk","pft_islem",
              "pft_siralama","pft_tarih_mod","pft_hizli","pft_bas","pft_bit","pft_fav",
              "pfav_secili_ilce","pfav_ekle_ac"]:
        st.session_state.pop(k, None)
    st.rerun()

# ── Düzenleme formu ───────────────────────────────────────────────────────

def duzenleme_formu(v, ilce_sec):
    kid = v.get("id")
    iller = ["İzmir","Aydın","Manisa","Balıkesir","Muğla","Diğer"]
    c1, c2, c3 = st.columns(3)
    with c1:
        oz = st.text_input("Özet", value=v.get("ozet","") or "", key=f"d_oz_{kid}")
        yi = st.selectbox("İl", iller,
            index=iller.index(v.get("il","")) if v.get("il","") in iller else 0, key=f"d_il_{kid}")
        yilce = st.selectbox("Birincil İlçe", [""]+ilce_sec,
            index=([""]+ilce_sec).index(v.get("ilce","")) if v.get("ilce","") in ilce_sec else 0,
            key=f"d_ilce_{kid}")
    with c2:
        ym = st.selectbox("Mülk", ["Konut","İşyeri","Arsa","Belirsiz"],
            index=["Konut","İşyeri","Arsa","Belirsiz"].index(v.get("mulk_tipi","Belirsiz"))
            if v.get("mulk_tipi","") in ["Konut","İşyeri","Arsa","Belirsiz"] else 3, key=f"d_m_{kid}")
        yis = st.selectbox("İşlem", ["Satılık","Kiralık","Belirsiz"],
            index=["Satılık","Kiralık","Belirsiz"].index(v.get("islem_tipi","Belirsiz"))
            if v.get("islem_tipi","") in ["Satılık","Kiralık","Belirsiz"] else 2, key=f"d_is_{kid}")
        ymh = st.text_input("Mahalle", value=v.get("mahalle","") or "", key=f"d_mh_{kid}")
    with c3:
        yb = st.text_input("Bölge/Konum", value=v.get("bolge","") or v.get("bolge_mahalle","") or "",
            key=f"d_b_{kid}")
        mevcut = v.get("ilceler") or []
        yilceler = st.multiselect("Tüm İlçeler", ilce_sec,
            default=[i for i in mevcut if i in ilce_sec], key=f"d_ilceler_{kid}")
    ca, cb = st.columns([1,4])
    with ca:
        if st.button("💾 Kaydet", key=f"d_kyd_{kid}", type="primary"):
            kayit_guncelle(kid, {
                "ozet":oz,"il":yi,"ilce":yilce,
                "ilceler":yilceler if yilceler else ([yilce] if yilce else []),
                "mulk_tipi":ym,"islem_tipi":yis,
                "mahalle":ymh,"bolge":yb,
                "bolge_mahalle":f"{ymh} {yb}".strip()
            })
    with cb:
        if st.button("İptal", key=f"d_ipt_{kid}"):
            st.session_state.pop(f"duzen_{kid}", None); st.rerun()

# ── Portföy kartı ─────────────────────────────────────────────────────────

def tarih_renk_bilgisi(gun):
    if gun <= 7:   return "#166534", "#dcfce7", "#16a34a"
    elif gun <= 30: return "#713f12", "#fef9c3", "#ca8a04"
    elif gun <= 90: return "#7c2d12", "#ffedd5", "#ea580c"
    elif gun <= 180: return "#7f1d1d", "#fee2e2", "#dc2626"
    else:           return "#374151", "#f3f4f6", "#9ca3af"


def portfoy_kart_html(v, rozet_html=""):
    """Hibrit portföy kartı — geniş, 2 sütunlu grid için."""
    kid       = v.get("id")
    isim      = isim_ayikla(v.get("talep_eden_danisan", ""))
    fiyat     = v.get("fiyat", "")
    oda       = v.get("oda_sayisi_m2", "") or ""
    islem     = v.get("islem_tipi", "") or ""
    mulk      = v.get("mulk_tipi", "") or ""
    ilan      = v.get("ilan_linki", "")
    ozet      = v.get("ozet", "") or v.get("mail_konusu", "") or ""
    ilceler_list = v.get("ilceler") or []
    mahalle   = v.get("mahalle", "") or ""

    _aks_k = aks_renk_bul(ilceler_list)

    _td = tarih_parse(en_iyi_tarih(v))
    if _td:
        _hast = hasattr(_td, "hour") and (_td.hour != 0 or _td.minute != 0)
        _tarih_k = _td.strftime("%d.%m.%Y %H:%M") if _hast else _td.strftime("%d.%m.%Y")
    else:
        _tarih_k = ""

    lok_parts = ilceler_list[:3] if ilceler_list else ([mahalle] if mahalle else [])
    _lokasyon = " · ".join(lok_parts)

    # İşlem badge
    if "iralık" in islem:   _ibg, _ic, _ilbl = "#f0fdf4", "#166534", "Kiralık"
    elif "atılık" in islem: _ibg, _ic, _ilbl = "#fef2f2", "#991b1b", "Satılık"
    else:                   _ibg, _ic, _ilbl = "#f8fafc", "#64748b", islem or ""

    # Başlık
    _b_parts = []
    if islem and islem not in ("Belirsiz", "Belirtilmemiş"): _b_parts.append(islem)
    if oda:  _b_parts.append(oda)
    if mulk and mulk not in ("Belirsiz", "Belirtilmemiş"):   _b_parts.append(mulk)
    _b_parts.append("İlanı" if islem and islem not in ("Belirsiz", "") else "Portföyü")
    _baslik = " ".join(_b_parts)

    # Kaynak chip
    _kaynak_raw = (v.get("kaynak") or "").lower()
    if _kaynak_raw in ("startkey_mail", ""):
        _k_lbl, _k_c, _k_bg = "Startkey", "#355C7D", "#EEF4FA"
    elif _kaynak_raw in ("zeta1", "zeta2", "ofis", "zeta"):
        _k_lbl, _k_c, _k_bg = "Zeta", "#0F6E56", "#E1F5EE"
    else:
        _k_lbl, _k_c, _k_bg = "Diğer", "#475569", "#f1f5f9"

    # Danışman initials
    _initials = "".join(w[0].upper() for w in isim.split()[:2]) if isim else "?"

    # Badge satırı
    _badges = ""
    if _lokasyon:
        _badges += (f'<span style="background:{_aks_k["bg"]};color:{_aks_k["text"]};'
                    f'padding:3px 9px;border-radius:5px;font-size:10.5px;font-weight:700;'
                    f'letter-spacing:0.06em;text-transform:uppercase;margin-right:5px;">{_lokasyon}</span>')
    if _ilbl:
        _badges += (f'<span style="background:{_ibg};color:{_ic};border:1px solid {_ibg};'
                    f'padding:3px 9px;border-radius:5px;font-size:10.5px;font-weight:700;margin-right:5px;">{_ilbl}</span>')
    if mulk and mulk not in ("Belirsiz", "Belirtilmemiş"):
        cfg = BADGE_PALETTE.get(mulk, ("#f1f5f9", "#475569", "#e2e8f0"))
        _badges += (f'<span style="background:{cfg[0]};color:{cfg[1]};border:1px solid {cfg[2]};'
                    f'padding:3px 9px;border-radius:5px;font-size:10.5px;font-weight:600;margin-right:5px;">{mulk}</span>')
    if ilan:
        _badges += (f'<a href="{ilan}" target="_blank" style="text-decoration:none;">'
                    f'<span style="background:#e0f2fe;color:#0369a1;border:1px solid #bae6fd;'
                    f'padding:3px 9px;border-radius:5px;font-size:10.5px;font-weight:600;">↗ İlan</span></a>')

    return (
        f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;'
        f'padding:18px 20px 14px;box-shadow:0 2px 10px rgba(15,23,42,0.06);margin-bottom:0;">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">'
        f'<div style="display:flex;flex-wrap:wrap;gap:4px;">{_badges}</div>'
        f'<div style="flex-shrink:0;margin-left:8px;">{rozet_html}</div>'
        f'</div>'
        f'<div style="font-size:17px;font-weight:800;color:#0F172A;line-height:1.3;'
        f'margin-bottom:7px;display:-webkit-box;-webkit-line-clamp:2;'
        f'-webkit-box-orient:vertical;overflow:hidden;">{_baslik}</div>'
        + (f'<div style="font-size:13px;color:#64748B;line-height:1.5;margin-bottom:10px;'
           f'display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">'
           f'{str(ozet)[:180]}</div>' if ozet else '<div style="margin-bottom:8px;"></div>')
        + (f'<div style="font-size:20px;font-weight:800;color:#0F172A;letter-spacing:-0.5px;'
           f'margin-bottom:14px;">{fiyat}</div>'
           if fiyat else
           '<div style="font-size:14px;color:#94a3b8;font-style:italic;margin-bottom:14px;">Fiyat belirtilmedi</div>')
        + f'<div style="border-top:1px solid #f1f5f9;margin-bottom:12px;"></div>'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        ""
        f'<span style="font-size:12px;font-weight:600;color:#374151;">{isim or "—"}</span>'
        + (f'<span style="color:#d1d5db;font-size:11px;">·</span>'
           f'<span style="font-size:11.5px;color:#64748b;">{_tarih_k}</span>' if _tarih_k else "")
        + f'<span style="color:#d1d5db;font-size:11px;">·</span>'
        f'<span style="background:{_k_bg};color:{_k_c};font-size:10px;font-weight:600;'
        f'padding:1px 7px;border-radius:4px;">{_k_lbl}</span>'
        f'</div>'
        f'</div>'
    )


def portfoy_karti(v, ilce_sec):
    kid = v.get("id")
    isim = isim_ayikla(v.get("talep_eden_danisan",""))
    ozet = v.get("ozet","") or v.get("mail_konusu","")
    fiyat = v.get("fiyat","")
    oda = v.get("oda_sayisi_m2","")
    islem = v.get("islem_tipi","")
    mulk = v.get("mulk_tipi","")
    ilan = v.get("ilan_linki","")
    mahalle = v.get("mahalle","") or ""
    bolge = v.get("bolge","") or v.get("bolge_mahalle","") or ""
    ilceler_list = v.get("ilceler") or []
    gun = tarih_gun_farki(en_iyi_tarih(v))
    yeni_kayit = gun <= 7
    favori = v.get("favori", False)
    gizli = v.get("gizli", False)
    duzen_modu = st.session_state.get(f"duzen_{kid}", False)
    okundu = kid in st.session_state.get("portfoy_goruldu_ids", set())

    if st.session_state.pop(f"guncellendi_{kid}", False):
        st.toast("✅ Güncellendi!")

    # Tarih parse + renk
    tarih_d = tarih_parse(en_iyi_tarih(v))
    if tarih_d:
        _hast = hasattr(tarih_d, 'hour') and (tarih_d.hour != 0 or tarih_d.minute != 0)
        tarih_g = tarih_d.strftime("%d.%m.%Y %H:%M") if _hast else tarih_d.strftime("%d.%m.%Y")
    else:
        tarih_g = ""

    _fg, _bg, _dot = tarih_renk_bilgisi(gun)
    tarih_html = (
        f'<span style="display:inline-flex;align-items:center;gap:4px;">'
        f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:{_dot};flex-shrink:0;"></span>'
        f'<span style="color:{_fg};font-weight:600;font-size:11px;">{tarih_g}</span>'
        f'</span>'
        if tarih_g else ""
    )

    # Aks rengi
    aks_renk = aks_renk_bul(ilceler_list)
    _aks_bar = aks_bar_gradient(ilceler_list)

    # Lokasyon özeti
    lok_parts = ilceler_list[:3] if ilceler_list else ([bolge] if bolge else [])
    lokasyon_str = " · ".join(lok_parts)

    # Sol şerit (durum rengi — talep tablosuyla aynı)
    if okundu:       left_border = "#cbd5e1"
    elif yeni_kayit: left_border = "#16a34a"
    elif favori:     left_border = "#f59e0b"
    else:            left_border = "#e2e8f0"

    # Köşe rozeti
    if okundu:
        _rozet = '<span class="nbadge nbadge-goruldu" style="position:absolute;top:8px;right:10px;">✓ Görüldü</span>'
    elif yeni_kayit:
        _rozet = '<span class="nbadge nbadge-yeni" style="position:absolute;top:8px;right:10px;"><span class="dot-live"></span> YENİ</span>'
    else:
        _rozet = ""

    # Başlık: talep tablosu stili
    _baslik_parts = []
    if islem and islem not in ("Belirsiz","Belirtilmemiş"): _baslik_parts.append(islem)
    if oda: _baslik_parts.append(oda)
    if mulk and mulk not in ("Belirsiz","Belirtilmemiş"): _baslik_parts.append(mulk)
    _baslik_parts.append("İlanı" if islem and islem not in ("Belirsiz","") else "Portföyü")
    baslik = " ".join(_baslik_parts)

    # Özet notu: mahalle + ozet
    kriter_ozet = (mahalle + (" · " if mahalle else "") + str(ozet)[:100]).strip(" · ")

    # Badge'ler
    etiketler = etiket_html(mulk) + etiket_html(islem)
    if ilan:
        etiketler += f'<a href="{ilan}" target="_blank" style="text-decoration:none;"><span style="background:#e0f2fe;color:#0369a1;border:1px solid #bae6fd;padding:2px 8px;border-radius:20px;font-size:10.5px;font-weight:600;margin-right:4px;display:inline-block;">↗ İlan</span></a>'
    if yeni_kayit and not okundu:
        etiketler += '<span style="background:#fffbeb;color:#92400e;border:1px solid #fde68a;padding:2px 8px;border-radius:999px;font-size:10.5px;font-weight:650;margin-right:4px;display:inline-block;">yeni</span>'

    # Fiyat HTML
    fiyat_html = (
        f'<span style="font-size:0.91rem;font-weight:750;color:#172B4D;">💰 {fiyat}</span>'
        if fiyat else
        '<span style="font-size:11px;color:#94a3b8;font-style:italic;">Fiyat belirtilmedi</span>'
    )

    # Avatar
    _avatar = avatar_html(isim, aks_renk)

    # Kaynak chip
    _kaynak_raw = (v.get("kaynak") or "").lower()
    if _kaynak_raw in ("startkey_mail", ""):
        _k_lbl, _k_c, _k_bg = "Startkey", "#355C7D", "#EEF4FA"
    elif _kaynak_raw in ("zeta1", "zeta2", "ofis", "zeta"):
        _k_lbl, _k_c, _k_bg = "Zeta", "#0F6E56", "#E1F5EE"
    else:
        _k_lbl, _k_c, _k_bg = "Diğer", "#475569", "#f1f5f9"
    _kaynak_chip = (f'<span style="background:{_k_bg};color:{_k_c};font-size:9.5px;font-weight:600;'
                    f'padding:1px 6px;border-radius:4px;margin-left:auto;">{_k_lbl}</span>')

    # Kart HTML — talep tablosuyla aynı yapı
    st.markdown(
        f'<div class="kart-wrapper" style="border:1px solid #dce4ee;border-left:4px solid {left_border};'
        f'border-radius:12px;overflow:hidden;margin-bottom:3px;'
        f'background:#ffffff;box-shadow:0 2px 8px rgba(15,23,42,0.05);">'
        f'<div style="height:3px;background:{_aks_bar};width:100%;"></div>'
        f'<div style="padding:10px 14px 9px 14px;position:relative;">'
        f'{_rozet}'
        + (f'<span style="font-size:10px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:{aks_renk["text"]};margin-bottom:3px;display:block;">{lokasyon_str}</span>' if lokasyon_str else "")
        + f'<div style="font-size:1.0rem;font-weight:700;color:#172B4D;line-height:1.3;margin-bottom:4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">{baslik}</div>'
        + (f'<div class="kart-kriter">{kriter_ozet}</div>' if kriter_ozet else "")
        + f'<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:6px;">{etiketler}</div>'
        + f'<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px;">'
        + f'{fiyat_html}'
        + (f'<span style="margin-left:auto;">{tarih_html}</span>' if tarih_html else "")
        + f'</div>'
        f'</div>'
        f'<div style="border-top:0.5px solid #e9eef5;padding:7px 14px;background:#f8fafc;'
        f'display:flex;align-items:center;gap:5px;font-size:11px;color:#64748B;">'
        f'{_avatar}{isim}'
        f'{_kaynak_chip}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Aksiyonlar — talep tablosuyla aynı sütun oranları
    a_detay, a_sunum, a_fav, a_duz, a_giz, a_spacer = st.columns([1.4, 1.5, 0.65, 0.65, 0.65, 5.15])

    with a_detay:
        if st.button("Detay", key=f"detay_btn_{kid}", type="primary", use_container_width=True):
            st.session_state.setdefault("portfoy_goruldu_ids", set()).add(kid)
            st.session_state[f"portfoy_detay_{kid}"] = not st.session_state.get(f"portfoy_detay_{kid}", False)
            st.rerun()

    with a_sunum:
        _p_takip = st.session_state.get(f"takip_p_{kid}", False)
        if st.button("⭐ Takipte" if _p_takip else "☆ Takibe Al",
                     key=f"p_takip_{kid}", use_container_width=True):
            _takip_listesi = st.session_state.setdefault("takip_listesi", {})
            if _p_takip:
                _takip_listesi.pop(str(kid), None)
                st.session_state[f"takip_p_{kid}"] = False
                st.toast("Takipten çıkarıldı.")
            else:
                _takip_listesi[str(kid)] = dict(v)
                _takip_listesi[str(kid)]["_takip_kaynak"] = "portfoy_havuzu"
                st.session_state[f"takip_p_{kid}"] = True
                st.toast("✅ Takip listesine eklendi! Ana Sayfadan açıklama ekleyip sunuma hazırlayabilirsiniz.")
            st.rerun()

    with a_fav:
        fav_label = "★" if favori else "☆"
        if st.button(fav_label, key=f"fav_{kid}", use_container_width=True):
            favori_guncelle(kid, favori)

    with a_duz:
        if st.button("✏", key=f"dz_{kid}", use_container_width=True):
            st.session_state[f"duzen_{kid}"] = not duzen_modu
            st.rerun()

    with a_giz:
        giz_label = "👁" if gizli else "⊘"
        if st.button(giz_label, key=f"giz_{kid}", use_container_width=True):
            if gizli:
                get_client().table("portfoyler").update({"gizli": False}).eq("id", kid).execute()
                st.cache_data.clear(); st.rerun()
            else:
                kayit_gizle(kid)

    kaynak_v = v.get("kaynak", "")
    if kaynak_v and kaynak_v != "startkey_mail":
        sil_key = f"psil_onay_{kid}"
        if not st.session_state.get(sil_key):
            if st.button("🗑", key=f"psil_{kid}", help="Kaydı sil"):
                st.session_state[sil_key] = True; st.rerun()
        else:
            st.warning("⚠️ Bu kaydı silmek istediğinizden emin misiniz?")
            sc1, sc2 = st.columns([1, 1])
            with sc1:
                if st.button("🗑 Evet, Sil", key=f"psil_evet_{kid}", type="primary"):
                    portfoy_sil(kid); st.toast("✅ Kayıt silindi.")
            with sc2:
                if st.button("İptal", key=f"psil_iptal_{kid}"):
                    st.session_state.pop(sil_key, None); st.rerun()

    if duzen_modu:
        duzenleme_formu(v, ilce_sec)
    if st.session_state.get(f"portfoy_detay_{kid}", False):
        portfoy_detay_goster(v, ilce_sec)




@st.dialog("Portföy Detayı", width="large")
def portfoy_detay_goster(v, ilce_sec):
    kid = v.get("id")
    isim = isim_ayikla(v.get("talep_eden_danisan",""))
    ilceler_list = v.get("ilceler") or []
    fiyat = v.get("fiyat","")
    oda = v.get("oda_sayisi_m2","")
    mahalle = v.get("mahalle","") or ""
    bolge = v.get("bolge","") or ""
    islem = v.get("islem_tipi","")
    mulk = v.get("mulk_tipi","")
    ilan = v.get("ilan_linki","")
    ozet = v.get("ozet","") or v.get("mail_konusu","")
    favori = v.get("favori", False)
    aks_renk = aks_renk_bul(ilceler_list)

    lok_parts = ilceler_list[:3] if ilceler_list else ([bolge] if bolge else [])
    lokasyon_str = " · ".join(lok_parts)

    # Başlık
    st.markdown(
        f'<div style="background:#FFF9ED;border-left:4px solid #F4B740;padding:10px 14px;border-radius:0 8px 8px 0;margin-bottom:12px;">'
        f'<div style="font-size:1.1rem;font-weight:800;color:#172B4D;">{"Satılık" if islem=="Satılık" else "Kiralık" if islem=="Kiralık" else ""} {oda} {mulk} {"İlanı" if islem else "Portföyü"}</div>'
        + (f'<div style="font-size:0.83rem;color:{aks_renk["text"]};font-weight:600;margin-top:4px;">📍 {lokasyon_str}</div>' if lokasyon_str else "")
        + f'</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;">Danışman</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:13px;font-weight:600;color:#172B4D;">{isim or "—"}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;">Fiyat</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:13px;font-weight:700;color:#172B4D;">{"💰 "+fiyat if fiyat else "Belirtilmedi"}</div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;">Oda / M²</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:13px;font-weight:600;color:#172B4D;">{"🏠 "+oda if oda else "—"}</div>', unsafe_allow_html=True)

    st.markdown(etiket_html(mulk) + etiket_html(islem), unsafe_allow_html=True)

    st.divider()

    if ilceler_list or mahalle or bolge:
        r2a, r2b = st.columns(2)
        with r2a:
            st.markdown(f'<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;">İlçeler</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:13px;color:#374151;">{", ".join(ilceler_list) if ilceler_list else "—"}</div>', unsafe_allow_html=True)
        with r2b:
            st.markdown(f'<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;">Mahalle</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:13px;color:#374151;">{mahalle or "—"}</div>', unsafe_allow_html=True)

    if v.get("ozellikler"):
        st.markdown(
            f'<div style="background:#FFF9ED;border-left:3px solid #F4B740;padding:8px 12px;border-radius:4px;font-size:12px;color:#475569;margin-top:8px;">'
            f'<b>Özellikler:</b> {v.get("ozellikler","")}</div>',
            unsafe_allow_html=True,
        )

    # Fotoğraflar
    foto_url_str = v.get("foto_url","") or ""
    foto_urls = [u.strip() for u in foto_url_str.split(",") if u.strip()]
    if foto_urls:
        foto_goster(foto_urls, max_cols=4)

    if ilan:
        st.link_button("↗ İlana Git", ilan)

    ic = html_temizle(v.get("mail_icerigi",""))
    if ic:
        st.markdown(f'<div style="font-size:11px;color:#64748b;font-weight:700;margin-top:10px;margin-bottom:3px;">📧 {v.get("mail_konusu","")}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="background:#f0f4ff;border-left:3px solid #2d7dd2;padding:8px 12px;border-radius:6px;font-size:11px;line-height:1.6;max-height:200px;overflow-y:auto;color:#374151;">{ic[:1500]}</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    not_m = v.get("not_alani","") or ""
    yn = st.text_area("Not", value=not_m, height=80, placeholder="Not ekle...",
                      key=f"pmod_not_{kid}", label_visibility="collapsed")
    nb1, nb2 = st.columns([1, 3])
    with nb1:
        if st.button("💾 Notu Kaydet", key=f"pmod_nb_{kid}", type="primary", use_container_width=True):
            not_kaydet(kid, yn)

    st.divider()
    ma1, ma2 = st.columns(2)
    with ma1:
        fav_label = "★ Favoriden Çıkar" if favori else "☆ Favoriye Ekle"
        if st.button(fav_label, key=f"pmod_fav_{kid}", use_container_width=True):
            favori_guncelle(kid, favori)
    with ma2:
        if v.get("il","") or v.get("ilce",""):
            if st.button("📦 Belirtilmemişe Taşı", key=f"pmod_blt_{kid}", use_container_width=True):
                belirtilmemise_tasi(kid)


# ── Liste görünümü ────────────────────────────────────────────────────────

def liste_goster(kayitlar, ilce_filtre_aktif, ilce_sec, fav_secili, key_prefix=""):
    def yeni_sayisi_hesapla(liste):
        return sum(1 for v in liste if tarih_gun_farki(en_iyi_tarih(v)) <= 7)

    def grup_button_label(baslik, adet, yeni):
        yeni_text = f"  · 🔴 {yeni} yeni" if yeni > 0 else ""
        return f"{baslik}  ·  {adet} portföy{yeni_text}"

    _btn_counter = [0]

    def grup_acik_mi(grup_adi, adet, yeni, default_acik=False):
        state_key = f"pg_open_{safe_key(grup_adi)}"
        if state_key not in st.session_state:
            st.session_state[state_key] = default_acik
        acik = st.session_state.get(state_key, False)
        _btn_counter[0] += 1
        btn_key = f"pgbtn_{_btn_counter[0]}_{safe_key(grup_adi)}"
        if st.button(grup_button_label(grup_adi, adet, yeni),
                     key=btn_key, use_container_width=True):
            st.session_state[state_key] = not acik
            st.rerun()
        return st.session_state.get(state_key, False)

    def ilce_acik_mi(ilce_adi, label_adi, adet, yeni, default_acik=False):
        state_key = f"pi_open_{safe_key(ilce_adi)}"
        if state_key not in st.session_state:
            st.session_state[state_key] = default_acik
        acik = st.session_state.get(state_key, False)
        _btn_counter[0] += 1
        btn_key = f"pibtn_{_btn_counter[0]}_{safe_key(ilce_adi)}"
        if st.button(grup_button_label(label_adi, adet, yeni),
                     key=btn_key, use_container_width=True, type="secondary"):
            st.session_state[state_key] = not acik
            st.rerun()
        return st.session_state.get(state_key, False)

    if ilce_filtre_aktif != "Tümü":
        yeni = yeni_sayisi_hesapla(kayitlar)

        st.markdown(
            f'<div style="font-size:12px;font-weight:700;color:#64748b;'
            f'text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">'
            f'{ilce_filtre_aktif} · {len(kayitlar)} portföy'
            f'{" · 🔴 " + str(yeni) + " yeni" if yeni > 0 else ""}</div>',
            unsafe_allow_html=True
        )

        for v in kayitlar:
            portfoy_karti(v, ilce_sec)

        return

    fav_ilceler = favori_ilceleri_cek()
    izmir = {}
    diger = {}
    belirsiz = []

    for v in kayitlar:
        il = il_grubu(v)
        ilce = ilce_grubu(v)

        if not il and not ilce:
            belirsiz.append(v)

        elif il == "İzmir":
            izmir.setdefault(ilce or "Belirtilmemiş", []).append(v)

        elif il:
            diger.setdefault(il, {}).setdefault(ilce or "Belirtilmemiş", []).append(v)

        else:
            belirsiz.append(v)

    # 1. FAVORİ İLÇELERİM
    fav_gruplar = {}

    for fav in fav_ilceler:
        if fav in izmir:
            fav_gruplar[fav] = izmir[fav]

    if fav_gruplar:
        toplam_fav = sum(len(k) for k in fav_gruplar.values())
        yeni_fav = sum(yeni_sayisi_hesapla(k) for k in fav_gruplar.values())

        st.markdown(
            '<div style="font-size:12px;font-weight:700;color:#92400e;'
            'text-transform:uppercase;letter-spacing:1px;margin:8px 0 6px 0;">'
            '★ FAVORİ İLÇELERİM</div>',
            unsafe_allow_html=True
        )

        fav_group_default = bool(fav_secili)
        if grup_acik_mi("Favori İlçelerim", toplam_fav, yeni_fav, default_acik=fav_group_default):
            for fav in fav_ilceler:
                if fav not in fav_gruplar:
                    continue

                k = fav_gruplar[fav]
                yeni = yeni_sayisi_hesapla(k)
                default_ilce_acik = fav_secili == fav

                if ilce_acik_mi(f"Favori İlçelerim / {fav}", f"★ {fav}", len(k), yeni, default_acik=default_ilce_acik):
                    for v in k:
                        portfoy_karti(v, ilce_sec)

    # 2. İZMİR
    izmir_render = {
        ilce: liste
        for ilce, liste in izmir.items()
        if ilce not in fav_ilceler
    }

    if izmir_render:
        toplam_izmir = sum(len(k) for k in izmir_render.values())
        yeni_izmir = sum(yeni_sayisi_hesapla(k) for k in izmir_render.values())

        if grup_acik_mi("İzmir", toplam_izmir, yeni_izmir, default_acik=False):
            for ilce in sorted(izmir_render.keys()):
                k = izmir_render[ilce]
                yeni = yeni_sayisi_hesapla(k)

                if ilce_acik_mi(f"İzmir / {ilce}", ilce, len(k), yeni, default_acik=False):
                    for v in k:
                        portfoy_karti(v, ilce_sec)

    # 3. DİĞER İLLER
    if diger:
        toplam_diger = sum(len(k) for il in diger.values() for k in il.values())
        yeni_diger = sum(yeni_sayisi_hesapla(k) for il in diger.values() for k in il.values())

        if grup_acik_mi("Diğer İller", toplam_diger, yeni_diger, default_acik=False):
            for il in sorted(diger.keys()):
                il_toplam = sum(len(k) for k in diger[il].values())
                il_yeni = sum(yeni_sayisi_hesapla(k) for k in diger[il].values())

                if ilce_acik_mi(f"Diğer İller / {il}", il, il_toplam, il_yeni, default_acik=False):
                    for ilce in sorted(diger[il].keys()):
                        k = diger[il][ilce]
                        yeni = yeni_sayisi_hesapla(k)

                        if ilce_acik_mi(f"{il} / {ilce}", ilce, len(k), yeni, default_acik=False):
                            for v in k:
                                portfoy_karti(v, ilce_sec)

    # 4. BELİRTİLMEMİŞ
    if belirsiz:
        yeni_belirsiz = yeni_sayisi_hesapla(belirsiz)

        if grup_acik_mi("Belirtilmemiş", len(belirsiz), yeni_belirsiz, default_acik=False):
            st.caption("İl veya ilçe bilgisi olmayan portföyler.")

            for v in belirsiz:
                portfoy_karti(v, ilce_sec)

# ── Sayfa ─────────────────────────────────────────────────────────────────

# Tüm kaynakları tek seferde yükle
veriler = verileri_yukle(None)

if not st.session_state.get("pft_gizli", False):
    veriler = [v for v in veriler if not v.get("gizli", False)]

gizli_sayi = sum(1 for v in verileri_yukle() if v.get("gizli", False))

ilce_sec = ilce_listesi_cek()
fav_ilceler = favori_ilceleri_cek()

if "pfav_secili_ilce" not in st.session_state:
    st.session_state["pfav_secili_ilce"] = None
if "portfoy_goruldu_ids" not in st.session_state:
    st.session_state["portfoy_goruldu_ids"] = set()

allowed_hizli = ["Tümü", "Bugün", "Son 7 gün", "Son 30 gün"]
if st.session_state.get("pft_hizli", "Son 7 gün") not in allowed_hizli:
    st.session_state["pft_hizli"] = "Son 7 gün"

hizli = st.session_state.get("pft_hizli", "Son 7 gün")

yeni_sayisi = sum(1 for v in veriler if tarih_gun_farki(en_iyi_tarih(v)) <= 7)
bugun_sayisi = sum(1 for v in veriler if tarih_gun_farki(en_iyi_tarih(v)) == 0)
son_7_sayisi = sum(1 for v in veriler if tarih_gun_farki(en_iyi_tarih(v)) <= 7)
son_30_sayisi = sum(1 for v in veriler if tarih_gun_farki(en_iyi_tarih(v)) <= 30)

danisman_sayisi = len(set(
    isim_ayikla(v.get("talep_eden_danisan",""))
    for v in veriler if v.get("talep_eden_danisan","")
))

ilce_sayilari = {}
for v in veriler:
    for ilce in (v.get("ilceler") or []):
        if ilce and ilce != "Diğer Bölge":
            ilce_sayilari[ilce] = ilce_sayilari.get(ilce, 0) + 1

ilce_sayisi = len(ilce_sayilari)
top_3_ilce = sorted(ilce_sayilari.items(), key=lambda x: x[1], reverse=True)[:3]
top_3_ilce_text = " · ".join([f"{ilce} {adet}" for ilce, adet in top_3_ilce])

# ── Navbar + Hero Başlık
_hdr1, _hdr2 = st.columns([1, 0.06])
with _hdr1:
    render_page_header("Portföy Merkezi")
with _hdr2:
    if st.button("↺", key="portfoy_yenile", help="Yenile", use_container_width=True):
        st.cache_data.clear(); st.rerun()

if not veriler:
    st.info("Henüz portföy bulunamadı.")
    st.stop()

hizli_sayilar = {
    "Tümü": len(veriler),
    "Bugün": bugun_sayisi,
    "Son 7 gün": son_7_sayisi,
    "Son 30 gün": son_30_sayisi,
}

tb1, tb2, tb3, tb4, t_spacer, tb5 = st.columns([1, 1, 1, 1, 3.8, 1.2])

hizli_button_map = [
    ("Son 7 gün",  f"7 Gün · {hizli_sayilar['Son 7 gün']}"),
    ("Son 30 gün", f"30 Gün · {hizli_sayilar['Son 30 gün']}"),
    ("Bugün",      f"Bugün · {hizli_sayilar['Bugün']}"),
    ("Tümü",       f"Tümü · {hizli_sayilar['Tümü']}"),
]

for col, deger, label in [
    (tb1, *hizli_button_map[0]),
    (tb2, *hizli_button_map[1]),
    (tb3, *hizli_button_map[2]),
    (tb4, *hizli_button_map[3]),
]:
    with col:
        portfoy_secim_butonu(label, deger, "pft_hizli", "hizli_btn")

aktif_filtre_sayisi = 0
if st.session_state.get("pft_il", "Tümü") != "Tümü": aktif_filtre_sayisi += 1
if st.session_state.get("pft_ilce", "Tümü") != "Tümü": aktif_filtre_sayisi += 1
if st.session_state.get("pft_danisan", "Tümü") != "Tümü": aktif_filtre_sayisi += 1
if st.session_state.get("pft_mulk", "Tümü") != "Tümü": aktif_filtre_sayisi += 1
if st.session_state.get("pft_islem", "Tümü") != "Tümü": aktif_filtre_sayisi += 1
if st.session_state.get("pft_siralama", "Tarih ↓") != "Tarih ↓": aktif_filtre_sayisi += 1
if st.session_state.get("pft_ara", "").strip(): aktif_filtre_sayisi += 1
if st.session_state.get("pft_fav", False): aktif_filtre_sayisi += 1
if st.session_state.get("pft_gizli", False): aktif_filtre_sayisi += 1

filtre_btn_text = f"Filtreler · {aktif_filtre_sayisi}" if aktif_filtre_sayisi > 0 else "Filtreler"

with tb5:
    if st.button(
        filtre_btn_text,
        key="toggle_portfoy_filter_panel_btn",
        use_container_width=True,
        type="secondary"
    ):
        st.session_state["show_portfoy_filters_panel"] = not st.session_state["show_portfoy_filters_panel"]
        st.rerun()

# ── Filtreler ─────────────────────────────────────────────────────────────

tum_iller = sorted(set(il_grubu(v) for v in veriler if il_grubu(v)))
tum_ilceler = sorted(set(
    ilce for v in veriler
    if (st.session_state.get("pft_il", "Tümü") == "Tümü" or il_grubu(v) == st.session_state.get("pft_il", "Tümü"))
    for ilce in (v.get("ilceler") or [])
    if ilce and ilce != "Diğer Bölge"
))
danismanlar = sorted(set(
    isim_ayikla(v.get("talep_eden_danisan", ""))
    for v in veriler if v.get("talep_eden_danisan", "")
))

if st.session_state.get("pft_il") not in (["Tümü"] + tum_iller + ["Belirtilmemiş"]):
    st.session_state["pft_il"] = "Tümü"
if st.session_state.get("pft_ilce") not in (["Tümü"] + tum_ilceler):
    st.session_state["pft_ilce"] = "Tümü"
if st.session_state.get("pft_danisan") not in (["Tümü"] + danismanlar):
    st.session_state["pft_danisan"] = "Tümü"
if st.session_state.get("pft_mulk") not in ["Tümü", "Konut", "İşyeri", "Arsa", "Belirtilmemiş"]:
    st.session_state["pft_mulk"] = "Tümü"
if st.session_state.get("pft_islem") not in ["Tümü", "Satılık", "Kiralık", "Belirtilmemiş"]:
    st.session_state["pft_islem"] = "Tümü"
if st.session_state.get("pft_siralama") not in ["Tarih ↓", "Tarih ↑", "İlçe A→Z", "İlçe Z→A", "Fiyat ↑", "Fiyat ↓"]:
    st.session_state["pft_siralama"] = "Tarih ↓"

if st.session_state.get("show_portfoy_filters_panel", False):
    with st.container(border=True):
        # Satır 1: Temel filtreler
        c1, c2, c3, c4, c5 = st.columns([1.1, 1.1, 1.7, 1.1, 1.1])
        with c1: il_filtre = st.selectbox("İl", ["Tümü"] + tum_iller + ["Belirtilmemiş"], key="pft_il")
        with c2: ilce_filtre = st.selectbox("İlçe", ["Tümü"] + tum_ilceler, key="pft_ilce")
        with c3: danisan_filtre = st.selectbox("Danışman", ["Tümü"] + danismanlar, key="pft_danisan")
        with c4: mulk_filtre = st.selectbox("Mülk", ["Tümü","Konut","İşyeri","Arsa","Belirtilmemiş"], key="pft_mulk")
        with c5: islem_filtre = st.selectbox("İşlem", ["Tümü","Satılık","Kiralık","Belirtilmemiş"], key="pft_islem")

        # Satır 2: Fiyat + Özellikler
        g1, g2, g3, g4, g5, g6 = st.columns([1.2, 1.2, 1.2, 1.2, 1.2, 1.2])
        with g1:
            st.caption("Fiyat Alt (TL)")
            fiyat_alt = st.number_input("", min_value=0, step=100000, key="pft_fiyat_alt", label_visibility="collapsed")
        with g2:
            st.caption("Fiyat Üst (TL)")
            fiyat_ust = st.number_input("", min_value=0, step=100000, key="pft_fiyat_ust", label_visibility="collapsed")
        oda_opts = ["Tümü"] + sorted(set(str(v.get("oda_sayisi_m2","")).strip() for v in veriler if v.get("oda_sayisi_m2","") not in ("","None",None)))
        with g3: oda_filtre = st.selectbox("Oda / M²", oda_opts, key="pft_oda")
        with g4: esyali_filtre = st.selectbox("Eşyalı", ["Tümü","Evet","Hayır"], key="pft_esyali")
        with g5: site_ici_filtre = st.selectbox("Site İçi", ["Tümü","Evet","Hayır"], key="pft_site_ici")
        with g6: kullanim_filtre = st.selectbox("Kullanım", ["Tümü","Boş","Kiracılı","Malik"], key="pft_kullanim")

        # Satır 3: Yapı + Arama + Sıralama
        h1, h2, h3, h4, h5 = st.columns([1.2, 1.2, 1.2, 1.8, 1.4])
        byas_opts = ["Tümü"] + sorted(set(str(v.get("bina_yasi","")).strip() for v in veriler if v.get("bina_yasi","") not in ("","None",None)))
        with h1: bina_yasi_filtre = st.selectbox("Bina Yaşı", byas_opts, key="pft_bina_yasi")
        kat_opts = ["Tümü"] + sorted(set(str(v.get("bulundugu_kat","")).strip() for v in veriler if v.get("bulundugu_kat","") not in ("","None",None)))
        with h2: kat_filtre = st.selectbox("Kat", kat_opts, key="pft_kat")
        with h3: siralama = st.selectbox("Sıralama", ["Tarih ↓","Tarih ↑","İlçe A→Z","İlçe Z→A","Fiyat ↑","Fiyat ↓"], key="pft_siralama")
        with h4: ara = st.text_input("Arama", placeholder="Başlık, ilçe, özellik...", key="pft_ara")
        with h5:
            tarih_aralik_cb = st.checkbox("Tarih Aralığı", key="pft_tarih_mod_cb")
            if tarih_aralik_cb:
                bas_tarih = st.date_input("Başlangıç", value=date.today()-timedelta(days=30), max_value=date.today(), key="pft_bas", label_visibility="collapsed")
                bit_tarih = st.date_input("Bitiş", value=date.today(), max_value=date.today(), key="pft_bit", label_visibility="collapsed")
            else:
                bas_tarih, bit_tarih = None, None
            tarih_mod = tarih_aralik_cb

        # Satır 4: Checkboxlar + Temizle
        e1, e2, e3, e4, e5 = st.columns([1, 1, 1, 1.2, 5.8])
        with e1: favori_filtre = st.checkbox("Favori", key="pft_fav")
        with e2: gizlileri_goster = st.checkbox("Gizli", key="pft_gizli")
        # tarih aralığı h5 içinde
        with e4: st.write(""); st.button("Temizle", key="portfoy_filtre_temizle_btn", use_container_width=True, on_click=filtre_temizle)

else:
    hizli = st.session_state.get("pft_hizli", "Son 7 gün")
    il_filtre = st.session_state.get("pft_il", "Tümü")
    ilce_filtre = st.session_state.get("pft_ilce", "Tümü")
    danisan_filtre = st.session_state.get("pft_danisan", "Tümü")
    mulk_filtre = st.session_state.get("pft_mulk", "Tümü")
    islem_filtre = st.session_state.get("pft_islem", "Tümü")
    siralama = st.session_state.get("pft_siralama", "Tarih ↓")
    tarih_mod = bool(st.session_state.get("pft_tarih_mod_cb", False))
    bas_tarih = st.session_state.get("pft_bas", None) if tarih_mod else None
    bit_tarih = st.session_state.get("pft_bit", None) if tarih_mod else None
    ara = st.session_state.get("pft_ara", "")
    favori_filtre = st.session_state.get("pft_fav", False)
    gizlileri_goster = st.session_state.get("pft_gizli", False)
    fiyat_alt = st.session_state.get("pft_fiyat_alt", 0)
    fiyat_ust = st.session_state.get("pft_fiyat_ust", 0)
    oda_filtre = st.session_state.get("pft_oda", "Tümü")
    esyali_filtre = st.session_state.get("pft_esyali", "Tümü")
    site_ici_filtre = st.session_state.get("pft_site_ici", "Tümü")
    kullanim_filtre = st.session_state.get("pft_kullanim", "Tümü")
    bina_yasi_filtre = st.session_state.get("pft_bina_yasi", "Tümü")
    kat_filtre = st.session_state.get("pft_kat", "Tümü")

# ── Filtreleme ────────────────────────────────────────────────────────────

f = veriler
if ara:
    f = [v for v in f if any(
        ara.lower() in str(v.get(k,"")).lower()
        for k in ["talep_eden_danisan","bolge_mahalle","mahalle","bolge","ilce","mail_konusu","ozet"]
    )]
if il_filtre == "Belirtilmemiş": f = [v for v in f if not il_grubu(v)]
elif il_filtre != "Tümü": f = [v for v in f if il_grubu(v) == il_filtre]
if ilce_filtre != "Tümü": f = [v for v in f if ilce_filtre in (v.get("ilceler") or [])]
if danisan_filtre != "Tümü": f = [v for v in f if isim_ayikla(v.get("talep_eden_danisan","")) == danisan_filtre]
if mulk_filtre == "Belirtilmemiş": f = [v for v in f if v.get("mulk_tipi","") in ("","Belirsiz","Belirtilmemiş",None)]
elif mulk_filtre != "Tümü": f = [v for v in f if v.get("mulk_tipi","") == mulk_filtre]
if islem_filtre == "Belirtilmemiş": f = [v for v in f if v.get("islem_tipi","") in ("","Belirsiz","Belirtilmemiş",None)]
elif islem_filtre != "Tümü": f = [v for v in f if v.get("islem_tipi","") == islem_filtre]
if hizli != "Tümü":
    gl = {"Son 7 gün":7,"Son 30 gün":30,"Son 60 gün":60,"Son 90 gün":90}.get(hizli,9999)
    f = [v for v in f if tarih_gun_farki(en_iyi_tarih(v)) <= gl]
if bas_tarih and bit_tarih:
    f = [v for v in f if (d:=tarih_parse(en_iyi_tarih(v))) and bas_tarih <= (d.date() if hasattr(d,"date") and callable(d.date) else d) <= bit_tarih]
if favori_filtre: f = [v for v in f if v.get("favori", False)]
if oda_filtre != "Tümü": f = [v for v in f if str(v.get("oda_sayisi_m2","")).strip() == oda_filtre]
if bina_yasi_filtre != "Tümü": f = [v for v in f if str(v.get("bina_yasi","")).strip() == bina_yasi_filtre]
if kat_filtre != "Tümü": f = [v for v in f if str(v.get("bulundugu_kat","")).strip() == kat_filtre]
if esyali_filtre == "Evet": f = [v for v in f if any(k in (str(v.get("ozellikler",""))+str(v.get("ozet",""))).lower() for k in ["eşyalı","eşyali","mobilyalı"])]
elif esyali_filtre == "Hayır": f = [v for v in f if not any(k in (str(v.get("ozellikler",""))+str(v.get("ozet",""))).lower() for k in ["eşyalı","eşyali","mobilyalı"])]
if site_ici_filtre == "Evet": f = [v for v in f if any(k in (str(v.get("ozellikler",""))+str(v.get("ozet",""))).lower() for k in ["site içi","siteiçi"])]
elif site_ici_filtre == "Hayır": f = [v for v in f if not any(k in (str(v.get("ozellikler",""))+str(v.get("ozet",""))).lower() for k in ["site içi","siteiçi"])]
if kullanim_filtre != "Tümü": f = [v for v in f if kullanim_filtre.lower() in (str(v.get("kullanim_durumu",""))+str(v.get("ozet",""))).lower()]
if fiyat_alt > 0: f = [v for v in f if fiyat_sayisal(v.get("fiyat","")) >= fiyat_alt]
if fiyat_ust > 0: f = [v for v in f if fiyat_sayisal(v.get("fiyat","")) <= fiyat_ust]
f = siralama_uygula(f, siralama)

# ── Yeni Çalışma Alanı: favoriler + aks haritası ──────────────────────────
workspace_options = ["Haftalık Liste", "Favori İlçeler", "İzmir Aksları", "Diğer İlçeler"]
if st.session_state.get("aktif_portfoy_workspace") not in workspace_options:
    st.session_state["aktif_portfoy_workspace"] = "Haftalık Liste"
if "portfoy_aks_secili_ilce" not in st.session_state:
    st.session_state["portfoy_aks_secili_ilce"] = None

# ── Favori ilçe chip'leri — session_state native (talep tablosuyla aynı mekanizma) ──
_pfav_list = favori_ilceleri_cek()
_pfav_secili = st.session_state.get("pfav_secili_ilce")

# query_params ile tıklama — talep tablosuyla aynı pattern
_qp = st.query_params
if "pfav_ilce" in _qp:
    _gelen = _qp["pfav_ilce"]
    if _gelen == "__tumu__":
        st.session_state["pfav_secili_ilce"] = None
        st.session_state["ana_portfoy_sekme"] = "Favorilerim"
        del st.query_params["pfav_ilce"]
        st.rerun()
    elif _gelen == "__ekle__":
        st.session_state["pfav_ekle_ac"] = True
        del st.query_params["pfav_ilce"]
        st.rerun()
    else:
        st.session_state["pfav_secili_ilce"] = None if _pfav_secili == _gelen else _gelen
        st.session_state["ana_portfoy_sekme"] = "Favorilerim"
        del st.query_params["pfav_ilce"]
        st.rerun()

_pfav_secili = st.session_state.get("pfav_secili_ilce")

# Chip HTML — talep tablosuyla birebir aynı CSS class'ları
_chip_html = '<div class="firsat-row">'
if _pfav_list:
    _pfav_toplam = sum(ilce_istatistik(i, f)[0] for i in _pfav_list[:5])
    _tumu_cls = "fchip fchip-tumu active" if not _pfav_secili else "fchip fchip-tumu"
    _chip_html += f'<a href="?pfav_ilce=__tumu__" style="text-decoration:none;"><button class="{_tumu_cls}">★ Tüm Favoriler &nbsp;{_pfav_toplam}</button></a>'
    for _pfilce in _pfav_list[:5]:
        _pftoplam, _pfyeni = ilce_istatistik(_pfilce, f)
        if _pftoplam == 0: continue
        _pfsecili = _pfav_secili == _pfilce
        _ilce_cls = "fchip fchip-ilce active" if _pfsecili else "fchip fchip-ilce"
        _yeni_html = f'<span class="fchip-yeni">{_pfyeni} yeni</span>' if _pfyeni > 0 else ""
        _chip_html += f'<a href="?pfav_ilce={_pfilce}" style="text-decoration:none;"><button class="{_ilce_cls}">★ {_pfilce} &nbsp;{_pftoplam}{_yeni_html}</button></a>'
    _chip_html += '<a href="?pfav_ilce=__ekle__" style="text-decoration:none;"><button class="fchip fchip-ekle">+ Favori Ekle</button></a>'
_chip_html += '</div>'
st.markdown(_chip_html, unsafe_allow_html=True)

if st.session_state.get("pfav_ekle_ac", False):
    eklenebilir = [i for i in ilce_sec if i not in _pfav_list]
    _ca, _cb, _cc = st.columns([2.2, 0.8, 5])
    with _ca:
        _yeni_ilce = st.selectbox("Favori ilçe seç", ["Seç..."] + eklenebilir, key="pfav_ilce_sec2", label_visibility="collapsed")
    with _cb:
        if st.button("Ekle", key="pfav_ekle_btn2", disabled=(_yeni_ilce == "Seç...")):
            favori_ilce_guncelle(_pfav_list + [_yeni_ilce])
            st.session_state["pfav_ekle_ac"] = False; st.rerun()

# ── Sekme satırı — sadece görünüm toggle ──────────────────────────────────────
_gsc = st.columns([0.2, 0.85, 0.85, 6])
for _si, _val, _vlbl in [(_gsc[1],"Kart","  🃏 Kart  "),(_gsc[2],"Tablo","  ≡ Tablo  ")]:
    with _si:
        _aktif = st.session_state.get("pft_gorunum") == _val
        if st.button(_vlbl, key=f"portfoy_view_{_val}", use_container_width=True,
                     type="primary" if _aktif else "secondary"):
            st.session_state["pft_gorunum"] = _val
            st.rerun()

fav_secili = st.session_state.get("pfav_secili_ilce")

# Favori ilçe chip seçimine göre filtrele
if fav_secili:
    f = [v for v in f if fav_secili in (v.get("ilceler") or [])]

# Favoriler ve tüm liste
fav_ilceler_for_filter = favori_ilceleri_cek()
def favori_portfoy_kaydi_mi(v, fav_il):
    return any(i in fav_il for i in (v.get("ilceler") or []))

favori_f = [v for v in f if favori_portfoy_kaydi_mi(v, fav_ilceler_for_filter)]

st.caption(f"**{len(f)}** / {len(veriler)} portföy" + (f" · {gizli_sayi} gizlenmiş" if gizli_sayi > 0 else ""))

# ── Render ────────────────────────────────────────────────────────────────

gorunum = st.session_state.get("pft_gorunum", "Tablo")
if gorunum not in ["Kart", "Tablo"]:
    gorunum = "Tablo"

# Renk açıklaması (legend)
st.markdown(
    '<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;font-size:10px;color:#94a3b8;">'
    '<span style="display:flex;align-items:center;gap:4px;"><span style="width:7px;height:7px;border-radius:50%;background:#16a34a;display:inline-block;"></span><span>≤7 gün</span></span>'
    '<span style="display:flex;align-items:center;gap:4px;"><span style="width:7px;height:7px;border-radius:50%;background:#ca8a04;display:inline-block;"></span><span>8-30 gün</span></span>'
    '<span style="display:flex;align-items:center;gap:4px;"><span style="width:7px;height:7px;border-radius:50%;background:#ea580c;display:inline-block;"></span><span>31-90 gün</span></span>'
    '<span style="display:flex;align-items:center;gap:4px;"><span style="width:7px;height:7px;border-radius:50%;background:#dc2626;display:inline-block;"></span><span>&gt;90 gün</span></span>'
    '<span style="display:flex;align-items:center;gap:4px;"><span style="width:7px;height:7px;border-radius:50%;background:#cbd5e1;display:inline-block;"></span><span>Görüldü</span></span>'
    '</div>',
    unsafe_allow_html=True
)

def _portfoy_tablo_render(kayitlar, prefix):
    """Portföy tablosu satırlarını render et."""
    COL_RATIOS = [1.5, 3.8, 1.2, 2, 2, 1.2, 0.9, 1, 0.5, 0.5]
    headers = ["İlçe", "Portföy Başlığı", "İşlem", "Fiyat", "Danışman", "Tarih", "Kaynak", "", "", ""]
    h = st.columns(COL_RATIOS)
    for col, hdr in zip(h, headers):
        with col:
            st.markdown(
                f'<div style="font-size:10px;font-weight:600;color:#94a3b8;'
                f'text-transform:uppercase;letter-spacing:0.06em;'
                f'padding:8px 0 6px;border-bottom:1px solid #e2e8f0;">{hdr}</div>',
                unsafe_allow_html=True
            )
    for v in kayitlar:
        kid = v.get("id","")
        isim = isim_ayikla(v.get("talep_eden_danisan",""))
        ilce = ilce_grubu(v) or "—"
        islem = v.get("islem_tipi","") or ""
        mulk = v.get("mulk_tipi","") or ""
        fiyat = v.get("fiyat","") or "—"
        oda = v.get("oda_sayisi_m2","") or ""
        ozet = v.get("ozet","") or v.get("mail_konusu","") or ""
        favori = v.get("favori", False)
        gun_farki = tarih_gun_farki(en_iyi_tarih(v))
        okundu = kid in st.session_state.get("portfoy_goruldu_ids", set())
        _tarih_fg, _tarih_bg, dot_c = tarih_renk_bilgisi(gun_farki)
        if okundu:
            dot_c = "#cbd5e1"; _tarih_fg = "#94a3b8"; _tarih_bg = "#f8fafc"
        tarih_d = tarih_parse(en_iyi_tarih(v))
        if tarih_d:
            _has_t = hasattr(tarih_d,"hour") and (tarih_d.hour != 0 or tarih_d.minute != 0)
            tarih_str = tarih_d.strftime("%d.%m %H:%M") if _has_t else tarih_d.strftime("%d.%m.%Y")
        else:
            tarih_str = "—"
        aks_r = aks_renk_bul([ilce] if ilce != "—" else [])
        if "iralık" in islem: tip_bg,tip_color,tip_lbl="#f0fdf4","#166534","Kiralık"
        elif "atılık" in islem: tip_bg,tip_color,tip_lbl="#fef2f2","#991b1b","Satılık"
        else: tip_bg,tip_color,tip_lbl="#f8fafc","#64748b", islem or mulk or "—"
        kaynak_raw = (v.get("kaynak") or "").lower()
        if kaynak_raw in ("startkey_mail", ""):
            k_lbl, k_c, k_bg = "Startkey", "#355C7D", "#EEF4FA"
        elif kaynak_raw in ("zeta1", "zeta2", "ofis", "zeta"):
            k_lbl, k_c, k_bg = "Zeta", "#0F6E56", "#E1F5EE"
        else:
            k_lbl, k_c, k_bg = "Diğer", "#475569", "#f1f5f9"
        initials = "".join(w[0].upper() for w in isim.split()[:2]) if isim else "?"
        _b_parts = []
        if islem and islem not in ("Belirsiz","Belirtilmemiş"): _b_parts.append(islem)
        if oda: _b_parts.append(oda)
        if mulk and mulk not in ("Belirsiz","Belirtilmemiş"): _b_parts.append(mulk)
        _b_parts.append("İlanı" if islem and islem not in ("Belirsiz","") else "Portföyü")
        baslik = " ".join(_b_parts)
        kriter = ozet[:55]
        ROW_BORDER = "border-bottom:0.5px solid #f1f5f9;padding:8px 0;"
        row = st.columns(COL_RATIOS)
        with row[0]:
            st.markdown(f'<div style="{ROW_BORDER}"><span style="background:{aks_r["bg"]};color:{aks_r["text"]};padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600;">{ilce}</span></div>', unsafe_allow_html=True)
        with row[1]:
            st.markdown(
                f'<div style="{ROW_BORDER}"><div style="display:flex;align-items:center;gap:6px;">'
                f'<span style="width:6px;height:6px;border-radius:50%;background:{dot_c};flex-shrink:0;display:inline-block;"></span>'
                f'<span style="font-size:12px;font-weight:600;color:#1e293b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:95%;display:block;">{baslik}</span>'
                f'</div>'
                + (f'<div style="font-size:10.5px;color:#64748b;margin-left:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{kriter}</div>' if kriter else "")
                + f'</div>', unsafe_allow_html=True)
        with row[2]:
            st.markdown(f'<div style="{ROW_BORDER}"><span style="background:{tip_bg};color:{tip_color};padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600;">{tip_lbl}</span></div>', unsafe_allow_html=True)
        with row[3]:
            st.markdown(f'<div style="{ROW_BORDER};font-size:11.5px;font-weight:600;color:#0f172a;">{fiyat}</div>', unsafe_allow_html=True)
        with row[4]:
            st.markdown(f'<div style="{ROW_BORDER};display:flex;align-items:center;gap:5px;"><span style="font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{isim or "—"}</span></div>', unsafe_allow_html=True)
        with row[5]:
            st.markdown(f'<div style="{ROW_BORDER}"><span style="background:{_tarih_bg};color:{_tarih_fg};font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:4px;white-space:nowrap;">{tarih_str}</span></div>', unsafe_allow_html=True)
        with row[6]:
            st.markdown(f'<div style="{ROW_BORDER}"><span style="background:{k_bg};color:{k_c};font-size:10px;font-weight:600;padding:2px 6px;border-radius:4px;">{k_lbl}</span></div>', unsafe_allow_html=True)
        with row[7]:
            if st.button("Detay", key=f"{prefix}_detay_{kid}", use_container_width=True, type="primary"):
                st.session_state.setdefault("portfoy_goruldu_ids", set()).add(kid)
                portfoy_detay_goster(v, ilce_sec)
        with row[8]:
            _fl = "★" if favori else "☆"
            if st.button(_fl, key=f"{prefix}_fav_{kid}", use_container_width=True):
                favori_guncelle(kid, favori)
        with row[9]:
            if st.button("✏", key=f"{prefix}_dz_{kid}", use_container_width=True):
                st.session_state[f"duzen_{kid}"] = not st.session_state.get(f"duzen_{kid}", False)
                st.rerun()
        if st.session_state.get(f"duzen_{kid}", False):
            duzenleme_formu(v, ilce_sec)


# ── Favori İlanlarım ─────────────────────────────────────────────────────────
if favori_f:
    st.markdown(
        '<div style="font-size:11px;font-weight:800;color:#92400e;text-transform:uppercase;'
        'letter-spacing:0.08em;padding:10px 0 6px 0;border-bottom:1px solid #fde68a;margin-bottom:6px;">'
        '★ Favori İlanlarım</div>',
        unsafe_allow_html=True
    )
    if gorunum == "Tablo":
        _portfoy_tablo_render(favori_f, "pfav")
    elif gorunum == "Kart":
        cols3 = st.columns(2, gap="medium")
        for idx, v in enumerate(favori_f):
            with cols3[idx % 2]:
                kid = v.get("id")
                yeni = tarih_gun_farki(en_iyi_tarih(v)) <= 7
                okundu_k = kid in st.session_state.get("portfoy_goruldu_ids", set())
                favori_k = v.get("favori", False)
                if okundu_k:
                    _rozet_k = '<span style="background:#f1f5f9;color:#64748b;font-size:10px;font-weight:700;padding:3px 9px;border-radius:5px;">Görüldü</span>'
                elif yeni:
                    _rozet_k = '<span style="background:#16a34a;color:#fff;font-size:10px;font-weight:700;padding:3px 9px;border-radius:5px;">Yeni</span>'
                else:
                    _rozet_k = ""
                st.markdown(portfoy_kart_html(v, rozet_html=_rozet_k), unsafe_allow_html=True)
                _pc1, _pc2, _pc3 = st.columns([3, 1, 1])
                with _pc1:
                    if st.button("Detay →", key=f"pfav_kd_{kid}", use_container_width=True, type="primary"):
                        st.session_state.setdefault("portfoy_goruldu_ids", set()).add(kid)
                        portfoy_detay_goster(v, ilce_sec)
                with _pc2:
                    if st.button("★" if favori_k else "☆", key=f"pfav_kfav_{kid}", use_container_width=True):
                        favori_guncelle(kid, favori_k)
                with _pc3:
                    if st.button("⋯", key=f"pfav_more_{kid}", use_container_width=True):
                        st.session_state[f"pmore_{kid}"] = not st.session_state.get(f"pmore_{kid}", False)
                        st.rerun()
                if st.session_state.get(f"pmore_{kid}", False):
                    _m1, _m2 = st.columns(2)
                    with _m1:
                        if st.button("Düzenle", key=f"pfav_dz_{kid}", use_container_width=True, type="secondary"):
                            st.session_state[f"duzen_{kid}"] = not st.session_state.get(f"duzen_{kid}", False)
                            st.session_state[f"pmore_{kid}"] = False
                            st.rerun()
                    with _m2:
                        if st.button("Gizle", key=f"pfav_giz_{kid}", use_container_width=True, type="secondary"):
                            get_client().table("portfoyler").update({"gizli": True}).eq("id", kid).execute()
                            st.cache_data.clear(); st.rerun()
                if st.session_state.get(f"duzen_{kid}", False):
                    duzenleme_formu(v, ilce_sec)

# ── Tüm İlanlar ──────────────────────────────────────────────────────────────
if not f:
    st.info("Bu filtreyle eşleşen portföy bulunamadı.")
else:
    st.markdown(
        f'<div style="font-size:11px;font-weight:800;color:#355C7D;text-transform:uppercase;'
        f'letter-spacing:0.08em;padding:14px 0 6px 0;border-bottom:1px solid #dce4ee;margin-bottom:6px;">'
        f'Tüm İlanlar · <span style="font-weight:500;color:#64748b;">{len(f)} portföy</span></div>',
        unsafe_allow_html=True
    )
    if gorunum == "Tablo":
        _portfoy_tablo_render(f, "tum")
    elif gorunum == "Kart":
        cols3 = st.columns(2, gap="medium")
        for idx, v in enumerate(f):
            with cols3[idx % 2]:
                kid = v.get("id")
                yeni = tarih_gun_farki(en_iyi_tarih(v)) <= 7
                okundu_k = kid in st.session_state.get("portfoy_goruldu_ids", set())
                favori_k = v.get("favori", False)
                if okundu_k:
                    _rozet_k = '<span style="background:#f1f5f9;color:#64748b;font-size:10px;font-weight:700;padding:3px 9px;border-radius:5px;">Görüldü</span>'
                elif yeni:
                    _rozet_k = '<span style="background:#16a34a;color:#fff;font-size:10px;font-weight:700;padding:3px 9px;border-radius:5px;">Yeni</span>'
                else:
                    _rozet_k = ""
                st.markdown(portfoy_kart_html(v, rozet_html=_rozet_k), unsafe_allow_html=True)
                _tc1, _tc2, _tc3 = st.columns([3, 1, 1])
                with _tc1:
                    if st.button("Detay →", key=f"tum_kd_{kid}", use_container_width=True, type="primary"):
                        st.session_state.setdefault("portfoy_goruldu_ids", set()).add(kid)
                        portfoy_detay_goster(v, ilce_sec)
                with _tc2:
                    if st.button("★" if favori_k else "☆", key=f"tum_kfav_{kid}", use_container_width=True):
                        favori_guncelle(kid, favori_k)
                with _tc3:
                    if st.button("⋯", key=f"tum_more_{kid}", use_container_width=True):
                        st.session_state[f"tpmore_{kid}"] = not st.session_state.get(f"tpmore_{kid}", False)
                        st.rerun()
                if st.session_state.get(f"tpmore_{kid}", False):
                    _m1, _m2 = st.columns(2)
                    with _m1:
                        if st.button("Düzenle", key=f"tum_dz_{kid}", use_container_width=True, type="secondary"):
                            st.session_state[f"duzen_{kid}"] = not st.session_state.get(f"duzen_{kid}", False)
                            st.session_state[f"tpmore_{kid}"] = False
                            st.rerun()
                    with _m2:
                        if st.button("Gizle", key=f"tum_giz_{kid}", use_container_width=True, type="secondary"):
                            get_client().table("portfoyler").update({"gizli": True}).eq("id", kid).execute()
                            st.cache_data.clear(); st.rerun()
                if st.session_state.get(f"duzen_{kid}", False):
                    duzenleme_formu(v, ilce_sec)


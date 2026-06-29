"""
arsiv_merkezi.py
Talep Arşivi + Portföy Arşivi — tek sayfada iki sekme.
60 günden eski kayıtları gösterir.
"""

import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.supabase_client import get_client
from core.ui_helpers import render_navbar, render_page_header
import pandas as pd
import re
from datetime import date, timedelta, datetime
from email.utils import parsedate_to_datetime


# ════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS (iki sekme için ortak — talep ve portföy stilleri birleşik)
# ════════════════════════════════════════════════════════════════════════════
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
    white-space: normal; line-height: 1.2; border-radius: 8px;
    border: 1px solid var(--border); min-height: 30px; padding: 6px 12px;
    font-size: 12px; font-weight: 600; background: var(--chip-bg);
    color: var(--text); transition: all 0.16s ease-in-out;
}
div[data-testid="stButton"] > button p {
    font-size: 12px !important; line-height: 1.2 !important; margin: 0 !important;
}
div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stButton"] > button[kind="primary"]:focus {
    background: var(--primary) !important; border-color: var(--primary) !important;
    color: #ffffff !important; box-shadow: 0 2px 8px rgba(53,92,125,0.18) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: var(--primary-hover) !important; border-color: var(--primary-hover) !important;
    color: #ffffff !important; box-shadow: 0 4px 12px rgba(53,92,125,0.16) !important;
}
div[data-testid="stButton"] > button[kind="secondary"] {
    background: var(--hover-bg) !important; border: 1px solid var(--border) !important;
    color: var(--text) !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover {
    background: #f4f8fd !important; border-color: #cad7e7 !important;
    box-shadow: 0 2px 8px rgba(53,92,125,0.08) !important;
}
div[data-testid="stButton"] > button:hover {
    border-color: #c8d7e5; box-shadow: 0 1px 4px rgba(53,92,125,0.08);
}

[data-testid="stContainer"] {
    border-radius: 10px; border-color: var(--border) !important;
    box-shadow: 0 2px 8px rgba(15,23,42,0.03); background: #ffffff;
}

.stCaption { color: var(--muted) !important; }
h1 { color: var(--text); letter-spacing: -0.7px; font-size: 1.4rem !important; margin-bottom: 0.1rem !important; }
h2, h3, h4 { color: #1f2937; letter-spacing: -0.2px; }

div[data-baseweb="select"] > div {
    border-radius: 6px !important; border-color: var(--border) !important;
    min-height: 32px !important; font-size: 12px !important;
}
input { border-radius: 6px !important; font-size: 12px !important; }
input::placeholder { color: #94a3b8 !important; opacity: 1 !important; }
label, .stSelectbox label, .stTextInput label {
    color: #475569 !important; font-weight: 600 !important; font-size: 11px !important;
}

/* ── FİRSAT / FAVORİ CHIP'LERİ ────────────────────────────────── */
.firsat-row {
    display: flex; gap: 8px; align-items: center;
    flex-wrap: wrap; padding: 6px 0 4px 0;
}
.fchip {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 6px 14px; border-radius: 999px; font-size: 12.5px;
    font-weight: 700; cursor: pointer; white-space: nowrap;
    border: none; transition: all 0.15s ease; font-family: inherit; line-height: 1;
}
.fchip-tumu { background: #f1f5f9; color: #475569; border: 1px solid #dce4ee; }
.fchip-tumu.active { background: linear-gradient(135deg,#1E3A5F,#355C7D); color:#fff; border-color:transparent; }
.fchip-ilce { background: linear-gradient(135deg,#fff1f3 0%,#fff8f0 100%); color: #b91c1c; border: 1px solid #fca5a5; }
.fchip-ilce:hover { background: linear-gradient(135deg,#ffe4e6 0%,#fff0e6 100%); box-shadow: 0 2px 8px rgba(220,38,38,0.18); }
.fchip-ilce.active { background: linear-gradient(135deg,#b91c1c,#dc2626); color:#fff; border-color:transparent; box-shadow: 0 3px 10px rgba(185,28,28,0.25); }
.fchip-yeni { background:#16a34a; color:white; border-radius:999px; font-size:10px; font-weight:750; padding:1px 6px; margin-left:3px; }
.fchip-ekle { background:transparent; color:#94a3b8; border: 1px dashed #dce4ee; font-weight:600; }
.fchip-ekle:hover { border-color:#b91c1c; color:#b91c1c; }

/* ── KART SİSTEMİ ─────────────────────────────────────────────── */
.nkart {
    background: #fff; border: 0.5px solid #e2e8f0; border-radius: 12px;
    overflow: hidden; display: flex; flex-direction: column;
    transition: border-color 0.15s, box-shadow 0.15s; margin-bottom: 10px;
}
.nkart:hover { border-color: #b0c4d8; box-shadow: 0 4px 16px rgba(15,23,42,0.08); }
.nkart-topbar { height: 3px; width: 100%; }
.nkart-body { padding: 12px 14px 8px; flex: 1; display: flex; flex-direction: column; gap: 6px; }
.nkart-district { font-size:10px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; }
.nkart-title { font-size:13px; font-weight:700; color:#0F172A; line-height:1.4; margin:0; }
.nkart-desc { font-size:11px; color:#64748B; line-height:1.5; flex:1;
    display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.nkart-meta { display:flex; flex-wrap:wrap; gap:4px; align-items:center; }
.nkart-price { font-size:14px; font-weight:600; color:#0F172A; }
.nkart-price-empty { font-size:11px; color:#94a3b8; font-style:italic; }
.nkart-date { font-size:10px; color:#94a3b8; }
.nkart-footer {
    border-top: 0.5px solid #e9eef5; padding: 8px 14px; background: #f8fafc;
    display: flex; align-items: center; justify-content: space-between; gap: 6px;
}
.nkart-avatar {
    width:22px; height:22px; border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-size:9px; font-weight:700; flex-shrink:0;
}
.nkart-agent { font-size:11px; color:#64748B; display:flex; align-items:center; gap:5px; }
.nbadge {
    display:inline-flex; align-items:center; gap:3px;
    font-size:10.5px; font-weight:500; padding:2px 7px; border-radius:20px;
}
.nbadge-yeni { background:#EAF3DE; color:#3B6D11; }
.nbadge-goruldu { background:#f1f5f9; color:#94a3b8; }
.nbadge-oda { background:#f1f5f9; color:#475569; border:1px solid #e2e8f0; }
.dot-live { width:5px; height:5px; border-radius:50%; background:#639922; display:inline-block; }

/* ── TABLO ──────────────────────────────────────────────────────── */
.zt-table-wrap { background:#fff; border:1px solid #e2e8f0; border-radius:10px; overflow:hidden; margin-top:4px; }
.zt-table { width:100%; border-collapse:collapse; table-layout:fixed; }
.zt-table thead tr { background:#f8fafc; }
.zt-table th {
    padding:9px 12px; text-align:left; font-size:10.5px; font-weight:600;
    color:#94a3b8; letter-spacing:0.06em; text-transform:uppercase;
    border-bottom:1px solid #e2e8f0; white-space:nowrap;
}
.zt-table td { padding:10px 12px; font-size:12px; color:#1e293b; border-bottom:0.5px solid #f1f5f9; vertical-align:middle; }
.zt-table tr:last-child td { border-bottom:none; }
.zt-table tr:hover td { background:rgba(30,58,95,0.02); }
.zt-row-title { font-size:12px; font-weight:600; color:#1e293b; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:100%; display:block; }
.zt-row-desc { font-size:11px; color:#64748b; margin-top:1px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; display:block; }
.zt-ilce-tag { display:inline-block; padding:2px 7px; border-radius:4px; font-size:10px; font-weight:600; white-space:nowrap; }
.zt-tip-satilik { background:#fef2f2; color:#991b1b; }
.zt-tip-kiralik { background:#f0fdf4; color:#166534; }
.zt-tip-belirsiz { background:#f8fafc; color:#64748b; }
.zt-butce { font-size:11.5px; font-weight:600; color:#0f172a; }
.zt-tarih { font-size:10.5px; color:#94a3b8; line-height:1.4; }

/* ── FİLTRE BADGE ────────────────────────────────────────────────── */
.filtre-badge {
    display:inline-block; background:#ff4d4f; color:white;
    border-radius:999px; font-size:10px; font-weight:700;
    padding:0 5px; margin-left:4px; vertical-align:middle; line-height:16px; height:16px;
}

/* ── KART ŞERIT / ROZET ──────────────────────────────────────────── */
.kart-kriter {
    font-size:11.5px; font-style:italic; color:#94a3b8; line-height:1.45;
    margin-bottom:6px; display:-webkit-box; -webkit-line-clamp:2;
    -webkit-box-orient:vertical; overflow:hidden;
}
.kart-serit-yeni   { background:linear-gradient(90deg,#16a34a,#4ade80); }
.kart-serit-normal { background:linear-gradient(90deg,#F4B740,#fbbf24); }
.kart-serit-okundu { background:#e2e8f0; }

/* ── TAB STİLİ (Streamlit native tabs için küçük tweak) ─────────── */
button[data-baseweb="tab"] { font-size:13px !important; font-weight:600 !important; }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# NAVBAR
# ════════════════════════════════════════════════════════════════════════════
render_navbar(
    user_role=st.session_state.get("user_role", "danisan"),
    user_name=st.session_state.get("user_name", ""),
    user_initials=st.session_state.get("user_initials", ""),
)


# ════════════════════════════════════════════════════════════════════════════
# ORTAK YARDIMCI FONKSİYONLAR
# ════════════════════════════════════════════════════════════════════════════

def safe_key(value):
    return re.sub(r"[^a-zA-Z0-9_ğüşöçıİĞÜŞÖÇ-]", "_", str(value or ""))


def isim_ayikla(g):
    if not g:
        return ""
    m = re.match(r'^([^<]+)', g)
    return m.group(1).strip().strip('"') if m else g


def html_temizle(text):
    if not text:
        return ""
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script.*?>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&#x[0-9a-fA-F]+;|&[a-zA-Z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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
    if not etiket or etiket in ("Belirsiz", "Belirtilmemiş"):
        return ""
    cfg = BADGE_PALETTE.get(etiket, ("#f1f5f9", "#475569", "#e2e8f0"))
    bg, fg, border = cfg
    if cls == "nbadge-oda":
        bg, fg, border = "#f1f5f9", "#475569", "#e2e8f0"
    return (
        f'<span style="background:{bg};color:{fg};border:1px solid {border};'
        f'padding:2px 7px;border-radius:20px;font-size:10.5px;font-weight:600;'
        f'margin-right:3px;display:inline-block;">{etiket}</span>'
    )


def avatar_html(isim, aks_r):
    if not isim:
        return '<div class="nkart-avatar" style="background:#f1f5f9;color:#94a3b8;">?</div>'
    harfler = "".join(p[0].upper() for p in isim.split()[:2] if p)
    return (
        f'<div class="nkart-avatar" style="background:{aks_r["bg"]};color:{aks_r["text"]};">'
        f'{harfler}</div>'
    )


def tarih_parse(s):
    if not s:
        return None
    try:
        return parsedate_to_datetime(str(s))
    except:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(s)[:len(fmt)], fmt)
        except:
            continue
    return None


def en_iyi_tarih(v):
    return (
        v.get("mail_tarihi") or v.get("kayit_tarihi")
        or v.get("olusturma_tarihi") or ""
    )


def tarih_gun_farki(s):
    d = tarih_parse(s)
    if not d:
        return 9999
    _d = d.date() if hasattr(d, 'date') and callable(d.date) else d
    return (date.today() - _d).days


def tarih_renk_bilgisi(gun):
    if gun <= 7:    return "#166534", "#dcfce7", "#16a34a"
    elif gun <= 30: return "#713f12", "#fef9c3", "#ca8a04"
    elif gun <= 90: return "#7c2d12", "#ffedd5", "#ea580c"
    elif gun <= 180: return "#7f1d1d", "#fee2e2", "#dc2626"
    else:           return "#374151", "#f3f4f6", "#9ca3af"


def fiyat_sayisal(s):
    if not s:
        return float('inf')
    t = re.sub(r'[^\d]', '', str(s))
    try:
        return float(t) if t else float('inf')
    except:
        return float('inf')


def il_grubu(v):
    il = (v.get("il") or "").strip()
    return il if il not in ("", "Diğer", None) else ""


def ilce_grubu(v):
    ilceler = v.get("ilceler") or []
    for i in ilceler:
        if i and i not in ("", "Diğer Bölge"):
            return i
    ilce = (v.get("ilce") or "").strip()
    return ilce if ilce not in ("", "Diğer Bölge") else ""


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


def ilce_istatistik(ilce, kayitlar):
    k = [v for v in kayitlar if ilce in (v.get("ilceler") or [])]
    yeni = [v for v in k if tarih_gun_farki(en_iyi_tarih(v)) <= 7]
    return len(k), len(yeni)


def izmir_kaydi_mi(v):
    return (v.get("il") or "").strip() == "İzmir"


def diger_il_kaydi_mi(v):
    il = (v.get("il") or "").strip()
    return bool(il) and il != "İzmir"


# ── İzmir Aks ─────────────────────────────────────────────────────────────
AKS_RENK = {
    "Yarımada":   {"bar": "#D85A30", "text": "#993C1D", "bg": "#FAECE7", "light": "#fdf2ef"},
    "Kuzey Aksı": {"bar": "#378ADD", "text": "#185FA5", "bg": "#E6F1FB", "light": "#eff6ff"},
    "Merkez Aks": {"bar": "#1D9E75", "text": "#0F6E56", "bg": "#E1F5EE", "light": "#f0fdf9"},
    "Güney Aksı": {"bar": "#8B5CF6", "text": "#5B21B6", "bg": "#EDE9FE", "light": "#f5f3ff"},
    "Diğer":      {"bar": "#94a3b8", "text": "#475569", "bg": "#f1f5f9", "light": "#f8fafc"},
}

IZMIR_AKS_MAP = {
    "Yarımada":   ["Güzelbahçe", "Narlıdere", "Balçova", "Urla", "Çeşme", "Karaburun", "Seferihisar"],
    "Kuzey Aksı": ["Karşıyaka", "Çiğli", "Menemen", "Foça", "Aliağa", "Dikili", "Bergama", "Kınık"],
    "Merkez Aks": ["Konak", "Bayraklı", "Bornova", "Buca", "Karabağlar", "Gaziemir"],
    "Güney Aksı": ["Menderes", "Torbalı", "Selçuk", "Tire", "Ödemiş", "Bayındır", "Kiraz", "Beydağ"],
}


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


def render_compact_aks_haritasi(kayitlar, state_key, key_prefix, entity_label="kayıt"):
    st.markdown(
        '<div style="font-size:11px;font-weight:800;color:var(--primary);'
        'letter-spacing:.08em;text-transform:uppercase;margin:10px 0 8px 0;">'
        'İzmir Aks Haritası</div>',
        unsafe_allow_html=True,
    )
    secili_ilce = st.session_state.get(state_key)
    cols = st.columns(4)
    for idx, (aks, ilceler) in enumerate(IZMIR_AKS_MAP.items()):
        with cols[idx % 4]:
            with st.container(border=True):
                renk = AKS_RENK[aks]
                st.markdown(
                    f'<div style="font-size:13px;font-weight:800;color:{renk["text"]};'
                    f'margin-bottom:6px;">{aks}</div>',
                    unsafe_allow_html=True,
                )
                for ilce in ilceler:
                    toplam, yeni = ilce_kayit_sayisi(kayitlar, ilce)
                    if toplam == 0:
                        continue
                    aktif = secili_ilce == ilce
                    yeni_str = f" · 🟢{yeni}" if yeni > 0 else ""
                    _lbl = f"{'▸ ' if aktif else ''}{ilce}  {toplam}{yeni_str}"
                    _kk = f"{key_prefix}_aks_{safe_key(ilce)}"
                    if st.button(_lbl, key=_kk, use_container_width=True,
                                 type="primary" if aktif else "secondary"):
                        st.session_state[state_key] = None if aktif else ilce
                        st.rerun()


# ── Supabase ortak ────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def ilce_listesi_cek():
    try:
        r = get_client().table("ilceler").select("ilce").execute()
        return sorted([x["ilce"] for x in r.data if x.get("ilce")])
    except:
        return []


@st.cache_data(ttl=60)
def favori_ilceleri_cek():
    try:
        r = (
            get_client().table("kullanici_tercihleri")
            .select("favori_ilceler").eq("kullanici_ad", "varsayilan").execute()
        )
        if r.data:
            return r.data[0].get("favori_ilceler") or []
        return []
    except:
        return []


def favori_ilce_guncelle(ilceler):
    try:
        get_client().table("kullanici_tercihleri") \
            .update({"favori_ilceler": ilceler}) \
            .eq("kullanici_ad", "varsayilan").execute()
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Hata: {e}")


# ════════════════════════════════════════════════════════════════════════════
# SAYFA BAŞLIĞI
# ════════════════════════════════════════════════════════════════════════════

_hdr1, _hdr2 = st.columns([1, 0.06])
with _hdr1:
    render_page_header(
        "📦 Arşiv Merkezi",
        "60 günden eski kayıtlar · Talep ve Portföy arşivi"
    )
with _hdr2:
    st.markdown("<div style='margin-top:14px'>", unsafe_allow_html=True)
    if st.button("↺", key="arsiv_yenile", help="Yenile", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# ANA SEKMELER
# ════════════════════════════════════════════════════════════════════════════

tab_talep, tab_portfoy = st.tabs(["📋 Talep Arşivi", "🏠 Portföy Arşivi"])


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  TALEP ARŞİVİ                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

with tab_talep:

    # ── Veri çekme ──────────────────────────────────────────────────────────

    @st.cache_data(ttl=30)
    def talep_verileri_yukle(kaynak_filtre=None):
        """ARŞİV MODU: 60 günden eski talep kayıtları."""
        ESIK = 60
        try:
            q = (
                get_client().table("alici_talepleri")
                .select("*").eq("kategori", "alici_talebi")
                .order("olusturma_tarihi", desc=True).limit(2000)
            )
            if kaynak_filtre:
                if kaynak_filtre == "startkey_mail":
                    r1 = q.eq("kaynak", "startkey_mail").execute()
                    r2 = q.is_("kaynak", "null").execute()
                    tum = (r1.data or []) + (r2.data or [])
                elif isinstance(kaynak_filtre, list):
                    tum = q.in_("kaynak", kaynak_filtre).execute().data or []
                else:
                    tum = q.eq("kaynak", kaynak_filtre).execute().data or []
            else:
                tum = q.execute().data or []
            return [v for v in tum if tarih_gun_farki(en_iyi_tarih(v)) > ESIK]
        except Exception as e:
            st.error(f"Talep verisi yüklenemedi: {e}")
            return []

    @st.cache_data(ttl=3600)
    def talep_gd_listesi_cek():
        try:
            r = get_client().table("alici_talepleri").select("talep_eden_danisan").execute()
            isimler = sorted(set(
                isim_ayikla(v.get("talep_eden_danisan", ""))
                for v in r.data if v.get("talep_eden_danisan", "")
            ))
            return [i for i in isimler if i]
        except:
            return []

    def talep_favori_kaydi_mi(v, fav_ilceler):
        return any(i in fav_ilceler for i in (v.get("ilceler") or []))

    def talep_favori_guncelle(kid, mevcut):
        try:
            get_client().table("alici_talepleri") \
                .update({"favori": not mevcut}).eq("id", kid).execute()
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Hata: {e}")

    def talep_kayit_guncelle(kid, data):
        try:
            get_client().table("alici_talepleri").update(data).eq("id", kid).execute()
            st.session_state.pop(f"ta_duzen_{kid}", None)
            st.session_state[f"ta_guncellendi_{kid}"] = True
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Hata: {e}")

    def talep_not_kaydet(kid, metin):
        try:
            get_client().table("alici_talepleri") \
                .update({"not_alani": metin}).eq("id", kid).execute()
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Hata: {e}")

    def talep_kayit_gizle(kid):
        try:
            get_client().table("alici_talepleri") \
                .update({"gizli": True}).eq("id", kid).execute()
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Hata: {e}")

    def talep_kayit_sil(kid):
        try:
            get_client().table("alici_talepleri").delete().eq("id", kid).execute()
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Silme hatası: {e}")

    def talep_belirtilmemise_tasi(kid):
        try:
            get_client().table("alici_talepleri").update(
                {"il": "", "ilce": "", "ilceler": [], "mahalle": "", "bolge": ""}
            ).eq("id", kid).execute()
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Hata: {e}")

    def talep_siralama_uygula(liste, siralama):
        if siralama == "Tarih ↓":   return sorted(liste, key=lambda v: tarih_gun_farki(en_iyi_tarih(v)))
        elif siralama == "Tarih ↑": return sorted(liste, key=lambda v: tarih_gun_farki(en_iyi_tarih(v)), reverse=True)
        elif siralama == "İlçe A→Z": return sorted(liste, key=lambda v: (ilce_grubu(v) or "").lower())
        elif siralama == "İlçe Z→A": return sorted(liste, key=lambda v: (ilce_grubu(v) or "").lower(), reverse=True)
        elif siralama == "Bütçe ↑":  return sorted(liste, key=lambda v: fiyat_sayisal(v.get("max_butce", "")))
        elif siralama == "Bütçe ↓":  return sorted(liste, key=lambda v: fiyat_sayisal(v.get("max_butce", "")), reverse=True)
        return liste

    def build_talep_ui_model(v):
        islem = (v.get("islem_tipi") or "").strip()
        mulk  = (v.get("mulk_tipi") or "").strip()
        oda   = (v.get("oda_sayisi_m2") or "").strip()
        butce = (v.get("max_butce") or "").strip()
        ozel  = (v.get("ozel_kriterler") or "").strip()
        ozet_ham = (v.get("ozet") or v.get("mail_konusu") or "").strip()
        mahalle  = (v.get("mahalle") or "").strip()
        bolge    = (v.get("bolge") or v.get("bolge_mahalle") or "").strip()
        ilceler  = [i for i in (v.get("ilceler") or []) if i and i != "Diğer Bölge"]

        islem_ok = islem not in ("", "Belirsiz", "Belirtilmemiş")
        mulk_ok  = mulk  not in ("", "Belirsiz", "Belirtilmemiş")
        oda_ok   = bool(oda)

        if islem_ok or mulk_ok or oda_ok:
            parts = []
            if islem_ok: parts.append(islem)
            if oda_ok:   parts.append(oda)
            if mulk_ok:  parts.append(mulk)
            suffix = "Arayışı" if islem_ok else "Talebi"
            baslik = " ".join(parts) + " " + suffix
        else:
            baslik = ozet_ham[:60] if ozet_ham else "Gayrimenkul Talebi"

        lokasyon_ozet = " · ".join(ilceler[:3]) if ilceler else ""

        kriter_parts = []
        if mahalle: kriter_parts.append(mahalle)
        if bolge and bolge != mahalle: kriter_parts.append(bolge)
        if ozel: kriter_parts.append(ozel[:100])
        elif ozet_ham and ozet_ham != baslik and not kriter_parts:
            kriter_parts.append(ozet_ham[:100])
        kriter_ozet = " · ".join(kriter_parts)

        return {
            "baslik":        baslik,
            "lokasyon_ozet": lokasyon_ozet,
            "kriter_ozet":   kriter_ozet,
            "meta":          isim_ayikla(v.get("talep_eden_danisan", "")),
        }

    def talep_filtre_temizle():
        for k in ["ta_ft_ara","ta_ft_il","ta_ft_ilce","ta_ft_danisan","ta_ft_mulk",
                  "ta_ft_islem","ta_ft_siralama","ta_ft_hizli","ta_ft_aralik","ta_ft_fav",
                  "ta_ft_gizli","ta_fav_secili_ilce","ta_ft_butce_alt","ta_ft_butce_ust",
                  "ta_ft_oda","ta_ft_bina_yasi","ta_ft_kat","ta_ft_site_ici",
                  "ta_ft_esyali","ta_ft_kullanim","ta_ft_gun_min","ta_ft_gun_max",
                  "ta_show_filters"]:
            st.session_state.pop(k, None)
        st.rerun()

    # ── Talep Detay Modal ────────────────────────────────────────────────────

    @st.dialog("Talep Detayı", width="large")
    def talep_detay_modal(v, ilce_sec):
        kid = v.get("id")
        isim = isim_ayikla(v.get("talep_eden_danisan", ""))
        ilceler_list = v.get("ilceler") or []
        butce = v.get("max_butce", "")
        oda   = v.get("oda_sayisi_m2", "")
        mulk  = v.get("mulk_tipi", "")
        islem = v.get("islem_tipi", "")
        mahalle = v.get("mahalle", "") or ""
        bolge   = v.get("bolge", "") or v.get("bolge_mahalle", "") or ""
        favori  = v.get("favori", False)
        gizli   = v.get("gizli", False)
        gun_farki = tarih_gun_farki(en_iyi_tarih(v))
        ui = build_talep_ui_model(v)

        st.markdown(
            f'<div style="background:#FFF9ED;border-left:4px solid #F4B740;padding:10px 14px;'
            f'border-radius:0 8px 8px 0;margin-bottom:12px;">'
            f'<div style="font-size:1.15rem;font-weight:800;color:#172B4D;">{ui["baslik"]}</div>'
            + (f'<div style="font-size:0.83rem;color:#355C7D;font-weight:600;margin-top:4px;">📍 {ui["lokasyon_ozet"]}</div>' if ui["lokasyon_ozet"] else "")
            + f'</div>',
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:2px;">Danışman</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:13px;font-weight:600;color:#172B4D;">{isim or "—"}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:2px;">Bütçe</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:13px;font-weight:700;color:#172B4D;">{"💰 "+butce if butce else "—"}</div>', unsafe_allow_html=True)
        with c3:
            st.markdown('<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:2px;">Oda / M²</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:13px;font-weight:600;color:#172B4D;">{"🏠 "+oda if oda else "—"}</div>', unsafe_allow_html=True)

        st.markdown(etiket_html(mulk) + etiket_html(islem), unsafe_allow_html=True)
        st.divider()

        if ilceler_list or mahalle or bolge:
            st.markdown('<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:4px;">İlçeler</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:13px;color:#374151;margin-bottom:8px;">{", ".join(ilceler_list) if ilceler_list else "—"}</div>', unsafe_allow_html=True)
            r2a, r2b = st.columns(2)
            with r2a:
                st.markdown('<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:2px;">Mahalle</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:13px;color:#374151;">{mahalle or "—"}</div>', unsafe_allow_html=True)
            with r2b:
                st.markdown('<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:2px;">Bölge</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:13px;color:#374151;">{bolge or "—"}</div>', unsafe_allow_html=True)

        if v.get("ozel_kriterler"):
            st.markdown(
                f'<div style="background:#FFF9ED;border-left:3px solid #F4B740;padding:8px 12px;'
                f'border-radius:4px;font-size:12px;color:#475569;margin-top:8px;">'
                f'<b>Özel Kriterler:</b> {v.get("ozel_kriterler","")}</div>',
                unsafe_allow_html=True,
            )

        ic = html_temizle(v.get("mail_icerigi", ""))
        if ic:
            st.markdown(f'<div style="font-size:11px;color:#64748b;font-weight:700;margin-top:10px;margin-bottom:3px;">📧 {v.get("mail_konusu","")}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div style="background:#f0f4ff;border-left:3px solid #2d7dd2;padding:8px 12px;'
                f'border-radius:6px;font-size:11px;line-height:1.6;max-height:200px;overflow-y:auto;color:#374151;">{ic[:1500]}</div>',
                unsafe_allow_html=True,
            )

        st.divider()
        not_m = v.get("not_alani", "") or ""
        yn = st.text_area("Not", value=not_m, height=80, placeholder="Not ekle...",
                          key=f"ta_modal_not_{kid}", label_visibility="collapsed")
        nb1, nb2 = st.columns([1, 3])
        with nb1:
            if st.button("💾 Notu Kaydet", key=f"ta_modal_nb_{kid}", type="primary", use_container_width=True):
                talep_not_kaydet(kid, yn)

        st.divider()
        ma1, ma2, ma3 = st.columns(3)
        with ma1:
            fav_label = "★ Favoriden Çıkar" if favori else "☆ Favoriye Ekle"
            if st.button(fav_label, key=f"ta_modal_fav_{kid}", use_container_width=True):
                talep_favori_guncelle(kid, favori)
        with ma2:
            if v.get("il", "") or v.get("ilce", ""):
                if st.button("📦 Belirtilmemişe Taşı", key=f"ta_modal_blt_{kid}", use_container_width=True):
                    talep_belirtilmemise_tasi(kid)
        with ma3:
            giz_label = "👁 Göster" if gizli else "⊘ Gizle"
            if st.button(giz_label, key=f"ta_modal_giz_{kid}", use_container_width=True):
                get_client().table("alici_talepleri") \
                    .update({"gizli": not gizli}).eq("id", kid).execute()
                st.cache_data.clear()
                st.rerun()

    # ── Hibrit Kart Fonksiyonları ─────────────────────────────────────────────

    def arsiv_talep_kart_html(v, rozet_html=""):
        """Arşiv talep hibrit kartı — geniş, 2 sütunlu."""
        ui_k  = build_talep_ui_model(v)
        isim  = isim_ayikla(v.get("talep_eden_danisan", ""))
        butce = v.get("max_butce", "")
        mulk  = v.get("mulk_tipi", "") or ""
        islem = v.get("islem_tipi", "") or ""
        ilceler_list = v.get("ilceler") or []
        _aks_k = aks_renk_bul(ilceler_list)
        _td = tarih_parse(en_iyi_tarih(v))
        if _td:
            _hast = hasattr(_td, "hour") and (_td.hour != 0 or _td.minute != 0)
            _tarih_k = _td.strftime("%d.%m.%Y %H:%M") if _hast else _td.strftime("%d.%m.%Y")
        else:
            _tarih_k = ""
        if "iralık" in islem:   _ibg, _ic, _ilbl = "#f0fdf4", "#166534", "Kiralık"
        elif "atılık" in islem: _ibg, _ic, _ilbl = "#fef2f2", "#991b1b", "Satılık"
        else:                   _ibg, _ic, _ilbl = "#f8fafc", "#64748b", islem or ""
        _kaynak_raw = (v.get("kaynak") or "").lower()
        if _kaynak_raw in ("startkey_mail", ""):
            _k_lbl, _k_c, _k_bg = "Startkey", "#355C7D", "#EEF4FA"
        elif _kaynak_raw in ("zeta1", "zeta2", "ofis", "zeta"):
            _k_lbl, _k_c, _k_bg = "Zeta", "#0F6E56", "#E1F5EE"
        else:
            _k_lbl, _k_c, _k_bg = "Diğer", "#475569", "#f1f5f9"
        _lokasyon = ui_k.get("lokasyon_ozet") or ""
        _kriter   = ui_k.get("kriter_ozet") or ""
        _baslik   = ui_k.get("baslik") or "Gayrimenkul Talebi"
        _initials = "".join(w[0].upper() for w in isim.split()[:2]) if isim else "?"
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
               f'{_kriter}</div>' if _kriter else '<div style="margin-bottom:8px;"></div>')
            + (f'<div style="font-size:20px;font-weight:800;color:#0F172A;letter-spacing:-0.5px;'
               f'margin-bottom:14px;">{butce}</div>'
               if butce else
               '<div style="font-size:14px;color:#94a3b8;font-style:italic;margin-bottom:14px;">—</div>')
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

    def arsiv_portfoy_kart_html(v, rozet_html=""):
        """Arşiv portföy hibrit kartı — geniş, 2 sütunlu."""
        isim  = isim_ayikla(v.get("talep_eden_danisan", ""))
        fiyat = v.get("fiyat", "")
        oda   = v.get("oda_sayisi_m2", "") or ""
        islem = v.get("islem_tipi", "") or ""
        mulk  = v.get("mulk_tipi", "") or ""
        ilan  = v.get("ilan_linki", "")
        ozet  = v.get("ozet", "") or v.get("mail_konusu", "") or ""
        ilceler_list = v.get("ilceler") or []
        mahalle = v.get("mahalle", "") or ""
        _aks_k = aks_renk_bul(ilceler_list)
        _td = tarih_parse(en_iyi_tarih(v))
        if _td:
            _hast = hasattr(_td, "hour") and (_td.hour != 0 or _td.minute != 0)
            _tarih_k = _td.strftime("%d.%m.%Y %H:%M") if _hast else _td.strftime("%d.%m.%Y")
        else:
            _tarih_k = ""
        lok_parts = ilceler_list[:3] if ilceler_list else ([mahalle] if mahalle else [])
        _lokasyon = " · ".join(lok_parts)
        if "iralık" in islem:   _ibg, _ic, _ilbl = "#f0fdf4", "#166534", "Kiralık"
        elif "atılık" in islem: _ibg, _ic, _ilbl = "#fef2f2", "#991b1b", "Satılık"
        else:                   _ibg, _ic, _ilbl = "#f8fafc", "#64748b", islem or ""
        _b_parts = []
        if islem and islem not in ("Belirsiz", "Belirtilmemiş"): _b_parts.append(islem)
        if oda:  _b_parts.append(oda)
        if mulk and mulk not in ("Belirsiz", "Belirtilmemiş"):   _b_parts.append(mulk)
        _b_parts.append("İlanı" if islem and islem not in ("Belirsiz", "") else "Portföyü")
        _baslik = " ".join(_b_parts)
        _kaynak_raw = (v.get("kaynak") or "").lower()
        if _kaynak_raw in ("startkey_mail", ""):
            _k_lbl, _k_c, _k_bg = "Startkey", "#355C7D", "#EEF4FA"
        elif _kaynak_raw in ("zeta1", "zeta2", "ofis", "zeta"):
            _k_lbl, _k_c, _k_bg = "Zeta", "#0F6E56", "#E1F5EE"
        else:
            _k_lbl, _k_c, _k_bg = "Diğer", "#475569", "#f1f5f9"
        _initials = "".join(w[0].upper() for w in isim.split()[:2]) if isim else "?"
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

    # ── Talep Kart ──────────────────────────────────────────────────────────

    def talep_kayit_karti(v, ilce_sec):
        kid = v.get("id")
        isim = isim_ayikla(v.get("talep_eden_danisan", ""))
        butce = v.get("max_butce", "")
        oda   = v.get("oda_sayisi_m2", "")
        islem = v.get("islem_tipi", "")
        mulk  = v.get("mulk_tipi", "")
        favori = v.get("favori", False)
        ilceler_list = v.get("ilceler") or []
        gun_farki = tarih_gun_farki(en_iyi_tarih(v))
        yeni_kayit = gun_farki <= 7
        duzen_modu = st.session_state.get(f"ta_duzen_{kid}", False)
        gizli = v.get("gizli", False)
        okundu = kid in st.session_state.get("ta_goruldu_ids", set())

        if st.session_state.pop(f"ta_guncellendi_{kid}", False):
            st.toast("Güncellendi!")

        ui = build_talep_ui_model(v)
        etiketler = etiket_html(mulk) + etiket_html(islem)
        if yeni_kayit:
            etiketler += (
                '<span style="background:#fffbeb;color:#92400e;border:1px solid #fde68a;'
                'padding:2px 8px;border-radius:999px;font-size:10.5px;font-weight:650;'
                'margin-right:4px;display:inline-block;">yeni</span>'
            )

        tarih_d = tarih_parse(en_iyi_tarih(v))
        if tarih_d:
            _has_time = hasattr(tarih_d, 'hour') and (tarih_d.hour != 0 or tarih_d.minute != 0)
            tarih_g = tarih_d.strftime("%d.%m.%Y %H:%M") if _has_time else tarih_d.strftime("%d.%m.%Y")
        else:
            tarih_g = ""

        _fg, _bg, _dot = tarih_renk_bilgisi(gun_farki)
        tarih_html = (
            f'<span style="display:inline-flex;align-items:center;gap:4px;">'
            f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:{_dot};flex-shrink:0;"></span>'
            f'<span style="color:{_fg};font-weight:600;font-size:11px;">{tarih_g}</span>'
            f'</span>' if tarih_g else ""
        )

        _ta_kaynak_raw = (v.get("kaynak") or "").lower()
        if _ta_kaynak_raw in ("startkey_mail", ""):
            _ta_k_lbl, _ta_k_c, _ta_k_bg = "Startkey", "#355C7D", "#EEF4FA"
        elif _ta_kaynak_raw in ("zeta1", "zeta2", "ofis", "zeta"):
            _ta_k_lbl, _ta_k_c, _ta_k_bg = "Zeta", "#0F6E56", "#E1F5EE"
        else:
            _ta_k_lbl, _ta_k_c, _ta_k_bg = "Diğer", "#475569", "#f1f5f9"
        _ta_kaynak_chip = (f'<span style="background:{_ta_k_bg};color:{_ta_k_c};font-size:9.5px;font-weight:600;'
                           f'padding:1px 6px;border-radius:4px;">{_ta_k_lbl}</span>')

        aks_renk = aks_renk_bul(ilceler_list)
        if okundu:       left_border = "#cbd5e1"
        elif yeni_kayit: left_border = "#16a34a"
        elif favori:     left_border = "#f59e0b"
        else:            left_border = "#e2e8f0"

        if okundu:
            _rozet_html = '<span style="position:absolute;top:8px;right:8px;background:#e2e8f0;color:#94a3b8;font-size:10px;font-weight:700;padding:2px 8px;border-radius:999px;">✓ Görüldü</span>'
        elif yeni_kayit:
            _rozet_html = '<span style="position:absolute;top:8px;right:8px;background:#16a34a;color:#fff;font-size:10px;font-weight:750;padding:2px 8px;border-radius:999px;">YENİ</span>'
        else:
            _rozet_html = ""

        lokasyon_str = ui["lokasyon_ozet"]
        ilan_baslik  = ui["baslik"]
        kriter_ozet_str = ui.get("kriter_ozet", "")

        st.markdown(
            f'<div class="kart-wrapper" style="border-left:3px solid {left_border};background:#ffffff;'
            f'border-radius:0 10px 10px 0;padding:12px 14px 10px;margin-bottom:4px;position:relative;">'
            f'{_rozet_html}'
            + (f'<span class="kart-lokasyon" style="color:{aks_renk["text"]};">{lokasyon_str}</span>' if lokasyon_str else "")
            + f'<div style="background:#FFF9ED;border-left:3px solid #F4B740;'
            f'padding:5px 10px;border-radius:0 6px 6px 0;margin-bottom:6px;">'
            f'<div style="font-size:1.0rem;font-weight:800;color:#172B4D;line-height:1.25;">{ilan_baslik}</div>'
            f'</div>'
            + (f'<div class="kart-kriter">{kriter_ozet_str}</div>' if kriter_ozet_str else "")
            + f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:6px;">'
            f'<span style="font-size:0.91rem;font-weight:750;color:#172B4D;">{str(butce) if butce else "—"}</span>'
            + (f'<span style="font-size:0.82rem;font-weight:600;color:#475569;">{oda}</span>' if oda else "")
            + f'<span style="font-size:11px;font-weight:600;color:#94a3b8;margin-left:2px;">{isim}</span>'
            f'{etiketler}'
            + _ta_kaynak_chip
            + (f'<span style="margin-left:auto;">{tarih_html}</span>' if tarih_html else "")
            + f'</div></div>',
            unsafe_allow_html=True,
        )

        a_detay, a_sunum, a_fav, a_duz, a_giz, _ = st.columns([1.4, 1.5, 0.65, 0.65, 0.65, 5.15])
        with a_detay:
            if st.button("Detay", key=f"ta_detay_{kid}", type="primary", use_container_width=True):
                st.session_state.setdefault("ta_goruldu_ids", set()).add(kid)
                talep_detay_modal(v, ilce_sec)
        with a_sunum:
            _t_takip = st.session_state.get(f"ta_takip_t_{kid}", False)
            if st.button("⭐ Takipte" if _t_takip else "☆ Takibe Al",
                         key=f"ta_t_takip_{kid}", use_container_width=True):
                _tl = st.session_state.setdefault("takip_listesi", {})
                if _t_takip:
                    _tl.pop(str(kid), None)
                    st.session_state[f"ta_takip_t_{kid}"] = False
                    st.toast("Takipten çıkarıldı.")
                else:
                    _tl[str(kid)] = dict(v)
                    _tl[str(kid)]["_takip_kaynak"] = "talep_arsivi"
                    st.session_state[f"ta_takip_t_{kid}"] = True
                    st.toast("✅ Takip listesine eklendi!")
                st.rerun()
        with a_fav:
            if st.button("★" if favori else "☆", key=f"ta_fav_{kid}", use_container_width=True):
                talep_favori_guncelle(kid, favori)
        with a_duz:
            if st.button("✏", key=f"ta_dz_{kid}", use_container_width=True):
                st.session_state[f"ta_duzen_{kid}"] = not duzen_modu
                st.rerun()
        with a_giz:
            if st.button("👁" if gizli else "⊘", key=f"ta_giz_{kid}", use_container_width=True):
                get_client().table("alici_talepleri") \
                    .update({"gizli": not gizli}).eq("id", kid).execute()
                st.cache_data.clear()
                st.rerun()

        if v.get("kaynak", "") and v.get("kaynak", "") != "startkey_mail":
            sil_key = f"ta_sil_onay_{kid}"
            if not st.session_state.get(sil_key):
                if st.button("🗑", key=f"ta_sil_{kid}", help="Kaydı sil"):
                    st.session_state[sil_key] = True
                    st.rerun()
            else:
                st.warning("Bu kaydı silmek istediğinizden emin misiniz?")
                sc1, sc2 = st.columns([1, 1])
                with sc1:
                    if st.button("🗑 Evet, Sil", key=f"ta_sil_evet_{kid}", type="primary"):
                        talep_kayit_sil(kid)
                with sc2:
                    if st.button("İptal", key=f"ta_sil_iptal_{kid}"):
                        st.session_state.pop(sil_key, None)
                        st.rerun()

        if duzen_modu:
            _talep_duzenleme_formu(v, ilce_sec)

        st.markdown("<div style='height:1px'></div>", unsafe_allow_html=True)

    def _talep_duzenleme_formu(v, ilce_sec):
        kid = v.get("id")
        iller = ["İzmir", "Aydın", "Manisa", "Balıkesir", "Muğla", "Diğer"]
        ilce_sec_wg = ["İzmir Genel"] + ilce_sec
        c1, c2, c3 = st.columns(3)
        with c1:
            oz = st.text_input("Özet", value=v.get("ozet", "") or "", key=f"ta_d_oz_{kid}")
            yi = st.selectbox("İl", iller,
                index=iller.index(v.get("il","")) if v.get("il","") in iller else 0,
                key=f"ta_d_il_{kid}")
            mevcut_ilce = v.get("ilce","") or ""
            ilce_idx = ilce_sec_wg.index(mevcut_ilce) if mevcut_ilce in ilce_sec_wg else 0
            yilce_sec = st.selectbox("Birincil İlçe", ilce_sec_wg, index=ilce_idx, key=f"ta_d_ilce_{kid}")
            yilce = "" if yilce_sec == "İzmir Genel" else yilce_sec
        with c2:
            ym = st.selectbox("Mülk", ["Konut","İşyeri","Arsa","Belirsiz"],
                index=["Konut","İşyeri","Arsa","Belirsiz"].index(v.get("mulk_tipi","Belirsiz"))
                if v.get("mulk_tipi","") in ["Konut","İşyeri","Arsa","Belirsiz"] else 3,
                key=f"ta_d_m_{kid}")
            yis = st.selectbox("İşlem", ["Satılık","Kiralık","Belirsiz"],
                index=["Satılık","Kiralık","Belirsiz"].index(v.get("islem_tipi","Belirsiz"))
                if v.get("islem_tipi","") in ["Satılık","Kiralık","Belirsiz"] else 2,
                key=f"ta_d_is_{kid}")
            ymh = st.text_input("Mahalle", value=v.get("mahalle","") or "", key=f"ta_d_mh_{kid}")
        with c3:
            yb = st.text_input("Bölge/Konum",
                value=v.get("bolge","") or v.get("bolge_mahalle","") or "",
                key=f"ta_d_b_{kid}")
            mevcut = v.get("ilceler") or []
            yilceler = st.multiselect("Tüm İlçeler", ilce_sec,
                default=[i for i in mevcut if i in ilce_sec], key=f"ta_d_ilceler_{kid}")
        ca, cb = st.columns([1, 4])
        with ca:
            if st.button("💾 Kaydet", key=f"ta_d_kyd_{kid}", type="primary"):
                talep_kayit_guncelle(kid, {
                    "ozet":oz,"il":yi,"ilce":yilce,
                    "ilceler":yilceler if yilceler else ([yilce] if yilce else []),
                    "mulk_tipi":ym,"islem_tipi":yis,"mahalle":ymh,"bolge":yb,
                    "bolge_mahalle":f"{ymh} {yb}".strip()
                })
        with cb:
            if st.button("İptal", key=f"ta_d_ipt_{kid}"):
                st.session_state.pop(f"ta_duzen_{kid}", None)
                st.rerun()

    def talep_tablo_goster(kayitlar, prefix="ta_tbl"):
        if not kayitlar:
            st.info("Gösterilecek kayıt yok.")
            return

        st.markdown(
            '<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;font-size:10px;color:#94a3b8;">'
            '<span style="display:flex;align-items:center;gap:4px;"><span style="width:7px;height:7px;border-radius:50%;background:#16a34a;display:inline-block;"></span><span>≤7 gün</span></span>'
            '<span style="display:flex;align-items:center;gap:4px;"><span style="width:7px;height:7px;border-radius:50%;background:#ca8a04;display:inline-block;"></span><span>8-30 gün</span></span>'
            '<span style="display:flex;align-items:center;gap:4px;"><span style="width:7px;height:7px;border-radius:50%;background:#ea580c;display:inline-block;"></span><span>31-90 gün</span></span>'
            '<span style="display:flex;align-items:center;gap:4px;"><span style="width:7px;height:7px;border-radius:50%;background:#dc2626;display:inline-block;"></span><span>&gt;90 gün</span></span>'
            '</div>',
            unsafe_allow_html=True
        )

        COL_RATIOS = [4, 1.5, 1.2, 2, 2, 1.2, 0.9, 1, 0.5, 0.5]
        headers = ["Talep Başlığı", "İlçe", "İşlem", "Bütçe", "Danışman", "Tarih", "Kaynak", "", "", ""]
        h = st.columns(COL_RATIOS)
        for col, hdr in zip(h, headers):
            with col:
                st.markdown(
                    f'<div style="font-size:10px;font-weight:600;color:#94a3b8;'
                    f'text-transform:uppercase;letter-spacing:0.06em;'
                    f'padding:8px 0 6px;border-bottom:1px solid #e2e8f0;">{hdr}</div>',
                    unsafe_allow_html=True
                )

        ilce_sec = ilce_listesi_cek()
        for v in kayitlar:
            kid    = v.get("id","")
            isim   = isim_ayikla(v.get("talep_eden_danisan",""))
            ilce   = ilce_grubu(v) or "—"
            islem  = v.get("islem_tipi","") or ""
            butce  = v.get("max_butce","") or "—"
            favori = v.get("favori", False)
            gun_farki = tarih_gun_farki(en_iyi_tarih(v))
            okundu    = kid in st.session_state.get("ta_goruldu_ids", set())
            _fg, _bg, dot_c = tarih_renk_bilgisi(gun_farki)
            if okundu:
                dot_c = "#cbd5e1"; _fg = "#94a3b8"; _bg = "#f8fafc"

            tarih_d = tarih_parse(en_iyi_tarih(v))
            if tarih_d:
                _has_t = hasattr(tarih_d,"hour") and (tarih_d.hour != 0 or tarih_d.minute != 0)
                tarih_str = tarih_d.strftime("%d.%m %H:%M") if _has_t else tarih_d.strftime("%d.%m.%Y")
            else:
                tarih_str = "—"

            aks_r = aks_renk_bul([ilce] if ilce != "—" else [])
            ui = build_talep_ui_model(v)

            if "iralık" in islem: tip_bg, tip_color, tip_lbl = "#f0fdf4","#166534","Kiralık"
            elif "atılık" in islem: tip_bg, tip_color, tip_lbl = "#fef2f2","#991b1b","Satılık"
            else: tip_bg, tip_color, tip_lbl = "#f8fafc","#64748b", islem or "—"

            kaynak_raw = (v.get("kaynak") or "").lower()
            if kaynak_raw in ("startkey_mail", ""):
                k_lbl, k_c, k_bg = "Startkey", "#355C7D", "#EEF4FA"
            elif kaynak_raw in ("zeta1", "zeta2", "ofis", "zeta"):
                k_lbl, k_c, k_bg = "Zeta", "#0F6E56", "#E1F5EE"
            else:
                k_lbl, k_c, k_bg = "Diğer", "#475569", "#f1f5f9"

            initials = "".join(w[0].upper() for w in isim.split()[:2]) if isim else "?"
            baslik = ui.get("baslik", "")
            kriter = (ui.get("kriter_ozet","") or "")[:55]
            ROW = "border-bottom:0.5px solid #f1f5f9;padding:8px 0;"

            row = st.columns(COL_RATIOS)
            with row[0]:
                st.markdown(
                    f'<div style="{ROW}"><div style="display:flex;align-items:center;gap:6px;">'
                    f'<span style="width:6px;height:6px;border-radius:50%;background:{dot_c};flex-shrink:0;display:inline-block;"></span>'
                    f'<span style="font-size:12px;font-weight:600;color:#1e293b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:95%;display:block;">{baslik}</span>'
                    f'</div>'
                    + (f'<div style="font-size:10.5px;color:#64748b;margin-left:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{kriter}</div>' if kriter else "")
                    + f'</div>', unsafe_allow_html=True)
            with row[1]:
                st.markdown(f'<div style="{ROW}"><span style="background:{aks_r["bg"]};color:{aks_r["text"]};padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600;">{ilce}</span></div>', unsafe_allow_html=True)
            with row[2]:
                st.markdown(f'<div style="{ROW}"><span style="background:{tip_bg};color:{tip_color};padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600;">{tip_lbl}</span></div>', unsafe_allow_html=True)
            with row[3]:
                st.markdown(f'<div style="{ROW};font-size:11.5px;font-weight:600;color:#0f172a;">{butce}</div>', unsafe_allow_html=True)
            with row[4]:
                st.markdown(f'<div style="{ROW};display:flex;align-items:center;gap:5px;"><span style="font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{isim or "—"}</span></div>', unsafe_allow_html=True)
            with row[5]:
                st.markdown(f'<div style="{ROW}"><span style="background:{_bg};color:{_fg};font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:4px;white-space:nowrap;">{tarih_str}</span></div>', unsafe_allow_html=True)
            with row[6]:
                st.markdown(f'<div style="{ROW}"><span style="background:{k_bg};color:{k_c};font-size:10px;font-weight:600;padding:2px 6px;border-radius:4px;">{k_lbl}</span></div>', unsafe_allow_html=True)
            with row[7]:
                if st.button("Detay", key=f"{prefix}_detay_{kid}", use_container_width=True, type="primary"):
                    st.session_state.setdefault("ta_goruldu_ids", set()).add(kid)
                    talep_detay_modal(v, ilce_sec)
            with row[8]:
                if st.button("★" if favori else "☆", key=f"{prefix}_fav_{kid}", use_container_width=True):
                    talep_favori_guncelle(kid, favori)
            with row[9]:
                if st.button("✏", key=f"{prefix}_dz_{kid}", use_container_width=True):
                    st.session_state[f"ta_duzen_{kid}"] = not st.session_state.get(f"ta_duzen_{kid}", False)
                    st.rerun()

    # ── State init ───────────────────────────────────────────────────────────

    TA_DEFAULTS = {
        "ta_ft_ara": "", "ta_ft_il": "Tümü", "ta_ft_ilce": "Tümü",
        "ta_ft_danisan": "Tümü", "ta_ft_mulk": "Tümü", "ta_ft_islem": "Tümü",
        "ta_ft_siralama": "Tarih ↓", "ta_ft_hizli": "Son 3 ay",
        "ta_ft_aralik": False, "ta_ft_fav": False, "ta_ft_gizli": False,
        "ta_ft_butce_alt": 0, "ta_ft_butce_ust": 0, "ta_ft_oda": "Tümü",
        "ta_ft_bina_yasi": "Tümü", "ta_ft_kat": "Tümü", "ta_ft_site_ici": "Tümü",
        "ta_ft_esyali": "Tümü", "ta_ft_kullanim": "Tümü",
        "ta_ft_gun_min": 0, "ta_ft_gun_max": 0, "ta_ft_gorunum": "Tablo",
        "ta_aktif_kaynak": "startkey", "ta_fav_secili_ilce": None,
        "ta_aktif_sekme": "TümüListe", "ta_ana_sekme": "TümüListe",
        "ta_aks_secili": None, "ta_show_filters": False,
        "ta_goruldu_ids": set(),
    }
    for k, v_def in TA_DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v_def

    # ── Veri yükleme ─────────────────────────────────────────────────────────

    ta_veriler = talep_verileri_yukle(None)

    if not st.session_state.get("ta_ft_gizli", False):
        ta_veriler = [v for v in ta_veriler if not v.get("gizli", False)]

    ilce_sec = ilce_listesi_cek()
    ta_fav_ilceler = favori_ilceleri_cek()

    ta_danisman_sayisi = len(set(
        isim_ayikla(v.get("talep_eden_danisan",""))
        for v in ta_veriler if v.get("talep_eden_danisan","")
    ))

    # ── Arşiv uyarısı ───────────────────────────────────────────────────────

    st.markdown(
        '<div style="background:#FFF9ED;border-left:4px solid #F4B740;padding:8px 14px;'
        'border-radius:6px;margin-bottom:10px;font-size:12px;color:#92400e;">'
        '📦 <b>Arşiv görünümü</b> — 60 günden eski talepler. Aktif kayıtlar için '
        '<a href="/2_Talep_Tablosu" style="color:#92400e;font-weight:700;">Talep Merkezi</a>\'ni kullanın.'
        '</div>',
        unsafe_allow_html=True
    )

    _ta_hdr, _ = st.columns([1, 0.001])
    with _ta_hdr:
        st.caption(f"**{len(ta_veriler)}** kayıt · {ta_danisman_sayisi} danışman")

    if not ta_veriler:
        st.info("Arşivde talep bulunamadı.")
        st.stop()

    # ── Hızlı filtre + filtreler butonu ─────────────────────────────────────

    ta_allowed_hizli = ["Tümü","Son 3 ay","Son 6 ay","Son 1 yıl"]
    if st.session_state.get("ta_ft_hizli") not in ta_allowed_hizli:
        st.session_state["ta_ft_hizli"] = "Son 3 ay"

    ta_hizli_sayilar = {
        "Son 3 ay":  sum(1 for v in ta_veriler if tarih_gun_farki(en_iyi_tarih(v)) <= 90),
        "Son 6 ay":  sum(1 for v in ta_veriler if tarih_gun_farki(en_iyi_tarih(v)) <= 180),
        "Son 1 yıl": sum(1 for v in ta_veriler if tarih_gun_farki(en_iyi_tarih(v)) <= 365),
        "Tümü":      len(ta_veriler),
    }
    ta_hizli_map = [
        ("Son 3 ay",  f"3 Ay · {ta_hizli_sayilar['Son 3 ay']}"),
        ("Son 6 ay",  f"6 Ay · {ta_hizli_sayilar['Son 6 ay']}"),
        ("Son 1 yıl", f"1 Yıl · {ta_hizli_sayilar['Son 1 yıl']}"),
        ("Tümü",      f"Tümü · {ta_hizli_sayilar['Tümü']}"),
    ]

    ta_aktif_filtre_sayisi = sum([
        st.session_state.get("ta_ft_il","Tümü") != "Tümü",
        st.session_state.get("ta_ft_ilce","Tümü") != "Tümü",
        st.session_state.get("ta_ft_danisan","Tümü") != "Tümü",
        st.session_state.get("ta_ft_mulk","Tümü") != "Tümü",
        st.session_state.get("ta_ft_islem","Tümü") != "Tümü",
        bool(st.session_state.get("ta_ft_ara","").strip()),
        st.session_state.get("ta_ft_fav",False),
        st.session_state.get("ta_ft_butce_alt",0) > 0,
        st.session_state.get("ta_ft_butce_ust",0) > 0,
    ])
    ta_filtre_btn = f"⚙ Filtreler {ta_aktif_filtre_sayisi}" if ta_aktif_filtre_sayisi else "⚙ Filtreler"

    tb1, tb2, tb3, tb4, tb5 = st.columns([1,1,1,1.3,0.9])
    for col, (deger, label) in zip([tb1,tb2,tb3,tb4], ta_hizli_map):
        with col:
            aktif = st.session_state.get("ta_ft_hizli") == deger
            if st.button(label, key=f"ta_hizli_{safe_key(deger)}", use_container_width=True,
                         type="primary" if aktif else "secondary"):
                st.session_state["ta_ft_hizli"] = deger
                st.rerun()
    with tb5:
        if st.button(ta_filtre_btn, key="ta_toggle_filters", use_container_width=True,
                     type="primary" if st.session_state.get("ta_show_filters") else "secondary"):
            st.session_state["ta_show_filters"] = not st.session_state.get("ta_show_filters",False)
            st.rerun()

    # ── Filtre paneli ────────────────────────────────────────────────────────

    if st.session_state.get("ta_show_filters", False):
        with st.container(border=True):
            tum_iller = sorted(set(il_grubu(v) for v in ta_veriler if il_grubu(v)))
            tum_ilceler = sorted(set(
                ilce for v in ta_veriler
                for ilce in (v.get("ilceler") or [])
                if ilce and ilce != "Diğer Bölge"
            ))
            danismanlar = sorted(set(
                isim_ayikla(v.get("talep_eden_danisan",""))
                for v in ta_veriler if v.get("talep_eden_danisan","")
            ))
            if st.session_state.get("ta_ft_il") not in (["Tümü"]+tum_iller+["Belirtilmemiş"]):
                st.session_state["ta_ft_il"] = "Tümü"
            if st.session_state.get("ta_ft_ilce") not in (["Tümü"]+tum_ilceler):
                st.session_state["ta_ft_ilce"] = "Tümü"
            if st.session_state.get("ta_ft_danisan") not in (["Tümü"]+danismanlar):
                st.session_state["ta_ft_danisan"] = "Tümü"

            f1,f2,f3,f4,f5 = st.columns([1.1,1.1,1.7,1.1,1.1])
            with f1: st.selectbox("İl", ["Tümü"]+tum_iller+["Belirtilmemiş"], key="ta_ft_il")
            with f2: st.selectbox("İlçe", ["Tümü"]+tum_ilceler, key="ta_ft_ilce")
            with f3: st.selectbox("Danışman", ["Tümü"]+danismanlar, key="ta_ft_danisan")
            with f4: st.selectbox("Mülk", ["Tümü","Konut","İşyeri","Arsa","Belirtilmemiş"], key="ta_ft_mulk")
            with f5: st.selectbox("İşlem", ["Tümü","Satılık","Kiralık","Belirtilmemiş"], key="ta_ft_islem")

            g1,g2,g3,g4,g5 = st.columns([1.2,1.2,1.8,1.2,1.4])
            with g1:
                st.caption("Bütçe Alt (TL)")
                st.number_input("", min_value=0, step=100000, key="ta_ft_butce_alt", label_visibility="collapsed")
            with g2:
                st.caption("Bütçe Üst (TL)")
                st.number_input("", min_value=0, step=100000, key="ta_ft_butce_ust", label_visibility="collapsed")
            with g3: st.text_input("Arama", placeholder="Başlık, ilçe, kriter...", key="ta_ft_ara")
            with g4: st.selectbox("Sıralama", ["Tarih ↓","Tarih ↑","İlçe A→Z","İlçe Z→A","Bütçe ↑","Bütçe ↓"], key="ta_ft_siralama")
            with g5:
                st.write("")
                st.button("Temizle", key="ta_filtre_temizle", use_container_width=True, on_click=talep_filtre_temizle)

            e1,e2,_ = st.columns([1,1,6])
            with e1: st.checkbox("Favori", key="ta_ft_fav")
            with e2: st.checkbox("Gizli", key="ta_ft_gizli")

    # ── Filtreleme ────────────────────────────────────────────────────────────

    ta_il_f     = st.session_state.get("ta_ft_il","Tümü")
    ta_ilce_f   = st.session_state.get("ta_ft_ilce","Tümü")
    ta_dan_f    = st.session_state.get("ta_ft_danisan","Tümü")
    ta_mulk_f   = st.session_state.get("ta_ft_mulk","Tümü")
    ta_islem_f  = st.session_state.get("ta_ft_islem","Tümü")
    ta_ara      = st.session_state.get("ta_ft_ara","")
    ta_siralama = st.session_state.get("ta_ft_siralama","Tarih ↓")
    ta_hizli    = st.session_state.get("ta_ft_hizli","Son 3 ay")
    ta_fav_f    = st.session_state.get("ta_ft_fav",False)
    ta_butce_alt = st.session_state.get("ta_ft_butce_alt",0)
    ta_butce_ust = st.session_state.get("ta_ft_butce_ust",0)
    ta_gorunum  = st.session_state.get("ta_ft_gorunum","Tablo")
    if ta_gorunum not in ["Kart","Tablo"]:
        ta_gorunum = "Tablo"

    ta_f = ta_veriler
    if ta_ara:
        ta_f = [v for v in ta_f if any(ta_ara.lower() in str(v.get(k,"")).lower()
                for k in ["talep_eden_danisan","bolge_mahalle","mahalle","bolge","ilce","ozet","ozel_kriterler","ilceler"])]
    if ta_il_f == "Belirtilmemiş": ta_f = [v for v in ta_f if not il_grubu(v)]
    elif ta_il_f != "Tümü": ta_f = [v for v in ta_f if il_grubu(v) == ta_il_f]
    if ta_ilce_f != "Tümü": ta_f = [v for v in ta_f if ta_ilce_f in (v.get("ilceler") or [])]
    if ta_dan_f != "Tümü": ta_f = [v for v in ta_f if isim_ayikla(v.get("talep_eden_danisan","")) == ta_dan_f]
    if ta_mulk_f == "Belirtilmemiş": ta_f = [v for v in ta_f if v.get("mulk_tipi","") in ("","Belirsiz","Belirtilmemiş",None)]
    elif ta_mulk_f != "Tümü": ta_f = [v for v in ta_f if v.get("mulk_tipi","") == ta_mulk_f]
    if ta_islem_f == "Belirtilmemiş": ta_f = [v for v in ta_f if v.get("islem_tipi","") in ("","Belirsiz","Belirtilmemiş",None)]
    elif ta_islem_f != "Tümü": ta_f = [v for v in ta_f if v.get("islem_tipi","") == ta_islem_f]
    if ta_hizli != "Tümü":
        gl = {"Son 3 ay":90,"Son 6 ay":180,"Son 1 yıl":365}.get(ta_hizli)
        if gl: ta_f = [v for v in ta_f if tarih_gun_farki(en_iyi_tarih(v)) <= gl]
    if ta_butce_alt > 0: ta_f = [v for v in ta_f if fiyat_sayisal(v.get("max_butce","")) >= ta_butce_alt]
    if ta_butce_ust > 0: ta_f = [v for v in ta_f if fiyat_sayisal(v.get("max_butce","")) <= ta_butce_ust]
    if ta_fav_f: ta_f = [v for v in ta_f if v.get("favori",False)]
    ta_f = talep_siralama_uygula(ta_f, ta_siralama)

    # ── Favori chip'leri ─────────────────────────────────────────────────────

    _ta_fav_list = ta_fav_ilceler
    _ta_fav_secili = st.session_state.get("ta_fav_secili_ilce")

    _ta_qp = st.query_params
    if "ta_fav_ilce" in _ta_qp:
        _gelen = _ta_qp["ta_fav_ilce"]
        if _gelen == "__tumu__":
            st.session_state["ta_fav_secili_ilce"] = None
            st.session_state["ta_ana_sekme"] = "Favorilerim"
            del st.query_params["ta_fav_ilce"]; st.rerun()
        elif _gelen == "__ekle__":
            st.session_state["ta_show_fav_ekle"] = True
            del st.query_params["ta_fav_ilce"]; st.rerun()
        else:
            st.session_state["ta_fav_secili_ilce"] = None if _ta_fav_secili == _gelen else _gelen
            st.session_state["ta_ana_sekme"] = "Favorilerim"
            del st.query_params["ta_fav_ilce"]; st.rerun()

    _chip_html = '<div class="firsat-row">'
    if _ta_fav_list:
        _fav_toplam = sum(ilce_kayit_sayisi(ta_f, fi)[0] for fi in _ta_fav_list[:5])
        _tumu_cls = "fchip fchip-tumu active" if not _ta_fav_secili else "fchip fchip-tumu"
        _chip_html += f'<a href="?ta_fav_ilce=__tumu__" style="text-decoration:none;"><button class="{_tumu_cls}">★ Tüm Favoriler &nbsp;{_fav_toplam}</button></a>'
        for _filce in _ta_fav_list[:5]:
            _ftoplam, _fyeni = ilce_kayit_sayisi(ta_f, _filce)
            if _ftoplam == 0: continue
            _fsecili = _ta_fav_secili == _filce
            _ilce_cls = "fchip fchip-ilce active" if _fsecili else "fchip fchip-ilce"
            _yeni_html = f'<span class="fchip-yeni">{_fyeni} yeni</span>' if _fyeni > 0 else ""
            _chip_html += f'<a href="?ta_fav_ilce={_filce}" style="text-decoration:none;"><button class="{_ilce_cls}">★ {_filce} &nbsp;{_ftoplam}{_yeni_html}</button></a>'
        _chip_html += '<a href="?ta_fav_ilce=__ekle__" style="text-decoration:none;"><button class="fchip fchip-ekle">+ Favori Ekle</button></a>'
    _chip_html += '</div>'
    st.markdown(_chip_html, unsafe_allow_html=True)

    # ── Ana sekme + görünüm toggle ────────────────────────────────────────────

    _ta_ana = st.session_state.get("ta_ana_sekme","Favorilerim")
    _ta_fav_ak = _ta_ana == "Favorilerim"
    _ta_tum_ak = _ta_ana == "TümüListe"

    _sc = st.columns([1.2,1.0,0.2,1.6,1.6,0.2,0.85,0.85,0.85])
    with _sc[0]:
        if st.button("⭐ Favoriler", key="ta_tog_fav", use_container_width=True,
                     type="primary" if _ta_fav_ak else "secondary"):
            st.session_state["ta_ana_sekme"] = "Favorilerim"
            st.session_state["ta_aktif_sekme"] = "Favorilerim"
            st.session_state["ta_fav_secili_ilce"] = None
            st.rerun()
    with _sc[1]:
        if st.button("Tümü", key="ta_tog_tum", use_container_width=True,
                     type="primary" if _ta_tum_ak else "secondary"):
            st.session_state["ta_ana_sekme"] = "TümüListe"
            st.session_state["ta_aktif_sekme"] = "TümüListe"
            st.rerun()
    for _si, val in [(_sc[3],"İzmir İlçeleri"),(_sc[4],"Diğer İlçeler")]:
        with _si:
            aktif_s = st.session_state.get("ta_aktif_sekme") == val
            if st.button(val, key=f"ta_sekme_{safe_key(val)}", use_container_width=True,
                         type="primary" if aktif_s else "secondary"):
                st.session_state["ta_aktif_sekme"] = (
                    ("Favorilerim" if _ta_fav_ak else "TümüListe") if aktif_s else val
                )
                st.rerun()
    for _si, _val, _vlbl in [(_sc[7],"Kart","  🃏 Kart  "),(_sc[8],"Tablo","  ≡ Tablo  ")]:
        with _si:
            _aktif = st.session_state.get("ta_ft_gorunum") == _val
            if st.button(_vlbl, key=f"ta_view_{_val}", use_container_width=True,
                         type="primary" if _aktif else "secondary"):
                st.session_state["ta_ft_gorunum"] = _val
                st.rerun()

    ta_aktif_sekme = st.session_state.get("ta_aktif_sekme","Favorilerim")
    ta_fav_f_filtre = [v for v in ta_f if talep_favori_kaydi_mi(v, ta_fav_ilceler)]

    # ── Render ───────────────────────────────────────────────────────────────

    if _ta_ana == "TümüListe":
        if not ta_f:
            st.info("Bu dönemde kayıt bulunamadı.")
        else:
            st.markdown(f'<div style="font-size:11px;color:#64748b;margin-bottom:8px;"><b>{len(ta_f)}</b> talep · {ta_hizli}</div>', unsafe_allow_html=True)
            if ta_gorunum == "Tablo":
                talep_tablo_goster(ta_f, "ta_tum_tbl")
            else:  # Kart
                cols3 = st.columns(2, gap="medium")
                for idx, v in enumerate(ta_f):
                    with cols3[idx % 2]:
                        kid = v.get("id")
                        yeni = tarih_gun_farki(en_iyi_tarih(v)) <= 7
                        okundu_k = kid in st.session_state.get("ta_goruldu_ids", set())
                        favori_k = v.get("favori", False)
                        if okundu_k:
                            _rozet_k = '<span style="background:#f1f5f9;color:#64748b;font-size:10px;font-weight:700;padding:3px 9px;border-radius:5px;">Görüldü</span>'
                        elif yeni:
                            _rozet_k = '<span style="background:#16a34a;color:#fff;font-size:10px;font-weight:700;padding:3px 9px;border-radius:5px;">Yeni</span>'
                        else:
                            _rozet_k = ""
                        st.markdown(arsiv_talep_kart_html(v, rozet_html=_rozet_k), unsafe_allow_html=True)
                        _tc1, _tc2, _tc3 = st.columns([3, 1, 1])
                        with _tc1:
                            if st.button("Detay →", key=f"ta_kd_{kid}", use_container_width=True, type="primary"):
                                st.session_state.setdefault("ta_goruldu_ids", set()).add(kid)
                                talep_detay_modal(v, ilce_sec)
                        with _tc2:
                            if st.button("★" if favori_k else "☆", key=f"ta_kfav_{kid}", use_container_width=True):
                                talep_favori_guncelle(kid, favori_k)
                        with _tc3:
                            if st.button("⋯", key=f"ta_tum_more_{kid}", use_container_width=True):
                                st.session_state[f"ta_more_{kid}"] = not st.session_state.get(f"ta_more_{kid}", False)
                                st.rerun()
                        if st.session_state.get(f"ta_more_{kid}", False):
                            _m1, _m2 = st.columns(2)
                            with _m1:
                                if st.button("Düzenle", key=f"ta_tum_dz_{kid}", use_container_width=True, type="secondary"):
                                    st.session_state[f"ta_duzen_{kid}"] = not st.session_state.get(f"ta_duzen_{kid}", False)
                                    st.session_state[f"ta_more_{kid}"] = False; st.rerun()
                            with _m2:
                                if st.button("Gizle", key=f"ta_tum_giz_{kid}", use_container_width=True, type="secondary"):
                                    get_client().table("alici_talepleri").update({"gizli": True}).eq("id", kid).execute()
                                    st.cache_data.clear(); st.rerun()

    elif ta_aktif_sekme == "Favorilerim":
        fav_render = (
            [v for v in ta_fav_f_filtre if _ta_fav_secili in kayit_ilce_listesi(v)]
            if _ta_fav_secili else ta_fav_f_filtre
        )
        if not ta_fav_f_filtre:
            st.info("Favori bölgelerinizdeki taleplerden bu dönemde kayıt bulunmamaktadır.")
        else:
            if ta_gorunum == "Tablo":
                talep_tablo_goster(fav_render, "ta_fav_tbl")
            else:  # Kart
                cols3 = st.columns(2, gap="medium")
                for idx, v in enumerate(fav_render):
                    with cols3[idx % 2]:
                        kid = v.get("id")
                        yeni = tarih_gun_farki(en_iyi_tarih(v)) <= 7
                        okundu_k = kid in st.session_state.get("ta_goruldu_ids", set())
                        favori_k = v.get("favori", False)
                        if okundu_k:
                            _rozet_k = '<span style="background:#f1f5f9;color:#64748b;font-size:10px;font-weight:700;padding:3px 9px;border-radius:5px;">Görüldü</span>'
                        elif yeni:
                            _rozet_k = '<span style="background:#16a34a;color:#fff;font-size:10px;font-weight:700;padding:3px 9px;border-radius:5px;">Yeni</span>'
                        else:
                            _rozet_k = ""
                        st.markdown(arsiv_talep_kart_html(v, rozet_html=_rozet_k), unsafe_allow_html=True)
                        _bc1, _bc2, _bc3 = st.columns([3, 1, 1])
                        with _bc1:
                            if st.button("Detay →", key=f"ta_fk_detay_{kid}", use_container_width=True, type="primary"):
                                st.session_state.setdefault("ta_goruldu_ids", set()).add(kid)
                                talep_detay_modal(v, ilce_sec)
                        with _bc2:
                            if st.button("★" if favori_k else "☆", key=f"ta_fk_fav_{kid}", use_container_width=True):
                                talep_favori_guncelle(kid, favori_k)
                        with _bc3:
                            if st.button("⋯", key=f"ta_fav_more_{kid}", use_container_width=True):
                                st.session_state[f"ta_fmore_{kid}"] = not st.session_state.get(f"ta_fmore_{kid}", False)
                                st.rerun()
                        if st.session_state.get(f"ta_fmore_{kid}", False):
                            _m1, _m2 = st.columns(2)
                            with _m1:
                                if st.button("Düzenle", key=f"ta_fav_dz_{kid}", use_container_width=True, type="secondary"):
                                    st.session_state[f"ta_duzen_{kid}"] = not st.session_state.get(f"ta_duzen_{kid}", False)
                                    st.session_state[f"ta_fmore_{kid}"] = False; st.rerun()
                            with _m2:
                                if st.button("Gizle", key=f"ta_fav_giz_{kid}", use_container_width=True, type="secondary"):
                                    get_client().table("alici_talepleri").update({"gizli": True}).eq("id", kid).execute()
                                    st.cache_data.clear(); st.rerun()

    if ta_aktif_sekme == "İzmir İlçeleri":
        render_compact_aks_haritasi(ta_f, "ta_aks_secili", "ta", entity_label="talep")
        ta_aks_secili = st.session_state.get("ta_aks_secili")
        if ta_aks_secili:
            f_render = [v for v in ta_f if ta_aks_secili in kayit_ilce_listesi(v)]
            st.markdown(f"<div style='font-size:11px;color:#64748b;margin:6px 0 5px;'>{len(f_render)} kayıt</div>", unsafe_allow_html=True)
            talep_tablo_goster(f_render, "ta_izmir_tbl") if ta_gorunum == "Tablo" else [st.markdown(arsiv_talep_kart_html(v), unsafe_allow_html=True) for v in f_render]

    elif ta_aktif_sekme == "Diğer İlçeler":
        diger_ilceler = sorted(set(ilce_grubu(v) for v in ta_f if diger_il_kaydi_mi(v) and ilce_grubu(v)))
        if diger_ilceler:
            cols = st.columns(4)
            for idx, ilce in enumerate(diger_ilceler):
                toplam, yeni = ilce_kayit_sayisi(ta_f, ilce)
                badge = f"  🟢 {yeni} yeni" if yeni > 0 else ""
                with cols[idx % 4]:
                    if st.button(f"{ilce} · {toplam}{badge}", key=f"ta_diger_{safe_key(ilce)}", use_container_width=True):
                        st.session_state["ta_ft_ilce"] = ilce
                        st.rerun()
        else:
            st.caption("Diğer il/ilçe kaydı bulunamadı.")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  PORTFÖY ARŞİVİ                                                         ║
# ╚══════════════════════════════════════════════════════════════════════════╝

with tab_portfoy:

    # ── Veri çekme ──────────────────────────────────────────────────────────

    @st.cache_data(ttl=30)
    def portfoy_verileri_yukle(kaynak_filtre=None):
        """ARŞİV MODU: 60 günden eski portföy kayıtları."""
        ESIK = 60
        try:
            q = (
                get_client().table("portfoyler")
                .select("*").order("olusturma_tarihi", desc=True).limit(2000)
            )
            if kaynak_filtre:
                if kaynak_filtre == "startkey_mail":
                    r1 = q.eq("kaynak","startkey_mail").execute()
                    r2 = q.is_("kaynak","null").execute()
                    tum = (r1.data or []) + (r2.data or [])
                elif isinstance(kaynak_filtre, list):
                    tum = q.in_("kaynak", kaynak_filtre).execute().data or []
                else:
                    tum = q.eq("kaynak", kaynak_filtre).execute().data or []
            else:
                tum = q.execute().data or []
            return [v for v in tum if tarih_gun_farki(en_iyi_tarih(v)) > ESIK]
        except Exception as e:
            st.error(f"Portföy verisi yüklenemedi: {e}")
            return []

    def portfoy_favori_guncelle(kid, mevcut):
        try:
            get_client().table("portfoyler") \
                .update({"favori": not mevcut}).eq("id", kid).execute()
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Hata: {e}")

    def portfoy_kayit_guncelle(kid, data):
        try:
            get_client().table("portfoyler").update(data).eq("id", kid).execute()
            st.session_state.pop(f"pa_duzen_{kid}", None)
            st.session_state[f"pa_guncellendi_{kid}"] = True
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Hata: {e}")

    def portfoy_kayit_gizle(kid):
        try:
            get_client().table("portfoyler") \
                .update({"gizli": True}).eq("id", kid).execute()
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Hata: {e}")

    def portfoy_sil(kid):
        try:
            get_client().table("portfoyler").delete().eq("id", kid).execute()
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Silme hatası: {e}")

    def portfoy_siralama_uygula(liste, siralama):
        if siralama == "Tarih ↓":   return sorted(liste, key=lambda v: tarih_gun_farki(en_iyi_tarih(v)))
        elif siralama == "Tarih ↑": return sorted(liste, key=lambda v: tarih_gun_farki(en_iyi_tarih(v)), reverse=True)
        elif siralama == "İlçe A→Z": return sorted(liste, key=lambda v: (ilce_grubu(v) or "").lower())
        elif siralama == "İlçe Z→A": return sorted(liste, key=lambda v: (ilce_grubu(v) or "").lower(), reverse=True)
        elif siralama == "Fiyat ↑":  return sorted(liste, key=lambda v: fiyat_sayisal(v.get("fiyat","")))
        elif siralama == "Fiyat ↓":  return sorted(liste, key=lambda v: fiyat_sayisal(v.get("fiyat","")), reverse=True)
        return liste

    def portfoy_filtre_temizle():
        for k in ["pa_ft_ara","pa_ft_il","pa_ft_ilce","pa_ft_danisan","pa_ft_mulk",
                  "pa_ft_islem","pa_ft_siralama","pa_ft_hizli","pa_ft_fav","pa_ft_gizli",
                  "pa_fav_secili_ilce","pa_show_filters","pa_ft_fiyat_alt","pa_ft_fiyat_ust",
                  "pa_ft_oda","pa_ft_bina_yasi","pa_ft_kat","pa_ft_esyali","pa_ft_site_ici","pa_ft_kullanim"]:
            st.session_state.pop(k, None)
        st.rerun()

    def foto_goster(foto_urls: list):
        if not foto_urls:
            return
        urls = [u.strip() for u in foto_urls if u.strip()]
        if not urls:
            return
        img_tags = "".join(
            f'<img src="{u}" style="width:100%;max-width:220px;height:160px;'
            f'object-fit:cover;border-radius:8px;margin:4px;" />'
            for u in urls
        )
        st.markdown(
            f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin:8px 0;">{img_tags}</div>',
            unsafe_allow_html=True
        )

    # ── Portföy Detay Modal ──────────────────────────────────────────────────

    @st.dialog("Portföy Detayı", width="large")
    def portfoy_detay_goster(v, ilce_sec):
        kid = v.get("id")
        isim = isim_ayikla(v.get("talep_eden_danisan",""))
        ilceler_list = v.get("ilceler") or []
        fiyat = v.get("fiyat","")
        oda   = v.get("oda_sayisi_m2","")
        mulk  = v.get("mulk_tipi","")
        islem = v.get("islem_tipi","")
        mahalle = v.get("mahalle","") or ""
        bolge   = v.get("bolge","") or v.get("bolge_mahalle","") or ""
        ozet    = v.get("ozet","") or v.get("mail_konusu","") or ""
        ilan    = v.get("ilan_linki","")
        favori  = v.get("favori", False)
        gizli   = v.get("gizli", False)
        gun_farki = tarih_gun_farki(en_iyi_tarih(v))

        lok_parts = ilceler_list[:3] if ilceler_list else ([mahalle] if mahalle else [])
        lokasyon_str = " · ".join(lok_parts)
        _b_parts = []
        if islem and islem not in ("Belirsiz","Belirtilmemiş"): _b_parts.append(islem)
        if oda: _b_parts.append(oda)
        if mulk and mulk not in ("Belirsiz","Belirtilmemiş"): _b_parts.append(mulk)
        _b_parts.append("İlanı" if islem and islem not in ("Belirsiz","") else "Portföyü")
        baslik = " ".join(_b_parts)

        st.markdown(
            f'<div style="background:#FFF9ED;border-left:4px solid #F4B740;padding:10px 14px;'
            f'border-radius:0 8px 8px 0;margin-bottom:12px;">'
            f'<div style="font-size:1.15rem;font-weight:800;color:#172B4D;">{baslik}</div>'
            + (f'<div style="font-size:0.83rem;color:#355C7D;font-weight:600;margin-top:4px;">📍 {lokasyon_str}</div>' if lokasyon_str else "")
            + f'</div>', unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:2px;">Danışman</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:13px;font-weight:600;color:#172B4D;">{isim or "—"}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:2px;">Fiyat</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:13px;font-weight:700;color:#172B4D;">{"💰 "+fiyat if fiyat else "—"}</div>', unsafe_allow_html=True)
        with c3:
            st.markdown('<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:2px;">Oda / M²</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:13px;font-weight:600;color:#172B4D;">{"🏠 "+oda if oda else "—"}</div>', unsafe_allow_html=True)

        st.markdown(etiket_html(mulk)+etiket_html(islem), unsafe_allow_html=True)

        if ilan:
            st.markdown(f'<a href="{ilan}" target="_blank" style="font-size:12px;color:#355C7D;font-weight:600;">↗ İlanı Gör</a>', unsafe_allow_html=True)

        st.divider()

        if ilceler_list or mahalle or bolge:
            st.markdown('<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:4px;">İlçeler</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:13px;color:#374151;margin-bottom:8px;">{", ".join(ilceler_list) if ilceler_list else "—"}</div>', unsafe_allow_html=True)
            r2a, r2b = st.columns(2)
            with r2a:
                st.markdown('<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:2px;">Mahalle</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:13px;color:#374151;">{mahalle or "—"}</div>', unsafe_allow_html=True)
            with r2b:
                st.markdown('<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:2px;">Bölge</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:13px;color:#374151;">{bolge or "—"}</div>', unsafe_allow_html=True)

        if ozet:
            st.markdown(
                f'<div style="background:#f8fafc;border-left:3px solid #e2e8f0;padding:8px 12px;'
                f'border-radius:4px;font-size:12px;color:#475569;margin-top:8px;">'
                f'<b>Özet:</b> {ozet}</div>', unsafe_allow_html=True,
            )

        # Fotoğraflar
        foto_url_str = v.get("foto_url","") or ""
        if foto_url_str:
            foto_urls = [u.strip() for u in foto_url_str.split(",") if u.strip()]
            if foto_urls:
                st.divider()
                st.markdown('<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:4px;">Fotoğraflar</div>', unsafe_allow_html=True)
                foto_goster(foto_urls)

        st.divider()
        not_m = v.get("not_alani","") or ""
        yn = st.text_area("Not", value=not_m, height=80, placeholder="Not ekle...",
                          key=f"pa_modal_not_{kid}", label_visibility="collapsed")
        nb1, _ = st.columns([1,3])
        with nb1:
            if st.button("💾 Notu Kaydet", key=f"pa_modal_nb_{kid}", type="primary", use_container_width=True):
                try:
                    get_client().table("portfoyler").update({"not_alani": yn}).eq("id", kid).execute()
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Hata: {e}")

        st.divider()
        ma1, ma2 = st.columns(2)
        with ma1:
            fav_label = "★ Favoriden Çıkar" if favori else "☆ Favoriye Ekle"
            if st.button(fav_label, key=f"pa_modal_fav_{kid}", use_container_width=True):
                portfoy_favori_guncelle(kid, favori)
        with ma2:
            giz_label = "👁 Göster" if gizli else "⊘ Gizle"
            if st.button(giz_label, key=f"pa_modal_giz_{kid}", use_container_width=True):
                get_client().table("portfoyler") \
                    .update({"gizli": not gizli}).eq("id", kid).execute()
                st.cache_data.clear()
                st.rerun()

    # ── Portföy Kartı ────────────────────────────────────────────────────────

    def portfoy_karti(v, ilce_sec):
        kid = v.get("id")
        isim = isim_ayikla(v.get("talep_eden_danisan",""))
        ozet = v.get("ozet","") or v.get("mail_konusu","")
        fiyat = v.get("fiyat","")
        oda   = v.get("oda_sayisi_m2","")
        islem = v.get("islem_tipi","")
        mulk  = v.get("mulk_tipi","")
        ilan  = v.get("ilan_linki","")
        mahalle = v.get("mahalle","") or ""
        bolge   = v.get("bolge","") or v.get("bolge_mahalle","") or ""
        ilceler_list = v.get("ilceler") or []
        gun = tarih_gun_farki(en_iyi_tarih(v))
        yeni_kayit = gun <= 7
        favori = v.get("favori", False)
        gizli  = v.get("gizli", False)
        duzen_modu = st.session_state.get(f"pa_duzen_{kid}", False)
        okundu = kid in st.session_state.get("pa_goruldu_ids", set())

        if st.session_state.pop(f"pa_guncellendi_{kid}", False):
            st.toast("✅ Güncellendi!")

        tarih_d = tarih_parse(en_iyi_tarih(v))
        if tarih_d:
            _hast = hasattr(tarih_d,'hour') and (tarih_d.hour != 0 or tarih_d.minute != 0)
            tarih_g = tarih_d.strftime("%d.%m.%Y %H:%M") if _hast else tarih_d.strftime("%d.%m.%Y")
        else:
            tarih_g = ""

        _fg, _bg, _dot = tarih_renk_bilgisi(gun)
        tarih_html = (
            f'<span style="display:inline-flex;align-items:center;gap:4px;">'
            f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:{_dot};flex-shrink:0;"></span>'
            f'<span style="color:{_fg};font-weight:600;font-size:11px;">{tarih_g}</span>'
            f'</span>' if tarih_g else ""
        )

        aks_renk = aks_renk_bul(ilceler_list)
        _aks_bar = aks_bar_gradient(ilceler_list)
        lok_parts = ilceler_list[:3] if ilceler_list else ([bolge] if bolge else [])
        lokasyon_str = " · ".join(lok_parts)

        if okundu:       left_border = "#cbd5e1"
        elif yeni_kayit: left_border = "#16a34a"
        elif favori:     left_border = "#f59e0b"
        else:            left_border = "#e2e8f0"

        if okundu:
            _rozet = '<span style="position:absolute;top:8px;right:8px;background:#e2e8f0;color:#94a3b8;font-size:10px;font-weight:700;padding:2px 8px;border-radius:999px;">✓ Görüldü</span>'
        elif yeni_kayit:
            _rozet = '<span style="position:absolute;top:8px;right:8px;background:#16a34a;color:#fff;font-size:10px;font-weight:750;padding:2px 8px;border-radius:999px;">YENİ</span>'
        else:
            _rozet = ""

        _pa_kaynak_raw = (v.get("kaynak") or "").lower()
        if _pa_kaynak_raw in ("startkey_mail", ""):
            _pa_k_lbl, _pa_k_c, _pa_k_bg = "Startkey", "#355C7D", "#EEF4FA"
        elif _pa_kaynak_raw in ("zeta1", "zeta2", "ofis", "zeta"):
            _pa_k_lbl, _pa_k_c, _pa_k_bg = "Zeta", "#0F6E56", "#E1F5EE"
        else:
            _pa_k_lbl, _pa_k_c, _pa_k_bg = "Diğer", "#475569", "#f1f5f9"
        _pa_kaynak_chip = (f'<span style="background:{_pa_k_bg};color:{_pa_k_c};font-size:9.5px;font-weight:600;'
                           f'padding:1px 6px;border-radius:4px;">{_pa_k_lbl}</span>')

        etiketler = etiket_html(mulk) + etiket_html(islem)
        if len(ilceler_list) > 1:
            ils = ", ".join(ilceler_list[:3])
            if len(ilceler_list) > 3: ils += f" +{len(ilceler_list)-3}"
            etiketler += (
                f'<span style="background:#fffbeb;color:#92400e;border:1px solid #fde68a;'
                f'padding:2px 8px;border-radius:999px;font-size:10.5px;font-weight:650;'
                f'margin-right:4px;display:inline-block;">{ils}</span>'
            )
        if ilan:
            etiketler += f'<a href="{ilan}" target="_blank" style="text-decoration:none;"><span style="background:#e0f2fe;color:#0369a1;border:1px solid #bae6fd;padding:2px 7px;border-radius:999px;font-size:10.5px;font-weight:600;margin-right:3px;display:inline-block;">↗ İlan</span></a>'

        _b_parts = []
        if islem and islem not in ("Belirsiz","Belirtilmemiş"): _b_parts.append(islem)
        if oda: _b_parts.append(oda)
        if mulk and mulk not in ("Belirsiz","Belirtilmemiş"): _b_parts.append(mulk)
        _b_parts.append("İlanı" if islem and islem not in ("Belirsiz","") else "Portföyü")
        baslik = " ".join(_b_parts)

        st.markdown(
            f'<div class="kart-wrapper" style="border-left:3px solid {left_border};background:#ffffff;'
            f'border-radius:0 10px 10px 0;padding:12px 14px 10px;margin-bottom:4px;position:relative;">'
            f'{_rozet}'
            + (f'<span class="kart-lokasyon" style="color:{aks_renk["text"]};">{lokasyon_str}</span>' if lokasyon_str else "")
            + f'<div style="background:#FFF9ED;border-left:3px solid #F4B740;'
            f'padding:5px 10px;border-radius:0 6px 6px 0;margin-bottom:6px;">'
            f'<div style="font-size:1.0rem;font-weight:800;color:#172B4D;line-height:1.25;">{baslik}</div>'
            f'</div>'
            + (f'<div class="kart-kriter">{ozet[:120]}</div>' if ozet else "")
            + f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:6px;">'
            f'<span style="font-size:0.91rem;font-weight:750;color:#172B4D;">{str(fiyat) if fiyat else "—"}</span>'
            + (f'<span style="font-size:0.82rem;font-weight:600;color:#475569;">{oda}</span>' if oda else "")
            + f'<span style="font-size:11px;font-weight:600;color:#94a3b8;margin-left:2px;">{isim}</span>'
            f'{etiketler}'
            + _pa_kaynak_chip
            + (f'<span style="margin-left:auto;">{tarih_html}</span>' if tarih_html else "")
            + f'</div></div>',
            unsafe_allow_html=True,
        )

        a_detay, a_fav, a_duz, a_giz, _ = st.columns([1.4, 0.65, 0.65, 0.65, 6])
        with a_detay:
            if st.button("Detay", key=f"pa_detay_{kid}", type="primary", use_container_width=True):
                st.session_state.setdefault("pa_goruldu_ids", set()).add(kid)
                portfoy_detay_goster(v, ilce_sec)
        with a_fav:
            if st.button("★" if favori else "☆", key=f"pa_fav_{kid}", use_container_width=True):
                portfoy_favori_guncelle(kid, favori)
        with a_duz:
            if st.button("✏", key=f"pa_dz_{kid}", use_container_width=True):
                st.session_state[f"pa_duzen_{kid}"] = not duzen_modu
                st.rerun()
        with a_giz:
            if st.button("👁" if gizli else "⊘", key=f"pa_giz_{kid}", use_container_width=True):
                get_client().table("portfoyler") \
                    .update({"gizli": not gizli}).eq("id", kid).execute()
                st.cache_data.clear()
                st.rerun()

        if v.get("kaynak","") and v.get("kaynak","") != "startkey_mail":
            sil_key = f"pa_sil_onay_{kid}"
            if not st.session_state.get(sil_key):
                if st.button("🗑", key=f"pa_sil_{kid}", help="Portföyü sil"):
                    st.session_state[sil_key] = True
                    st.rerun()
            else:
                st.warning("Bu portföyü silmek istediğinizden emin misiniz?")
                sc1, sc2 = st.columns([1,1])
                with sc1:
                    if st.button("🗑 Evet, Sil", key=f"pa_sil_evet_{kid}", type="primary"):
                        portfoy_sil(kid)
                with sc2:
                    if st.button("İptal", key=f"pa_sil_iptal_{kid}"):
                        st.session_state.pop(sil_key, None)
                        st.rerun()

        if duzen_modu:
            _portfoy_duzenleme_formu(v, ilce_sec)

        st.markdown("<div style='height:1px'></div>", unsafe_allow_html=True)

    def _portfoy_duzenleme_formu(v, ilce_sec):
        kid = v.get("id")
        iller = ["İzmir","Aydın","Manisa","Balıkesir","Muğla","Diğer"]
        c1, c2, c3 = st.columns(3)
        with c1:
            oz = st.text_input("Özet", value=v.get("ozet","") or "", key=f"pa_d_oz_{kid}")
            yi = st.selectbox("İl", iller,
                index=iller.index(v.get("il","")) if v.get("il","") in iller else 0,
                key=f"pa_d_il_{kid}")
            yilce = st.selectbox("Birincil İlçe", [""]+ilce_sec,
                index=([""]+ilce_sec).index(v.get("ilce","")) if v.get("ilce","") in ilce_sec else 0,
                key=f"pa_d_ilce_{kid}")
        with c2:
            ym = st.selectbox("Mülk", ["Konut","İşyeri","Arsa","Belirsiz"],
                index=["Konut","İşyeri","Arsa","Belirsiz"].index(v.get("mulk_tipi","Belirsiz"))
                if v.get("mulk_tipi","") in ["Konut","İşyeri","Arsa","Belirsiz"] else 3,
                key=f"pa_d_m_{kid}")
            yis = st.selectbox("İşlem", ["Satılık","Kiralık","Belirsiz"],
                index=["Satılık","Kiralık","Belirsiz"].index(v.get("islem_tipi","Belirsiz"))
                if v.get("islem_tipi","") in ["Satılık","Kiralık","Belirsiz"] else 2,
                key=f"pa_d_is_{kid}")
            ymh = st.text_input("Mahalle", value=v.get("mahalle","") or "", key=f"pa_d_mh_{kid}")
        with c3:
            yb = st.text_input("Bölge/Konum",
                value=v.get("bolge","") or v.get("bolge_mahalle","") or "",
                key=f"pa_d_b_{kid}")
            mevcut = v.get("ilceler") or []
            yilceler = st.multiselect("Tüm İlçeler", ilce_sec,
                default=[i for i in mevcut if i in ilce_sec], key=f"pa_d_ilceler_{kid}")
        ca, cb = st.columns([1,4])
        with ca:
            if st.button("💾 Kaydet", key=f"pa_d_kyd_{kid}", type="primary"):
                portfoy_kayit_guncelle(kid, {
                    "ozet":oz,"il":yi,"ilce":yilce,
                    "ilceler":yilceler if yilceler else ([yilce] if yilce else []),
                    "mulk_tipi":ym,"islem_tipi":yis,"mahalle":ymh,"bolge":yb,
                    "bolge_mahalle":f"{ymh} {yb}".strip()
                })
        with cb:
            if st.button("İptal", key=f"pa_d_ipt_{kid}"):
                st.session_state.pop(f"pa_duzen_{kid}", None)
                st.rerun()

    def portfoy_tablo_goster(kayitlar, prefix="pa_tbl"):
        if not kayitlar:
            st.info("Gösterilecek portföy yok.")
            return

        st.markdown(
            '<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;font-size:10px;color:#94a3b8;">'
            '<span style="display:flex;align-items:center;gap:4px;"><span style="width:7px;height:7px;border-radius:50%;background:#16a34a;display:inline-block;"></span><span>≤7 gün</span></span>'
            '<span style="display:flex;align-items:center;gap:4px;"><span style="width:7px;height:7px;border-radius:50%;background:#ca8a04;display:inline-block;"></span><span>8-30 gün</span></span>'
            '<span style="display:flex;align-items:center;gap:4px;"><span style="width:7px;height:7px;border-radius:50%;background:#ea580c;display:inline-block;"></span><span>31-90 gün</span></span>'
            '<span style="display:flex;align-items:center;gap:4px;"><span style="width:7px;height:7px;border-radius:50%;background:#dc2626;display:inline-block;"></span><span>&gt;90 gün</span></span>'
            '</div>',
            unsafe_allow_html=True
        )

        COL = [4,1.5,1.2,2,2,1.2,0.9,1,0.5,0.5]
        headers = ["Portföy Başlığı","İlçe","İşlem","Fiyat","Danışman","Tarih","Kaynak","","",""]
        h = st.columns(COL)
        for col, hdr in zip(h, headers):
            with col:
                st.markdown(
                    f'<div style="font-size:10px;font-weight:600;color:#94a3b8;text-transform:uppercase;'
                    f'letter-spacing:0.06em;padding:8px 0 6px;border-bottom:1px solid #e2e8f0;">{hdr}</div>',
                    unsafe_allow_html=True
                )

        ilce_sec = ilce_listesi_cek()
        for v in kayitlar:
            kid   = v.get("id","")
            isim  = isim_ayikla(v.get("talep_eden_danisan",""))
            ilce  = ilce_grubu(v) or "—"
            islem = v.get("islem_tipi","") or ""
            mulk  = v.get("mulk_tipi","") or ""
            fiyat = v.get("fiyat","") or "—"
            ozet  = v.get("ozet","") or v.get("mail_konusu","") or ""
            favori = v.get("favori",False)
            gun_farki = tarih_gun_farki(en_iyi_tarih(v))
            okundu    = kid in st.session_state.get("pa_goruldu_ids",set())
            _fg, _bg, dot_c = tarih_renk_bilgisi(gun_farki)
            if okundu: dot_c="#cbd5e1"; _fg="#94a3b8"; _bg="#f8fafc"

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

            _b_parts = []
            if islem and islem not in ("Belirsiz","Belirtilmemiş"): _b_parts.append(islem)
            if v.get("oda_sayisi_m2",""): _b_parts.append(v.get("oda_sayisi_m2",""))
            if mulk and mulk not in ("Belirsiz","Belirtilmemiş"): _b_parts.append(mulk)
            _b_parts.append("İlanı" if islem and islem not in ("Belirsiz","") else "Portföyü")
            baslik = " ".join(_b_parts)
            kriter = ozet[:55]
            initials = "".join(w[0].upper() for w in isim.split()[:2]) if isim else "?"
            ROW = "border-bottom:0.5px solid #f1f5f9;padding:8px 0;"

            row = st.columns(COL)
            with row[0]:
                st.markdown(
                    f'<div style="{ROW}"><div style="display:flex;align-items:center;gap:6px;">'
                    f'<span style="width:6px;height:6px;border-radius:50%;background:{dot_c};flex-shrink:0;display:inline-block;"></span>'
                    f'<span style="font-size:12px;font-weight:600;color:#1e293b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:95%;display:block;">{baslik}</span>'
                    f'</div>'
                    + (f'<div style="font-size:10.5px;color:#64748b;margin-left:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{kriter}</div>' if kriter else "")
                    + f'</div>', unsafe_allow_html=True)
            with row[1]:
                st.markdown(f'<div style="{ROW}"><span style="background:{aks_r["bg"]};color:{aks_r["text"]};padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600;">{ilce}</span></div>', unsafe_allow_html=True)
            with row[2]:
                st.markdown(f'<div style="{ROW}"><span style="background:{tip_bg};color:{tip_color};padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600;">{tip_lbl}</span></div>', unsafe_allow_html=True)
            with row[3]:
                st.markdown(f'<div style="{ROW};font-size:11.5px;font-weight:600;color:#0f172a;">{fiyat}</div>', unsafe_allow_html=True)
            with row[4]:
                st.markdown(f'<div style="{ROW};display:flex;align-items:center;gap:5px;"><span style="font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{isim or "—"}</span></div>', unsafe_allow_html=True)
            with row[5]:
                st.markdown(f'<div style="{ROW}"><span style="background:{_bg};color:{_fg};font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:4px;white-space:nowrap;">{tarih_str}</span></div>', unsafe_allow_html=True)
            with row[6]:
                st.markdown(f'<div style="{ROW}"><span style="background:{k_bg};color:{k_c};font-size:10px;font-weight:600;padding:2px 6px;border-radius:4px;">{k_lbl}</span></div>', unsafe_allow_html=True)
            with row[7]:
                if st.button("Detay", key=f"{prefix}_detay_{kid}", use_container_width=True, type="primary"):
                    st.session_state.setdefault("pa_goruldu_ids",set()).add(kid)
                    portfoy_detay_goster(v, ilce_sec)
            with row[8]:
                if st.button("★" if favori else "☆", key=f"{prefix}_fav_{kid}", use_container_width=True):
                    portfoy_favori_guncelle(kid, favori)
            with row[9]:
                if st.button("✏", key=f"{prefix}_dz_{kid}", use_container_width=True):
                    st.session_state[f"pa_duzen_{kid}"] = not st.session_state.get(f"pa_duzen_{kid}",False)
                    st.rerun()

    # ── State init ───────────────────────────────────────────────────────────

    PA_DEFAULTS = {
        "pa_ft_ara":"","pa_ft_il":"Tümü","pa_ft_ilce":"Tümü",
        "pa_ft_danisan":"Tümü","pa_ft_mulk":"Tümü","pa_ft_islem":"Tümü",
        "pa_ft_siralama":"Tarih ↓","pa_ft_hizli":"Son 3 ay",
        "pa_ft_fav":False,"pa_ft_gizli":False,
        "pa_ft_fiyat_alt":0,"pa_ft_fiyat_ust":0,"pa_ft_oda":"Tümü",
        "pa_ft_bina_yasi":"Tümü","pa_ft_kat":"Tümü","pa_ft_esyali":"Tümü",
        "pa_ft_site_ici":"Tümü","pa_ft_kullanim":"Tümü",
        "pa_ft_gorunum":"Tablo","pa_aktif_kaynak":"startkey",
        "pa_fav_secili_ilce":None,"pa_aktif_sekme":"TümüListe",
        "pa_ana_sekme":"TümüListe","pa_aks_secili":None,
        "pa_show_filters":False,"pa_goruldu_ids":set(),
    }
    for k, v_def in PA_DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v_def

    # ── Veri yükleme ─────────────────────────────────────────────────────────

    pa_veriler = portfoy_verileri_yukle(None)

    if not st.session_state.get("pa_ft_gizli",False):
        pa_veriler = [v for v in pa_veriler if not v.get("gizli",False)]

    ilce_sec_p = ilce_listesi_cek()
    pa_fav_ilceler = favori_ilceleri_cek()

    pa_danisman_sayisi = len(set(
        isim_ayikla(v.get("talep_eden_danisan",""))
        for v in pa_veriler if v.get("talep_eden_danisan","")
    ))

    # ── Arşiv uyarısı ───────────────────────────────────────────────────────

    st.markdown(
        '<div style="background:#FFF9ED;border-left:4px solid #F4B740;padding:8px 14px;'
        'border-radius:6px;margin-bottom:10px;font-size:12px;color:#92400e;">'
        '🏠 <b>Arşiv görünümü</b> — 60 günden eski portföyler. Aktif kayıtlar için '
        '<a href="/3_Portfoy_Tablosu" style="color:#92400e;font-weight:700;">Portföy Merkezi</a>\'ni kullanın.'
        '</div>',
        unsafe_allow_html=True
    )

    st.caption(f"**{len(pa_veriler)}** portföy · {pa_danisman_sayisi} danışman")

    if not pa_veriler:
        st.info("Arşivde portföy bulunamadı.")
        st.stop()

    # ── Hızlı filtre + filtreler butonu ─────────────────────────────────────

    pa_allowed_hizli = ["Tümü","Son 3 ay","Son 6 ay","Son 1 yıl"]
    if st.session_state.get("pa_ft_hizli") not in pa_allowed_hizli:
        st.session_state["pa_ft_hizli"] = "Son 3 ay"

    pa_hizli_sayilar = {
        "Son 3 ay":  sum(1 for v in pa_veriler if tarih_gun_farki(en_iyi_tarih(v)) <= 90),
        "Son 6 ay":  sum(1 for v in pa_veriler if tarih_gun_farki(en_iyi_tarih(v)) <= 180),
        "Son 1 yıl": sum(1 for v in pa_veriler if tarih_gun_farki(en_iyi_tarih(v)) <= 365),
        "Tümü":      len(pa_veriler),
    }
    pa_hizli_map = [
        ("Son 3 ay",  f"3 Ay · {pa_hizli_sayilar['Son 3 ay']}"),
        ("Son 6 ay",  f"6 Ay · {pa_hizli_sayilar['Son 6 ay']}"),
        ("Son 1 yıl", f"1 Yıl · {pa_hizli_sayilar['Son 1 yıl']}"),
        ("Tümü",      f"Tümü · {pa_hizli_sayilar['Tümü']}"),
    ]

    pa_aktif_filtre_sayisi = sum([
        st.session_state.get("pa_ft_il","Tümü") != "Tümü",
        st.session_state.get("pa_ft_ilce","Tümü") != "Tümü",
        st.session_state.get("pa_ft_danisan","Tümü") != "Tümü",
        st.session_state.get("pa_ft_mulk","Tümü") != "Tümü",
        st.session_state.get("pa_ft_islem","Tümü") != "Tümü",
        bool(st.session_state.get("pa_ft_ara","").strip()),
        st.session_state.get("pa_ft_fav",False),
    ])
    pa_filtre_btn = f"⚙ Filtreler {pa_aktif_filtre_sayisi}" if pa_aktif_filtre_sayisi else "⚙ Filtreler"

    pb1, pb2, pb3, pb4, pb5 = st.columns([1,1,1,1.3,0.9])
    for col, (deger, label) in zip([pb1,pb2,pb3,pb4], pa_hizli_map):
        with col:
            aktif = st.session_state.get("pa_ft_hizli") == deger
            if st.button(label, key=f"pa_hizli_{safe_key(deger)}", use_container_width=True,
                         type="primary" if aktif else "secondary"):
                st.session_state["pa_ft_hizli"] = deger
                st.rerun()
    with pb5:
        if st.button(pa_filtre_btn, key="pa_toggle_filters", use_container_width=True,
                     type="primary" if st.session_state.get("pa_show_filters") else "secondary"):
            st.session_state["pa_show_filters"] = not st.session_state.get("pa_show_filters",False)
            st.rerun()

    # ── Filtre paneli ────────────────────────────────────────────────────────

    if st.session_state.get("pa_show_filters",False):
        with st.container(border=True):
            pa_tum_iller = sorted(set(il_grubu(v) for v in pa_veriler if il_grubu(v)))
            pa_tum_ilceler = sorted(set(
                ilce for v in pa_veriler
                for ilce in (v.get("ilceler") or [])
                if ilce and ilce != "Diğer Bölge"
            ))
            pa_danismanlar = sorted(set(
                isim_ayikla(v.get("talep_eden_danisan",""))
                for v in pa_veriler if v.get("talep_eden_danisan","")
            ))
            if st.session_state.get("pa_ft_il") not in (["Tümü"]+pa_tum_iller+["Belirtilmemiş"]):
                st.session_state["pa_ft_il"] = "Tümü"
            if st.session_state.get("pa_ft_ilce") not in (["Tümü"]+pa_tum_ilceler):
                st.session_state["pa_ft_ilce"] = "Tümü"
            if st.session_state.get("pa_ft_danisan") not in (["Tümü"]+pa_danismanlar):
                st.session_state["pa_ft_danisan"] = "Tümü"

            f1,f2,f3,f4,f5 = st.columns([1.1,1.1,1.7,1.1,1.1])
            with f1: st.selectbox("İl", ["Tümü"]+pa_tum_iller+["Belirtilmemiş"], key="pa_ft_il")
            with f2: st.selectbox("İlçe", ["Tümü"]+pa_tum_ilceler, key="pa_ft_ilce")
            with f3: st.selectbox("Danışman", ["Tümü"]+pa_danismanlar, key="pa_ft_danisan")
            with f4: st.selectbox("Mülk", ["Tümü","Konut","İşyeri","Arsa","Belirtilmemiş"], key="pa_ft_mulk")
            with f5: st.selectbox("İşlem", ["Tümü","Satılık","Kiralık","Belirtilmemiş"], key="pa_ft_islem")

            g1,g2,g3,g4,g5 = st.columns([1.2,1.2,1.8,1.2,1.4])
            with g1:
                st.caption("Fiyat Alt (TL)")
                st.number_input("", min_value=0, step=100000, key="pa_ft_fiyat_alt", label_visibility="collapsed")
            with g2:
                st.caption("Fiyat Üst (TL)")
                st.number_input("", min_value=0, step=100000, key="pa_ft_fiyat_ust", label_visibility="collapsed")
            with g3: st.text_input("Arama", placeholder="Başlık, ilçe, özellik...", key="pa_ft_ara")
            with g4: st.selectbox("Sıralama", ["Tarih ↓","Tarih ↑","İlçe A→Z","İlçe Z→A","Fiyat ↑","Fiyat ↓"], key="pa_ft_siralama")
            with g5:
                st.write("")
                st.button("Temizle", key="pa_filtre_temizle", use_container_width=True, on_click=portfoy_filtre_temizle)

            e1,e2,_ = st.columns([1,1,6])
            with e1: st.checkbox("Favori", key="pa_ft_fav")
            with e2: st.checkbox("Gizli", key="pa_ft_gizli")

    # ── Filtreleme ────────────────────────────────────────────────────────────

    pa_il_f    = st.session_state.get("pa_ft_il","Tümü")
    pa_ilce_f  = st.session_state.get("pa_ft_ilce","Tümü")
    pa_dan_f   = st.session_state.get("pa_ft_danisan","Tümü")
    pa_mulk_f  = st.session_state.get("pa_ft_mulk","Tümü")
    pa_islem_f = st.session_state.get("pa_ft_islem","Tümü")
    pa_ara     = st.session_state.get("pa_ft_ara","")
    pa_siralama= st.session_state.get("pa_ft_siralama","Tarih ↓")
    pa_hizli   = st.session_state.get("pa_ft_hizli","Son 3 ay")
    pa_fav_f   = st.session_state.get("pa_ft_fav",False)
    pa_fiyat_alt = st.session_state.get("pa_ft_fiyat_alt",0)
    pa_fiyat_ust = st.session_state.get("pa_ft_fiyat_ust",0)
    pa_gorunum = st.session_state.get("pa_ft_gorunum","Tablo")
    if pa_gorunum not in ["Kart","Tablo"]:
        pa_gorunum = "Tablo"

    pa_f = pa_veriler
    if pa_ara:
        pa_f = [v for v in pa_f if any(pa_ara.lower() in str(v.get(k,"")).lower()
                for k in ["talep_eden_danisan","bolge_mahalle","mahalle","bolge","ilce","ozet","ilceler"])]
    if pa_il_f == "Belirtilmemiş": pa_f = [v for v in pa_f if not il_grubu(v)]
    elif pa_il_f != "Tümü": pa_f = [v for v in pa_f if il_grubu(v) == pa_il_f]
    if pa_ilce_f != "Tümü": pa_f = [v for v in pa_f if pa_ilce_f in (v.get("ilceler") or [])]
    if pa_dan_f != "Tümü": pa_f = [v for v in pa_f if isim_ayikla(v.get("talep_eden_danisan","")) == pa_dan_f]
    if pa_mulk_f == "Belirtilmemiş": pa_f = [v for v in pa_f if v.get("mulk_tipi","") in ("","Belirsiz","Belirtilmemiş",None)]
    elif pa_mulk_f != "Tümü": pa_f = [v for v in pa_f if v.get("mulk_tipi","") == pa_mulk_f]
    if pa_islem_f == "Belirtilmemiş": pa_f = [v for v in pa_f if v.get("islem_tipi","") in ("","Belirsiz","Belirtilmemiş",None)]
    elif pa_islem_f != "Tümü": pa_f = [v for v in pa_f if v.get("islem_tipi","") == pa_islem_f]
    if pa_hizli != "Tümü":
        gl = {"Son 3 ay":90,"Son 6 ay":180,"Son 1 yıl":365}.get(pa_hizli)
        if gl: pa_f = [v for v in pa_f if tarih_gun_farki(en_iyi_tarih(v)) <= gl]
    if pa_fiyat_alt > 0: pa_f = [v for v in pa_f if fiyat_sayisal(v.get("fiyat","")) >= pa_fiyat_alt]
    if pa_fiyat_ust > 0: pa_f = [v for v in pa_f if fiyat_sayisal(v.get("fiyat","")) <= pa_fiyat_ust]
    if pa_fav_f: pa_f = [v for v in pa_f if v.get("favori",False)]
    pa_f = portfoy_siralama_uygula(pa_f, pa_siralama)

    # ── Favori chip'leri ─────────────────────────────────────────────────────

    _pa_fav_list = pa_fav_ilceler
    _pa_fav_secili = st.session_state.get("pa_fav_secili_ilce")

    _pa_qp = st.query_params
    if "pa_fav_ilce" in _pa_qp:
        _gelen = _pa_qp["pa_fav_ilce"]
        if _gelen == "__tumu__":
            st.session_state["pa_fav_secili_ilce"] = None
            st.session_state["pa_ana_sekme"] = "Favorilerim"
            del st.query_params["pa_fav_ilce"]; st.rerun()
        elif _gelen == "__ekle__":
            st.session_state["pa_show_fav_ekle"] = True
            del st.query_params["pa_fav_ilce"]; st.rerun()
        else:
            st.session_state["pa_fav_secili_ilce"] = None if _pa_fav_secili == _gelen else _gelen
            st.session_state["pa_ana_sekme"] = "Favorilerim"
            del st.query_params["pa_fav_ilce"]; st.rerun()

    _pa_chip_html = '<div class="firsat-row">'
    if _pa_fav_list:
        _pa_fav_toplam = sum(ilce_kayit_sayisi(pa_f, fi)[0] for fi in _pa_fav_list[:5])
        _tumu_cls = "fchip fchip-tumu active" if not _pa_fav_secili else "fchip fchip-tumu"
        _pa_chip_html += f'<a href="?pa_fav_ilce=__tumu__" style="text-decoration:none;"><button class="{_tumu_cls}">★ Tüm Favoriler &nbsp;{_pa_fav_toplam}</button></a>'
        for _pfilce in _pa_fav_list[:5]:
            _pftoplam, _pfyeni = ilce_kayit_sayisi(pa_f, _pfilce)
            if _pftoplam == 0: continue
            _pfsecili = _pa_fav_secili == _pfilce
            _ilce_cls = "fchip fchip-ilce active" if _pfsecili else "fchip fchip-ilce"
            _yeni_html = f'<span class="fchip-yeni">{_pfyeni} yeni</span>' if _pfyeni > 0 else ""
            _pa_chip_html += f'<a href="?pa_fav_ilce={_pfilce}" style="text-decoration:none;"><button class="{_ilce_cls}">★ {_pfilce} &nbsp;{_pftoplam}{_yeni_html}</button></a>'
        _pa_chip_html += '<a href="?pa_fav_ilce=__ekle__" style="text-decoration:none;"><button class="fchip fchip-ekle">+ Favori Ekle</button></a>'
    _pa_chip_html += '</div>'
    st.markdown(_pa_chip_html, unsafe_allow_html=True)

    # ── Ana sekme + görünüm toggle ────────────────────────────────────────────

    _pa_ana = st.session_state.get("pa_ana_sekme","Favorilerim")
    _pa_fav_ak = _pa_ana == "Favorilerim"
    _pa_tum_ak = _pa_ana == "TümüListe"

    _psc = st.columns([1.2,1.0,0.2,1.6,1.6,0.2,0.85,0.85,0.85])
    with _psc[0]:
        if st.button("⭐ Favoriler", key="pa_tog_fav", use_container_width=True,
                     type="primary" if _pa_fav_ak else "secondary"):
            st.session_state["pa_ana_sekme"] = "Favorilerim"
            st.session_state["pa_aktif_sekme"] = "Favorilerim"
            st.session_state["pa_fav_secili_ilce"] = None
            st.rerun()
    with _psc[1]:
        if st.button("Tümü", key="pa_tog_tum", use_container_width=True,
                     type="primary" if _pa_tum_ak else "secondary"):
            st.session_state["pa_ana_sekme"] = "TümüListe"
            st.session_state["pa_aktif_sekme"] = "TümüListe"
            st.rerun()
    for _si, val in [(_psc[3],"İzmir İlçeleri"),(_psc[4],"Diğer İlçeler")]:
        with _si:
            aktif_s = st.session_state.get("pa_aktif_sekme") == val
            if st.button(val, key=f"pa_sekme_{safe_key(val)}", use_container_width=True,
                         type="primary" if aktif_s else "secondary"):
                st.session_state["pa_aktif_sekme"] = (
                    ("Favorilerim" if _pa_fav_ak else "TümüListe") if aktif_s else val
                )
                st.rerun()
    for _si, _val, _vlbl in [(_psc[7],"Kart","  🃏 Kart  "),(_psc[8],"Tablo","  ≡ Tablo  ")]:
        with _si:
            _aktif = st.session_state.get("pa_ft_gorunum") == _val
            if st.button(_vlbl, key=f"pa_view_{_val}", use_container_width=True,
                         type="primary" if _aktif else "secondary"):
                st.session_state["pa_ft_gorunum"] = _val
                st.rerun()

    pa_aktif_sekme = st.session_state.get("pa_aktif_sekme","Favorilerim")
    pa_fav_f_filtre = [v for v in pa_f if any(
        i in pa_fav_ilceler for i in (v.get("ilceler") or [])
    )]

    # ── Render ───────────────────────────────────────────────────────────────

    st.caption(f"**{len(pa_f)}** / {len(pa_veriler)} portföy")

    if _pa_ana == "TümüListe":
        if not pa_f:
            st.info("Bu dönemde portföy bulunamadı.")
        else:
            if pa_gorunum == "Tablo":
                portfoy_tablo_goster(pa_f, "pa_tum_tbl")
            else:  # Kart
                cols3 = st.columns(2, gap="medium")
                for idx, v in enumerate(pa_f):
                    with cols3[idx % 2]:
                        kid = v.get("id")
                        yeni = tarih_gun_farki(en_iyi_tarih(v)) <= 7
                        okundu_k = kid in st.session_state.get("pa_goruldu_ids", set())
                        favori_k = v.get("favori", False)
                        if okundu_k:
                            _rozet_k = '<span style="background:#f1f5f9;color:#64748b;font-size:10px;font-weight:700;padding:3px 9px;border-radius:5px;">Görüldü</span>'
                        elif yeni:
                            _rozet_k = '<span style="background:#16a34a;color:#fff;font-size:10px;font-weight:700;padding:3px 9px;border-radius:5px;">Yeni</span>'
                        else:
                            _rozet_k = '<span style="background:#94a3b8;color:#fff;font-size:10px;font-weight:600;padding:3px 9px;border-radius:5px;">Arşiv</span>'
                        st.markdown(arsiv_portfoy_kart_html(v, rozet_html=_rozet_k), unsafe_allow_html=True)
                        _ac1, _ac2, _ac3 = st.columns([3, 1, 1])
                        with _ac1:
                            if st.button("Detay →", key=f"pa_tum_kd_{kid}", use_container_width=True, type="primary"):
                                st.session_state.setdefault("pa_goruldu_ids", set()).add(kid)
                                portfoy_detay_goster(v, ilce_sec_p)
                        with _ac2:
                            if st.button("★" if favori_k else "☆", key=f"pa_tum_fav_{kid}", use_container_width=True):
                                portfoy_favori_guncelle(kid, favori_k)
                        with _ac3:
                            if st.button("⋯", key=f"pa_tum_more_{kid}", use_container_width=True):
                                st.session_state[f"pa_tmore_{kid}"] = not st.session_state.get(f"pa_tmore_{kid}", False)
                                st.rerun()
                        if st.session_state.get(f"pa_tmore_{kid}", False):
                            _m1, _m2 = st.columns(2)
                            with _m1:
                                if st.button("Düzenle", key=f"pa_tum_dz_{kid}", use_container_width=True, type="secondary"):
                                    st.session_state[f"pa_duzen_{kid}"] = not st.session_state.get(f"pa_duzen_{kid}", False)
                                    st.session_state[f"pa_tmore_{kid}"] = False; st.rerun()
                            with _m2:
                                if st.button("Gizle", key=f"pa_tum_giz_{kid}", use_container_width=True, type="secondary"):
                                    get_client().table("portfoyler").update({"gizli": True}).eq("id", kid).execute()
                                    st.cache_data.clear(); st.rerun()
    elif pa_aktif_sekme == "Favorilerim":
        fav_render = (
            [v for v in pa_fav_f_filtre if _pa_fav_secili in kayit_ilce_listesi(v)]
            if _pa_fav_secili else pa_fav_f_filtre
        )
        if not pa_fav_f_filtre:
            st.info("Favori bölgelerinizdeki portföylerden bu dönemde kayıt bulunmamaktadır.")
        else:
            if pa_gorunum == "Tablo":
                portfoy_tablo_goster(fav_render, "pa_fav_tbl")
            else:  # Kart
                cols3 = st.columns(2, gap="medium")
                for idx, v in enumerate(fav_render):
                    with cols3[idx % 2]:
                        kid = v.get("id")
                        yeni = tarih_gun_farki(en_iyi_tarih(v)) <= 7
                        okundu_k = kid in st.session_state.get("pa_goruldu_ids", set())
                        favori_k = v.get("favori", False)
                        if okundu_k:
                            _rozet_k = '<span style="background:#f1f5f9;color:#64748b;font-size:10px;font-weight:700;padding:3px 9px;border-radius:5px;">Görüldü</span>'
                        elif yeni:
                            _rozet_k = '<span style="background:#16a34a;color:#fff;font-size:10px;font-weight:700;padding:3px 9px;border-radius:5px;">Yeni</span>'
                        else:
                            _rozet_k = '<span style="background:#94a3b8;color:#fff;font-size:10px;font-weight:600;padding:3px 9px;border-radius:5px;">Arşiv</span>'
                        st.markdown(arsiv_portfoy_kart_html(v, rozet_html=_rozet_k), unsafe_allow_html=True)
                        _bc1, _bc2, _bc3 = st.columns([3, 1, 1])
                        with _bc1:
                            if st.button("Detay →", key=f"pa_fk_detay_{kid}", use_container_width=True, type="primary"):
                                st.session_state.setdefault("pa_goruldu_ids", set()).add(kid)
                                portfoy_detay_goster(v, ilce_sec_p)
                        with _bc2:
                            if st.button("★" if favori_k else "☆", key=f"pa_fk_fav_{kid}", use_container_width=True):
                                portfoy_favori_guncelle(kid, favori_k)
                        with _bc3:
                            if st.button("⋯", key=f"pa_fav_more_{kid}", use_container_width=True):
                                st.session_state[f"pa_fmore_{kid}"] = not st.session_state.get(f"pa_fmore_{kid}", False)
                                st.rerun()
                        if st.session_state.get(f"pa_fmore_{kid}", False):
                            _m1, _m2 = st.columns(2)
                            with _m1:
                                if st.button("Düzenle", key=f"pa_fav_dz_{kid}", use_container_width=True, type="secondary"):
                                    st.session_state[f"pa_duzen_{kid}"] = not st.session_state.get(f"pa_duzen_{kid}", False)
                                    st.session_state[f"pa_fmore_{kid}"] = False; st.rerun()
                            with _m2:
                                if st.button("Gizle", key=f"pa_fav_giz_{kid}", use_container_width=True, type="secondary"):
                                    get_client().table("portfoyler").update({"gizli": True}).eq("id", kid).execute()
                                    st.cache_data.clear(); st.rerun()
    if pa_aktif_sekme == "İzmir İlçeleri":
        render_compact_aks_haritasi(pa_f, "pa_aks_secili", "pa", entity_label="portföy")
        pa_aks_secili = st.session_state.get("pa_aks_secili")
        if pa_aks_secili:
            f_render = [v for v in pa_f if pa_aks_secili in kayit_ilce_listesi(v)]
            st.markdown(f"<div style='font-size:11px;color:#64748b;margin:6px 0 5px;'>{len(f_render)} portföy</div>", unsafe_allow_html=True)
            if pa_gorunum == "Tablo":
                portfoy_tablo_goster(f_render, "pa_izmir_tbl")
            else:
                for v in f_render:
                    pass  # portfoy_karti kaldırıldı

    elif pa_aktif_sekme == "Diğer İlçeler":
        diger_ilceler = sorted(set(ilce_grubu(v) for v in pa_f if diger_il_kaydi_mi(v) and ilce_grubu(v)))
        if diger_ilceler:
            cols = st.columns(4)
            for idx, ilce in enumerate(diger_ilceler):
                toplam, yeni = ilce_kayit_sayisi(pa_f, ilce)
                badge = f"  🟢 {yeni} yeni" if yeni > 0 else ""
                with cols[idx % 4]:
                    if st.button(f"{ilce} · {toplam}{badge}", key=f"pa_diger_{safe_key(ilce)}", use_container_width=True):
                        st.session_state["pa_ft_ilce"] = ilce
                        st.rerun()
        else:
            st.caption("Diğer il/ilçe portföyü bulunamadı.")

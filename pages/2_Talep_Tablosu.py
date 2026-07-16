import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.supabase_client import get_client
from core.ui_helpers import render_navbar, render_page_header
import pandas as pd
import re
from datetime import date, timedelta, datetime
from email.utils import parsedate_to_datetime
import time
_t_sayfa0 = time.time()

# ── PERF DEBUG ────────────────────────────────────────────────────────────────
# P0 performans stabilizasyonu sonrası geçici gözlem anahtarı.
# True yapılırsa ekranda render edilen kayıt sayıları küçük bir caption olarak
# gösterilir. Varsayılan olarak kapalı, kalıcı debug arayüzü DEĞİLDİR.
PERF_DEBUG = False


# ── GLOBAL CSS ───────────────────────────────────────────────────────────────
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

.stApp {
    background: var(--bg);
}

.block-container {
    padding-top: 0.5rem;
    padding-bottom: 2rem;
    max-width: 1520px;
}

/* ── UNIFIED BUTTON SYSTEM ─────────────────────────────────── */
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

/* Primary */
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

/* Secondary */
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

/* Compact mode */
body.compact-mode div[data-testid="stButton"] > button {
    min-height: 24px !important;
    padding: 2px 7px !important;
    font-size: 11px !important;
}

.detail-panel div[data-testid="stButton"] > button {
    min-height: 32px !important;
    padding: 5px 10px !important;
    font-size: 11px !important;
}

.detail-panel .detail-meta-bar {
    font-size: 11px;
    color: #334155;
    letter-spacing: 0.01em;
}

.detail-panel .detail-summary {
    font-size: 11px;
    line-height: 1.35;
    color: #172B4D;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
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

h2, h3, h4 {
    color: #1f2937;
    letter-spacing: -0.2px;
}

div[data-baseweb="select"] > div {
    border-radius: 6px !important;
    border-color: var(--border) !important;
    min-height: 32px !important;
    font-size: 12px !important;
}

input {
    border-radius: 6px !important;
    font-size: 12px !important;
}

input::placeholder {
    color: #94a3b8 !important;
    opacity: 1 !important;
}

label, .stSelectbox label, .stTextInput label {
    color: #475569 !important;
    font-weight: 600 !important;
    font-size: 11px !important;
}

/* ── UTILITY CLASSES ────────────────────────────────────────── */
.red-accent { color: var(--accent-red); font-weight: 750; }

.red-badge {
    display: inline-block;
    background: #faeeda;
    color: #633806;
    border: 1px solid #f5d9a0;
    padding: 1px 6px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 700;
    margin-left: 3px;
}

.red-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    background: var(--accent-red);
    border-radius: 50%;
    margin-right: 4px;
    box-shadow: 0 0 0 2px rgba(255,77,79,0.12);
}

.charcoal-note { color: #374151; font-weight: 650; }

.fav-section-title {
    font-size: 10px;
    font-weight: 750;
    color: #8a6124;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
}

/* ── KPI TOOLBAR ────────────────────────────────────────────── */
.kpi-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    flex-wrap: wrap;
    padding: 2px 0 6px 0;
    margin-bottom: 8px;
}

.kpi-main {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    font-size: 12px;
    color: #374151;
    font-weight: 650;
    line-height: 1.4;
}

.kpi-chip {
    display: inline-flex;
    flex-direction: column;
    justify-content: center;
    min-width: 92px;
    background: var(--chip-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 8px 10px;
    box-shadow: 0 1px 2px rgba(53, 92, 125, 0.08);
}

.kpi-chip strong {
    display: block;
    font-size: 13px;
    font-weight: 800;
    color: var(--text);
}

.insight-chip {
    min-width: 130px;
    background: var(--hover-bg);
}

.kpi-chip small {
    display: block;
    margin-top: 4px;
    color: #64748b;
    font-size: 11px;
    font-weight: 600;
}

.kpi-top3 {
    font-size: 11px;
    color: #64748b;
    font-weight: 500;
    white-space: nowrap;
    opacity: 0.96;
}

/* ── WORKSPACE TABS ─────────────────────────────────────────── */
.ws-tab-active {
    background: #eef4fb !important;
    border-color: #eef4fb !important;
    color: var(--text) !important;
    box-shadow: inset 0 0 0 1px rgba(232,93,117,0.12) !important;
    border-left: 2px solid rgba(232,93,117,0.40) !important;
}

/* ── VIEW TOGGLE ────────────────────────────────────────────── */
.gorunum-label {
    font-size: 11px;
    font-weight: 700;
    color: #64748b;
    white-space: nowrap;
    padding-top: 8px;
    text-align: right;
}

/* ── COMPACT MODE ───────────────────────────────────────────── */
.compact-kart { font-size: 11px !important; }
.compact-kart .kart-isim { font-size: 12px !important; }
.compact-kart .kart-ozet { font-size: 11px !important; }

/* ── FILTRE BADGE ───────────────────────────────────────────── */
.filtre-badge {
    display: inline-block;
    background: #ff4d4f;
    color: white;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 700;
    padding: 0 5px;
    margin-left: 4px;
    vertical-align: middle;
    line-height: 16px;
    height: 16px;
}

/* ── SAYFA HERO ────────────────────────────────────── */
.page-hero {
    width: 100%;
    text-align: center;
    padding: 14px 0 8px 0;
    margin-bottom: 4px;
}
.page-hero-stripe {
    height: 4px;
    background: linear-gradient(90deg, #1E3A5F 0%, #355C7D 50%, #527EA0 100%);
    border-radius: 0 0 3px 3px;
    margin: 0 -2rem 18px -2rem;
}
.page-hero-title {
    font-size: 3rem;
    font-weight: 900;
    background: linear-gradient(135deg, #172B4D 0%, #355C7D 55%, #527EA0 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: 0.06em;
    line-height: 1.05;
    margin-bottom: 10px;
    display: inline-block;
    text-transform: uppercase;
}

.page-hero-sep {
    border: none;
    border-bottom: 1px solid #E2E8F0;
    margin: 4px 0 4px 0;
}

/* ── FIRSAT / FAVORİ BUTONLARI ─────────────────────── */
.firsat-row {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
    padding: 6px 0 4px 0;
}
.fchip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 6px 14px;
    border-radius: 999px;
    font-size: 12.5px;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
    border: none;
    transition: all 0.15s ease;
    font-family: inherit;
    line-height: 1;
}
.fchip-tumu {
    background: #f1f5f9;
    color: #475569;
    border: 1px solid #dce4ee;
}
.fchip-tumu.active {
    background: linear-gradient(135deg, #1E3A5F, #355C7D);
    color: #ffffff;
    border-color: transparent;
}
.fchip-ilce {
    background: linear-gradient(135deg, #fff1f3 0%, #fff8f0 100%);
    color: #b91c1c;
    border: 1px solid #fca5a5;
}
.fchip-ilce:hover {
    background: linear-gradient(135deg, #ffe4e6 0%, #fff0e6 100%);
    box-shadow: 0 2px 8px rgba(220,38,38,0.18);
}
.fchip-ilce.active {
    background: linear-gradient(135deg, #b91c1c, #dc2626);
    color: #ffffff;
    border-color: transparent;
    box-shadow: 0 3px 10px rgba(185,28,28,0.25);
}
.fchip-yeni {
    background: #16a34a;
    color: white;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 750;
    padding: 1px 6px;
    margin-left: 3px;
}
.fchip-ekle {
    background: transparent;
    color: #94a3b8;
    border: 1px dashed #dce4ee;
    font-weight: 600;
}
.fchip-ekle:hover {
    border-color: #b91c1c;
    color: #b91c1c;
}



/* ── KART LOKASYON ──────────────────────────────────── */
.kart-lokasyon {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 2px;
    display: block;
}
.kart-kriter {
    font-size: 11.5px;
    font-style: italic;
    color: #94a3b8;
    line-height: 1.45;
    margin-bottom: 6px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

/* ── YENİ KART SİSTEMİ ───────────────────────────── */
.nkart {
    background: var(--color-background-primary, #fff);
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 280px;
    transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
    margin-bottom: 0;
    box-shadow: 0 1px 4px rgba(15,23,42,0.06);
}
.nkart:hover {
    border-color: #93b4d0;
    box-shadow: 0 6px 20px rgba(15,23,42,0.10);
    transform: translateY(-2px);
}
.nkart-topbar { height: 4px; width: 100%; }
.nkart-body { padding: 14px 16px 10px; flex: 1; display: flex; flex-direction: column; gap: 7px; }
.nkart-district { font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; }
.nkart-title { font-size: 13.5px; font-weight: 800; color: #0F172A; line-height: 1.45; margin: 0; }
.nkart-desc { font-size: 11px; color: #64748B; line-height: 1.55; flex: 1;
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.nkart-meta { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
.nkart-price { font-size: 14px; font-weight: 700; color: #0F172A; }
.nkart-price-empty { font-size: 11px; color: #94a3b8; font-style: italic; }
.nkart-date { font-size: 10px; color: #94a3b8; }
.nkart-footer {
    border-top: 1px solid #edf2f7;
    padding: 10px 16px;
    background: #f8fafc;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
}

/* Not: stColumn için global height:100% kaldırıldı.
   Bu kural toolbar/filtre butonlarının üstüne görünmez katman bindirip
   Tümü ve Filtreler gibi butonların tıklanmasını engelleyebiliyordu. */
.nkart-avatar {
    width: 22px; height: 22px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 9px; font-weight: 700; flex-shrink: 0;
}
.nkart-agent { font-size: 11px; color: #64748B; display: flex; align-items: center; gap: 5px; }
.nkart-actions { display: flex; align-items: center; gap: 5px; }
.nkart-icon-btn {
    width: 28px; height: 28px; border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; color: #64748B;
    border: 0.5px solid #dce4ee; background: #fff;
    font-size: 13px; transition: all 0.12s;
}
.nkart-icon-btn:hover { background: #f1f5f9; border-color: #b0c4d8; }
.nkart-detay-btn {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 5px 12px; border-radius: 6px;
    font-size: 12px; font-weight: 600; cursor: pointer;
    background: #1E3A5F; color: #fff; border: none;
    transition: background 0.12s;
}
.nkart-detay-btn:hover { background: #2d5a8e; }
.nbadge {
    display: inline-flex; align-items: center; gap: 3px;
    font-size: 10.5px; font-weight: 500; padding: 2px 7px; border-radius: 20px;
}
.nbadge-yeni { background: #EAF3DE; color: #3B6D11; }
.nbadge-goruldu { background: #f1f5f9; color: #94a3b8; }
.nbadge-oda { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }
.dot-live { width: 5px; height: 5px; border-radius: 50%; background: #639922; display: inline-block; }

/* ── OKUNDU / OKUNMADI ──────────────────────────────── */
.kart-serit {
    height: 3px;
    border-radius: 0 0 3px 3px;
    margin: 8px -14px -10px -14px;
}
.kart-serit-yeni   { background: linear-gradient(90deg, #16a34a, #4ade80); }
.kart-serit-normal { background: linear-gradient(90deg, #F4B740, #fbbf24); }
.kart-serit-okundu { background: #e2e8f0; }

.kart-yeni-rozet {
    position: absolute;
    top: 8px;
    right: 8px;
    background: #16a34a;
    color: white;
    font-size: 10px;
    font-weight: 750;
    padding: 2px 8px;
    border-radius: 999px;
    letter-spacing: 0.04em;
}
.kart-wrapper {
    position: relative;
}

/* ── MOCKUP TABLO GÖRÜNÜMÜ ─────────────────────────────────────────── */
.zt-table-wrap {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    overflow: hidden;
    margin-top: 4px;
}
.zt-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.zt-table thead tr { background: #f8fafc; }
.zt-table th {
    padding: 9px 12px;
    text-align: left;
    font-size: 10.5px;
    font-weight: 600;
    color: #94a3b8;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    border-bottom: 1px solid #e2e8f0;
    white-space: nowrap;
}
.zt-table td {
    padding: 10px 12px;
    font-size: 12px;
    color: #1e293b;
    border-bottom: 0.5px solid #f1f5f9;
    vertical-align: middle;
}
.zt-table tr:last-child td { border-bottom: none; }
.zt-table tr:hover td { background: rgba(30,58,95,0.02); }
.zt-col-baslik { width: 32%; }
.zt-col-ilce   { width: 12%; }
.zt-col-tip    { width: 9%; }
.zt-col-butce  { width: 18%; }
.zt-col-danisan{ width: 16%; }
.zt-col-tarih  { width: 10%; }
.zt-col-aksiyon{ width: 3%; }
.zt-row-title { font-size: 12px; font-weight: 600; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; display: block; }
.zt-row-desc  { font-size: 11px; color: #64748b; margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; }
.zt-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; flex-shrink: 0; margin-right: 6px; vertical-align: middle; }
.zt-dot-yeni  { background: #22c55e; }
.zt-dot-aktif { background: #3b82f6; }
.zt-dot-bekle { background: #f59e0b; }
.zt-ilce-tag {
    display: inline-block; padding: 2px 7px; border-radius: 4px;
    font-size: 10px; font-weight: 600; white-space: nowrap;
}
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
/* Gizli buton / pointer-events:none kuralı kaldırıldı.
   Tablo altındaki aksiyon butonlarını ve üst toolbar tıklamalarını bozabiliyordu. */

</style>
""", unsafe_allow_html=True)

# ── SIDEBAR — CSS'den hemen sonra çağır (collapsed sorunu önler) ─────────────
from core.auth import oturum_kontrol

if not oturum_kontrol():
    st.switch_page("pages/giris.py")

render_navbar(
    user_role=st.session_state.get("user_role", "danisan"),
    user_name=st.session_state.get("user_name", ""),
    user_initials=st.session_state.get("user_initials", ""),
)


# ── YARDIMCI FONKSİYONLAR ───────────────────────────────────────────────────
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


# ── Standart badge renk paleti ───────────────────────────────────────────────
BADGE_PALETTE = {
    "Satılık": ("#FCEBEB", "#A32D2D", "#f5c0c0"),
    "Kiralık": ("#FAEEDA", "#854F0B", "#f0d0a0"),
    "Konut":   ("#f1f5f9", "#475569", "#e2e8f0"),
    "İşyeri":  ("#f1f5f9", "#475569", "#e2e8f0"),
    "Arsa":    ("#f1f5f9", "#475569", "#e2e8f0"),
}

def etiket_html(etiket):
    """Standart badge — liste ve kart görünümünde aynı stil."""
    if not etiket or etiket in ("Belirsiz", "Belirtilmemiş"):
        return ""
    cfg = BADGE_PALETTE.get(etiket, ("#f1f5f9", "#475569", "#e2e8f0"))
    bg, fg, border = cfg
    return (
        f'<span style="background:{bg};color:{fg};border:1px solid {border};'
        f'padding:2px 8px;border-radius:20px;font-size:10.5px;font-weight:600;'
        f'margin-right:4px;display:inline-block;">{etiket}</span>'
    )


def yeni_badge_html(yeni_sayi):
    if yeni_sayi and yeni_sayi > 0:
        return f'<span class="new-badge">{yeni_sayi} yeni</span>'
    return ""


def nbadge(etiket, cls=None):
    """Kart görünümü badge — BADGE_PALETTE ile aynı standart."""
    if not etiket or etiket in ("Belirsiz","Belirtilmemiş"):
        return ""
    cfg = BADGE_PALETTE.get(etiket, ("#f1f5f9", "#475569", "#e2e8f0"))
    bg, fg, border = cfg
    # cls ile override mümkün (oda sayısı için)
    if cls == "nbadge-oda":
        bg, fg, border = "#f1f5f9", "#475569", "#e2e8f0"
    return (
        f'<span style="background:{bg};color:{fg};border:1px solid {border};'
        f'padding:2px 7px;border-radius:20px;font-size:10.5px;font-weight:600;'
        f'margin-right:3px;display:inline-block;">{etiket}</span>'
    )


def avatar_html(isim, aks_r):
    """Danışman baş harf avatarı."""
    if not isim:
        return '<div class="nkart-avatar" style="background:#f1f5f9;color:#94a3b8;">?</div>'
    harfler = "".join(p[0].upper() for p in isim.split()[:2] if p)
    return (
        f'<div class="nkart-avatar" style="background:{aks_r["bg"]};color:{aks_r["text"]};">'
        f'{harfler}</div>'
    )


def nkart_html(v, rozet_html=""):
    """
    Hibrit kart — geniş, 2 sütunlu grid için optimize.
    Tasarım: üst badge satırı → başlık → açıklama → fiyat → alt meta (danışman · tarih · kaynak)
    """
    ui_k  = build_talep_ui_model(v)
    isim  = isim_ayikla(v.get("talep_eden_danisan", ""))
    butce = v.get("max_butce", "")
    mulk  = v.get("mulk_tipi", "") or ""
    islem = v.get("islem_tipi", "") or ""
    oda   = v.get("oda_sayisi_m2", "") or ""
    ilceler_list = v.get("ilceler") or []
    _aks_k  = aks_renk_bul(ilceler_list)

    _td = tarih_parse(en_iyi_tarih(v))
    if _td:
        _hast = hasattr(_td, "hour") and (_td.hour != 0 or _td.minute != 0)
        _tarih_k = _td.strftime("%d.%m.%Y %H:%M") if _hast else _td.strftime("%d.%m.%Y")
    else:
        _tarih_k = ""

    # İşlem badge
    if "iralık" in islem:   _ibg, _ic, _ilbl = "#f0fdf4", "#166534", "Kiralık"
    elif "atılık" in islem: _ibg, _ic, _ilbl = "#fef2f2", "#991b1b", "Satılık"
    else:                   _ibg, _ic, _ilbl = "#f8fafc", "#64748b", islem or ""

    # Kaynak chip
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

    # Danışman initials
    _initials = "".join(w[0].upper() for w in isim.split()[:2]) if isim else "?"

    # Badge satırı: İlçe + İşlem + Mülk + Rozet
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
        f'padding:18px 20px 14px;box-shadow:0 2px 10px rgba(15,23,42,0.06);'
        f'transition:box-shadow 0.15s;margin-bottom:0;">'
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


def build_talep_ui_model(v):
    """
    Kayıt verisinden normalize talep UI modeli döndürür.
    Başlık: müşteri talebi dili (portföy ilanı gibi değil).
    """
    islem = (v.get("islem_tipi") or "").strip()
    mulk  = (v.get("mulk_tipi") or "").strip()
    oda   = (v.get("oda_sayisi_m2") or "").strip()
    butce = (v.get("max_butce") or "").strip()
    ozel  = (v.get("ozel_kriterler") or "").strip()
    ozet_ham = (v.get("ozet") or v.get("mail_konusu") or "").strip()
    mahalle  = (v.get("mahalle") or "").strip()
    bolge    = (v.get("bolge") or v.get("bolge_mahalle") or "").strip()
    ilceler  = [i for i in (v.get("ilceler") or []) if i and i != "Diğer Bölge"]

    # ── BAŞLIK ──────────────────────────────────────────────────────
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

    # ── LOKASYON: sadece ana ilçeler ─────────────────────────────────
    lokasyon_ozet = " · ".join(ilceler[:3]) if ilceler else ""

    # ── KRİTER NOTU: mahalle + bölge + özel kriterler/özet ───────────
    kriter_parts = []
    if mahalle:
        kriter_parts.append(mahalle)
    if bolge and bolge != mahalle:
        kriter_parts.append(bolge)
    if ozel:
        kriter_parts.append(ozel[:100])
    elif ozet_ham and ozet_ham != baslik and not kriter_parts:
        kriter_parts.append(ozet_ham[:100])
    kriter_ozet = " · ".join(kriter_parts)

    # ── KISA ÖZET (eski uyumluluk) ────────────────────────────────────
    kisa_parts = []
    if butce:    kisa_parts.append(f"Bütçe: {butce}")
    if ozel:     kisa_parts.append(ozel[:80])
    elif ozet_ham and ozet_ham != baslik:
        kisa_parts.append(ozet_ham[:80])
    kisa_ozet = " · ".join(kisa_parts)

    isim = isim_ayikla(v.get("talep_eden_danisan", ""))

    return {
        "baslik":        baslik,
        "lokasyon_ozet": lokasyon_ozet,
        "kriter_ozet":   kriter_ozet,
        "kisa_ozet":     kisa_ozet,
        "meta":          isim,
    }


def tarih_parse(s):
    """Tarih string'ini datetime olarak döndürür (saat dahil).
    ISO 8601 (mikrosaniye/timezone/Z dahil) ve RFC2822 (mail) formatlarını destekler.
    DÜZELTME: Eski strptime[:len(fmt)] deseni format string'inin karakter sayısını
    (örn. "%Y-%m-%d" -> 8) tarih uzunluğu sanıyordu, bu yüzden hiçbir gerçek ISO
    tarihi (10+ karakter) doğru ayrıştırılamıyordu."""
    if not s:
        return None
    if isinstance(s, datetime):
        return s
    text = str(s).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        pass
    try:
        return parsedate_to_datetime(text)
    except (TypeError, ValueError, OverflowError):
        return None


def tarih_parse_date(s):
    """Geriye uyumluluk için sadece date döndürür."""
    dt = tarih_parse(s)
    return dt.date() if dt else None


def en_iyi_tarih(v):
    """Mail tarihi varsa onu, yoksa kayıt/oluşturma tarihini döndürür."""
    return (
        v.get("mail_tarihi")
        or v.get("kayit_tarihi")
        or v.get("olusturma_tarihi")
        or ""
    )


def tarih_renk_bilgisi(gun):
    """
    Gün sayısına göre (fg_color, bg_color, dot_color) döndürür.
      0-8   gün → yeşil
      8-30  gün → sarı
      30-90 gün → turuncu
      90-180 gün → kırmızı
      180+  gün → gri
    """
    if gun <= 7:
        return "#166534", "#dcfce7", "#16a34a"    # yeşil
    elif gun <= 30:
        return "#713f12", "#fef9c3", "#ca8a04"    # sarı
    elif gun <= 90:
        return "#7c2d12", "#ffedd5", "#ea580c"    # turuncu
    elif gun <= 180:
        return "#7f1d1d", "#fee2e2", "#dc2626"    # kırmızı
    else:
        return "#374151", "#f3f4f6", "#9ca3af"    # gri


def tarih_gun_farki(s):
    d = tarih_parse(s)
    if not d:
        return 9999
    _d = d.date() if hasattr(d, 'date') and callable(d.date) else d
    return (date.today() - _d).days


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


def ilce_istatistik(ilce, kayitlar):
    k = [v for v in kayitlar if ilce in (v.get("ilceler") or [])]
    yeni = [v for v in k if tarih_gun_farki(en_iyi_tarih(v)) <= 7]
    return len(k), len(yeni)


def siralama_uygula(liste, siralama):
    if siralama == "Tarih ↓":
        return sorted(liste, key=lambda v: tarih_gun_farki(en_iyi_tarih(v)))
    elif siralama == "Tarih ↑":
        return sorted(liste, key=lambda v: tarih_gun_farki(en_iyi_tarih(v)), reverse=True)
    elif siralama == "İlçe A→Z":
        return sorted(liste, key=lambda v: (ilce_grubu(v) or "").lower())
    elif siralama == "İlçe Z→A":
        return sorted(liste, key=lambda v: (ilce_grubu(v) or "").lower(), reverse=True)
    elif siralama == "Bütçe ↑":
        return sorted(liste, key=lambda v: fiyat_sayisal(v.get("max_butce", "")))
    elif siralama == "Bütçe ↓":
        return sorted(liste, key=lambda v: fiyat_sayisal(v.get("max_butce", "")), reverse=True)
    return liste


# ── İzmir İlçeleri UX yardımcıları ─────────────────────────────────────────
IZMIR_AKS_MAP = {
    "Yarımada": ["Güzelbahçe", "Narlıdere", "Balçova", "Urla", "Çeşme", "Karaburun", "Seferihisar"],
    "Kuzey Aksı": ["Karşıyaka", "Çiğli", "Menemen", "Foça", "Aliağa", "Dikili", "Bergama", "Kınık"],
    "Merkez Aks": ["Konak", "Bayraklı", "Bornova", "Buca", "Karabağlar", "Gaziemir"],
    "Güney Aksı": ["Menderes", "Torbalı", "Selçuk", "Tire", "Ödemiş", "Bayındır", "Kiraz", "Beydağ"],
}

# Aks renk paleti — kart şeridi, lokasyon metni, badge için
AKS_RENK = {
    "Yarımada":  {"bar": "#D85A30", "text": "#993C1D", "bg": "#FAECE7", "light": "#fdf2ef"},
    "Kuzey Aksı":{"bar": "#378ADD", "text": "#185FA5", "bg": "#E6F1FB", "light": "#eff6ff"},
    "Merkez Aks":{"bar": "#1D9E75", "text": "#0F6E56", "bg": "#E1F5EE", "light": "#f0fdf9"},
    "Güney Aksı":{"bar": "#8B5CF6", "text": "#5B21B6", "bg": "#EDE9FE", "light": "#f5f3ff"},
    "Diğer":     {"bar": "#94a3b8", "text": "#475569", "bg": "#f1f5f9", "light": "#f8fafc"},
}

def aks_renk_bul(ilce_listesi):
    """İlçe listesinden aks renklerini döndürür. Multi-ilçe için ilk eşleşen aks."""
    if not ilce_listesi:
        return AKS_RENK["Diğer"]
    for ilce in ilce_listesi:
        for aks, ilceler in IZMIR_AKS_MAP.items():
            if ilce in ilceler:
                return AKS_RENK[aks]
    return AKS_RENK["Diğer"]

def aks_bar_gradient(ilce_listesi):
    """Multi-aks kartlarda gradient bar oluşturur."""
    if not ilce_listesi:
        return AKS_RENK["Diğer"]["bar"]
    akslar_bulundu = []
    for ilce in ilce_listesi:
        for aks, ilceler in IZMIR_AKS_MAP.items():
            if ilce in ilceler and aks not in akslar_bulundu:
                akslar_bulundu.append(aks)
    if len(akslar_bulundu) == 0:
        return AKS_RENK["Diğer"]["bar"]
    if len(akslar_bulundu) == 1:
        return AKS_RENK[akslar_bulundu[0]]["bar"]
    # Multi-aks: gradient
    renkler = [AKS_RENK[a]["bar"] for a in akslar_bulundu[:3]]
    pct = 100 // len(renkler)
    stops = []
    for i, r in enumerate(renkler):
        stops.append(f"{r} {i*pct}%")
        stops.append(f"{r} {(i+1)*pct}%")
    return f"linear-gradient(90deg, {', '.join(stops)})"


def aks_adi_bul(ilce):
    for aks, ilceler in IZMIR_AKS_MAP.items():
        if ilce in ilceler:
            return aks
    return "Diğer İzmir"


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
    st.markdown(
        """
        <div style="font-size:11px;font-weight:800;color:var(--primary);letter-spacing:.08em;text-transform:uppercase;margin:10px 0 8px 0;">
            İzmir İlçeleri
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
                    f"<div style='font-size:13px;font-weight:800;color:var(--text);margin-bottom:8px;border-bottom:1px solid var(--border);padding-bottom:8px;'>{aks}</div>",
                    unsafe_allow_html=True,
                )
                for ilce in ilceler:
                    toplam, yeni = ilce_kayit_sayisi(kayitlar, ilce)
                    if toplam <= 0:
                        continue
                    yeni_label = f" · {yeni} yeni" if yeni > 0 else ""
                    aktif = secili_ilce == ilce
                    label = f"{ilce} · {toplam}{yeni_label}"
                    if st.button(
                        label,
                        key=f"{key_prefix}_aks_{safe_key(ilce)}",
                        use_container_width=True,
                        type="primary" if aktif else "secondary",
                    ):
                        st.session_state[state_key] = None if aktif else ilce
                        st.rerun()

    if secili_ilce:
        if st.button(f"✕ Temizle: {secili_ilce}", key=f"{key_prefix}_aks_clear", use_container_width=True, type="secondary"):
            st.session_state[state_key] = None
            st.rerun()


def izmir_kaydi_mi(v):
    return il_grubu(v) == "İzmir"


def diger_il_kaydi_mi(v):
    il = il_grubu(v)
    return bool(il) and il != "İzmir"


def favori_kaydi_mi(v, fav_ilceler):
    return any(i in fav_ilceler for i in (v.get("ilceler") or []))


def favori_guncelle(kid, mevcut):
    try:
        get_client().table("alici_talepleri").update({"favori": not mevcut}).eq("id", kid).execute()
        verileri_yukle.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")


def not_kaydet(kid, metin):
    try:
        get_client().table("alici_talepleri").update({"not_alani": metin}).eq("id", kid).execute()
        verileri_yukle.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")


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
            get_client()
            .table("kullanici_tercihleri")
            .select("favori_ilceler")
            .eq("kullanici_ad", "varsayilan")
            .execute()
        )
        if r.data:
            return r.data[0].get("favori_ilceler") or []
        return []
    except:
        return []


def favori_ilce_guncelle(ilceler):
    try:
        (
            get_client()
            .table("kullanici_tercihleri")
            .update({"favori_ilceler": ilceler})
            .eq("kullanici_ad", "varsayilan")
            .execute()
        )
        favori_ilceleri_cek.clear()
    except Exception as e:
        st.error(f"Hata: {e}")


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
            # "kaynak='startkey_mail' VEYA kaynak NULL" — iki ayrı sorgu,
            # ikisi de sayfalanarak birleştiriliyor.
            def _b1():
                return (
                    get_client().table("alici_talepleri").select("*")
                    .eq("kategori", "alici_talebi")
                    .order("olusturma_tarihi", desc=True)
                    .eq("kaynak", "startkey_mail")
                )

            def _b2():
                return (
                    get_client().table("alici_talepleri").select("*")
                    .eq("kategori", "alici_talebi")
                    .order("olusturma_tarihi", desc=True)
                    .is_("kaynak", "null")
                )
            return _sayfali_cek(_b1) + _sayfali_cek(_b2)

        def _builder():
            q = (
                get_client()
                .table("alici_talepleri")
                .select("*")
                .eq("kategori", "alici_talebi")
                .order("olusturma_tarihi", desc=True)
            )
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
def gd_listesi_cek():
    try:
        r = get_client().table("alici_talepleri").select("talep_eden_danisan").execute()
        isimler = sorted(set(
            isim_ayikla(v.get("talep_eden_danisan",""))
            for v in r.data if v.get("talep_eden_danisan","")
        ))
        return [i for i in isimler if i]
    except Exception:
        return []


# ── AI Parse & Manuel Kayıt ──────────────────────────────────────────────

ILLER = ["İzmir", "Aydın", "Manisa", "Balıkesir", "Muğla", "İstanbul", "Ankara", "Diğer"]

def ai_parse_talep(metin: str) -> dict:
    import requests, json
    prompt = f"""Aşağıdaki gayrimenkul talep açıklamasını analiz et ve JSON olarak döndür.
Sadece JSON döndür, başka hiçbir şey yazma.

Talep:
{metin}

JSON formatı:
{{
  "il": "İzmir",
  "ilce": "birincil ilçe veya boş",
  "ilceler": ["ilçe1", "ilçe2"],
  "mulk_tipi": "Konut/İşyeri/Arsa/Belirsiz",
  "islem_tipi": "Satılık/Kiralık/Belirsiz",
  "oda_sayisi_m2": "3+1 veya 120 m² gibi",
  "max_butce": "rakam ve para birimi",
  "mahalle": "mahalle/semt bilgisi",
  "ozel_kriterler": "özel istekler, notlar",
  "ozet": "talebi özetleyen kısa cümle (şehir adı yazma, sadece talep özeti)"
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


def talep_kaydet(veri: dict):
    try:
        get_client().table("alici_talepleri").insert(veri).execute()
        verileri_yukle.clear()
        return True
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")
        return False


def yeni_talep_modal(kaynak: str, kaynak_etiket: str, ilce_sec: list):
    modal_key = f"yeni_talep_{kaynak}"
    if not st.session_state.get(modal_key, False):
        if st.button(f"+ Yeni Talep Ekle", key=f"btn_{modal_key}"):
            st.session_state[modal_key] = True
            st.rerun()
        return

    st.markdown(
        '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:14px;margin-bottom:10px;">',
        unsafe_allow_html=True
    )
    st.markdown(f"**Yeni Talep — {kaynak_etiket}**")

    gd_list = gd_listesi_cek()
    gc1, gc2 = st.columns([2,1])
    with gc1:
        gd_sec = st.selectbox("Danışman", ["Seç..."] + gd_list + ["Diğer (manuel gir)"],
            key=f"gd_sec_{kaynak}")
    with gc2:
        if gd_sec == "Diğer (manuel gir)":
            gd_manuel = st.text_input("Danışman adı", key=f"gd_manuel_{kaynak}")
        else:
            gd_manuel = ""
    gd_ad = gd_manuel if gd_sec == "Diğer (manuel gir)" else (gd_sec if gd_sec != "Seç..." else "")

    yontem = st.radio("Giriş yöntemi", ["AI Parse", "Form"],
        horizontal=True, key=f"yontem_{kaynak}")

    parse_sonuc = st.session_state.get(f"parse_{kaynak}", {})

    if yontem == "AI Parse":
        metin = st.text_area(
            "Talep açıklaması",
            placeholder="Örn: Müşterim Bornova veya Karşıyaka'da 3+1 kiralık daire arıyor, max 25.000 TL...",
            height=80, key=f"metin_{kaynak}"
        )
        pa, pb = st.columns([1,5])
        with pa:
            if st.button("AI ile Doldur", key=f"parse_btn_{kaynak}", type="primary"):
                if metin.strip():
                    with st.spinner("Parse ediliyor..."):
                        sonuc = ai_parse_talep(metin)
                        mahalle_metin = sonuc.get("mahalle","") or metin
                        lookup = mahalle_ile_ilce_bul(mahalle_metin)
                        if not lookup and mahalle_metin != metin:
                            lookup = mahalle_ile_ilce_bul(metin)
                        if lookup:
                            sonuc["il"] = lookup.get("il","")
                            sonuc["ilce"] = lookup.get("ilce","")
                            if not sonuc.get("mahalle"):
                                sonuc["mahalle"] = lookup.get("mahalle","")
                        st.session_state[f"parse_{kaynak}"] = sonuc
                        st.rerun()
                else:
                    st.warning("Açıklama yazın.")

        if parse_sonuc:
            st.markdown("**Önizleme — düzenleyebilirsiniz:**")
    else:
        parse_sonuc = {}

    if yontem == "Form" or parse_sonuc:
        f1, f2, f3 = st.columns(3)
        with f1:
            ozet = st.text_input("Özet", value=parse_sonuc.get("ozet",""), key=f"f_ozet_{kaynak}")
            il = st.selectbox("İl", ILLER,
                index=ILLER.index(parse_sonuc.get("il","İzmir")) if parse_sonuc.get("il","") in ILLER else 0,
                key=f"f_il_{kaynak}")
            ilce_raw = parse_sonuc.get("ilce","")
            ilce_idx = (["İzmir Genel"]+ilce_sec).index(ilce_raw) if ilce_raw in (["İzmir Genel"]+ilce_sec) else 0
            ilce_sec2 = st.selectbox("Birincil İlçe", ["İzmir Genel"]+ilce_sec,
                index=ilce_idx, key=f"f_ilce_{kaynak}")
            ilce_val = "" if ilce_sec2 == "İzmir Genel" else ilce_sec2
        with f2:
            mulk = st.selectbox("Mülk Tipi", ["Konut","İşyeri","Arsa","Belirsiz"],
                index=["Konut","İşyeri","Arsa","Belirsiz"].index(parse_sonuc.get("mulk_tipi","Belirsiz"))
                if parse_sonuc.get("mulk_tipi","") in ["Konut","İşyeri","Arsa","Belirsiz"] else 3,
                key=f"f_mulk_{kaynak}")
            islem = st.selectbox("İşlem Tipi", ["Satılık","Kiralık","Belirsiz"],
                index=["Satılık","Kiralık","Belirsiz"].index(parse_sonuc.get("islem_tipi","Belirsiz"))
                if parse_sonuc.get("islem_tipi","") in ["Satılık","Kiralık","Belirsiz"] else 2,
                key=f"f_islem_{kaynak}")
            butce = st.text_input("Bütçe", value=parse_sonuc.get("max_butce",""), key=f"f_butce_{kaynak}")
        with f3:
            oda = st.text_input("Oda/M²", value=parse_sonuc.get("oda_sayisi_m2",""), key=f"f_oda_{kaynak}")
            mahalle = st.text_input("Mahalle", value=parse_sonuc.get("mahalle",""), key=f"f_mahalle_{kaynak}")
            kriterler = st.text_area("Özel Kriterler", value=parse_sonuc.get("ozel_kriterler",""),
                height=80, key=f"f_kriter_{kaynak}")

        ilceler_default = [i for i in (parse_sonuc.get("ilceler") or []) if i in ilce_sec]
        ilceler = st.multiselect("Tüm İlçeler", ilce_sec, default=ilceler_default, key=f"f_ilceler_{kaynak}")

        ka, kb = st.columns([1,5])
        with ka:
            if st.button("Kaydet", key=f"kaydet_{kaynak}", type="primary"):
                if not gd_ad:
                    st.warning("Danışman seçin.")
                else:
                    veri = {
                        "talep_eden_danisan": gd_ad,
                        "kategori": "alici_talebi",
                        "kaynak": kaynak,
                        "giren_gd": gd_ad,
                        "il": il,
                        "ilce": ilce_val,
                        "ilceler": ilceler if ilceler else ([ilce_val] if ilce_val else []),
                        "mulk_tipi": mulk,
                        "islem_tipi": islem,
                        "max_butce": butce,
                        "oda_sayisi_m2": oda,
                        "mahalle": mahalle,
                        "ozel_kriterler": kriterler,
                        "ozet": ozet,
                        "olusturma_tarihi": datetime.now().isoformat(),
                    }
                    if talep_kaydet(veri):
                        st.session_state.pop(f"parse_{kaynak}", None)
                        st.session_state[modal_key] = False
                        st.success("Kaydedildi!")
                        st.rerun()

        with kb:
            if st.button("İptal", key=f"iptal_{kaynak}"):
                st.session_state.pop(f"parse_{kaynak}", None)
                st.session_state[modal_key] = False
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def mahalle_lookup_cek():
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
    if not metin:
        return {}
    lookup = mahalle_lookup_cek()
    metin_lower = metin.lower()
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
    st.session_state["ft_ara"] = ""
    st.session_state["ft_il"] = "Tümü"
    st.session_state["ft_ilce"] = "Tümü"
    st.session_state["ft_danisan"] = "Tümü"
    st.session_state["ft_mulk"] = "Tümü"
    st.session_state["ft_siralama"] = "Tarih ↓"
    st.session_state["ft_hizli"] = "Son 7 gün"
    st.session_state["talep_donem"] = "Son 7 Gün"
    st.session_state["talep_ilce_kapsam"] = "Tüm İlçeler"
    st.session_state["ft_aralik"] = False
    st.session_state["ft_fav"] = False
    st.session_state["ft_gizli"] = False
    st.session_state["fav_secili_ilce"] = None
    st.session_state["aktif_talep_workspace"] = "Tümü"
    st.session_state.pop("ft_bas", None)
    st.session_state.pop("ft_bit", None)
    st.session_state["ft_butce_alt"] = 0
    st.session_state["ft_butce_ust"] = 0
    st.session_state["ft_oda"] = "Tümü"
    st.session_state["ft_bina_yasi"] = "Tümü"
    st.session_state["ft_kat"] = "Tümü"
    st.session_state["ft_site_ici"] = "Tümü"
    st.session_state["ft_esyali"] = "Tümü"
    st.session_state["ft_kullanim"] = "Tümü"
    st.session_state["ft_gun_min"] = 0
    st.session_state["ft_gun_max"] = 0


def kayit_guncelle(kid, data):
    try:
        get_client().table("alici_talepleri").update(data).eq("id", kid).execute()
        st.session_state.pop(f"duzen_{kid}", None)
        st.session_state[f"guncellendi_{kid}"] = True
        verileri_yukle.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")


def belirtilmemise_tasi(kid):
    try:
        get_client().table("alici_talepleri").update(
            {"il": "", "ilce": "", "ilceler": [], "mahalle": "", "bolge": ""}
        ).eq("id", kid).execute()
        st.session_state[f"guncellendi_{kid}"] = True
        verileri_yukle.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")


def kayit_sil(kid):
    try:
        get_client().table("alici_talepleri").delete().eq("id", kid).execute()
        verileri_yukle.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Silme hatası: {e}")


def kayit_gizle(kid):
    try:
        get_client().table("alici_talepleri").update({"gizli": True}).eq("id", kid).execute()
        verileri_yukle.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")


def not_kaydet_fn(kid, metin):
    try:
        get_client().table("alici_talepleri").update({"not_alani": metin}).eq("id", kid).execute()
        verileri_yukle.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")


def duzenleme_formu(v, ilce_sec):
    kid = v.get("id")
    iller = ["İzmir", "Aydın", "Manisa", "Balıkesir", "Muğla", "Diğer"]
    ilce_sec_with_genel = ["İzmir Genel"] + ilce_sec

    c1, c2, c3 = st.columns(3)

    with c1:
        oz = st.text_input("Özet", value=v.get("ozet", "") or "", key=f"d_oz_{kid}")
        yi = st.selectbox(
            "İl",
            iller,
            index=iller.index(v.get("il", "")) if v.get("il", "") in iller else 0,
            key=f"d_il_{kid}"
        )
        mevcut_ilce = v.get("ilce", "") or ""
        ilce_idx = ilce_sec_with_genel.index(mevcut_ilce) if mevcut_ilce in ilce_sec_with_genel else 0
        yilce_sec = st.selectbox("Birincil İlçe", ilce_sec_with_genel, index=ilce_idx, key=f"d_ilce_{kid}")
        yilce = "" if yilce_sec == "İzmir Genel" else yilce_sec

    with c2:
        ym = st.selectbox(
            "Mülk",
            ["Konut", "İşyeri", "Arsa", "Belirsiz"],
            index=["Konut", "İşyeri", "Arsa", "Belirsiz"].index(v.get("mulk_tipi", "Belirsiz"))
            if v.get("mulk_tipi", "") in ["Konut", "İşyeri", "Arsa", "Belirsiz"] else 3,
            key=f"d_m_{kid}"
        )
        yis = st.selectbox(
            "İşlem",
            ["Satılık", "Kiralık", "Belirsiz"],
            index=["Satılık", "Kiralık", "Belirsiz"].index(v.get("islem_tipi", "Belirsiz"))
            if v.get("islem_tipi", "") in ["Satılık", "Kiralık", "Belirsiz"] else 2,
            key=f"d_is_{kid}"
        )
        ymh = st.text_input("Mahalle", value=v.get("mahalle", "") or "", key=f"d_mh_{kid}")

    with c3:
        yb = st.text_input(
            "Bölge/Konum",
            value=v.get("bolge", "") or v.get("bolge_mahalle", "") or "",
            key=f"d_b_{kid}"
        )
        mevcut = v.get("ilceler") or []
        yilceler = st.multiselect(
            "Tüm İlçeler",
            ilce_sec,
            default=[i for i in mevcut if i in ilce_sec],
            key=f"d_ilceler_{kid}"
        )

    ca, cb = st.columns([1, 4])

    with ca:
        if st.button("💾 Kaydet", key=f"d_kyd_{kid}", type="primary"):
            kayit_guncelle(kid, {
                "ozet": oz,
                "il": yi,
                "ilce": yilce,
                "ilceler": yilceler if yilceler else ([yilce] if yilce else []),
                "mulk_tipi": ym,
                "islem_tipi": yis,
                "mahalle": ymh,
                "bolge": yb,
                "bolge_mahalle": f"{ymh} {yb}".strip()
            })

    with cb:
        if st.button("İptal", key=f"d_ipt_{kid}"):
            st.session_state.pop(f"duzen_{kid}", None)
            st.rerun()



def tablo_satirlari_html(kayitlar):
    """Mockup tablo görünümü için HTML satırları üretir."""
    satirlar = []
    for v in kayitlar:
        kid = v.get("id", "")
        ui = build_talep_ui_model(v)
        isim = isim_ayikla(v.get("talep_eden_danisan", ""))
        ilce = ilce_grubu(v) or "—"
        islem = v.get("islem_tipi", "") or ""
        mulk = v.get("mulk_tipi", "") or ""
        butce = v.get("max_butce", "") or "—"
        favori = v.get("favori", False)
        gun_farki = tarih_gun_farki(en_iyi_tarih(v))
        yeni = gun_farki <= 7
        okundu = kid in st.session_state.get("goruldu_ids", set())

        # Tarih
        tarih_d = tarih_parse(en_iyi_tarih(v))
        if tarih_d:
            _has_t = hasattr(tarih_d, "hour") and (tarih_d.hour != 0 or tarih_d.minute != 0)
            tarih_str = tarih_d.strftime("%d.%m<br>%H:%M") if _has_t else tarih_d.strftime("%d.%m.%Y")
        else:
            tarih_str = "—"

        # Durum dot
        if okundu:
            dot = '<span class="zt-dot" style="background:#cbd5e1;"></span>'
        elif yeni:
            dot = '<span class="zt-dot zt-dot-yeni"></span>'
        elif favori:
            dot = '<span class="zt-dot zt-dot-bekle"></span>'
        else:
            dot = '<span class="zt-dot zt-dot-aktif"></span>'

        # Başlık + açıklama
        baslik = ui.get("baslik", "") or "—"
        kriter = ui.get("kriter_ozet", "") or ""

        # İlçe tag rengi
        aks_r = aks_renk_bul([ilce] if ilce != "—" else [])
        ilce_html = (
            f'<span class="zt-ilce-tag" style="background:{aks_r["bg"]};color:{aks_r["text"]};">'
            f'{ilce}</span>'
        )

        # Tip tag
        if "iralık" in islem or "ираlik" in islem.lower():
            tip_cls = "zt-tip-kiralik"
            tip_lbl = "Kiralık"
        elif "atılık" in islem or "satilik" in islem.lower():
            tip_cls = "zt-tip-satilik"
            tip_lbl = "Satılık"
        else:
            tip_cls = "zt-tip-belirsiz"
            tip_lbl = islem or mulk or "—"

        # Avatar
        aks_dan = aks_renk_bul([isim[:2]] if isim else [])
        initials = "".join(w[0].upper() for w in isim.split()[:2]) if isim else "?"

        # Favori yıldız
        fav_html = "★" if favori else "☆"
        fav_cls = "zt-fav-star" if favori else ""

        satirlar.append(
            f'<tr>'
            f'<td class="zt-col-baslik">'
            f'<div style="display:flex;align-items:flex-start;gap:0;">'
            f'{dot}'
            f'<div style="min-width:0;">'
            f'<span class="zt-row-title">{baslik}</span>'
            + (f'<span class="zt-row-desc">{kriter}</span>' if kriter else "")
            + f'</div></div></td>'
            f'<td class="zt-col-ilce">{ilce_html}</td>'
            f'<td class="zt-col-tip"><span class="zt-ilce-tag {tip_cls}">{tip_lbl}</span></td>'
            f'<td class="zt-col-butce"><span class="zt-butce">{butce}</span></td>'
            f'<td class="zt-col-danisan">'
            f'<div class="zt-agent">'
            f'<span class="zt-avatar" style="background:{aks_r["bg"]};color:{aks_r["text"]};">{initials}</span>'
            f'<span class="zt-agent-name">{isim or "—"}</span>'
            f'</div></td>'
            f'<td class="zt-col-tarih"><span class="zt-tarih">{tarih_str}</span></td>'
            f'<td class="zt-col-aksiyon"><span class="{fav_cls}">{fav_html}</span></td>'
            f'</tr>'
        )
    return "".join(satirlar)


# ── P0 SAYFALAMA HELPER'LARI ──────────────────────────────────────────────────
# taleplerim.py'deki _page_slice()/_render_pagination_controls() deseninden
# esinlenilmiştir. Bu dosyaya özel, bağımsız bir kopyadır — ortak modül
# refactor'u bu görevin kapsamı dışında tutulmuştur.
#
# P0 HOTFIX: Sayfa numarası artık TEK kaynaktan yönetiliyor. Prev/Next ve
# selectbox, callback'ler aracılığıyla hem ana page key'ini hem de
# selectbox'ın kendi widget key'ini ({key}_select) birlikte günceller.
# Böylece rerun sonrası selectbox'ın eski değeri page state'ine geri yazamaz.

# Sayfa değişiminde/filtre değişiminde temizlenecek per-kayıt state prefix'leri.
# Sadece "artık görünmeyen" id'ler için bu prefix + id kombinasyonları silinir.
_TALEP_PAGE_CLEANUP_PREFIXES = ["duzen_", "more_open_", "tmore_open_"]


def _clear_stale_page_state(key, prefixes=_TALEP_PAGE_CLEANUP_PREFIXES):
    """Liste tamamen boşaldığı için _page_slice() hiç çağrılmadığında,
    bir önceki sayfada açık kalan duzen/more_open gibi per-id state'leri
    temizler ve prev_ids'i boş sete çeker (P0 hotfix — ek küçük düzeltme)."""
    prev_ids_key = f"{key}_prev_ids"
    eski_ids = st.session_state.get(prev_ids_key, set())
    for kid in eski_ids:
        for pfx in prefixes:
            st.session_state.pop(f"{pfx}{kid}", None)
    st.session_state[prev_ids_key] = set()


def _pagination_set_page(page_key, select_key, value):
    """Prev/Next butonlarının on_click callback'i — iki state'i birlikte günceller."""
    value = int(value)
    st.session_state[page_key] = value
    st.session_state[select_key] = value


def _pagination_select_changed(page_key, select_key):
    """Selectbox'ın on_change callback'i — ana page key'ini selectbox'a göre günceller."""
    st.session_state[page_key] = int(st.session_state[select_key])


def _page_slice(liste, key, per_page):
    """Verilen listeyi session_state'teki sayfa numarasına göre dilimler.
    Sayfa numarası geçersiz hale geldiyse (ör. filtre daraldı) 1'e çeker ve
    selectbox widget state'ini ({key}_select) de aynı değere senkronize eder.
    Ayrıca bir önceki render'da görünen ama artık görünmeyen kayıtların
    duzen/more_open gibi per-id state'lerini temizler (P0-5)."""
    select_key = f"{key}_select"
    total = len(liste)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = int(st.session_state.get(key, 1) or 1)
    if page < 1 or page > total_pages:
        page = 1
        st.session_state[key] = 1
    # P0 HOTFIX madde 5: clamp sonrası selectbox state'i de senkron olmalı.
    if st.session_state.get(select_key) != page:
        st.session_state[select_key] = page

    start = (page - 1) * per_page
    page_items = liste[start:start + per_page]

    prev_ids_key = f"{key}_prev_ids"
    yeni_ids = {str(v.get("id", "")) for v in page_items}
    eski_ids = st.session_state.get(prev_ids_key, set())
    if eski_ids != yeni_ids:
        for kid in (eski_ids - yeni_ids):
            for pfx in _TALEP_PAGE_CLEANUP_PREFIXES:
                st.session_state.pop(f"{pfx}{kid}", None)
        st.session_state[prev_ids_key] = yeni_ids

    return page_items, page, total_pages, start


def _render_pagination_controls(key, page, total_pages, total, start, per_page, label_suffix=""):
    select_key = f"{key}_select"
    if total_pages <= 1:
        if total:
            st.caption(f"Gösterilen: 1-{total} / {total} kayıt{label_suffix}")
        return

    options = list(range(1, total_pages + 1))
    # Selectbox oluşturulmadan önce state'i geçerli bir değere sabitle —
    # aksi halde total_pages daraldığında eski değer options dışında kalabilir.
    if st.session_state.get(select_key) not in options:
        st.session_state[select_key] = page

    p1, p2, p3, p4 = st.columns([.75, 1.35, .75, 5.2], gap="small")
    with p1:
        st.button(
            "‹ Önceki", key=f"{key}_prev", use_container_width=True, disabled=page <= 1,
            on_click=_pagination_set_page, args=(key, select_key, max(1, page - 1)),
        )
    with p2:
        st.selectbox(
            "Sayfa", options, key=select_key, label_visibility="collapsed",
            on_change=_pagination_select_changed, args=(key, select_key),
        )
    with p3:
        st.button(
            "Sonraki ›", key=f"{key}_next", use_container_width=True, disabled=page >= total_pages,
            on_click=_pagination_set_page, args=(key, select_key, min(total_pages, page + 1)),
        )
    with p4:
        st.caption(
            f"Gösterilen: {start + 1}-{min(start + per_page, total)} / {total} kayıt · "
            f"Sayfa {page}/{total_pages}{label_suffix}"
        )


# ── YENİ FİLTRE MİMARİSİ: İşlem Tipi / Dönem / İlçe Kapsamı ──────────────────
# Bu bölüm 2_Talep_Tablosu.py ve 3_Portfoy_Tablosu.py'de birebir aynıdır
# (ortak modül refactor'u bu görevin kapsamı dışında tutulmuştur).

ISLEM_SEKME_OPTIONS = ["Satılık", "Kiralık", "Tespit Edilmemiş"]
DONEM_OPTIONS = ["Son 7 Gün", "Son 30 Gün", "Son 60 Gün"]
ILCE_KAPSAM_OPTIONS = ["Tüm İlçeler", "Favori İlçeler"]


def _islem_tipi_norm(v):
    """islem_tipi alanını üç sabit değere normalize eder: Satılık / Kiralık /
    Tespit Edilmemiş. Türkçe karakter varyasyonlarına (satılık/satilik/SATILIK
    gibi) karşı dayanıklıdır."""
    ham = str(v.get("islem_tipi") or "").strip()
    if not ham:
        return "Tespit Edilmemiş"
    low = ham.lower().replace("ı", "i").replace("İ", "i")
    if "kirali" in low:
        return "Kiralık"
    if "satili" in low:
        return "Satılık"
    return "Tespit Edilmemiş"


def _islem_sekmesi_degistir(state_key, value):
    st.session_state[state_key] = value


def _render_islem_sekmesi(state_key, counts):
    """Satılık / Kiralık / Tespit Edilmemiş seçimi. st.segmented_control
    mevcutsa onu (format_func ile sayaç göstererek), değilse üç native
    st.button kullanır."""
    if state_key not in st.session_state or st.session_state[state_key] not in ISLEM_SEKME_OPTIONS:
        st.session_state[state_key] = "Satılık"

    if hasattr(st, "segmented_control"):
        widget_key = f"{state_key}_widget"
        if st.session_state.get(widget_key) not in ISLEM_SEKME_OPTIONS:
            st.session_state[widget_key] = st.session_state[state_key]
        secim = st.segmented_control(
            "İşlem Tipi", ISLEM_SEKME_OPTIONS, key=widget_key,
            format_func=lambda opt: f"{opt} · {counts.get(opt, 0)}",
            label_visibility="collapsed",
        )
        if secim is not None and secim != st.session_state[state_key]:
            st.session_state[state_key] = secim
    else:
        aktif = st.session_state[state_key]
        cols = st.columns(3)
        for col, opt in zip(cols, ISLEM_SEKME_OPTIONS):
            with col:
                label = f"{opt} · {counts.get(opt, 0)}"
                st.button(
                    label, key=f"{state_key}_btn_{safe_key(opt)}", use_container_width=True,
                    type="primary" if aktif == opt else "secondary",
                    on_click=_islem_sekmesi_degistir, args=(state_key, opt),
                )


def _donem_degistir(donem_key, value, hizli_key, aralik_key, bas_key, bit_key, gun_min_key, gun_max_key):
    """Dönem butonlarının on_click callback'i. Tek bir source of truth
    (donem_key) günceller ve eski/paralel tarih state'lerini (hızlı filtre,
    özel aralık, ilan günü min/max) çakışmayacak şekilde sıfırlar.
    NOT: Havuz sayfasında azami dönem 60 gündür — "Tüm Zamanlar" seçeneği
    bilinçli olarak kaldırıldı (60 günden eski kayıtlar yalnızca Arşiv
    Merkezi'nden erişilebilir)."""
    st.session_state[donem_key] = value
    st.session_state[aralik_key] = False
    st.session_state.pop(bas_key, None)
    st.session_state.pop(bit_key, None)
    st.session_state[gun_min_key] = 0
    st.session_state[gun_max_key] = 0
    if value == "Son 60 Gün":
        st.session_state[hizli_key] = "Son 60 gün"
    elif value == "Son 7 Gün":
        st.session_state[hizli_key] = "Son 7 gün"
    elif value == "Son 30 Gün":
        st.session_state[hizli_key] = "Son 30 gün"


def _render_donem_secimi(donem_key, counts, hizli_key, aralik_key, bas_key, bit_key, gun_min_key, gun_max_key):
    """Son 7 Gün / Son 30 Gün / Son 60 Gün seçimi. Callback tabanlı,
    manuel st.rerun() çağırmaz (on_click sonrası Streamlit otomatik rerun eder)."""
    if donem_key not in st.session_state:
        st.session_state[donem_key] = "Son 7 Gün"
    aktif = st.session_state[donem_key]
    cols = st.columns(3)
    for col, opt in zip(cols, DONEM_OPTIONS):
        with col:
            label = f"{opt} · {counts.get(opt, 0)}"
            st.button(
                label, key=f"{donem_key}_btn_{safe_key(opt)}", use_container_width=True,
                type="primary" if aktif == opt else "secondary",
                on_click=_donem_degistir,
                args=(donem_key, opt, hizli_key, aralik_key, bas_key, bit_key, gun_min_key, gun_max_key),
            )


def _ilce_kapsami_degistir(kapsam_key, value, fav_secili_key):
    st.session_state[kapsam_key] = value
    if value == "Tüm İlçeler":
        st.session_state[fav_secili_key] = None


def _render_ilce_kapsami(kapsam_key, fav_secili_key, counts):
    """Tüm İlçeler / Favori İlçeler kapsam seçimi. 'Tüm İlçeler' seçilince
    seçili favori ilçe otomatik temizlenir."""
    if kapsam_key not in st.session_state:
        st.session_state[kapsam_key] = "Tüm İlçeler"
    aktif = st.session_state[kapsam_key]
    cols = st.columns(2)
    for col, opt in zip(cols, ILCE_KAPSAM_OPTIONS):
        with col:
            label = f"{opt} · {counts.get(opt, 0)}"
            st.button(
                label, key=f"{kapsam_key}_btn_{safe_key(opt)}", use_container_width=True,
                type="primary" if aktif == opt else "secondary",
                on_click=_ilce_kapsami_degistir, args=(kapsam_key, opt, fav_secili_key),
            )


def tablo_goster_html(kayitlar, prefix="tbl"):
    """Tablo: İlçe · İşlem · Talep · Bütçe · Danışman · Tarih · Kaynak · Detay · ★ · ✏"""
    if not kayitlar:
        st.info("Gösterilecek kayıt yok.")
        return

    # İlçe(1.4) | İşlem(1.1) | Talep(3.8) | Bütçe(2.0) | Danışman(1.8) | Tarih(1.2) | Kaynak(0.9) | Detay(0.9) | ★(0.4) | ✏(0.4)
    COL_RATIOS = [1.4, 1.1, 3.8, 2.0, 1.8, 1.2, 0.9, 0.9, 0.4, 0.4]

    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;'
        'font-size:10px;color:#94a3b8;">'
        '<span style="display:flex;align-items:center;gap:4px;"><span style="width:7px;height:7px;border-radius:50%;background:#16a34a;display:inline-block;"></span><span style="font-size:10px;color:#94a3b8;">≤7 gün</span></span>'
        '<span style="display:flex;align-items:center;gap:4px;"><span style="width:7px;height:7px;border-radius:50%;background:#ca8a04;display:inline-block;"></span><span style="font-size:10px;color:#94a3b8;">8-30 gün</span></span>'
        '<span style="display:flex;align-items:center;gap:4px;"><span style="width:7px;height:7px;border-radius:50%;background:#ea580c;display:inline-block;"></span><span style="font-size:10px;color:#94a3b8;">31-90 gün</span></span>'
        '<span style="display:flex;align-items:center;gap:4px;"><span style="width:7px;height:7px;border-radius:50%;background:#dc2626;display:inline-block;"></span><span style="font-size:10px;color:#94a3b8;">>90 gün</span></span>'
        '<span style="display:flex;align-items:center;gap:4px;"><span style="width:7px;height:7px;border-radius:50%;background:#cbd5e1;display:inline-block;"></span><span style="font-size:10px;color:#94a3b8;">Görüldü</span></span>'
        '</div>',
        unsafe_allow_html=True
    )

    HDR = 'font-size:10px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;padding:8px 0 6px;border-bottom:1px solid #e2e8f0;'
    h = st.columns(COL_RATIOS)
    for col, hdr in zip(h, ["İlçe", "İşlem", "Talep", "Bütçe", "Danışman", "Tarih", "Kaynak", "", "", ""]):
        with col:
            st.markdown(f'<div style="{HDR}">{hdr}</div>', unsafe_allow_html=True)

    for v in kayitlar:
        kid   = v.get("id", "")
        ui    = build_talep_ui_model(v)
        isim  = isim_ayikla(v.get("talep_eden_danisan", ""))
        ilce  = ilce_grubu(v) or "—"
        islem = v.get("islem_tipi", "") or ""
        butce = v.get("max_butce", "") or "—"
        favori   = v.get("favori", False)
        gun_farki = tarih_gun_farki(en_iyi_tarih(v))
        okundu   = kid in st.session_state.get("goruldu_ids", set())
        _tarih_fg, _tarih_bg, dot_c = tarih_renk_bilgisi(gun_farki)
        if okundu:
            dot_c = "#cbd5e1"; _tarih_fg = "#94a3b8"; _tarih_bg = "#f8fafc"

        tarih_d = tarih_parse(en_iyi_tarih(v))
        if tarih_d:
            _has_t = hasattr(tarih_d, "hour") and (tarih_d.hour != 0 or tarih_d.minute != 0)
            tarih_str = tarih_d.strftime("%d.%m %H:%M") if _has_t else tarih_d.strftime("%d.%m.%Y")
        else:
            tarih_str = "—"

        aks_r = aks_renk_bul([ilce] if ilce != "—" else [])

        if "iralık" in islem:   tip_bg, tip_color, tip_lbl = "#f0fdf4","#166534","Kiralık"
        elif "atılık" in islem: tip_bg, tip_color, tip_lbl = "#fef2f2","#991b1b","Satılık"
        else:                   tip_bg, tip_color, tip_lbl = "#f8fafc","#64748b", islem or "—"

        initials = "".join(w[0].upper() for w in isim.split()[:2]) if isim else "?"

        kaynak_raw = (v.get("kaynak") or "").lower()
        if kaynak_raw in ("startkey_mail", ""):
            k_lbl, k_c, k_bg = "Startkey", "#355C7D", "#EEF4FA"
        elif kaynak_raw in ("zeta1", "zeta2", "ofis", "zeta"):
            k_lbl, k_c, k_bg = "Zeta", "#0F6E56", "#E1F5EE"
        else:
            k_lbl, k_c, k_bg = "Diğer", "#475569", "#f1f5f9"

        RB = "border-bottom:0.5px solid #f1f5f9;padding:8px 0;"
        row = st.columns(COL_RATIOS)

        with row[0]:
            st.markdown(f'<div style="{RB}"><span style="background:{aks_r["bg"]};color:{aks_r["text"]};padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600;">{ilce}</span></div>', unsafe_allow_html=True)
        with row[1]:
            st.markdown(f'<div style="{RB}"><span style="background:{tip_bg};color:{tip_color};padding:3px 8px;border-radius:4px;font-size:10.5px;font-weight:700;">{tip_lbl}</span></div>', unsafe_allow_html=True)
        with row[2]:
            baslik = ui.get("baslik","") or "—"
            kriter = (ui.get("kriter_ozet","") or "")[:60]
            st.markdown(
                f'<div style="{RB}">'
                f'<div style="display:flex;align-items:center;gap:6px;">'
                f'<span style="width:6px;height:6px;border-radius:50%;background:{dot_c};flex-shrink:0;display:inline-block;"></span>'
                f'<span style="font-size:12px;font-weight:600;color:#1e293b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:95%;display:block;">{baslik}</span></div>'
                + (f'<div style="font-size:10.5px;color:#64748b;margin-left:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{kriter}</div>' if kriter else "")
                + f'</div>', unsafe_allow_html=True)
        with row[3]:
            st.markdown(f'<div style="{RB};font-size:11.5px;font-weight:600;color:#0f172a;">{butce}</div>', unsafe_allow_html=True)
        with row[4]:
            st.markdown(
                f'<div style="{RB};display:flex;align-items:center;gap:5px;">'
                f''
                f'<span style="font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{isim or "—"}</span></div>',
                unsafe_allow_html=True)
        with row[5]:
            st.markdown(f'<div style="{RB}"><span style="background:{_tarih_bg};color:{_tarih_fg};font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:4px;white-space:nowrap;">{tarih_str}</span></div>', unsafe_allow_html=True)
        with row[6]:
            st.markdown(f'<div style="{RB}"><span style="background:{k_bg};color:{k_c};font-size:10px;font-weight:600;padding:2px 6px;border-radius:4px;">{k_lbl}</span></div>', unsafe_allow_html=True)
        with row[7]:
            _dt = st.session_state.get("acik_detay_id") == kid
            if st.button("✕" if _dt else "Detay", key=f"{prefix}_detay_{kid}", use_container_width=True, type="primary"):
                st.session_state.setdefault("goruldu_ids", set()).add(kid)
                st.session_state["acik_detay_id"] = None if _dt else kid
                st.rerun()
        with row[8]:
            if st.button("★" if favori else "☆", key=f"{prefix}_fav_{kid}", use_container_width=True):
                favori_guncelle(kid, favori)
        with row[9]:
            if st.button("✏", key=f"{prefix}_dz_{kid}", use_container_width=True):
                st.session_state[f"duzen_{kid}"] = not st.session_state.get(f"duzen_{kid}", False)
                st.rerun()

        if st.session_state.get("acik_detay_id") == kid:
            talep_detay_modal(v, st.session_state.get("aktif_ilce_sec", []))


def kayit_karti(v, ilce_sec, prefix=""):
    kid = v.get("id")
    isim = isim_ayikla(v.get("talep_eden_danisan", ""))
    ozet = v.get("ozet", "") or v.get("mail_konusu", "")
    butce = v.get("max_butce", "")
    oda = v.get("oda_sayisi_m2", "")
    islem = v.get("islem_tipi", "")
    mulk = v.get("mulk_tipi", "")
    mahalle = v.get("mahalle", "") or ""
    bolge = v.get("bolge", "") or v.get("bolge_mahalle", "") or ""
    tarih_d = tarih_parse(en_iyi_tarih(v))
    if tarih_d:
        _has_time = hasattr(tarih_d, 'hour') and (tarih_d.hour != 0 or tarih_d.minute != 0)
        tarih_g = tarih_d.strftime("%d.%m.%Y %H:%M") if _has_time else tarih_d.strftime("%d.%m.%Y")
    else:
        tarih_g = ""
    favori = v.get("favori", False)
    ilceler_list = v.get("ilceler") or []
    gun_farki = tarih_gun_farki(en_iyi_tarih(v))
    yeni_kayit = gun_farki <= 7
    duzen_modu = st.session_state.get(f"duzen_{kid}", False)
    gizli = v.get("gizli", False)
    okundu = kid in st.session_state.get("goruldu_ids", set())

    if st.session_state.pop(f"guncellendi_{kid}", False):
        st.toast("Güncellendi!")

    # Normalize UI model
    ui = build_talep_ui_model(v)
    ilan_baslik = ui["baslik"]
    lokasyon_str = ui["lokasyon_ozet"]
    kriter_ozet_str = ui.get("kriter_ozet", "")

    _fg, _bg, _dot = tarih_renk_bilgisi(gun_farki)
    tarih_html = (
        f'<span style="display:inline-flex;align-items:center;gap:4px;">'
        f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:{_dot};flex-shrink:0;"></span>'
        f'<span style="color:{_fg};font-weight:600;font-size:11px;">{tarih_g}</span></span>'
        if tarih_g else ""
    )

    aks_renk = aks_renk_bul(ilceler_list or [v.get("ilce",""), v.get("bolge",""), v.get("mahalle","")])
    _aks_bar = aks_bar_gradient(ilceler_list)

    if okundu:       left_border = "#cbd5e1"
    elif yeni_kayit: left_border = "#16a34a"
    elif favori:     left_border = "#f59e0b"
    else:            left_border = "#e2e8f0"
    card_bg = "#ffffff"

    if okundu:
        _rozet_html = '<span style="background:#e2e8f0;color:#94a3b8;font-size:10px;font-weight:700;padding:2px 8px;border-radius:999px;">✓ Görüldü</span>'
    elif yeni_kayit:
        _rozet_html = '<span style="background:#16a34a;color:#fff;font-size:10px;font-weight:750;padding:2px 8px;border-radius:999px;letter-spacing:0.04em;">YENİ</span>'
    else:
        _rozet_html = ""

    # İşlem chip
    if "iralık" in islem:   _ibg, _ic, _ilbl = "#f0fdf4","#166534","Kiralık"
    elif "atılık" in islem: _ibg, _ic, _ilbl = "#fef2f2","#991b1b","Satılık"
    else:                   _ibg, _ic, _ilbl = "#f8fafc","#64748b", islem or ""

    # Kaynak chip
    _kaynak_raw = (v.get("kaynak") or "").lower()
    if _kaynak_raw in ("startkey_mail", ""):
        _k_lbl, _k_c, _k_bg = "Startkey", "#355C7D", "#EEF4FA"
    elif _kaynak_raw in ("zeta1", "zeta2", "ofis", "zeta"):
        _k_lbl, _k_c, _k_bg = "Zeta", "#0F6E56", "#E1F5EE"
    else:
        _k_lbl, _k_c, _k_bg = "Diğer", "#475569", "#f1f5f9"
    _kaynak_chip = (f'<span style="background:{_k_bg};color:{_k_c};font-size:9.5px;font-weight:600;'
                    f'padding:1px 6px;border-radius:4px;">{_k_lbl}</span>')

    _chip_row = ""
    if _ilbl:
        _chip_row += f'<span style="background:{_ibg};color:{_ic};border:1px solid {_ibg};padding:2px 9px;border-radius:4px;font-size:10.5px;font-weight:700;margin-right:5px;">{_ilbl}</span>'
    if mulk and mulk not in ("Belirsiz","Belirtilmemiş"):
        cfg = BADGE_PALETTE.get(mulk, ("#f1f5f9","#475569","#e2e8f0"))
        _chip_row += f'<span style="background:{cfg[0]};color:{cfg[1]};border:1px solid {cfg[2]};padding:2px 9px;border-radius:4px;font-size:10.5px;font-weight:600;margin-right:5px;">{mulk}</span>'
    if oda:
        _chip_row += f'<span style="background:#f1f5f9;color:#475569;border:1px solid #e2e8f0;padding:2px 9px;border-radius:4px;font-size:10.5px;font-weight:600;">{oda}</span>'

    st.markdown(
        f'<div class="kart-wrapper" style="border:1px solid #dce4ee;border-left:4px solid {left_border};'
        f'border-radius:12px;overflow:hidden;margin-bottom:3px;background:{card_bg};box-shadow:0 2px 8px rgba(15,23,42,0.05);">'
        f'<div style="height:3px;background:{_aks_bar};width:100%;"></div>'
        f'<div style="padding:10px 14px 10px 14px;">'
        # 1. İlçe chip + rozet
        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:5px;">'
        + (f'<span style="background:{aks_renk["bg"]};color:{aks_renk["text"]};padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;">{lokasyon_str}</span>' if lokasyon_str else '<span></span>')
        + f'{_rozet_html}</div>'
        # 2. İşlem + Mülk chip'leri
        + (f'<div style="margin-bottom:5px;">{_chip_row}</div>' if _chip_row else "")
        # 3. Başlık
        + f'<div style="background:#FFF9ED;border-left:3px solid #F4B740;padding:5px 10px;border-radius:0 6px 6px 0;margin-bottom:6px;">'
        f'<div style="font-size:1.0rem;font-weight:800;color:#172B4D;line-height:1.25;'
        f'display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">{ilan_baslik}</div></div>'
        # 4. Kriter
        + (f'<div class="kart-kriter">{kriter_ozet_str}</div>' if kriter_ozet_str else "")
        # 5. Meta: Bütçe · Danışman · Kaynak · Tarih
        + f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:6px;">'
        f'<span style="font-size:0.91rem;font-weight:750;color:#172B4D;">{str(butce) if butce else "—"}</span>'
        f'<span style="font-size:11px;font-weight:600;color:#94a3b8;margin-left:2px;">{isim}</span>'
        f'{_kaynak_chip}'
        + (f'<span style="margin-left:auto;">{tarih_html}</span>' if tarih_html else "")
        + f'</div></div></div></div>',
        unsafe_allow_html=True,
    )

    # ── Aksiyon satırı — sadece Detay (★/✏/⊘ panelde mevcut)
    a_detay, a_spacer = st.columns([1.4, 8.0])
    with a_detay:
        _detay_acik = st.session_state.get("acik_detay_id") == kid
        if st.button("✕ Kapat" if _detay_acik else "Detay", key=f"{prefix}detay_btn_{kid}", type="primary", use_container_width=True):
            st.session_state.setdefault("goruldu_ids", set()).add(kid)
            st.session_state["acik_detay_id"] = None if _detay_acik else kid
            st.rerun()

    # Sil butonu — sadece manuel kayıtlar
    kaynak_v = v.get("kaynak", "")
    if kaynak_v and kaynak_v != "startkey_mail":
        sil_key = f"tsil_onay_{prefix}{kid}"
        if not st.session_state.get(sil_key):
            if st.button("🗑", key=f"tsil_{prefix}{kid}", help="Kaydı sil"):
                st.session_state[sil_key] = True
                st.rerun()
        else:
            st.warning("⚠️ Bu kaydı silmek istediğinizden emin misiniz?")
            sc1, sc2 = st.columns([1, 1])
            with sc1:
                if st.button("🗑 Evet, Sil", key=f"tsil_evet_{prefix}{kid}", type="primary"):
                    kayit_sil(kid); st.toast("✅ Kayıt silindi.")
            with sc2:
                if st.button("İptal", key=f"tsil_iptal_{prefix}{kid}"):
                    st.session_state.pop(sil_key, None); st.rerun()

    if duzen_modu:
        duzenleme_formu(v, ilce_sec)

    if st.session_state.get("acik_detay_id") == kid:
        talep_detay_modal(v, ilce_sec)

    st.markdown("<div style='height:1px'></div>", unsafe_allow_html=True)


def talep_detay_modal(v, ilce_sec):
    """
    INLINE detay paneli — satırın altında açılır, modal/popup kullanmaz.
    session_state["acik_detay_id"] ile hangi satırın açık olduğu kontrol edilir.
    """
    kid = v.get("id")
    isim = isim_ayikla(v.get("talep_eden_danisan", ""))
    ofis = v.get("ofis_adi", "") or v.get("kaynak", "") or ""
    ilceler_list = v.get("ilceler") or []
    butce = v.get("max_butce", "")
    oda = v.get("oda_sayisi_m2", "")
    mulk = v.get("mulk_tipi", "")
    islem = v.get("islem_tipi", "")
    mahalle = v.get("mahalle", "") or ""
    bolge = v.get("bolge", "") or v.get("bolge_mahalle", "") or ""
    favori = v.get("favori", False)
    gizli = v.get("gizli", False)
    gun_farki = tarih_gun_farki(en_iyi_tarih(v))
    yeni_kayit = gun_farki <= 7
    ui = build_talep_ui_model(v)
    aks_r = aks_renk_bul(ilceler_list)
    ic = html_temizle(v.get("mail_icerigi", ""))
    not_m = v.get("not_alani", "") or ""
    mail_open = st.session_state.get(f"dp_mail_open_{kid}", False)
    note_open = st.session_state.get(f"dp_not_open_{kid}", False)
    panel_compact = not mail_open and not note_open and not st.session_state.get(f"duzen_{kid}", False)
    panel_max_style = "max-height:190px;overflow:hidden;" if panel_compact else ""

    # ── Panel wrapper ─────────────────────────────────────────────────────────
    st.markdown(
        f'<div class="detail-panel" style="background:#FAFBFD;border:1px solid #D6E4F0;border-left:4px solid #355C7D;'
        f'border-radius:0 0 10px 10px;margin:-4px 0 6px 0;padding:12px 16px 8px 16px;{panel_max_style}">'
        f'<!-- DETAY PANEL: {kid} -->',
        unsafe_allow_html=True,
    )

    # ── ÜST BÖLÜM: Başlık + tek şerit bilgi kartı ─────────────────────────
    ozet_metin = v.get("ozet", "") or ""
    kriter_metin = v.get("ozel_kriterler", "") or ""

    def _compact_summary(ozet_text, kriter_text):
        def normalize(text):
            return " ".join(text.split())

        ozet_text = normalize(ozet_text)
        kriter_text = normalize(kriter_text)

        def split_criteria(text):
            return [item.strip() for item in re.split(r"[\n,;·]+", text) if item.strip()]

        summary_parts = []
        if ozet_text:
            short = ozet_text
            if len(short) > 100:
                short = short[:100].rsplit(" ", 1)[0] + "…"
            summary_parts.append(short)

        criteria_items = split_criteria(kriter_text)
        if criteria_items:
            filtered = criteria_items
            if ozet_text:
                filtered = [item for item in criteria_items if item not in ozet_text]
            selected = filtered[:2]
            if selected:
                if summary_parts:
                    summary_parts.append(" · ".join(selected))
                else:
                    summary_parts.extend(selected)

        summary = " · ".join(summary_parts).strip()
        if len(summary) > 180:
            summary = summary[:180].rsplit(" ", 1)[0] + "…"
        return summary

    summary_text = _compact_summary(ozet_metin, kriter_metin)
    ilce_str = " · ".join(ilceler_list[:4]) if ilceler_list else (mahalle or bolge or "—")
    meta_parts = [ilce_str]
    if ofis:
        meta_parts.append(ofis)
    if islem:
        meta_parts.append(islem)
    if mulk:
        meta_parts.append(mulk)
    if oda:
        meta_parts.append(oda)
    if butce:
        meta_parts.append(butce)
    if isim:
        meta_parts.append(isim)
    meta_text = " · ".join([part for part in meta_parts if part])

    title_html = f"""
<div style="background:#FFF9ED;border-left:3px solid #F4B740;padding:10px 12px;border-radius:0 6px 6px 0;margin-bottom:8px;">
    <div style="font-size:0.9rem;font-weight:800;color:#172B4D;line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{ui["baslik"]}</div>
    <div style="font-size:10px;color:#475569;margin-top:6px;line-height:1.3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{meta_text}</div>
    {f'<div style="font-size:11px;font-weight:700;color:#1f2937;margin-top:6px;line-height:1.4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{summary_text}</div>' if summary_text else ""}
</div>
""".strip()
    st.markdown(title_html, unsafe_allow_html=True)

    # ── KOMPAKT AKSİYON TOOLBAR ─────────────────────────────────────────────
    # Sıralama: Favori · ✉ Göster · Notum · Sunum · Metin · Düzenle · Pasife Al
    # "Mail" → Streamlit "Posta" yapıyor → "✉ Göster" kullanıyoruz
    # "Not"  → Streamlit "Değil" yapıyor → "Notum" kullanıyoruz
    mail_open = st.session_state.get(f"dp_mail_open_{kid}", False)
    note_open = st.session_state.get(f"dp_not_open_{kid}", False)

    tb_c1, tb_c2, tb_c3, tb_c4, tb_c5, tb_c6, tb_c7 = st.columns(
        [0.85, 0.82, 0.78, 0.78, 0.78, 0.90, 0.95], gap="small"
    )

    with tb_c1:
        fav_text = "★ Favori" if favori else "☆ Favori"
        if st.button(fav_text, key=f"dp_fav_{kid}", use_container_width=True, type="secondary"):
            favori_guncelle(kid, favori)

    with tb_c2:
        mail_lbl = "✕ Kapat" if mail_open else "✉ Göster"
        if st.button(mail_lbl, key=f"dp_mailgoster_{kid}", use_container_width=True, type="secondary"):
            st.session_state[f"dp_mail_open_{kid}"] = not mail_open
            if not mail_open:
                st.session_state[f"dp_not_open_{kid}"] = False
            st.rerun()

    with tb_c3:
        not_lbl = "✕ Kapat" if note_open else "Notum"
        if st.button(not_lbl, key=f"dp_notgir_{kid}", use_container_width=True, type="secondary"):
            st.session_state[f"dp_not_open_{kid}"] = not note_open
            if not note_open:
                st.session_state[f"dp_mail_open_{kid}"] = False
            st.rerun()

    with tb_c4:
        if st.button("Sunum", key=f"dp_sunum_{kid}", use_container_width=True, type="secondary"):
            st.session_state["side_panel"] = {"tip": "sunum", "kid": kid, "v": dict(v)}
            st.toast("Sunum Merkezi için kayıt hazırlandı.")

    with tb_c5:
        if st.button("Metin", key=f"dp_metin_{kid}", use_container_width=True, type="secondary"):
            st.session_state["side_panel"] = {"tip": "metin", "kid": kid, "v": dict(v)}
            st.toast("Metin oluşturma hazırlanıyor.")

    with tb_c6:
        if st.button("Düzenle", key=f"dp_dz_{kid}", use_container_width=True, type="secondary"):
            st.session_state[f"duzen_{kid}"] = not st.session_state.get(f"duzen_{kid}", False)
            st.rerun()

    with tb_c7:
        gizle_lbl = "Gizlendi" if gizli else "Pasife Al"
        if st.button(gizle_lbl, key=f"dp_pasif_{kid}", use_container_width=True, type="secondary"):
            get_client().table("alici_talepleri").update({"gizli": not gizli}).eq("id", kid).execute()
            verileri_yukle.clear()
            st.rerun()

    st.markdown('<div style="height:4px;border-top:1px solid #e8eef5;margin-top:4px;"></div>', unsafe_allow_html=True)

    if st.session_state.get(f"dp_mail_open_{kid}", False):
        mail_konu = v.get("mail_konusu", "") or ""
        if mail_konu:
            st.markdown(f'<div style="font-size:11px;font-weight:700;color:#355C7D;margin:4px 0 5px 0;">Konu: {mail_konu}</div>', unsafe_allow_html=True)
        mail_text = ic if ic else "Bu kayıt için mail içeriği bulunmuyor."
        st.markdown(
            f'<div style="background:#f0f4ff;border-left:3px solid #2d7dd2;padding:8px 10px;'
            f'border-radius:6px;font-size:11px;line-height:1.5;max-height:140px;overflow-y:auto;'
            f'color:#374151;">{mail_text}</div>', unsafe_allow_html=True)

    elif st.session_state.get(f"dp_not_open_{kid}", False):
        yn = st.text_area("Not gir", value=not_m, height=68, placeholder="Not ekle...",
                          key=f"dp_notarea_{kid}", label_visibility="collapsed")
        nb1, _sp = st.columns([1.5, 6.5])
        with nb1:
            if st.button("Kaydet", key=f"dp_notkaydet_{kid}", type="primary", use_container_width=True):
                not_kaydet_fn(kid, yn)

    if st.session_state.get(f"duzen_{kid}", False):
        st.markdown('<div style="border-top:1px solid #e2e8f0;margin-top:8px;padding-top:6px;"></div>', unsafe_allow_html=True)
        duzenleme_formu(v, ilce_sec)

    st.markdown('</div>', unsafe_allow_html=True)


def render_talep_detay(v, ilce_sec):
    """Uyumluluk wrapper — inline panel'i çağırır."""
    talep_detay_modal(v, ilce_sec)


@st.dialog("Talep Detayı", width="large")
def talep_detay_dialog(v, ilce_sec):
    """Kart görünümü için popup dialog."""
    kid = v.get("id")
    isim = isim_ayikla(v.get("talep_eden_danisan", ""))
    ofis = v.get("ofis_adi", "") or v.get("kaynak", "") or ""
    ilceler_list = v.get("ilceler") or []
    butce = v.get("max_butce", "")
    oda = v.get("oda_sayisi_m2", "")
    mulk = v.get("mulk_tipi", "")
    islem = v.get("islem_tipi", "")
    mahalle = v.get("mahalle", "") or ""
    bolge = v.get("bolge", "") or v.get("bolge_mahalle", "") or ""
    favori = v.get("favori", False)
    gizli = v.get("gizli", False)
    ui = build_talep_ui_model(v)
    ic = html_temizle(v.get("mail_icerigi", ""))
    not_m = v.get("not_alani", "") or ""
    ilce_str = " · ".join(ilceler_list[:4]) if ilceler_list else (mahalle or bolge or "—")
    meta_parts = [p for p in [ilce_str, ofis, islem, mulk, oda, butce, isim] if p]

    # Başlık
    st.markdown(
        f'<div style="background:#FFF9ED;border-left:3px solid #F4B740;'
        f'padding:10px 12px;border-radius:0 6px 6px 0;margin-bottom:12px;">'
        f'<div style="font-size:0.9rem;font-weight:800;color:#172B4D;line-height:1.2;">{ui["baslik"]}</div>'
        f'<div style="font-size:10px;color:#475569;margin-top:5px;">{" · ".join(meta_parts)}</div>'
        + (f'<div style="font-size:11px;font-weight:700;color:#1f2937;margin-top:5px;">{(v.get("ozet","") or "")[:180]}</div>' if v.get("ozet") else "")
        + f'</div>', unsafe_allow_html=True)

    # Toolbar
    tb1, tb2, tb3, tb4, tb5 = st.columns([1, 1, 1, 1, 1], gap="small")
    with tb1:
        if st.button("★ Favori" if favori else "☆ Favori", key=f"dlg_fav_{kid}", use_container_width=True, type="secondary"):
            favori_guncelle(kid, favori)
    with tb2:
        if st.button("Sunum", key=f"dlg_sunum_{kid}", use_container_width=True, type="secondary"):
            st.toast("Sunum Merkezi için kayıt hazırlandı.")
    with tb3:
        if st.button("Metin", key=f"dlg_metin_{kid}", use_container_width=True, type="secondary"):
            st.toast("Metin oluşturma hazırlanıyor.")
    with tb4:
        if st.button("Düzenle", key=f"dlg_dz_{kid}", use_container_width=True, type="secondary"):
            st.session_state[f"duzen_{kid}"] = not st.session_state.get(f"duzen_{kid}", False)
            st.rerun()
    with tb5:
        if st.button("Gizlendi" if gizli else "Pasife Al", key=f"dlg_pasif_{kid}", use_container_width=True, type="secondary"):
            get_client().table("alici_talepleri").update({"gizli": not gizli}).eq("id", kid).execute()
            verileri_yukle.clear(); st.rerun()

    st.markdown('<div style="height:3px;border-top:1px solid #e8eef5;margin-top:4px;margin-bottom:8px;"></div>', unsafe_allow_html=True)

    # Mail içeriği — her zaman göster (rerun gerektirmiyor)
    if ic:
        mail_konu = v.get("mail_konusu", "") or ""
        with st.expander("✉ Mail İçeriği", expanded=False):
            if mail_konu:
                st.markdown(f'<div style="font-size:11px;font-weight:700;color:#355C7D;margin-bottom:5px;">Konu: {mail_konu}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div style="background:#f0f4ff;border-left:3px solid #2d7dd2;padding:8px 10px;'
                f'border-radius:6px;font-size:11px;line-height:1.5;color:#374151;">{ic}</div>',
                unsafe_allow_html=True)

    # Not alanı — her zaman göster
    with st.expander("📝 Not", expanded=bool(not_m)):
        yn = st.text_area("Not gir", value=not_m, height=80, placeholder="Not ekle...",
                          key=f"dlg_notarea_{kid}", label_visibility="collapsed")
        nb1, _ = st.columns([1.5, 6.5])
        with nb1:
            if st.button("💾 Kaydet", key=f"dlg_notkaydet_{kid}", type="primary", use_container_width=True):
                not_kaydet_fn(kid, yn)

    if st.session_state.get(f"duzen_{kid}", False):
        st.markdown('<div style="border-top:1px solid #e2e8f0;margin-top:8px;padding-top:6px;"></div>', unsafe_allow_html=True)
        duzenleme_formu(v, ilce_sec)


def grup_baslik_bar(baslik, toplam, yeni, key, default_acik=False):
    if key not in st.session_state:
        st.session_state[key] = default_acik

    acik = st.session_state[key]
    yeni_str = f"  🟢 {yeni} yeni" if yeni > 0 else ""

    if st.button(
        f"{baslik}    {toplam} talep{yeni_str}",
        key=f"toggle_{key}",
        use_container_width=True
    ):
        st.session_state[key] = not acik
        st.rerun()

    return st.session_state[key]


def liste_goster(kayitlar, ilce_filtre_aktif, ilce_sec, fav_secili):
    if ilce_filtre_aktif != "Tümü":
        yeni = sum(1 for v in kayitlar if tarih_gun_farki(en_iyi_tarih(v)) <= 7)
        st.markdown(
            f'<div style="font-size:11px;color:#64748b;margin-bottom:6px;">'
            f'{ilce_filtre_aktif} · {len(kayitlar)} talep {yeni_badge_html(yeni)}</div>',
            unsafe_allow_html=True
        )

        for v in kayitlar:
            kayit_karti(v, ilce_sec)

        return

    fav_ilceler_list = favori_ilceleri_cek()
    izmir, izmir_genel, diger = {}, [], []

    for v in kayitlar:
        il = il_grubu(v)
        ilce = ilce_grubu(v)

        if il == "İzmir" and ilce:
            izmir.setdefault(ilce, []).append(v)
        elif il == "İzmir" and not ilce:
            izmir_genel.append(v)
        else:
            diger.append(v)

    if fav_ilceler_list:
        st.markdown(
            '<div class="fav-section-title">Favori İlçelerim</div>',
            unsafe_allow_html=True
        )

        for fav in fav_ilceler_list:
            if fav in izmir:
                ilce_bar(
                    fav,
                    izmir[fav],
                    ilce_sec,
                    key_prefix="fav",
                    her_zaman_acik=(fav_secili == fav)
                )

        st.markdown("<div style='height:3px'></div>", unsafe_allow_html=True)

    if izmir or izmir_genel:
        toplam = sum(len(k) for k in izmir.values()) + len(izmir_genel)
        yeni_t = sum(1 for g in izmir.values() for v in g if tarih_gun_farki(en_iyi_tarih(v)) <= 7)
        yeni_t += sum(1 for v in izmir_genel if tarih_gun_farki(en_iyi_tarih(v)) <= 7)

        acik = grup_baslik_bar("İZMİR", toplam, yeni_t, "izmir_acik", default_acik=False)

        if acik:
            for ilce in sorted(izmir.keys()):
                if ilce in fav_ilceler_list:
                    continue

                ilce_bar(ilce, izmir[ilce], ilce_sec, key_prefix="izmir")

            if izmir_genel:
                ilce_bar("İzmir Genel", izmir_genel, ilce_sec, key_prefix="izmir")

    if diger:
        yeni_d = sum(1 for v in diger if tarih_gun_farki(en_iyi_tarih(v)) <= 7)
        acik = grup_baslik_bar("DİĞER", len(diger), yeni_d, "diger_acik", default_acik=False)

        if acik:
            diger_gruplar = {}

            for v in diger:
                il = il_grubu(v) or "Belirsiz"
                diger_gruplar.setdefault(il, []).append(v)

            for il in sorted(diger_gruplar.keys()):
                ilce_bar(il, diger_gruplar[il], ilce_sec, key_prefix="diger")


def secim_butonu(label, value, state_key):
    aktif = st.session_state.get(state_key) == value

    if st.button(
        label,
        key=f"{state_key}_{value}",
        use_container_width=True,
        type="primary" if aktif else "secondary"
    ):
        st.session_state[state_key] = value
        st.rerun()


def workspace_tab(label, value):
    aktif = st.session_state.get("aktif_talep_workspace") == value

    if st.button(
        label,
        key=f"ws_{value}",
        use_container_width=True,
        type="primary" if aktif else "secondary"
    ):
        st.session_state["aktif_talep_workspace"] = value

        if value != "Favori İlçeler":
            st.session_state["fav_secili_ilce"] = None

        st.rerun()


# ── VERİ YÜKLEME ─────────────────────────────────────────────────────────────
import time
_t_talep0 = time.time()
with st.spinner("Talepler yükleniyor..."):
    veriler = verileri_yukle(None)
if PERF_DEBUG:
    st.caption(f"[PERF] verileri_yukle: {time.time()-_t_talep0:.2f}s")

# DÜZELTME: "hiç kayıt yok" (veritabanı boş) ile "gizli filtresi tüm kayıtları
# elediği için sonuç boş" durumları ayrılıyor. Eskiden ikisi de aynı st.stop()
# ile karışıyordu ve tüm kayıtlar gizliyken kullanıcı "Gizli" filtresine hiç
# ulaşamıyordu çünkü toolbar/filtre paneli st.stop()'tan sonra render ediliyordu.
_veriler_ham_bos = not veriler

if not st.session_state.get("ft_gizli", False):
    veriler = [v for v in veriler if not v.get("gizli", False)]

ilce_sec = ilce_listesi_cek()
fav_ilceler = favori_ilceleri_cek()

FILTER_DEFAULTS = {
    "ft_ara": "",
    "ft_il": "Tümü",
    "ft_ilce": "Tümü",
    "ft_danisan": "Tümü",
    "ft_mulk": "Tümü",
    "ft_islem": "Tümü",
    "ft_siralama": "Tarih ↓",
    "ft_hizli": "Son 7 gün",
    "ft_aralik": False,
    "ft_fav": False,
    "ft_gizli": False,
    "ft_butce_alt": 0,
    "ft_butce_ust": 0,
    "ft_oda": "Tümü",
    "ft_bina_yasi": "Tümü",
    "ft_kat": "Tümü",
    "ft_site_ici": "Tümü",
    "ft_esyali": "Tümü",
    "ft_kullanim": "Tümü",
    "ft_gun_min": 0,
    "ft_gun_max": 0,
    "ft_gorunum": "Tablo",
    "aktif_talep_workspace": "Tümü",
    "fav_secili_ilce": None,
    "compact_mode": False,
    "acik_detay_id": None,
    "side_panel": None,
    "talep_islem_sekme": "Satılık",
    "talep_donem": "Son 7 Gün",
    "talep_ilce_kapsam": "Tüm İlçeler",
}

for key, value in FILTER_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

if st.session_state.get("fav_secili_ilce") and st.session_state["fav_secili_ilce"] not in fav_ilceler:
    st.session_state["fav_secili_ilce"] = None

yeni_sayisi = sum(1 for v in veriler if tarih_gun_farki(en_iyi_tarih(v)) <= 7)
bugun_sayisi = sum(1 for v in veriler if tarih_gun_farki(en_iyi_tarih(v)) == 0)
son_7_sayisi = sum(1 for v in veriler if tarih_gun_farki(en_iyi_tarih(v)) <= 7)
son_30_sayisi = sum(1 for v in veriler if tarih_gun_farki(en_iyi_tarih(v)) <= 30)

danisman_sayisi = len(
    set(
        isim_ayikla(v.get("talep_eden_danisan", ""))
        for v in veriler
        if v.get("talep_eden_danisan", "")
    )
)

ilce_sayilari = {}

for v in veriler:
    for ilce in (v.get("ilceler") or []):
        if ilce and ilce != "Diğer Bölge":
            ilce_sayilari[ilce] = ilce_sayilari.get(ilce, 0) + 1

ilce_sayisi = len(ilce_sayilari)

top_3_ilce = sorted(
    ilce_sayilari.items(),
    key=lambda x: x[1],
    reverse=True
)[:3]

top_3_ilce_text = " · ".join([f"{ilce} {adet}" for ilce, adet in top_3_ilce])

# ── SAYFA BAŞLIĞI ─────────────────────────────────────────────────────────
_hdr1, _hdr2 = st.columns([1, 0.06])
with _hdr1:
    render_page_header(
        "Talep Merkezi",
        f"Son 7 gün · {son_7_sayisi} kayıt · {danisman_sayisi} danışman"
    )
with _hdr2:
    st.markdown("<div style='margin-top:14px'>", unsafe_allow_html=True)
    if st.button("↺", key="talep_yenile", help="Yenile", use_container_width=True):
        verileri_yukle.clear(); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

if _veriler_ham_bos:
    st.info("Henüz kayıt bulunamadı.")
    st.stop()

# NOT: Filtrelenmiş `veriler` boş olabilir (ör. tüm kayıtlar gizli ve "Gizli"
# filtresi kapalı) — bu durumda sayfayı burada durdurmuyoruz, toolbar/filtre
# paneli her zaman render edilir ki kullanıcı "Gizli" kutusunu işaretleyip
# kayıtlara ulaşabilsin. Filtrelenmiş sonuç boşsa liste_goster() zaten kendi
# "Gösterilecek kayıt yok." mesajını gösteriyor.

# ── TOOLBAR ──────────────────────────────────────────────────────────────────

if "show_filters_panel" not in st.session_state:
    st.session_state["show_filters_panel"] = False

# ── AŞAMA 1: Gelişmiş filtre değerlerini oku ─────────────────────────────────
# Panel kapalıyken de widget değerleri session_state'te durur; panel açıksa
# aşağıdaki widget'lar aynı key'lerle bu değerleri günceller. Bu sayede sayaç
# hesapları panelin açık/kapalı olmasından bağımsız çalışır.
il_filtre = st.session_state.get("ft_il", "Tümü")
ilce_filtre = st.session_state.get("ft_ilce", "Tümü")
danisan_filtre = st.session_state.get("ft_danisan", "Tümü")
mulk_filtre = st.session_state.get("ft_mulk", "Tümü")
ara = st.session_state.get("ft_ara", "")
siralama = st.session_state.get("ft_siralama", "Tarih ↓")
favori_filtre = st.session_state.get("ft_fav", False)
tarih_araligi_aktif = st.session_state.get("ft_aralik", False)
bas_tarih = st.session_state.get("ft_bas", None) if tarih_araligi_aktif else None
bit_tarih = st.session_state.get("ft_bit", None) if tarih_araligi_aktif else None
butce_alt = st.session_state.get("ft_butce_alt", 0)
butce_ust = st.session_state.get("ft_butce_ust", 0)
oda_filtre = st.session_state.get("ft_oda", "Tümü")
bina_yasi_filtre = st.session_state.get("ft_bina_yasi", "Tümü")
kat_filtre = st.session_state.get("ft_kat", "Tümü")
site_ici_filtre = st.session_state.get("ft_site_ici", "Tümü")
esyali_filtre = st.session_state.get("ft_esyali", "Tümü")
kullanim_filtre = st.session_state.get("ft_kullanim", "Tümü")
gun_min = st.session_state.get("ft_gun_min", 0)
gun_max = st.session_state.get("ft_gun_max", 0)
gorunum = st.session_state.get("ft_gorunum", "Tablo")
if gorunum not in ["Kart", "Tablo"]:
    gorunum = "Tablo"

# Aktif (gelişmiş panel) filtre sayısı — İşlem Tipi/Dönem/İlçe Kapsamı artık
# birincil gezinme kontrolleri olduğu için bu sayaca dahil edilmiyor.
aktif_filtre_sayisi = 0
if il_filtre != "Tümü": aktif_filtre_sayisi += 1
if ilce_filtre != "Tümü": aktif_filtre_sayisi += 1
if danisan_filtre != "Tümü": aktif_filtre_sayisi += 1
if mulk_filtre != "Tümü": aktif_filtre_sayisi += 1
if ara.strip(): aktif_filtre_sayisi += 1
if siralama != "Tarih ↓": aktif_filtre_sayisi += 1
if favori_filtre: aktif_filtre_sayisi += 1
if st.session_state.get("ft_gizli", False): aktif_filtre_sayisi += 1
if tarih_araligi_aktif: aktif_filtre_sayisi += 1
if butce_alt > 0: aktif_filtre_sayisi += 1
if butce_ust > 0: aktif_filtre_sayisi += 1
if oda_filtre != "Tümü": aktif_filtre_sayisi += 1
if bina_yasi_filtre != "Tümü": aktif_filtre_sayisi += 1
if kat_filtre != "Tümü": aktif_filtre_sayisi += 1
if site_ici_filtre != "Tümü": aktif_filtre_sayisi += 1
if esyali_filtre != "Tümü": aktif_filtre_sayisi += 1
if kullanim_filtre != "Tümü": aktif_filtre_sayisi += 1
if gun_min > 0: aktif_filtre_sayisi += 1
if gun_max > 0: aktif_filtre_sayisi += 1

filtre_btn_text = f"⚙ Filtreler {aktif_filtre_sayisi}" if aktif_filtre_sayisi > 0 else "⚙ Filtreler"

# ── AŞAMA 2: gelişmiş filtreleri uygula ──────────────────────────────────────
f = veriler

if ara:
    f = [v for v in f if any(ara.lower() in str(v.get(k, "")).lower()
         for k in ["talep_eden_danisan","bolge_mahalle","mahalle","bolge","ilce",
                   "mail_konusu","ozel_kriterler","ozet","ilceler"])]
if il_filtre == "Belirtilmemiş": f = [v for v in f if not il_grubu(v)]
elif il_filtre != "Tümü": f = [v for v in f if il_grubu(v) == il_filtre]
if ilce_filtre != "Tümü": f = [v for v in f if ilce_filtre in (v.get("ilceler") or [])]
if danisan_filtre != "Tümü": f = [v for v in f if isim_ayikla(v.get("talep_eden_danisan", "")) == danisan_filtre]
if mulk_filtre == "Belirtilmemiş": f = [v for v in f if v.get("mulk_tipi", "") in ("", "Belirsiz", "Belirtilmemiş", None)]
elif mulk_filtre != "Tümü": f = [v for v in f if v.get("mulk_tipi", "") == mulk_filtre]

if oda_filtre != "Tümü":
    f = [v for v in f if str(v.get("oda_sayisi_m2","")).strip() == oda_filtre]
if bina_yasi_filtre != "Tümü":
    f = [v for v in f if str(v.get("bina_yasi","")).strip() == bina_yasi_filtre]
if kat_filtre != "Tümü":
    f = [v for v in f if str(v.get("bulundugu_kat","")).strip() == kat_filtre]

if site_ici_filtre == "Evet":
    f = [v for v in f if any(k in (str(v.get("ozel_kriterler","")) + str(v.get("ozet",""))).lower()
         for k in ["site içi","site ici","siteiçi"])]
elif site_ici_filtre == "Hayır":
    f = [v for v in f if not any(k in (str(v.get("ozel_kriterler","")) + str(v.get("ozet",""))).lower()
         for k in ["site içi","site ici","siteiçi"])]

if esyali_filtre == "Evet":
    f = [v for v in f if any(k in (str(v.get("ozel_kriterler","")) + str(v.get("ozet",""))).lower()
         for k in ["eşyalı","eşyali","eşya","mobilyalı"])]
elif esyali_filtre == "Hayır":
    f = [v for v in f if not any(k in (str(v.get("ozel_kriterler","")) + str(v.get("ozet",""))).lower()
         for k in ["eşyalı","eşyali","eşya","mobilyalı"])]

if kullanim_filtre != "Tümü":
    f = [v for v in f if kullanim_filtre.lower() in (str(v.get("kullanim_durumu","")) +
         str(v.get("ozel_kriterler","")) + str(v.get("ozet",""))).lower()]

if butce_alt > 0 or butce_ust > 0:
    def _butce_sayisal(v):
        return fiyat_sayisal(v.get("max_butce",""))
    if butce_alt > 0:
        f = [v for v in f if _butce_sayisal(v) >= butce_alt]
    if butce_ust > 0:
        f = [v for v in f if _butce_sayisal(v) <= butce_ust]

if favori_filtre:
    f = [v for v in f if v.get("favori", False)]

# ── AŞAMA 3: TARİH KAPSAMI (Dönem) — önce sayaç, sonra uygulama ─────────────
# NOT: Havuz'da azami dönem 60 gündür — "Tüm Zamanlar" seçeneği kaldırıldı.
# 60 günden eski kayıtlar yalnızca Arşiv Merkezi'nden erişilebilir.
_donem_sayilar = {
    "Son 7 Gün": sum(1 for v in f if tarih_gun_farki(en_iyi_tarih(v)) <= 7),
    "Son 30 Gün": sum(1 for v in f if tarih_gun_farki(en_iyi_tarih(v)) <= 30),
    "Son 60 Gün": sum(1 for v in f if tarih_gun_farki(en_iyi_tarih(v)) <= 60),
}

if gun_min > 0:
    f = [v for v in f if tarih_gun_farki(en_iyi_tarih(v)) >= gun_min]
if gun_max > 0:
    f = [v for v in f if tarih_gun_farki(en_iyi_tarih(v)) <= gun_max]

hizli = st.session_state.get("ft_hizli", "Son 7 gün")
if hizli != "Tümü":
    gl = {"Bugün": 0, "Son 7 gün": 7, "Son 30 gün": 30, "Son 60 gün": 60}.get(hizli)
    if gl == 0: f = [v for v in f if tarih_gun_farki(en_iyi_tarih(v)) == 0]
    elif gl is not None: f = [v for v in f if tarih_gun_farki(en_iyi_tarih(v)) <= gl]
if bas_tarih and bit_tarih:
    f = [
        v for v in f
        if (d := tarih_parse(en_iyi_tarih(v))) and bas_tarih <= d.date() <= bit_tarih
    ]

# ── AŞAMA 4: İŞLEM TİPİ SEKMESİ — önce sayaç, sonra uygulama ────────────────
_islem_sayilar = {"Satılık": 0, "Kiralık": 0, "Tespit Edilmemiş": 0}
for v in f:
    _islem_sayilar[_islem_tipi_norm(v)] += 1

talep_islem_sekme_secili = st.session_state.get("talep_islem_sekme", "Satılık")
f = [v for v in f if _islem_tipi_norm(v) == talep_islem_sekme_secili]

# ── AŞAMA 5: FAVORİ / TÜM İLÇELER KAPSAMI — önce sayaç, sonra uygulama ──────
_ilce_kapsam_sayilar = {
    "Tüm İlçeler": len(f),
    "Favori İlçeler": sum(1 for v in f if favori_kaydi_mi(v, fav_ilceler)),
}
talep_ilce_kapsam_secili = st.session_state.get("talep_ilce_kapsam", "Tüm İlçeler")

if talep_ilce_kapsam_secili == "Favori İlçeler":
    f_favori_kapsam = [v for v in f if favori_kaydi_mi(v, fav_ilceler)]
else:
    f_favori_kapsam = f

_fav_secili_ilce_deger = st.session_state.get("fav_secili_ilce")
if talep_ilce_kapsam_secili == "Favori İlçeler" and _fav_secili_ilce_deger:
    f = [v for v in f_favori_kapsam if _fav_secili_ilce_deger in kayit_ilce_listesi(v)]
else:
    f = f_favori_kapsam

f = siralama_uygula(f, siralama)

# ── P0-4: FİLTRE/GÖRÜNÜM İMZASI → SAYFA RESET ────────────────────────────────
# İşlem sekmesi, dönem veya ilçe kapsamı değiştiğinde de favori/ana sayfa 1'e
# dönmeli (yeni filtre mimarisi kabul testi #9/#10).
_talep_filter_signature = (
    hizli, il_filtre, ilce_filtre, danisan_filtre, mulk_filtre,
    str(ara), siralama, bool(favori_filtre), bool(tarih_araligi_aktif),
    str(bas_tarih), str(bit_tarih), butce_alt, butce_ust,
    oda_filtre, bina_yasi_filtre, kat_filtre, site_ici_filtre,
    esyali_filtre, kullanim_filtre, gun_min, gun_max,
    gorunum, bool(st.session_state.get("ft_gizli", False)),
    talep_islem_sekme_secili, st.session_state.get("talep_donem", "Son 7 Gün"),
    talep_ilce_kapsam_secili, _fav_secili_ilce_deger,
)
if st.session_state.get("talep_pagination_signature") != _talep_filter_signature:
    st.session_state["talep_pagination_signature"] = _talep_filter_signature
    st.session_state["talep_fav_page"] = 1
    st.session_state["talep_main_page"] = 1
    st.session_state["talep_fav_page_select"] = 1
    st.session_state["talep_main_page_select"] = 1

# ── YENİ KONTROL SIRASI: İşlem Tipi → Dönem → İlçe Kapsamı ──────────────────
st.markdown(
    '<div style="font-size:10px;font-weight:800;color:#94a3b8;letter-spacing:0.06em;'
    'text-transform:uppercase;margin:4px 0 3px 0;">İşlem Tipi</div>',
    unsafe_allow_html=True,
)
_render_islem_sekmesi("talep_islem_sekme", _islem_sayilar)

st.markdown(
    '<div style="font-size:10px;font-weight:800;color:#94a3b8;letter-spacing:0.06em;'
    'text-transform:uppercase;margin:10px 0 3px 0;">Dönem</div>',
    unsafe_allow_html=True,
)
_render_donem_secimi(
    "talep_donem", _donem_sayilar,
    "ft_hizli", "ft_aralik", "ft_bas", "ft_bit", "ft_gun_min", "ft_gun_max",
)

st.markdown(
    '<div style="font-size:10px;font-weight:800;color:#94a3b8;letter-spacing:0.06em;'
    'text-transform:uppercase;margin:10px 0 3px 0;">İlçe Kapsamı</div>',
    unsafe_allow_html=True,
)
_kapsam_col, _filtre_btn_col = st.columns([3, 1])
with _kapsam_col:
    _render_ilce_kapsami("talep_ilce_kapsam", "fav_secili_ilce", _ilce_kapsam_sayilar)
with _filtre_btn_col:
    if st.button(
        filtre_btn_text,
        key="toggle_filter_panel_btn",
        use_container_width=True,
        type="primary" if st.session_state.get("show_filters_panel") else "secondary"
    ):
        st.session_state["show_filters_panel"] = not st.session_state["show_filters_panel"]
        st.rerun()

# ── FİLTRE PANELİ (gelişmiş) ─────────────────────────────────────────────────
if st.session_state.get("show_filters_panel", False):
    with st.container(border=True):
        tum_iller = sorted(set(il_grubu(v) for v in veriler if il_grubu(v)))
        tum_ilceler = sorted(set(
            ilce for v in veriler
            for ilce in (v.get("ilceler") or [])
            if ilce and ilce != "Diğer Bölge"
        ))
        danismanlar = sorted(set(
            isim_ayikla(v.get("talep_eden_danisan", ""))
            for v in veriler if v.get("talep_eden_danisan", "")
        ))

        if st.session_state.get("ft_il") not in (["Tümü"] + tum_iller + ["Belirtilmemiş"]):
            st.session_state["ft_il"] = "Tümü"
        if st.session_state.get("ft_ilce") not in (["Tümü"] + tum_ilceler):
            st.session_state["ft_ilce"] = "Tümü"
        if st.session_state.get("ft_danisan") not in (["Tümü"] + danismanlar):
            st.session_state["ft_danisan"] = "Tümü"
        if st.session_state.get("ft_mulk") not in ["Tümü", "Konut", "İşyeri", "Arsa", "Belirtilmemiş"]:
            st.session_state["ft_mulk"] = "Tümü"
        if st.session_state.get("ft_siralama") not in ["Tarih ↓", "Tarih ↑", "İlçe A→Z", "İlçe Z→A", "Bütçe ↑", "Bütçe ↓"]:
            st.session_state["ft_siralama"] = "Tarih ↓"

        # ── SATIR 1: Temel filtreler (İşlem Tipi kaldırıldı — ana sekmede) ──
        f1, f2, f3, f4 = st.columns([1.2, 1.2, 1.9, 1.2])
        with f1: st.selectbox("İl", ["Tümü"] + tum_iller + ["Belirtilmemiş"], key="ft_il")
        with f2: st.selectbox("İlçe", ["Tümü"] + tum_ilceler, key="ft_ilce")
        with f3: st.selectbox("Danışman", ["Tümü"] + danismanlar, key="ft_danisan")
        with f4: st.selectbox("Mülk", ["Tümü", "Konut", "İşyeri", "Arsa", "Belirtilmemiş"], key="ft_mulk")

        # ── SATIR 2: Bütçe + Oda + Yapı bilgileri ───────────────────────────
        g1, g2, g3, g4, g5, g6 = st.columns([1.2, 1.2, 1.2, 1.2, 1.2, 1.2])
        with g1:
            st.caption("Bütçe Alt (TL)")
            st.number_input("Bütçe Alt (TL)", min_value=0, step=100000,
                key="ft_butce_alt", label_visibility="collapsed")
        with g2:
            st.caption("Bütçe Üst (TL)")
            st.number_input("Bütçe Üst (TL)", min_value=0, step=100000,
                key="ft_butce_ust", label_visibility="collapsed")

        oda_opts = ["Tümü"] + sorted(set(
            str(v.get("oda_sayisi_m2","")).strip()
            for v in veriler if v.get("oda_sayisi_m2","") not in ("","None",None)
        ))
        with g3: st.selectbox("Oda / M²", oda_opts, key="ft_oda")

        with g4: st.selectbox("Site İçi", ["Tümü","Evet","Hayır"], key="ft_site_ici")
        with g5: st.selectbox("Eşyalı", ["Tümü","Evet","Hayır"], key="ft_esyali")
        with g6: st.selectbox("Kullanım", ["Tümü","Boş","Kiracılı","Malik"], key="ft_kullanim")

        # ── SATIR 3: Yapı + İlan süresi + Sıralama ──────────────────────────
        h1, h2, h3, h4, h5, h6 = st.columns([1.2, 1.2, 1.2, 1.2, 1.2, 1.2])
        byas_opts = ["Tümü"] + sorted(set(
            str(v.get("bina_yasi","")).strip()
            for v in veriler if v.get("bina_yasi","") not in ("","None",None)
        ))
        with h1: st.selectbox("Bina Yaşı", byas_opts, key="ft_bina_yasi")

        kat_opts = ["Tümü"] + sorted(set(
            str(v.get("bulundugu_kat","")).strip()
            for v in veriler if v.get("bulundugu_kat","") not in ("","None",None)
        ))
        with h2: st.selectbox("Bulunduğu Kat", kat_opts, key="ft_kat")

        with h3:
            st.caption("İlan Süresi Min (gün)")
            st.number_input("İlan Süresi Min (gün)", min_value=0, step=1,
                key="ft_gun_min", label_visibility="collapsed")
        with h4:
            st.caption("İlan Süresi Maks (gün)")
            st.number_input("İlan Süresi Maks (gün)", min_value=0, step=1,
                key="ft_gun_max", label_visibility="collapsed")

        with h5: st.text_input("Arama", placeholder="Başlık, ilçe, kriter...", key="ft_ara")
        with h6: st.selectbox("Sıralama", ["Tarih ↓", "Tarih ↑", "İlçe A→Z", "İlçe Z→A", "Bütçe ↑", "Bütçe ↓"], key="ft_siralama")

        # ── SATIR 4: Checkbox'lar + Temizle ─────────────────────────────────
        e1, e2, e3, e4 = st.columns([1.05, 0.95, 1.35, 1.05])
        with e1: st.checkbox("Favori", key="ft_fav")
        with e2: st.checkbox("Gizli", key="ft_gizli")
        with e3: st.checkbox("Tarih Aralığı", key="ft_aralik")
        with e4: st.write(""); st.button("Temizle", key="filtre_temizle_btn", use_container_width=True, on_click=filtre_temizle)

        if st.session_state.get("ft_aralik", False):
            d1, d2, d3 = st.columns([1.3, 1.3, 5.4])
            with d1: st.date_input("Başlangıç", value=st.session_state.get("ft_bas", date.today() - timedelta(days=30)), key="ft_bas")
            with d2: st.date_input("Bitiş", value=st.session_state.get("ft_bit", date.today()), key="ft_bit")

        st.caption(
            "Not: İşlem Tipi artık yukarıdaki ana sekmeden seçiliyor; bu panelde "
            "ayrı bir İşlem Tipi filtresi bulunmuyor (çakışmayı önlemek için kaldırıldı)."
        )

# ── WORKSPACE SEKMELERİ ──────────────────────────────────────────────────────
if "talep_aks_secili_ilce" not in st.session_state:
    st.session_state["talep_aks_secili_ilce"] = None
if "aktif_talep_sekme" not in st.session_state:
    st.session_state["aktif_talep_sekme"] = "Favorilerim"
# Okundu takibi — session bazlı (geçici)
if "goruldu_ids" not in st.session_state:
    st.session_state["goruldu_ids"] = set()

# ── Favori ilçe chip'leri — yalnızca "Favori İlçeler" kapsamı seçiliyken ────
_ws_fav_list = favori_ilceleri_cek()
_ws_fav_secili = st.session_state.get("fav_secili_ilce")

if talep_ilce_kapsam_secili == "Favori İlçeler" and _ws_fav_list:
    _fav_toplam = sum(ilce_kayit_sayisi(f_favori_kapsam, _filce)[0] for _filce in _ws_fav_list[:5])
    fav_cols = st.columns([1.35] + [1.05] * min(len(_ws_fav_list[:5]), 5) + [1.0], gap="small")

    with fav_cols[0]:
        if st.button(
            f"★ Tüm Favoriler · {_fav_toplam}",
            key="fav_chip_tum_favoriler",
            use_container_width=True,
            type="primary" if not _ws_fav_secili else "secondary",
        ):
            st.session_state["fav_secili_ilce"] = None
            st.session_state["aktif_talep_sekme"] = "Favorilerim"
            st.rerun()

    for idx, _filce in enumerate(_ws_fav_list[:5], start=1):
        _ftoplam, _fyeni = ilce_kayit_sayisi(f_favori_kapsam, _filce)
        if _ftoplam == 0:
            continue
        _fsecili = _ws_fav_secili == _filce
        _label = f"★ {_filce} · {_ftoplam}" + (f" · {_fyeni} yeni" if _fyeni > 0 else "")
        with fav_cols[idx]:
            if st.button(
                _label,
                key=f"fav_chip_{safe_key(_filce)}",
                use_container_width=True,
                type="primary" if _fsecili else "secondary",
            ):
                st.session_state["fav_secili_ilce"] = None if _fsecili else _filce
                st.session_state["aktif_talep_sekme"] = "Favorilerim"
                st.rerun()

    with fav_cols[-1]:
        if st.button("+ Favori Ekle", key="fav_chip_ekle", use_container_width=True):
            st.session_state["show_fav_ekle"] = True
            st.rerun()

# ── Sekme değişkenleri (geriye dönük uyumluluk) ──────────────────────────────
aktif_sekme = st.session_state.get("aktif_talep_sekme", "Favorilerim")

fav_secili = st.session_state.get("fav_secili_ilce")
aks_secili = st.session_state.get("talep_aks_secili_ilce")
favori_f = [v for v in f if favori_kaydi_mi(v, fav_ilceler)]
bugun_favori_f = favori_f
bugun_tum_f = f

# ── GÖRÜNÜM TOGGLE ──────────────────────────────────────────────────────────
_gsc = st.columns([0.2, 0.85, 0.85, 6])
for _si, _val, _vlbl in [(_gsc[1],"Kart","  🃏 Kart  "),(_gsc[2],"Tablo","  ≡ Tablo  ")]:
    with _si:
        _aktif = st.session_state.get("ft_gorunum") == _val
        if st.button(_vlbl, key=f"talep_view_{_val}", use_container_width=True,
                     type="primary" if _aktif else "secondary"):
            st.session_state["ft_gorunum"] = _val
            st.rerun()

gorunum = st.session_state.get("ft_gorunum", "Tablo")
if gorunum not in ["Kart", "Tablo"]:
    gorunum = "Tablo"

# ── RENDER: önce Favori Kayıtlar, sonra Diğer ────────────────────────────────

# Seçim açıklaması — İşlem Tipi · Dönem · İlçe Kapsamı(/seçili ilçe) · kayıt sayısı
_secim_kapsam_metin = (
    _fav_secili_ilce_deger
    if (talep_ilce_kapsam_secili == "Favori İlçeler" and _fav_secili_ilce_deger)
    else talep_ilce_kapsam_secili
)
st.caption(
    f"{talep_islem_sekme_secili} · {st.session_state.get('talep_donem', 'Son 7 Gün')} · "
    f"{_secim_kapsam_metin} · {len(f)} kayıt"
)

# Favori Kayıtlar bölümü
fav_render = (
    [v for v in bugun_favori_f if _ws_fav_secili in kayit_ilce_listesi(v)]
    if _ws_fav_secili else bugun_favori_f
)

FAVORITE_PAGE_SIZE = 10
MAIN_PAGE_SIZE = 25

if fav_render:
    st.markdown(
        '<div style="font-size:11px;font-weight:800;color:#92400e;text-transform:uppercase;'
        'letter-spacing:0.08em;padding:10px 0 6px 0;border-bottom:1px solid #fde68a;margin-bottom:6px;">'
        '★ Favori Kayıtlar</div>',
        unsafe_allow_html=True
    )
    fav_page_items, fav_page, fav_total_pages, fav_start = _page_slice(
        fav_render, "talep_fav_page", FAVORITE_PAGE_SIZE
    )
    if gorunum == "Tablo":
        tablo_goster_html(fav_page_items, prefix="fav_tbl")
    elif gorunum == "Kart":
        cols3 = st.columns(2, gap="medium")
        for idx, v in enumerate(fav_page_items):
            with cols3[idx % 2]:
                kid      = v.get("id")
                yeni     = tarih_gun_farki(en_iyi_tarih(v)) <= 7
                okundu_k = kid in st.session_state.get("goruldu_ids", set())
                favori_k = v.get("favori", False)
                if okundu_k:
                    _rozet_k = '<span style="background:#f1f5f9;color:#64748b;font-size:10px;font-weight:700;padding:3px 9px;border-radius:5px;">Görüldü</span>'
                elif yeni:
                    _rozet_k = '<span style="background:#16a34a;color:#fff;font-size:10px;font-weight:700;padding:3px 9px;border-radius:5px;">Yeni</span>'
                else:
                    _rozet_k = ""
                st.markdown(nkart_html(v, rozet_html=_rozet_k), unsafe_allow_html=True)
                _bc1, _bc2, _bc3 = st.columns([3, 1, 1])
                with _bc1:
                    if st.button("Detay →", key=f"fav_kart_detay_{kid}", use_container_width=True, type="primary"):
                        st.session_state.setdefault("goruldu_ids", set()).add(kid)
                        talep_detay_dialog(v, ilce_sec)
                with _bc2:
                    _fstar = "★" if favori_k else "☆"
                    if st.button(_fstar, key=f"fav_kart_fav_{kid}", use_container_width=True):
                        favori_guncelle(kid, favori_k)
                with _bc3:
                    if st.button("⋯", key=f"fav_kart_more_{kid}", use_container_width=True):
                        st.session_state[f"more_open_{kid}"] = not st.session_state.get(f"more_open_{kid}", False)
                        st.rerun()
                if st.session_state.get(f"more_open_{kid}", False):
                    with st.container():
                        _m1, _m2 = st.columns(2)
                        with _m1:
                            if st.button("Düzenle", key=f"fav_kart_dz_{kid}", use_container_width=True, type="secondary"):
                                st.session_state[f"duzen_{kid}"] = not st.session_state.get(f"duzen_{kid}", False)
                                st.session_state[f"more_open_{kid}"] = False
                                st.rerun()
                        with _m2:
                            if st.button("Gizle", key=f"fav_kart_giz_{kid}", use_container_width=True, type="secondary"):
                                get_client().table("alici_talepleri").update({"gizli": True}).eq("id", kid).execute()
                                verileri_yukle.clear(); st.rerun()
                if st.session_state.get(f"duzen_{kid}", False):
                    duzenleme_formu(v, ilce_sec)
    _render_pagination_controls(
        "talep_fav_page", fav_page, fav_total_pages, len(fav_render),
        fav_start, FAVORITE_PAGE_SIZE, " · Favori Kayıtlar"
    )
else:
    # Liste tamamen boşaldı — _page_slice() hiç çağrılmadı, stale state'i temizle.
    _clear_stale_page_state("talep_fav_page")

# Diğer bölüm — başlık seçili İşlem Tipi sekmesine göre dinamik
# P0-2 DÜZELTMESİ: Önceden burada `diger_f` hesaplanıp kullanılmıyor, tekrar
# `f` (favoriler dahil) render ediliyordu — favori kayıtlar iki kez basılıyordu.
# Artık yalnızca favori OLMAYAN kayıtlar (diger_f) bu bölümde gösteriliyor.
diger_f = [v for v in f if not favori_kaydi_mi(v, fav_ilceler)]

if talep_islem_sekme_secili == "Tespit Edilmemiş":
    _diger_baslik = "İncelenecek Talepler"
else:
    _diger_baslik = f"Diğer {talep_islem_sekme_secili} Talepler"

if PERF_DEBUG:
    st.caption(
        f"[PERF] filtrelenmiş toplam: {len(f)} · favori: {len(fav_render)} · "
        f"diğer: {len(diger_f)} · sayfa başına render: "
        f"{min(len(fav_render), FAVORITE_PAGE_SIZE) + min(len(diger_f), MAIN_PAGE_SIZE)}"
    )

if not f:
    st.info("Bu dönemde kayıt bulunamadı.")
    _clear_stale_page_state("talep_main_page")
elif not diger_f:
    st.caption("Filtreyle eşleşen tüm kayıtlar yukarıdaki Favori Kayıtlar bölümünde gösteriliyor.")
    _clear_stale_page_state("talep_main_page")
else:
    st.markdown(
        f'<div style="font-size:11px;font-weight:800;color:#355C7D;text-transform:uppercase;'
        f'letter-spacing:0.08em;padding:14px 0 6px 0;border-bottom:1px solid #dce4ee;margin-bottom:6px;">'
        f'{_diger_baslik} · <span style="font-weight:500;color:#64748b;">{len(diger_f)} kayıt</span></div>',
        unsafe_allow_html=True
    )
    diger_page_items, diger_page, diger_total_pages, diger_start = _page_slice(
        diger_f, "talep_main_page", MAIN_PAGE_SIZE
    )
    if gorunum == "Tablo":
        tablo_goster_html(diger_page_items, prefix="tum_tbl")
    elif gorunum == "Kart":
        cols3 = st.columns(2, gap="medium")
        for idx, v in enumerate(diger_page_items):
            with cols3[idx % 2]:
                kid  = v.get("id")
                yeni = tarih_gun_farki(en_iyi_tarih(v)) <= 7
                okundu_k = kid in st.session_state.get("goruldu_ids", set())
                favori_k = v.get("favori", False)
                if okundu_k:
                    _rozet_k = '<span style="background:#f1f5f9;color:#64748b;font-size:10px;font-weight:700;padding:3px 9px;border-radius:5px;">Görüldü</span>'
                elif yeni:
                    _rozet_k = '<span style="background:#16a34a;color:#fff;font-size:10px;font-weight:700;padding:3px 9px;border-radius:5px;">Yeni</span>'
                else:
                    _rozet_k = ""
                st.markdown(nkart_html(v, rozet_html=_rozet_k), unsafe_allow_html=True)
                _tc1, _tc2, _tc3 = st.columns([3, 1, 1])
                with _tc1:
                    if st.button("Detay →", key=f"tum_detay_{kid}", use_container_width=True, type="primary"):
                        st.session_state.setdefault("goruldu_ids", set()).add(kid)
                        talep_detay_dialog(v, ilce_sec)
                with _tc2:
                    _fstar = "★" if favori_k else "☆"
                    if st.button(_fstar, key=f"tum_fav_{kid}", use_container_width=True):
                        favori_guncelle(kid, favori_k)
                with _tc3:
                    if st.button("⋯", key=f"tum_more_{kid}", use_container_width=True):
                        st.session_state[f"tmore_open_{kid}"] = not st.session_state.get(f"tmore_open_{kid}", False)
                        st.rerun()
                if st.session_state.get(f"tmore_open_{kid}", False):
                    _m1, _m2 = st.columns(2)
                    with _m1:
                        if st.button("Düzenle", key=f"tum_dz_{kid}", use_container_width=True, type="secondary"):
                            st.session_state[f"duzen_{kid}"] = not st.session_state.get(f"duzen_{kid}", False)
                            st.session_state[f"tmore_open_{kid}"] = False
                            st.rerun()
                    with _m2:
                        if st.button("Gizle", key=f"tum_giz_{kid}", use_container_width=True, type="secondary"):
                            get_client().table("alici_talepleri").update({"gizli": True}).eq("id", kid).execute()
                            verileri_yukle.clear(); st.rerun()
                if st.session_state.get(f"duzen_{kid}", False):
                    duzenleme_formu(v, ilce_sec)
    _render_pagination_controls(
        "talep_main_page", diger_page, diger_total_pages, len(diger_f),
        diger_start, MAIN_PAGE_SIZE, f" · {_diger_baslik}"
    )
if PERF_DEBUG:
    st.caption(f"[PERF] SAYFA TOPLAM (script başından sonuna): {time.time()-_t_sayfa0:.2f}s")
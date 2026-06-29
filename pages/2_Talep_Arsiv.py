import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.supabase_client import get_client
from core.ui_helpers import render_navbar, render_page_header
import pandas as pd
import re
from datetime import date, timedelta, datetime
from email.utils import parsedate_to_datetime


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
    border: 0.5px solid #e2e8f0;
    border-radius: 12px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    transition: border-color 0.15s, box-shadow 0.15s;
    margin-bottom: 10px;
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
    border-top: 0.5px solid #e9eef5;
    padding: 8px 14px;
    background: #f8fafc;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
}
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
/* Tablo seç butonu görünmez */
.zt-table-wrap + div [data-testid="stColumn"]:first-child [data-testid="stButton"] > button {
    opacity: 0 !important;
    width: 1px !important;
    min-width: 1px !important;
    padding: 0 !important;
    pointer-events: none !important;
}

</style>
""", unsafe_allow_html=True)

# ── SIDEBAR — CSS'den hemen sonra çağır (collapsed sorunu önler) ─────────────
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
    """Tarih string'ini datetime olarak döndürür (saat dahil)."""
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
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")


def not_kaydet(kid, metin):
    try:
        get_client().table("alici_talepleri").update({"not_alani": metin}).eq("id", kid).execute()
        st.cache_data.clear()
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
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Hata: {e}")


@st.cache_data(ttl=30)
def verileri_yukle(kaynak_filtre=None):
    """ARŞİV MODU: en_iyi_tarih() ile 45 günden eski kayıtları döndürür."""
    ESIK_GUN = 45
    try:
        q = (
            get_client()
            .table("alici_talepleri")
            .select("*")
            .eq("kategori", "alici_talebi")
            .order("olusturma_tarihi", desc=True)
            .limit(2000)
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
        return [v for v in tum if tarih_gun_farki(en_iyi_tarih(v)) > ESIK_GUN]
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
        st.cache_data.clear()
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
    st.session_state["ft_islem"] = "Tümü"
    st.session_state["ft_siralama"] = "Tarih ↓"
    st.session_state["ft_hizli"] = "Son 3 ay"
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
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")


def belirtilmemise_tasi(kid):
    try:
        get_client().table("alici_talepleri").update(
            {"il": "", "ilce": "", "ilceler": [], "mahalle": "", "bolge": ""}
        ).eq("id", kid).execute()
        st.session_state[f"guncellendi_{kid}"] = True
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")


def kayit_sil(kid):
    try:
        get_client().table("alici_talepleri").delete().eq("id", kid).execute()
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Silme hatası: {e}")


def kayit_gizle(kid):
    try:
        get_client().table("alici_talepleri").update({"gizli": True}).eq("id", kid).execute()
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")


def not_kaydet_fn(kid, metin):
    try:
        get_client().table("alici_talepleri").update({"not_alani": metin}).eq("id", kid).execute()
        st.cache_data.clear()
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


def tablo_goster_html(kayitlar, prefix="tbl"):
    """Mockup tablo görünümü — HTML tablo + inline aksiyon butonları."""
    if not kayitlar:
        st.info("Gösterilecek kayıt yok.")
        return

    # Tablo sütun oranları — tablo genişliğiyle hizalı
    # Başlık(4) | İlçe(1.5) | Tip(1.2) | Bütçe(2.2) | Danışman(2) | Tarih(1.2) | Detay(1) | Fav(0.5) | Dz(0.5)
    COL_RATIOS = [4, 1.5, 1.2, 2.2, 2, 1.2, 1, 0.5, 0.5]

    # Renk açıklaması (legend)
    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;"'        'font-size:10px;color:#94a3b8;">'        '<span style="display:flex;align-items:center;gap:4px;">'        '<span style="width:7px;height:7px;border-radius:50%;background:#16a34a;display:inline-block;"></span>'        '<span style="font-size:10px;color:#94a3b8;">≤7 gün</span></span>'        '<span style="display:flex;align-items:center;gap:4px;">'        '<span style="width:7px;height:7px;border-radius:50%;background:#ca8a04;display:inline-block;"></span>'        '<span style="font-size:10px;color:#94a3b8;">8-30 gün</span></span>'        '<span style="display:flex;align-items:center;gap:4px;">'        '<span style="width:7px;height:7px;border-radius:50%;background:#ea580c;display:inline-block;"></span>'        '<span style="font-size:10px;color:#94a3b8;">31-90 gün</span></span>'        '<span style="display:flex;align-items:center;gap:4px;">'        '<span style="width:7px;height:7px;border-radius:50%;background:#dc2626;display:inline-block;"></span>'        '<span style="font-size:10px;color:#94a3b8;">>90 gün</span></span>'        '<span style="display:flex;align-items:center;gap:4px;">'        '<span style="width:7px;height:7px;border-radius:50%;background:#cbd5e1;display:inline-block;"></span>'        '<span style="font-size:10px;color:#94a3b8;">Görüldü</span></span>'        '</div>',
        unsafe_allow_html=True
    )

    # Başlık satırı
    h = st.columns(COL_RATIOS)
    headers = ["Talep Başlığı", "İlçe", "Tip", "Bütçe", "Danışman", "Tarih", "", "", ""]
    for col, hdr in zip(h, headers):
        with col:
            st.markdown(
                f'<div style="font-size:10px;font-weight:600;color:#94a3b8;'                f'text-transform:uppercase;letter-spacing:0.06em;'                f'padding:8px 0 6px;border-bottom:1px solid #e2e8f0;">{hdr}</div>',
                unsafe_allow_html=True
            )

    # Veri satırları
    for v in kayitlar:
        kid = v.get("id", "")
        ui = build_talep_ui_model(v)
        isim = isim_ayikla(v.get("talep_eden_danisan", ""))
        ilce = ilce_grubu(v) or "—"
        islem = v.get("islem_tipi", "") or ""
        butce = v.get("max_butce", "") or "—"
        favori = v.get("favori", False)
        gun_farki = tarih_gun_farki(en_iyi_tarih(v))
        yeni = gun_farki <= 7
        okundu = kid in st.session_state.get("goruldu_ids", set())
        _tarih_fg, _tarih_bg, dot_c = tarih_renk_bilgisi(gun_farki)

        tarih_d = tarih_parse(en_iyi_tarih(v))
        if tarih_d:
            _has_t = hasattr(tarih_d, "hour") and (tarih_d.hour != 0 or tarih_d.minute != 0)
            tarih_str = tarih_d.strftime("%d.%m %H:%M") if _has_t else tarih_d.strftime("%d.%m.%Y")
        else:
            tarih_str = "—"

        # Okundu ise gri, favoriyse amber, aksi halde yaş rengi
        if okundu:
            dot_c = "#cbd5e1"
            _tarih_fg = "#94a3b8"
            _tarih_bg = "#f8fafc"

        # İlçe rengi
        aks_r = aks_renk_bul([ilce] if ilce != "—" else [])

        # Tip
        if "iralık" in islem: tip_bg, tip_color, tip_lbl = "#f0fdf4","#166534","Kiralık"
        elif "atılık" in islem: tip_bg, tip_color, tip_lbl = "#fef2f2","#991b1b","Satılık"
        else: tip_bg, tip_color, tip_lbl = "#f8fafc","#64748b", islem or "—"

        # Avatar
        initials = "".join(w[0].upper() for w in isim.split()[:2]) if isim else "?"

        ROW_BORDER = "border-bottom:0.5px solid #f1f5f9;padding:8px 0;"

        row = st.columns(COL_RATIOS)
        with row[0]:
            baslik = ui.get("baslik","") or "—"
            kriter = (ui.get("kriter_ozet","") or "")[:55]
            st.markdown(
                f'<div style="{ROW_BORDER}">'                f'<div style="display:flex;align-items:center;gap:6px;">'                f'<span style="width:6px;height:6px;border-radius:50%;background:{dot_c};flex-shrink:0;display:inline-block;"></span>'                f'<span style="font-size:12px;font-weight:600;color:#1e293b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:95%;display:block;">{baslik}</span>'                f'</div>'                + (f'<div style="font-size:10.5px;color:#64748b;margin-left:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{kriter}</div>' if kriter else "")
                + f'</div>',
                unsafe_allow_html=True
            )
        with row[1]:
            st.markdown(
                f'<div style="{ROW_BORDER}">'                f'<span style="background:{aks_r["bg"]};color:{aks_r["text"]};'                f'padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600;">{ilce}</span>'                f'</div>',
                unsafe_allow_html=True
            )
        with row[2]:
            st.markdown(
                f'<div style="{ROW_BORDER}">'                f'<span style="background:{tip_bg};color:{tip_color};'                f'padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600;">{tip_lbl}</span>'                f'</div>',
                unsafe_allow_html=True
            )
        with row[3]:
            st.markdown(
                f'<div style="{ROW_BORDER};font-size:11.5px;font-weight:600;color:#0f172a;">{butce}</div>',
                unsafe_allow_html=True
            )
        with row[4]:
            st.markdown(
                f'<div style="{ROW_BORDER};display:flex;align-items:center;gap:5px;">'                f'<span style="width:20px;height:20px;border-radius:50%;'                f'background:{aks_r["bg"]};color:{aks_r["text"]};'                f'display:inline-flex;align-items:center;justify-content:center;'                f'font-size:8px;font-weight:700;flex-shrink:0;">{initials}</span>'                f'<span style="font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{isim or "—"}</span>'                f'</div>',
                unsafe_allow_html=True
            )
        with row[5]:
            st.markdown(
                f'<div style="{ROW_BORDER}">'                f'<span style="background:{_tarih_bg};color:{_tarih_fg};'                f'font-size:10.5px;font-weight:600;'                f'padding:2px 6px;border-radius:4px;white-space:nowrap;">{tarih_str}</span>'                f'</div>',
                unsafe_allow_html=True
            )
        with row[6]:
            if st.button("Detay", key=f"{prefix}_detay_{kid}", use_container_width=True, type="primary"):
                st.session_state.setdefault("goruldu_ids", set()).add(kid)
                talep_detay_modal(v, st.session_state.get("aktif_ilce_sec"))
        with row[7]:
            _fl = "★" if favori else "☆"
            if st.button(_fl, key=f"{prefix}_fav_{kid}", use_container_width=True):
                favori_guncelle(kid, favori)
        with row[8]:
            if st.button("✏", key=f"{prefix}_dz_{kid}", use_container_width=True):
                st.session_state[f"duzen_{kid}"] = not st.session_state.get(f"duzen_{kid}", False)
                st.rerun()


def kayit_karti(v, ilce_sec):
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

    etiketler = etiket_html(mulk) + etiket_html(islem)
    if yeni_kayit:
        etiketler += (
            '<span style="background:#fffbeb;color:#92400e;border:1px solid #fde68a;'
            'padding:2px 8px;border-radius:999px;font-size:10.5px;font-weight:650;'
            'letter-spacing:0.1px;margin-right:4px;display:inline-block;">yeni</span>'
        )
    if len(ilceler_list) > 1:
        ils = ", ".join(ilceler_list[:3])
        if len(ilceler_list) > 3:
            ils += f" +{len(ilceler_list)-3}"
        etiketler += (
            f'<span style="background:#fffbeb;color:#92400e;border:1px solid #fde68a;'
            f'padding:2px 8px;border-radius:999px;font-size:10.5px;font-weight:650;'
            f'letter-spacing:0.1px;margin-right:4px;display:inline-block;">{ils}</span>'
        )

    # Normalize başlık
    ilan_baslik = ui["baslik"]
    lokasyon_str = ui["lokasyon_ozet"]

    _fg, _bg, _dot = tarih_renk_bilgisi(gun_farki)

    # Tarih renk noktası HTML
    tarih_html = (
        f'<span style="display:inline-flex;align-items:center;gap:4px;">'
        f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:{_dot};flex-shrink:0;"></span>'
        f'<span style="color:{_fg};font-weight:600;font-size:11px;">{tarih_g}</span>'
        f'</span>'
        if tarih_g else ""
    )

    # Aks rengi hesapla (lokasyon metni için)
    aks_renk = aks_renk_bul(ilceler_list or [
        v.get("ilce",""), v.get("bolge",""), v.get("mahalle","")
    ])

    # Sol şerit: sadece durum bilgisi — yeni=yeşil, okundu=gri, favori=amber, normal=nötr
    if okundu:
        left_border = "#cbd5e1"
    elif yeni_kayit:
        left_border = "#16a34a"
    elif favori:
        left_border = "#f59e0b"
    else:
        left_border = "#e2e8f0"   # nötr — aks rengi sol borderde yok, üst şeritte
    card_bg = "#ffffff"

    kriter_ozet_str = ui.get("kriter_ozet", "")

    # Köşe rozeti: yeni=yeşil, okundu=gri tik, normal=yok
    if okundu:
        _rozet_html = (
            '<span style="position:absolute;top:8px;right:10px;'
            'background:#e2e8f0;color:#94a3b8;font-size:10px;font-weight:700;'
            'padding:2px 8px;border-radius:999px;letter-spacing:0.03em;">✓ Görüldü</span>'
        )
    elif yeni_kayit:
        _rozet_html = '<span class="kart-yeni-rozet">YENİ</span>'
    else:
        _rozet_html = ""

    # Üst aks şeridi
    _aks_bar = aks_bar_gradient(ilceler_list)

    st.markdown(
        f'<div class="kart-wrapper" style="border:1px solid #dce4ee;'
        f'border-left:4px solid {left_border};'
        f'border-radius:12px;overflow:hidden;margin-bottom:3px;'
        f'background:{card_bg};box-shadow:0 2px 8px rgba(15,23,42,0.05);">'
        f'<div style="height:3px;background:{_aks_bar};width:100%;"></div>'
        f'<div style="padding:10px 14px 10px 14px;">'
        f'{_rozet_html}'
        # 1. LOKASYON — aks rengi
        # 1. LOKASYON — renk değişmez, her zaman canlı
        + (
            f'<span style="font-size:12px;font-style:italic;font-weight:750;'
            f'color:{aks_renk["text"]};'
            f'letter-spacing:0.06em;text-transform:uppercase;margin-bottom:5px;display:block;">'
            f'{lokasyon_str}</span>'
            if lokasyon_str else ""
        )
        # 2. BAŞLIK — amber bant her zaman kalır
        + f'<div style="background:#FFF9ED;border-left:3px solid #F4B740;'
        f'padding:5px 10px;border-radius:0 6px 6px 0;margin-bottom:6px;">'
        f'<div style="font-size:1.0rem;font-weight:800;color:#172B4D;line-height:1.25;'
        f'display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">{ilan_baslik}</div>'
        f'</div>'
        # 3. KRİTER NOTU
        + (f'<div class="kart-kriter">{kriter_ozet_str}</div>' if kriter_ozet_str else "")
        # 4. META SATIRI
        + f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:6px;">'
        f'<span style="font-size:0.91rem;font-weight:750;color:#172B4D;">{str(butce) if butce else "—"}</span>'
        + (f'<span style="font-size:0.82rem;font-weight:600;color:#475569;">{oda}</span>' if oda else "")
        + f'<span style="font-size:11px;font-weight:600;color:#94a3b8;margin-left:2px;">{isim}</span>'
        f'{etiketler}'
        + (f'<span style="margin-left:auto;">{tarih_html}</span>' if tarih_html else "")
        + f'</div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Aksiyon butonları ────────────────────────────────────────────────────
    a_detay, a_sunum, a_fav, a_duz, a_giz, a_spacer = st.columns([1.4, 1.5, 0.65, 0.65, 0.65, 5.15])

    with a_detay:
        if st.button("Detay", key=f"detay_btn_{kid}", type="primary", use_container_width=True):
            # Görüldü olarak işaretle
            st.session_state.setdefault("goruldu_ids", set()).add(kid)
            talep_detay_modal(v, ilce_sec)

    with a_sunum:
        _t_takip = st.session_state.get(f"takip_t_{kid}", False)
        if st.button("⭐ Takipte" if _t_takip else "☆ Takibe Al",
                     key=f"t_takip_{kid}", use_container_width=True):
            _takip_listesi = st.session_state.setdefault("takip_listesi", {})
            if _t_takip:
                _takip_listesi.pop(str(kid), None)
                st.session_state[f"takip_t_{kid}"] = False
                st.toast("Takipten çıkarıldı.")
            else:
                _takip_listesi[str(kid)] = dict(v)
                _takip_listesi[str(kid)]["_takip_kaynak"] = "talep_havuzu"
                st.session_state[f"takip_t_{kid}"] = True
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
                get_client().table("alici_talepleri").update({"gizli": False}).eq("id", kid).execute()
                st.cache_data.clear()
                st.rerun()
            else:
                kayit_gizle(kid)

    # Sil butonu — sadece manuel kayıtlar
    kaynak_v = v.get("kaynak", "")
    if kaynak_v and kaynak_v != "startkey_mail":
        sil_key = f"tsil_onay_{kid}"
        if not st.session_state.get(sil_key):
            if st.button("🗑", key=f"tsil_{kid}", help="Kaydı sil"):
                st.session_state[sil_key] = True
                st.rerun()
        else:
            st.warning("⚠️ Bu kaydı silmek istediğinizden emin misiniz?")
            sc1, sc2 = st.columns([1, 1])
            with sc1:
                if st.button("🗑 Evet, Sil", key=f"tsil_evet_{kid}", type="primary"):
                    kayit_sil(kid)
                    st.toast("✅ Kayıt silindi.")
            with sc2:
                if st.button("İptal", key=f"tsil_iptal_{kid}"):
                    st.session_state.pop(sil_key, None)
                    st.rerun()

    if duzen_modu:
        duzenleme_formu(v, ilce_sec)

    st.markdown("<div style='height:1px'></div>", unsafe_allow_html=True)


@st.dialog("Talep Detayı", width="large")
def talep_detay_modal(v, ilce_sec):
    """Popup modal — talep detayını gösterir."""
    kid = v.get("id")
    isim = isim_ayikla(v.get("talep_eden_danisan", ""))
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

    # ── Başlık ──
    st.markdown(
        f'<div style="background:#FFF9ED;border-left:4px solid #F4B740;padding:10px 14px;'
        f'border-radius:0 8px 8px 0;margin-bottom:12px;">' 
        f'<div style="font-size:1.15rem;font-weight:800;color:#172B4D;line-height:1.25;">{ui["baslik"]}</div>'
        + (f'<div style="font-size:0.83rem;color:#355C7D;font-weight:600;margin-top:4px;">📍 {ui["lokasyon_ozet"]}</div>' if ui["lokasyon_ozet"] else "")
        + f'</div>',
        unsafe_allow_html=True,
    )

    # ── Meta grid ──
    etiketler_m = etiket_html(mulk) + etiket_html(islem)
    if yeni_kayit:
        etiketler_m += (
            '<span style="background:#fffbeb;color:#92400e;border:1px solid #fde68a;'
            'padding:2px 8px;border-radius:999px;font-size:10.5px;font-weight:650;margin-right:4px;">yeni</span>'
        )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:2px;">Danışman</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:13px;font-weight:600;color:#172B4D;">{isim or "—"}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:2px;">Bütçe</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:13px;font-weight:700;color:#172B4D;">{"💰 "+butce if butce else "—"}</div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:2px;">Oda / M²</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:13px;font-weight:600;color:#172B4D;">{"🏠 "+oda if oda else "—"}</div>', unsafe_allow_html=True)

    st.markdown("<div style='margin:8px 0 4px 0;'>", unsafe_allow_html=True)
    st.markdown(etiketler_m, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # ── Lokasyon detay ──
    if ilceler_list or mahalle or bolge:
        st.markdown(f'<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:4px;">İlçeler</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:13px;color:#374151;margin-bottom:8px;">{", ".join(ilceler_list) if ilceler_list else "—"}</div>', unsafe_allow_html=True)
        row2a, row2b = st.columns(2)
        with row2a:
            st.markdown(f'<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:2px;">Mahalle</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:13px;color:#374151;">{mahalle or "—"}</div>', unsafe_allow_html=True)
        with row2b:
            st.markdown(f'<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:2px;">Bölge</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:13px;color:#374151;">{bolge or "—"}</div>', unsafe_allow_html=True)

    # ── Özel kriterler ──
    if v.get("ozel_kriterler"):
        st.markdown(
            f'<div style="background:#FFF9ED;border-left:3px solid #F4B740;padding:8px 12px;'
            f'border-radius:4px;font-size:12px;color:#475569;margin-top:8px;">'
            f'<b>Özel Kriterler:</b> {v.get("ozel_kriterler","")}</div>',
            unsafe_allow_html=True,
        )

    # ── Mail içeriği ──
    ic = html_temizle(v.get("mail_icerigi", ""))
    if ic:
        st.markdown(f'<div style="font-size:11px;color:#64748b;font-weight:700;margin-top:10px;margin-bottom:3px;">📧 {v.get("mail_konusu","")}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="background:#f0f4ff;border-left:3px solid #2d7dd2;padding:8px 12px;'
            f'border-radius:6px;font-size:11px;line-height:1.6;max-height:200px;overflow-y:auto;color:#374151;">{ic[:1500]}</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Not alanı ──
    not_m = v.get("not_alani", "") or ""
    yn = st.text_area("Not", value=not_m, height=80, placeholder="Not ekle...",
                      key=f"modal_not_{kid}", label_visibility="collapsed")
    nb1, nb2 = st.columns([1, 3])
    with nb1:
        if st.button("💾 Notu Kaydet", key=f"modal_nb_{kid}", type="primary", use_container_width=True):
            not_kaydet_fn(kid, yn)

    # ── Aksiyon satırı ──
    st.divider()
    ma1, ma2, ma3 = st.columns(3)
    with ma1:
        fav_label = "★ Favoriden Çıkar" if favori else "☆ Favoriye Ekle"
        if st.button(fav_label, key=f"modal_fav_{kid}", use_container_width=True):
            favori_guncelle(kid, favori)
    with ma2:
        if v.get("il", "") or v.get("ilce", ""):
            if st.button("📦 Belirtilmemişe Taşı", key=f"modal_blt_{kid}", use_container_width=True):
                belirtilmemise_tasi(kid)
    with ma3:
        giz_label = "👁 Göster" if gizli else "⊘ Gizle"
        if st.button(giz_label, key=f"modal_giz_{kid}", use_container_width=True):
            if gizli:
                get_client().table("alici_talepleri").update({"gizli": False}).eq("id", kid).execute()
            else:
                get_client().table("alici_talepleri").update({"gizli": True}).eq("id", kid).execute()
            st.cache_data.clear()
            st.rerun()


def render_talep_detay(v, ilce_sec):
    """Eski inline detay — artık kullanılmıyor, modal'a geçildi."""
    talep_detay_modal(v, ilce_sec)

def ilce_bar(ilce, kayitlar, ilce_sec, key_prefix="", her_zaman_acik=False):
    kid_key = f"{key_prefix}_{safe_key(ilce)}_acik"

    if her_zaman_acik and kid_key not in st.session_state:
        st.session_state[kid_key] = True

    acik = st.session_state.get(kid_key, False)
    toplam = len(kayitlar)
    yeni = sum(1 for v in kayitlar if tarih_gun_farki(en_iyi_tarih(v)) <= 7)

    if key_prefix == "fav":
        yeni_str = f"  🟢 {yeni} yeni" if yeni > 0 else ""
        label = f"★ {ilce} — {toplam} talep{yeni_str}"

        if st.button(
            label,
            key=f"bar_{key_prefix}_{safe_key(ilce)}",
            use_container_width=True,
            type="secondary"
        ):
            st.session_state[kid_key] = not acik
            st.rerun()

    else:
        yeni_str = f"  🟢 {yeni} yeni" if yeni > 0 else ""
        if st.button(
            f"{ilce}    {toplam} talep{yeni_str}",
            key=f"bar_{key_prefix}_{safe_key(ilce)}",
            use_container_width=True
        ):
            st.session_state[kid_key] = not acik
            st.rerun()

    if acik:
        for v in kayitlar:
            kayit_karti(v, ilce_sec)


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


# ── KAYNAK SEKMELERİ ─────────────────────────────────────────────────────────
kaynak_tab = st.session_state.get("aktif_kaynak_tab", "startkey")

if kaynak_tab == "startkey":
    veriler = verileri_yukle("startkey_mail")
elif kaynak_tab == "ofis":
    veriler = verileri_yukle(["zeta1", "zeta2", "ofis"])
elif kaynak_tab == "dis":
    veriler = verileri_yukle("dis_kaynak")
else:
    veriler = verileri_yukle(None)

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
    "ft_hizli": "Son 3 ay",
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
    "ft_gorunum": "Liste",
    "aktif_talep_workspace": "Tümü",
    "fav_secili_ilce": None,
    "compact_mode": False,
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
        "📦 Talep Arşivi",
        f"45 günden eski kayıtlar · {len(veriler)} kayıt · {danisman_sayisi} danışman"
    )
with _hdr2:
    st.markdown("<div style='margin-top:14px'>", unsafe_allow_html=True)
    if st.button("↺", key="talep_yenile", help="Yenile", use_container_width=True):
        st.cache_data.clear(); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    '<div style="background:#FFF9ED;border-left:4px solid #F4B740;padding:8px 14px;'
    'border-radius:6px;margin-bottom:10px;font-size:12px;color:#92400e;">'
    '📦 <b>Arşiv görünümü</b> — 45 günden eski talepler. Aktif kayıtlar için '
    '<a href="/2_Talep_Tablosu" style="color:#92400e;font-weight:700;">Talep Merkezi</a>\'ni kullanın.'
    '</div>',
    unsafe_allow_html=True
)

# ── KAYNAK SEKMELERİ ─────────────────────────────────────────────────────────
ks1, ks2, ks3, ks4, ks_sp = st.columns([1, 1, 1.2, 1.5, 4.3])
with ks1:
    if st.button("Tümü", key="ktab_tumu", use_container_width=True,
                 type="primary" if kaynak_tab == "tumu" else "secondary"):
        st.session_state["aktif_kaynak_tab"] = "tumu"; st.rerun()
with ks2:
    if st.button("🏢 Ofis", key="ktab_ofis", use_container_width=True,
                 type="primary" if kaynak_tab == "ofis" else "secondary"):
        st.session_state["aktif_kaynak_tab"] = "ofis"; st.rerun()
with ks3:
    if st.button("📧 Startkey", key="ktab_startkey", use_container_width=True,
                 type="primary" if kaynak_tab == "startkey" else "secondary"):
        st.session_state["aktif_kaynak_tab"] = "startkey"; st.rerun()
with ks4:
    if st.button("🌐 Dış Kaynak", key="ktab_dis", use_container_width=True,
                 type="primary" if kaynak_tab == "dis" else "secondary"):
        st.session_state["aktif_kaynak_tab"] = "dis"; st.rerun()

kaynak_tab = st.session_state.get("aktif_kaynak_tab", "startkey")

if not veriler:
    kaynak_etiket = {"tumu":"Tümü","startkey":"Startkey","ofis":"Ofis","dis":"Dış Kaynak"}.get(kaynak_tab,"")
    st.info(f"{kaynak_etiket} kaynağında henüz kayıt bulunamadı.")
    if kaynak_tab != "startkey":
        kaynak_db = {"ofis": "ofis", "dis": "dis_kaynak"}.get(kaynak_tab, "ofis")
        kaynak_et = {"ofis": "🏢 Ofis", "dis": "🌐 Dış Kaynak"}.get(kaynak_tab, "")
        ilce_sec = ilce_listesi_cek()
        yeni_talep_modal(kaynak_db, kaynak_et, ilce_sec)
    st.stop()

# KPI strip kaldırıldı — hızlı filtre butonları yeterli

# ── TOOLBAR: Hızlı filtreler + Görünüm + Compact + Filtreler ─────────────────
allowed_hizli = ["Tümü", "Son 3 ay", "Son 6 ay", "Son 1 yıl"]

if st.session_state.get("ft_hizli", "Son 3 ay") not in allowed_hizli:
    st.session_state["ft_hizli"] = "Son 3 ay"

if "show_filters_panel" not in st.session_state:
    st.session_state["show_filters_panel"] = False

hizli_sayilar = {
    "Tümü":      len(veriler),
    "Son 3 ay":  sum(1 for v in veriler if tarih_gun_farki(en_iyi_tarih(v)) <= 90),
    "Son 6 ay":  sum(1 for v in veriler if tarih_gun_farki(en_iyi_tarih(v)) <= 180),
    "Son 1 yıl": sum(1 for v in veriler if tarih_gun_farki(en_iyi_tarih(v)) <= 365),
}

# Aktif filtre sayısı
aktif_filtre_sayisi = 0
if st.session_state.get("ft_il", "Tümü") != "Tümü": aktif_filtre_sayisi += 1
if st.session_state.get("ft_ilce", "Tümü") != "Tümü": aktif_filtre_sayisi += 1
if st.session_state.get("ft_danisan", "Tümü") != "Tümü": aktif_filtre_sayisi += 1
if st.session_state.get("ft_mulk", "Tümü") != "Tümü": aktif_filtre_sayisi += 1
if st.session_state.get("ft_islem", "Tümü") != "Tümü": aktif_filtre_sayisi += 1
if st.session_state.get("ft_ara", "").strip(): aktif_filtre_sayisi += 1
if st.session_state.get("ft_siralama", "Tarih ↓") != "Tarih ↓": aktif_filtre_sayisi += 1
if st.session_state.get("ft_fav", False): aktif_filtre_sayisi += 1
if st.session_state.get("ft_gizli", False): aktif_filtre_sayisi += 1
if st.session_state.get("ft_aralik", False): aktif_filtre_sayisi += 1
if st.session_state.get("ft_butce_alt", 0) > 0: aktif_filtre_sayisi += 1
if st.session_state.get("ft_butce_ust", 0) > 0: aktif_filtre_sayisi += 1
if st.session_state.get("ft_oda", "Tümü") != "Tümü": aktif_filtre_sayisi += 1
if st.session_state.get("ft_bina_yasi", "Tümü") != "Tümü": aktif_filtre_sayisi += 1
if st.session_state.get("ft_kat", "Tümü") != "Tümü": aktif_filtre_sayisi += 1
if st.session_state.get("ft_site_ici", "Tümü") != "Tümü": aktif_filtre_sayisi += 1
if st.session_state.get("ft_esyali", "Tümü") != "Tümü": aktif_filtre_sayisi += 1
if st.session_state.get("ft_kullanim", "Tümü") != "Tümü": aktif_filtre_sayisi += 1
if st.session_state.get("ft_gun_min", 0) > 0: aktif_filtre_sayisi += 1
if st.session_state.get("ft_gun_max", 0) > 0: aktif_filtre_sayisi += 1

badge_html = f'<span class="filtre-badge">{aktif_filtre_sayisi}</span>' if aktif_filtre_sayisi > 0 else ""
filtre_btn_text = f"⚙ Filtreler {aktif_filtre_sayisi}" if aktif_filtre_sayisi > 0 else "⚙ Filtreler"

hizli_button_map = [
    ("Son 3 ay",  f"3 Ay · {hizli_sayilar['Son 3 ay']}"),
    ("Son 6 ay",  f"6 Ay · {hizli_sayilar['Son 6 ay']}"),
    ("Son 1 yıl", f"1 Yıl · {hizli_sayilar['Son 1 yıl']}"),
    ("Tümü",      f"Tümü · {hizli_sayilar['Tümü']}"),
]

tb1, tb2, tb3, tb4, tb5 = st.columns([1.0, 1.0, 1.0, 1.3, 0.9])

for col, (deger, label) in zip([tb1, tb2, tb3, tb4], hizli_button_map):
    with col:
        aktif = st.session_state.get("ft_hizli", "Tümü") == deger
        if st.button(
            label,
            key=f"hizli_btn_{safe_key(deger)}",
            use_container_width=True,
            type="primary" if aktif else "secondary"
        ):
            st.session_state["ft_hizli"] = deger
            st.rerun()

with tb5:
    if st.button(
        filtre_btn_text,
        key="toggle_filter_panel_btn",
        use_container_width=True,
        type="primary" if st.session_state.get("show_filters_panel") else "secondary"
    ):
        st.session_state["show_filters_panel"] = not st.session_state["show_filters_panel"]
        st.rerun()

# ── FİLTRE PANELİ ────────────────────────────────────────────────────────────
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
        if st.session_state.get("ft_islem") not in ["Tümü", "Satılık", "Kiralık", "Belirtilmemiş"]:
            st.session_state["ft_islem"] = "Tümü"
        if st.session_state.get("ft_siralama") not in ["Tarih ↓", "Tarih ↑", "İlçe A→Z", "İlçe Z→A", "Bütçe ↑", "Bütçe ↓"]:
            st.session_state["ft_siralama"] = "Tarih ↓"

        # ── SATIR 1: Temel filtreler ────────────────────────────────────────
        f1, f2, f3, f4, f5 = st.columns([1.1, 1.1, 1.7, 1.1, 1.1])
        with f1: il_filtre = st.selectbox("İl", ["Tümü"] + tum_iller + ["Belirtilmemiş"], key="ft_il")
        with f2: ilce_filtre = st.selectbox("İlçe", ["Tümü"] + tum_ilceler, key="ft_ilce")
        with f3: danisan_filtre = st.selectbox("Danışman", ["Tümü"] + danismanlar, key="ft_danisan")
        with f4: mulk_filtre = st.selectbox("Mülk", ["Tümü", "Konut", "İşyeri", "Arsa", "Belirtilmemiş"], key="ft_mulk")
        with f5: islem_filtre = st.selectbox("İşlem", ["Tümü", "Satılık", "Kiralık", "Belirtilmemiş"], key="ft_islem")

        # ── SATIR 2: Bütçe + Oda + Yapı bilgileri ───────────────────────────
        g1, g2, g3, g4, g5, g6 = st.columns([1.2, 1.2, 1.2, 1.2, 1.2, 1.2])
        with g1:
            st.caption("Bütçe Alt (TL)")
            butce_alt = st.number_input("", min_value=0, step=100000,
                key="ft_butce_alt", label_visibility="collapsed")
        with g2:
            st.caption("Bütçe Üst (TL)")
            butce_ust = st.number_input("", min_value=0, step=100000,
                key="ft_butce_ust", label_visibility="collapsed")

        # Oda seçenekleri — veriden çek
        oda_opts = ["Tümü"] + sorted(set(
            str(v.get("oda_sayisi_m2","")).strip()
            for v in veriler if v.get("oda_sayisi_m2","") not in ("","None",None)
        ))
        with g3: oda_filtre = st.selectbox("Oda / M²", oda_opts, key="ft_oda")

        with g4: site_ici_filtre = st.selectbox("Site İçi", ["Tümü","Evet","Hayır"], key="ft_site_ici")
        with g5: esyali_filtre = st.selectbox("Eşyalı", ["Tümü","Evet","Hayır"], key="ft_esyali")
        with g6: kullanim_filtre = st.selectbox("Kullanım", ["Tümü","Boş","Kiracılı","Malik"], key="ft_kullanim")

        # ── SATIR 3: Yapı + İlan süresi + Sıralama ──────────────────────────
        h1, h2, h3, h4, h5, h6 = st.columns([1.2, 1.2, 1.2, 1.2, 1.2, 1.2])
        # Bina yaşı seçenekleri
        byas_opts = ["Tümü"] + sorted(set(
            str(v.get("bina_yasi","")).strip()
            for v in veriler if v.get("bina_yasi","") not in ("","None",None)
        ))
        with h1: bina_yasi_filtre = st.selectbox("Bina Yaşı", byas_opts, key="ft_bina_yasi")

        # Bulunduğu kat seçenekleri
        kat_opts = ["Tümü"] + sorted(set(
            str(v.get("bulundugu_kat","")).strip()
            for v in veriler if v.get("bulundugu_kat","") not in ("","None",None)
        ))
        with h2: kat_filtre = st.selectbox("Bulunduğu Kat", kat_opts, key="ft_kat")

        with h3:
            st.caption("İlan Süresi Min (gün)")
            gun_min = st.number_input("", min_value=0, step=1,
                key="ft_gun_min", label_visibility="collapsed")
        with h4:
            st.caption("İlan Süresi Maks (gün)")
            gun_max = st.number_input("", min_value=0, step=1,
                key="ft_gun_max", label_visibility="collapsed")

        with h5: ara = st.text_input("Arama", placeholder="Başlık, ilçe, kriter...", key="ft_ara")
        with h6: siralama = st.selectbox("Sıralama", ["Tarih ↓", "Tarih ↑", "İlçe A→Z", "İlçe Z→A", "Bütçe ↑", "Bütçe ↓"], key="ft_siralama")

        # ── SATIR 4: Checkbox'lar + Temizle ─────────────────────────────────
        e1, e2, e3, e4, e5 = st.columns([1.05, 0.95, 1.35, 1.05, 5.6])
        with e1: favori_filtre = st.checkbox("Favori", key="ft_fav")
        with e2: st.checkbox("Gizli", key="ft_gizli")
        with e3: tarih_araligi_aktif = st.checkbox("Tarih Aralığı", key="ft_aralik")
        with e4: st.write(""); st.button("Temizle", key="filtre_temizle_btn", use_container_width=True, on_click=filtre_temizle)

        bas_tarih, bit_tarih = None, None
        if tarih_araligi_aktif:
            d1, d2, d3 = st.columns([1.3, 1.3, 5.4])
            with d1: bas_tarih = st.date_input("Başlangıç", value=st.session_state.get("ft_bas", date.today() - timedelta(days=30)), key="ft_bas")
            with d2: bit_tarih = st.date_input("Bitiş", value=st.session_state.get("ft_bit", date.today()), key="ft_bit")
else:
    il_filtre = st.session_state.get("ft_il", "Tümü")
    ilce_filtre = st.session_state.get("ft_ilce", "Tümü")
    danisan_filtre = st.session_state.get("ft_danisan", "Tümü")
    mulk_filtre = st.session_state.get("ft_mulk", "Tümü")
    islem_filtre = st.session_state.get("ft_islem", "Tümü")
    ara = st.session_state.get("ft_ara", "")
    siralama = st.session_state.get("ft_siralama", "Tarih ↓")
    favori_filtre = st.session_state.get("ft_fav", False)
    tarih_araligi_aktif = st.session_state.get("ft_aralik", False)
    bas_tarih = st.session_state.get("ft_bas", None)
    bit_tarih = st.session_state.get("ft_bit", None)
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

hizli = st.session_state.get("ft_hizli", "Tümü")
gorunum = st.session_state.get("ft_gorunum", "Liste")
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
if islem_filtre == "Belirtilmemiş": f = [v for v in f if v.get("islem_tipi", "") in ("", "Belirsiz", "Belirtilmemiş", None)]
elif islem_filtre != "Tümü": f = [v for v in f if v.get("islem_tipi", "") == islem_filtre]

# ── Yeni filtreler ───────────────────────────────────────────────────────────
if oda_filtre != "Tümü":
    f = [v for v in f if str(v.get("oda_sayisi_m2","")).strip() == oda_filtre]

if bina_yasi_filtre != "Tümü":
    f = [v for v in f if str(v.get("bina_yasi","")).strip() == bina_yasi_filtre]

if kat_filtre != "Tümü":
    f = [v for v in f if str(v.get("bulundugu_kat","")).strip() == kat_filtre]

# Site içi / eşyalı / kullanım — ozel_kriterler + ozet metninde ara
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

# Bütçe filtresi — sayısal karşılaştırma
if butce_alt > 0 or butce_ust > 0:
    def _butce_sayisal(v):
        return fiyat_sayisal(v.get("max_butce",""))
    if butce_alt > 0:
        f = [v for v in f if _butce_sayisal(v) >= butce_alt]
    if butce_ust > 0:
        f = [v for v in f if _butce_sayisal(v) <= butce_ust]

# İlan süresi filtresi
if gun_min > 0:
    f = [v for v in f if tarih_gun_farki(en_iyi_tarih(v)) >= gun_min]
if gun_max > 0:
    f = [v for v in f if tarih_gun_farki(en_iyi_tarih(v)) <= gun_max]
if hizli != "Tümü":
    gl = {"Son 3 ay": 90, "Son 6 ay": 180, "Son 1 yıl": 365}.get(hizli)
    if gl is not None: f = [v for v in f if tarih_gun_farki(en_iyi_tarih(v)) <= gl]
if bas_tarih and bit_tarih: f = [v for v in f if (d := tarih_parse(en_iyi_tarih(v))) and bas_tarih <= d <= bit_tarih]
if favori_filtre: f = [v for v in f if v.get("favori", False)]

f = siralama_uygula(f, siralama)

# ── WORKSPACE SEKMELERİ + GÖRÜNÜM TOGGLE ─────────────────────────────────────
if "talep_aks_secili_ilce" not in st.session_state:
    st.session_state["talep_aks_secili_ilce"] = None
if "aktif_talep_sekme" not in st.session_state:
    st.session_state["aktif_talep_sekme"] = "Favorilerim"
# Okundu takibi — session bazlı (geçici)
if "goruldu_ids" not in st.session_state:
    st.session_state["goruldu_ids"] = set()

# ── Favori ilçe chip'leri ────────────────────────────────────────────────────
_ws_fav_list = favori_ilceleri_cek()
_ws_fav_secili = st.session_state.get("fav_secili_ilce")

# query_params ile tıklama — koşulsuz kontrol (her render'da)
_qp = st.query_params
if "fav_ilce" in _qp:
    _gelen = _qp["fav_ilce"]
    if _gelen == "__tumu__":
        st.session_state["fav_secili_ilce"] = None
        st.session_state["aktif_talep_sekme"] = "Favorilerim"
        del st.query_params["fav_ilce"]
        st.rerun()
    elif _gelen == "__ekle__":
        st.session_state["show_fav_ekle"] = True
        del st.query_params["fav_ilce"]
        st.rerun()
    else:
        st.session_state["fav_secili_ilce"] = None if st.session_state.get("fav_secili_ilce") == _gelen else _gelen
        st.session_state["aktif_talep_sekme"] = "Favorilerim"
        del st.query_params["fav_ilce"]
        st.rerun()

# Chip HTML — koşulsuz render (DOM tutarlılığı)
_chip_html = '<div class="firsat-row">'
if _ws_fav_list:
    _fav_toplam = sum(ilce_kayit_sayisi(f, _filce)[0] for _filce in _ws_fav_list[:5])
    _tumu_cls = "fchip fchip-tumu active" if not _ws_fav_secili else "fchip fchip-tumu"
    _chip_html += f'<a href="?fav_ilce=__tumu__" style="text-decoration:none;"><button class="{_tumu_cls}">★ Tüm Favoriler &nbsp;{_fav_toplam}</button></a>'
    for _filce in _ws_fav_list[:5]:
        _ftoplam, _fyeni = ilce_kayit_sayisi(f, _filce)
        if _ftoplam == 0:
            continue
        _fsecili = _ws_fav_secili == _filce
        _ilce_cls = "fchip fchip-ilce active" if _fsecili else "fchip fchip-ilce"
        _yeni_html = f'<span class="fchip-yeni">{_fyeni} yeni</span>' if _fyeni > 0 else ""
        _chip_html += (
            f'<a href="?fav_ilce={_filce}" style="text-decoration:none;">'
            f'<button class="{_ilce_cls}">★ {_filce} &nbsp;{_ftoplam}{_yeni_html}</button></a>'
        )
    _chip_html += '<a href="?fav_ilce=__ekle__" style="text-decoration:none;"><button class="fchip fchip-ekle">+ Favori Ekle</button></a>'
_chip_html += '</div>'
st.markdown(_chip_html, unsafe_allow_html=True)

# ── Ana toggle + alt sekmeler + görünüm ──────────────────────────────────────

# FAVORİLER | TÜMÜ toggle — başlık seviyesi
_ana_sekme = st.session_state.get("ana_talep_sekme", "Favorilerim")
_fav_aktif = _ana_sekme == "Favorilerim"
_tum_aktif = _ana_sekme == "TümüListe"

# ── Sekme satırı — tek columns bloğu ─────────────────────────────────────────
# ⭐Favoriler | Tümü | sep | İzmir İlçeleri | Diğer İlçeler | sep | Liste | Kart | Tablo
_sc = st.columns([1.2, 1.0, 0.2, 1.6, 1.6, 0.2, 0.85, 0.85, 0.85])

with _sc[0]:
    if st.button("⭐ Favoriler", key="ana_tog_fav", use_container_width=True,
                 type="primary" if _fav_aktif else "secondary"):
        st.session_state["ana_talep_sekme"] = "Favorilerim"
        st.session_state["aktif_talep_sekme"] = "Favorilerim"
        st.session_state["fav_secili_ilce"] = None
        st.rerun()

with _sc[1]:
    if st.button("Tümü", key="ana_tog_tum", use_container_width=True,
                 type="primary" if _tum_aktif else "secondary"):
        st.session_state["ana_talep_sekme"] = "TümüListe"
        st.session_state["aktif_talep_sekme"] = "TümüListe"
        st.rerun()

# _sc[2] ayırıcı boş

for _si, val in [(_sc[3], "İzmir İlçeleri"), (_sc[4], "Diğer İlçeler")]:
    with _si:
        aktif_s = st.session_state.get("aktif_talep_sekme") == val
        if st.button(val, key=f"sekme_{safe_key(val)}", use_container_width=True,
                     type="primary" if aktif_s else "secondary"):
            if aktif_s:
                # Aktifse kapat — ana moda dön
                st.session_state["aktif_talep_sekme"] = (
                    "Favorilerim" if _fav_aktif else "TümüListe"
                )
            else:
                st.session_state["aktif_talep_sekme"] = val
            st.rerun()

# _sc[5] ayırıcı boş

for _si, _val, _vlbl in [(_sc[6],"Liste","Liste"),(_sc[7],"Kart","Kart"),(_sc[8],"Tablo","Tablo")]:
    with _si:
        _aktif = st.session_state.get("ft_gorunum") == _val
        if st.button(_vlbl, key=f"gorunum_ws_{_val}", use_container_width=True,
                     type="primary" if _aktif else "secondary"):
            st.session_state["ft_gorunum"] = _val
            st.rerun()

aktif_sekme = st.session_state.get("aktif_talep_sekme", "Favorilerim")

fav_secili = st.session_state.get("fav_secili_ilce")
aks_secili = st.session_state.get("talep_aks_secili_ilce")
favori_f = [v for v in f if favori_kaydi_mi(v, fav_ilceler)]
bugun_favori_f = favori_f
bugun_tum_f = f

# ── SEKME İÇERİKLERİ ─────────────────────────────────────────────────────────

# TÜMÜ modu — tüm kayıtları karışık göster
if _ana_sekme == "TümüListe":
    gorunum = st.session_state.get("ft_gorunum", "Tablo")
    if not f:
        st.info(f"Bu dönemde kayıt bulunamadı.")
    else:
        st.markdown(
            f'<div style="font-size:11px;color:#64748b;margin-bottom:8px;">'
            f'<b>{len(f)}</b> talep · {hizli}</div>',
            unsafe_allow_html=True
        )
        if gorunum == "Tablo":
            tablo_goster_html(f, prefix="tum_tbl")
        elif gorunum == "Kart":
            cols3 = st.columns(3, gap="small")
            for idx, v in enumerate(f):
                with cols3[idx % 3]:
                    kid = v.get("id")
                    ui_k = build_talep_ui_model(v)
                    isim = isim_ayikla(v.get("talep_eden_danisan", ""))
                    butce = v.get("max_butce", "")
                    mulk = v.get("mulk_tipi", "")
                    islem = v.get("islem_tipi", "")
                    oda = v.get("oda_sayisi_m2", "")
                    yeni = tarih_gun_farki(en_iyi_tarih(v)) <= 7
                    _aks_k = aks_renk_bul(v.get("ilceler") or [])
                    _topbar = aks_bar_gradient(v.get("ilceler") or [])
                    _td = tarih_parse(en_iyi_tarih(v))
                    if _td:
                        _hast = hasattr(_td, "hour") and (_td.hour != 0 or _td.minute != 0)
                        _tarih_k = _td.strftime("%d.%m · %H:%M") if _hast else _td.strftime("%d.%m.%Y")
                    else:
                        _tarih_k = ""
                    _rozet_k = '<span class="nbadge nbadge-yeni"><span class="dot-live"></span> YENİ</span>' if yeni else ""
                    _badges = nbadge(mulk) + nbadge(islem)
                    if oda: _badges += nbadge(oda, "nbadge-oda")
                    _butce_html = f'<span class="nkart-price">{butce}</span>' if butce else '<span class="nkart-price-empty">Bütçe belirtilmedi</span>'
                    _avatar = avatar_html(isim, _aks_k)
                    st.markdown(
                        f'<div class="nkart">'                        f'<div class="nkart-topbar" style="background:{_topbar};"></div>'                        f'<div class="nkart-body">'                        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:2px;">'                        f'<span class="nkart-district" style="color:{_aks_k["text"]};">{ui_k["lokasyon_ozet"] or "—"}</span>'                        f'{_rozet_k}</div>'                        f'<p class="nkart-title">{ui_k["baslik"]}</p>'                        + (f'<p class="nkart-desc">{ui_k["kriter_ozet"]}</p>' if ui_k.get("kriter_ozet") else "")
                        + f'<div class="nkart-meta">{_badges}</div>'                        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-top:auto;padding-top:6px;">'                        f'{_butce_html}<span class="nkart-date">{_tarih_k}</span></div>'                        f'</div>'                        f'<div class="nkart-footer">'                        f'<div class="nkart-agent">{_avatar}{isim}</div>'                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
                    _bc1, _bc2 = st.columns([1, 1])
                    with _bc1:
                        if st.button("Detay", key=f"tum_detay_{kid}", use_container_width=True, type="primary"):
                            st.session_state.setdefault("goruldu_ids", set()).add(kid)
                            talep_detay_modal(v, ilce_sec)
                    with _bc2:
                        _fav_lbl = "★ Favori" if v.get("favori") else "☆ Favori"
                        if st.button(_fav_lbl, key=f"tum_fav_{kid}", use_container_width=True):
                            favori_guncelle(kid, v.get("favori", False))
        else:  # Liste
            for v in f:
                kayit_karti(v, ilce_sec)

elif aktif_sekme == "Favorilerim":
    # fav_secili_ilce üzerinden filtrele (üstteki chip'ten gelir)
    fav_render = (
        [v for v in bugun_favori_f if _ws_fav_secili in kayit_ilce_listesi(v)]
        if _ws_fav_secili else bugun_favori_f
    )
    if not bugun_favori_f:
        donem = {"Bugün": "bugün", "Son 7 gün": "bu hafta", "Son 30 gün": "bu ay", "Tümü": "tüm zamanlarda"}.get(hizli, "bu dönemde")
        st.info(f"Favori bölgelerinizdeki taleplerden {donem} kayıt bulunmamaktadır.")
    else:
        if gorunum == "Liste":
            for v in fav_render:
                kayit_karti(v, ilce_sec)
        elif gorunum == "Kart":
            cols3 = st.columns(3, gap="small")
            for idx, v in enumerate(fav_render):
                with cols3[idx % 3]:
                    kid = v.get("id")
                    isim = isim_ayikla(v.get("talep_eden_danisan", ""))
                    butce = v.get("max_butce", "")
                    mulk = v.get("mulk_tipi", "")
                    islem = v.get("islem_tipi", "")
                    oda = v.get("oda_sayisi_m2", "")
                    yeni = tarih_gun_farki(en_iyi_tarih(v)) <= 7
                    okundu_k = kid in st.session_state.get("goruldu_ids", set())
                    ui_k = build_talep_ui_model(v)
                    _aks_k = aks_renk_bul(v.get("ilceler") or [])

                    # Tarih kısa format
                    _td = tarih_parse(en_iyi_tarih(v))
                    if _td:
                        _hast = hasattr(_td, "hour") and (_td.hour != 0 or _td.minute != 0)
                        _tarih_k = _td.strftime("%d.%m · %H:%M") if _hast else _td.strftime("%d.%m.%Y")
                    else:
                        _tarih_k = ""

                    # Üst şerit — gradient veya düz aks rengi
                    _topbar = aks_bar_gradient(v.get("ilceler") or [])

                    # Okundu/yeni rozet
                    if okundu_k:
                        _rozet_k = '<span class="nbadge nbadge-goruldu">✓ Görüldü</span>'
                    elif yeni:
                        _rozet_k = '<span class="nbadge nbadge-yeni"><span class="dot-live"></span> YENİ</span>'
                    else:
                        _rozet_k = ""

                    # Badge'ler
                    _badges = nbadge(mulk) + nbadge(islem)
                    if oda:
                        _badges += nbadge(oda, "nbadge-oda")

                    # Bütçe HTML
                    _butce_html = (
                        f'<span class="nkart-price">{butce}</span>'
                        if butce else
                        '<span class="nkart-price-empty">Bütçe belirtilmedi</span>'
                    )

                    # Avatar
                    _avatar = avatar_html(isim, _aks_k)

                    # Kart HTML
                    st.markdown(
                        f'<div class="nkart">'
                        f'<div class="nkart-topbar" style="background:{_topbar};"></div>'
                        f'<div class="nkart-body">'
                        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:2px;">'
                        f'<span class="nkart-district" style="color:{_aks_k["text"]};">{ui_k["lokasyon_ozet"] or "—"}</span>'
                        f'{_rozet_k}'
                        f'</div>'
                        f'<p class="nkart-title">{ui_k["baslik"]}</p>'
                        + (f'<p class="nkart-desc">{ui_k["kriter_ozet"]}</p>' if ui_k.get("kriter_ozet") else "")
                        + f'<div class="nkart-meta">{_badges}</div>'
                        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-top:auto;padding-top:6px;">'
                        f'{_butce_html}'
                        f'<span class="nkart-date">{_tarih_k}</span>'
                        f'</div>'
                        f'</div>'
                        f'<div class="nkart-footer">'
                        f'<div class="nkart-agent">{_avatar}{isim}</div>'
                        f'<div class="nkart-actions">'
                        f'<div class="nkart-icon-btn" id="fav_html_{kid}">{"★" if v.get("favori") else "☆"}</div>'
                        f'<button class="nkart-detay-btn" id="detay_html_{kid}">👁 Detay</button>'
                        f'</div>'
                        f'</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    # Gizli işlevsel butonlar
                    _bc1, _bc2 = st.columns([1, 1])
                    with _bc1:
                        if st.button("Detay", key=f"detay_btn_{kid}",
                                     use_container_width=True, type="primary"):
                            st.session_state.setdefault("goruldu_ids", set()).add(kid)
                            talep_detay_modal(v, ilce_sec)
                    with _bc2:
                        _fav_lbl = "★ Favori" if v.get("favori") else "☆ Favori"
                        if st.button(_fav_lbl, key=f"fav_{kid}", use_container_width=True):
                            favori_guncelle(kid, v.get("favori", False))
        elif gorunum == "Tablo":
            tablo_goster_html(fav_render, prefix="fav_tbl")

if aktif_sekme in ("İzmir İlçeleri",) or (aktif_sekme == "TümüListe" and st.session_state.get("aktif_talep_sekme") == "İzmir İlçeleri"):
    render_compact_aks_haritasi(f, "talep_aks_secili_ilce", "talep", entity_label="talep")
    aks_secili = st.session_state.get("talep_aks_secili_ilce")
    if aks_secili:
        f_render = [v for v in f if aks_secili in kayit_ilce_listesi(v)]
        st.markdown(f"<div style='font-size:11px;color:#64748b;margin:6px 0 5px;'>{len(f_render)} kayıt</div>", unsafe_allow_html=True)
        if gorunum == "Tablo":
            tablo_goster_html(f_render, prefix="izmir_tbl")
        else:
            for v in f_render:
                kayit_karti(v, ilce_sec)

elif aktif_sekme == "Diğer İlçeler":
    diger_ilceler = sorted(set(ilce_grubu(v) for v in f if diger_il_kaydi_mi(v) and ilce_grubu(v)))
    if diger_ilceler:
        cols = st.columns(4)
        for idx, ilce in enumerate(diger_ilceler):
            toplam, yeni = ilce_kayit_sayisi(f, ilce)
            badge = f"  🟢 {yeni} yeni" if yeni > 0 else ""
            with cols[idx % 4]:
                if st.button(f"{ilce} · {toplam}{badge}", key=f"talep_diger_{safe_key(ilce)}", use_container_width=True):
                    st.session_state["ft_ilce"] = ilce
                    st.rerun()
    else:
        st.caption("Diğer il/ilçe kaydı bulunamadı.")

if kaynak_tab != "startkey":
    kaynak_etiket = {"ofis": "🏢 Ofis", "dis": "🌐 Dış Kaynak"}.get(kaynak_tab, "")
    kaynak_db = {"ofis": "ofis", "dis": "dis_kaynak"}.get(kaynak_tab, "ofis")
    yeni_talep_modal(kaynak_db, kaynak_etiket, ilce_sec)

"""
proje_hafizasi_app_v2.py
Proje Hafızası — Kompakt CRM Kart Görünümü + Özet + Detay + Kullanıcı Notu + Çıktı
"""

import re
import uuid
import json
import requests
from datetime import datetime
from typing import Optional
import streamlit as st
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from core.ui_helpers import render_navbar, render_page_header


# =========================================================
# STYLE
# =========================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family:'Source Sans 3', sans-serif !important; }
.stApp { background:#f3f6fb !important; }
.main .block-container {
    max-width: 1180px;
    padding: 1.25rem 1.75rem 5rem 1.75rem;
    background:#f3f6fb !important;
}

[data-testid="stSidebarNav"] { display:none !important; }

.sidebar-title {
    font-size:18px;
    font-weight:800;
    color:#f8fafc;
    padding:8px 6px 2px 6px;
    letter-spacing:-.01em;
}
.sidebar-sub {
    font-size:12px;
    color:#64748b;
    padding:0 6px 14px 6px;
}
.side-section-title {
    font-size:10px;
    font-weight:800;
    letter-spacing:.12em;
    text-transform:uppercase;
    color:#64748b;
    margin:18px 6px 8px 6px;
    padding-top:14px;
    border-top:1px solid #1e293b;
}

.app-menu-link {
    display:block;
    color:#e5e7eb !important;
    text-decoration:none !important;
    font-size:14px;
    font-weight:700;
    padding:9px 10px;
    border-radius:10px;
    margin:3px 0;
}
.app-menu-link:hover { background:#1e293b; color:#fff !important; }
.app-menu-active { background:#2563eb; color:#fff !important; }

.hero-title {
    font-size:34px;
    font-weight:800;
    color:#111827;
    margin:0 0 2px 0;
    letter-spacing:-.03em;
}
.hero-sub {
    color:#64748b;
    font-size:14px;
    margin-bottom:18px;
}
.topbar {
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:16px;
    margin-bottom:18px;
}
.top-actions { display:flex; gap:8px; align-items:center; }

.section-divider {
    margin:18px 0 12px 0;
    font-size:20px;
    font-weight:800;
    color:#111827;
    border-bottom:1px solid #d8dee8;
    padding-bottom:10px;
    display:flex;
    align-items:center;
    gap:10px;
}
.section-count {
    font-size:12px;
    font-weight:800;
    background:#e8eef7;
    color:#64748b;
    border:1px solid #d8dee8;
    border-radius:999px;
    padding:2px 9px;
}

.chip {
    border-radius:999px;
    padding:2px 8px;
    font-size:10px;
    font-weight:800;
    text-transform:uppercase;
    letter-spacing:.35px;
}
.chip-ux { background:#e8f0fe; color:#1967d2; }
.chip-teknik { background:#fff3e6; color:#ea580c; }
.chip-operasyon { background:#fee2e2; color:#dc2626; }
.chip-fikir { background:#f3e8ff; color:#7c3aed; }
.chip-page { background:#edf2f7; color:#64748b; }
.chip-yeni { background:#dcfce7; color:#15803d; }
.chip-devam { background:#fef3c7; color:#a16207; }
.chip-tamam { background:#dbeafe; color:#1d4ed8; }
.chip-bekle { background:#f1f5f9; color:#64748b; }
.chip-kritik  { background:#fee2e2; color:#b91c1c; }
.chip-yuksek  { background:#fef3c7; color:#b45309; }
.chip-orta    { background:#e8f5e9; color:#2e7d32; }
.chip-dusuk   { background:#f3f4f6; color:#9ca3af; }

/* Genel butonlar */
.stButton > button {
    background:#ffffff !important;
    color:#0f172a !important;
    border:1px solid #d8dee8 !important;
    border-radius:10px !important;
    font-size:13px !important;
    font-weight:700 !important;
    padding:0.38rem 0.75rem !important;
    transition:.12s !important;
    box-shadow:none !important;
    margin:0 !important;
}
.stButton > button:hover {
    background:#f8fafc !important;
    border-color:#cbd5e1 !important;
    color:#111827 !important;
}
.stButton > button[kind="primary"] {
    background:#0f172a !important;
    color:#fff !important;
    border:1px solid #0f172a !important;
    padding:0.48rem 1rem !important;
    font-size:14px !important;
}
.stButton > button[kind="primary"]:hover { background:#111827 !important; }

.stTextInput input, .stTextArea textarea {
    background:#ffffff !important;
    border:1px solid #d8dee8 !important;
    border-radius:10px !important;
    color:#0f172a !important;
    font-size:13.5px !important;
}
div[data-baseweb="select"] > div {
    background:#fff !important;
    border:1px solid #d8dee8 !important;
    border-radius:10px !important;
}
label { color:#64748b !important; font-size:12px !important; font-weight:700 !important; }

.empty-state {
    text-align:center;
    color:#94a3b8;
    padding:70px 20px;
    font-size:14px;
    line-height:2.2;
}

.page-block-header {
    padding: 8px 2px 12px 2px;
    display:flex;
    align-items:center;
    gap:8px;
}
.page-block-name {
    font-size:12px;
    font-weight:800;
    letter-spacing:.12em;
    text-transform:uppercase;
    color:#64748b;
}
.page-block-count {
    font-size:11px;
    background:#e8eef7;
    color:#64748b;
    border-radius:999px;
    padding:2px 9px;
    font-weight:800;
}

/* Sekmeler: koyu değil, ürün ailesiyle uyumlu */
.stTabs [data-baseweb="tab-list"] {
    background:#e5e9f0 !important;
    border:1px solid #d8dee8 !important;
    border-radius:12px 12px 0 0 !important;
    gap:2px !important;
    padding:5px 5px 0 5px !important;
}
.stTabs [data-baseweb="tab"] {
    background:transparent !important;
    color:#475569 !important;
    border-radius:9px 9px 0 0 !important;
    font-size:14px !important;
    font-weight:700 !important;
    padding:10px 22px !important;
    border:none !important;
}
.stTabs [aria-selected="true"] {
    background:#ffffff !important;
    color:#0f172a !important;
    border-bottom:3px solid #3b82f6 !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background:#f3f6fb !important;
    padding:18px 0 0 0 !important;
}

.note-card-wrap {
    background:#ffffff;
    border-radius:12px;
    border:1px solid #d8dee8;
    border-left:5px solid #cbd5e1;
    margin-bottom:12px;
    padding:16px 20px 15px 18px;
    box-shadow:0 4px 14px rgba(15,23,42,0.055);
    position:relative;
    transition:box-shadow .12s, transform .08s;
}
.note-card-wrap:hover {
    box-shadow:0 8px 24px rgba(15,23,42,0.09);
    transform:translateY(-1px);
}
.note-card-wrap.cat-ux        { border-left-color:#3b82f6; }
.note-card-wrap.cat-teknik    { border-left-color:#f97316; }
.note-card-wrap.cat-operasyon { border-left-color:#ef4444; }
.note-card-wrap.cat-fikir     { border-left-color:#8b5cf6; }
.note-chips { display:flex; gap:7px; flex-wrap:wrap; align-items:center; margin-bottom:8px; }
.chip-xs {
    font-size:10px;
    font-weight:800;
    padding:1px 6px;
    border-radius:4px;
    text-transform:uppercase;
    letter-spacing:.45px;
    opacity:.75;
}

/* detay alanları */
textarea:disabled { color:#0f172a !important; opacity:1 !important; }
hr { border-color:#d8dee8 !important; }

/* ── Rehber görünümü ── */
.rehber-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-top: 4px;
}
.rehber-blok {
    background: #ffffff;
    border-radius: 14px;
    border: 1px solid #d8dee8;
    padding: 20px 22px;
    box-shadow: 0 2px 8px rgba(15,23,42,0.04);
}
.rehber-blok.full {
    grid-column: 1 / -1;
}
.rehber-blok-label {
    font-size: 10px;
    font-weight: 800;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 7px;
}
.rehber-label-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
}
/* Durum sayıları */
.durum-row {
    display: flex;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    overflow: hidden;
}
.durum-stat {
    flex: 1;
    text-align: center;
    padding: 14px 8px;
    border-right: 1px solid #e2e8f0;
}
.durum-stat:last-child { border-right: none; }
.durum-sayi {
    font-size: 30px;
    font-weight: 800;
    color: #0f172a;
    line-height: 1;
    margin-bottom: 4px;
    letter-spacing: -0.03em;
}
.durum-sayi.s-amber  { color: #f59e0b; }
.durum-sayi.s-green  { color: #22c55e; }
.durum-sayi.s-muted  { color: #94a3b8; }
.durum-etiket {
    font-size: 11px;
    color: #94a3b8;
    font-weight: 600;
}
/* Ham not öğesi */
.ham-item {
    padding: 11px 0;
    border-bottom: 1px solid #f1f5f9;
}
.ham-item:last-child { border-bottom: none; padding-bottom: 0; }
.ham-item:first-child { padding-top: 0; }
.ham-meta {
    display: flex;
    align-items: center;
    gap: 5px;
    margin-bottom: 5px;
    flex-wrap: wrap;
}
.ham-tarih {
    font-size: 10px;
    color: #94a3b8;
    font-weight: 600;
}
.ham-text {
    font-size: 13px;
    color: #475569;
    line-height: 1.55;
    font-style: italic;
}
/* Yarım kalan */
.yarim-item {
    display: flex;
    gap: 11px;
    padding: 11px 0;
    border-bottom: 1px solid #f1f5f9;
    align-items: flex-start;
}
.yarim-item:last-child { border-bottom: none; }
.yarim-item:first-child { padding-top: 0; }
.yarim-bar {
    width: 3px;
    border-radius: 2px;
    flex-shrink: 0;
    align-self: stretch;
    min-height: 36px;
}
.yarim-ozet {
    font-size: 13px;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.4;
    margin-bottom: 3px;
}
.yarim-ham {
    font-size: 11.5px;
    color: #94a3b8;
    line-height: 1.45;
    font-style: italic;
    margin-top: 4px;
}
/* Unutulan */
.unutulan-blok {
    background: linear-gradient(135deg, #fafbff 0%, #eff4ff 100%) !important;
    border-color: #dde6fb !important;
}
.unutulan-yas {
    background: #e8f0fe;
    color: #3b82f6;
    border-radius: 999px;
    padding: 2px 9px;
    font-size: 10px;
    font-weight: 800;
    margin-left: auto;
}
.unutulan-text {
    font-size: 14px;
    color: #1e293b;
    line-height: 1.65;
    font-style: italic;
    margin-bottom: 12px;
    padding-left: 2px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# CONSTANTS
# =========================================================

KATEGORILER = ["UX", "Teknik", "Operasyon", "Fikir"]

SAYFALAR = [
    "Proje Hafızası",
    "Talep Tablosu",
    "Portföy Tablosu",
    "Ofis Paneli",
    "Mail İşlem",
    "Zeta Radar",
    "Sunum Merkezi",
    "Eşleştirme",
    "Dashboard",
    "Müşteri / CRM",
    "Raporlama",
    "Ayarlar",
    "Genel / Tümü",
]

DURUMLAR  = ["Yeni", "İnceleniyor", "Geliştiriliyor", "Test", "Tamamlandı", "Beklemede"]
ONCELIKLER = ["Kritik", "Yüksek", "Orta", "Düşük"]

CAT_CHIP = {
    "UX": "chip-ux",
    "Teknik": "chip-teknik",
    "Operasyon": "chip-operasyon",
    "Fikir": "chip-fikir",
}

CAT_DOT = {
    "UX": "#4a80e0",
    "Teknik": "#d96030",
    "Operasyon": "#cc3333",
    "Fikir": "#7a50c0",
}

PAGE_DOT = {
    "Proje Hafızası": "#3b82f6",
    "Talep Tablosu": "#4a80e0",
    "Portföy Tablosu": "#e07040",
    "Ofis Paneli": "#5aaa7a",
    "Mail İşlem": "#555555",
    "Zeta Radar": "#c8a030",
    "Sunum Merkezi": "#9b59b6",
    "Eşleştirme": "#cc3333",
    "Dashboard": "#5aaa7a",
    "Müşteri / CRM": "#5b9cf6",
    "Raporlama": "#2eaa88",
    "Ayarlar": "#888888",
    "Genel / Tümü": "#bbbbbb",
}

DUR_CHIP = {
    "Yeni": "chip-yeni",
    "İnceleniyor": "chip-devam",
    "Geliştiriliyor": "chip-devam",
    "Test": "chip-devam",
    "Tamamlandı": "chip-tamam",
    "Beklemede": "chip-bekle",
}

PAGE_PATTERNS = {
    # Sadece sayfa adına özgü, çok spesifik kelimeler — genel kelimeler YOK
    "Talep Tablosu": ["talep tablosu", "talep ekrani", "alici talepleri", "musteri talepleri"],
    "Portföy Tablosu": ["portfoy tablosu", "portfoy ekrani", "portfoy listesi", "ilan listesi"],
    "Ofis Paneli": ["ofis paneli", "ofis dashboard", "ofis portfoyleri", "ofis ilanlari"],
    "Mail İşlem": ["mail islem", "mail cekme", "mail isleme", "imap entegrasyon"],
    "Zeta Radar": ["zeta radar", "gd calisma sayfasi"],
    "Sunum Merkezi": ["sunum merkezi", "musteri sunumu", "sunum olustur"],
    "Eşleştirme": ["eslestirme motoru", "talep portfoy eslesmesi", "otomatik eslestir"],
    "Müşteri / CRM": ["musteri crm", "alici karti", "crm modulu"],
    "Raporlama": ["raporlama ekrani", "rapor olustur"],
    "Ayarlar": ["ayarlar sayfasi", "sistem ayarlari"],
    "Proje Hafızası": ["proje hafizasi", "proje hafıza", "proje hafızası"],
}

# Referans ifadeleri — bu sayfalar etkilenen değil, örnek alınan
REFERANS_PATTERNS = {
    "Ofis Paneli": ["ofis panelindeki gibi", "ofis paneli gibi", "ofis panelindeki filtre",
                    "ofis panelinde oldugu gibi", "ofis paneli standardi"],
    "Talep Tablosu": ["talep tablosundaki gibi", "talep tablosu gibi"],
    "Portföy Tablosu": ["portfoy tablosundaki gibi", "portfoy tablosu gibi"],
}

# =========================================================
# HELPERS
# =========================================================

def today_text():
    return datetime.now().strftime("%d.%m.%Y")


def safe_key(text):
    return (
        str(text)
        .replace(" ", "_")
        .replace("/", "_")
        .replace("ı", "i")
        .replace("İ", "I")
        .replace("ğ", "g")
        .replace("Ğ", "G")
        .replace("ü", "u")
        .replace("Ü", "U")
        .replace("ş", "s")
        .replace("Ş", "S")
        .replace("ö", "o")
        .replace("Ö", "O")
        .replace("ç", "c")
        .replace("Ç", "C")
        .replace(".", "_")
        .replace(",", "_")
        .replace(":", "_")
        .replace(";", "_")
    )


def normalize_text(text):
    text = str(text or "").lower()
    replacements = {
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c",
        "İ": "i",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


def clean_page_name(sf):
    mapping = {
        "Talep Ekranı": "Talep Tablosu",
        "Talep Ekrani": "Talep Tablosu",
        "Portföy Ekranı": "Portföy Tablosu",
        "Portfoy Ekrani": "Portföy Tablosu",
        "Portföy / İlanlar": "Portföy Tablosu",
        "Ofis Dashboard": "Ofis Paneli",
        "Panel": "Ofis Paneli",
    }
    return mapping.get(sf, sf)


def first_sentence(text, max_len=180):
    text = " ".join(str(text or "").split())
    if not text:
        return "Başlıksız kayıt"
    parts = re.split(r"(?<=[.!?])\s+", text)
    s = parts[0] if parts else text
    return s[:max_len] + ("..." if len(s) > max_len else "")


# =========================================================
# PARSER
# =========================================================

def detect_pages(raw_text):
    """Hedef sayfa tespiti.

    Kural: Metinde adı geçen her modül hedef sayfa değildir.
    - "X gibi", "X ile aynı", "X referans" ifadeleri referanstır.
    - "Proje Hafızası ekranında ... Talep Tablosu, Portföy Tablosu ... menüde görünmüyor" gibi cümlelerde hedef sadece Proje Hafızasıdır.
    """
    text = normalize_text(raw_text)
    found = []

    # 1) Proje Hafızası'nın kendi ekran problemiyse diğer modül adları sadece menü öğesidir.
    proje_context = any(k in text for k in [
        "proje hafizasi", "proje hafiza", "proje hafızası"
    ])
    menu_context = any(k in text for k in [
        "ana menu", "ana menü", "giris secenek", "giriş seçenek",
        "modul adina tiklayarak", "modül adına tıklayarak", "menuye giris", "menüye giriş"
    ])
    if proje_context and menu_context:
        return ["Proje Hafızası"]

    # 2) Referans sayfaları ayır.
    referans_sayfalar = set(detect_reference(raw_text))

    # 3) Hedef sayfaları bul.
    for page, patterns in PAGE_PATTERNS.items():
        for pat in patterns:
            if normalize_text(pat) in text:
                if page not in referans_sayfalar and page not in found:
                    found.append(page)
                break

    # 4) "Talep ve portföy ekranında ..." gibi çift hedefleri koru.
    if re.search(r"talep (tablosu|ekrani).{0,80}portfoy (tablosu|ekrani)|portfoy (tablosu|ekrani).{0,80}talep (tablosu|ekrani)", text):
        for page in ["Talep Tablosu", "Portföy Tablosu"]:
            if page not in referans_sayfalar and page not in found:
                found.append(page)

    return found or ["Genel / Tümü"]


def detect_category(raw_text):
    text = normalize_text(raw_text)

    if any(w in text for w in [
        "hata", "bug", "supabase", "api", "veritabani", "database", "kod",
        "algoritma", "performans", "parser", "duplicate", "key", "entegrasyon",
        "veri modeli", "otomasyon", "selenium", "normalize", "standart liste"
    ]):
        return "Teknik"

    if any(w in text for w in [
        "surec", "takip", "operasyon", "kontrol", "rapor", "is akisi",
        "veri kalitesi", "gd", "danisman", "yonetici", "onay", "yetki",
        "temizleme", "standart", "kayit"
    ]):
        return "Operasyon"

    if any(w in text for w in [
        "gorunum", "gorsel", "arayuz", "tasarim", "buton", "renk", "font",
        "filtre", "kart", "liste", "tablo", "badge", "ikon", "hiza",
        "kullanim kolayligi", "ekran", "yerlesim", "sade"
    ]):
        return "UX"

    return "Fikir"


def detect_reference(raw_text):
    """Örnek alınan sayfaları bulur; bu sayfalar hedef sayfa olarak kayıt açmaz."""
    text = normalize_text(raw_text)
    refs = []

    for ref_page, ref_pats in REFERANS_PATTERNS.items():
        for pat in ref_pats:
            if normalize_text(pat) in text:
                refs.append(ref_page)
                break

    # Genel kalıplar: "X ... gibi", "X ... ile aynı", "X referans"
    for page, patterns in PAGE_PATTERNS.items():
        if page in refs:
            continue
        for pat in patterns:
            p = normalize_text(pat)
            if re.search(re.escape(p) + r".{0,35}(gibi|ile ayni|ile aynı|referans|standardi|standardı|ornek|örnek)", text):
                refs.append(page)
                break

    return refs


def build_summary(raw_text, page):
    text = normalize_text(raw_text)

    # Proje Hafızası özel durumlar
    if page == "Proje Hafızası":
        if any(k in text for k in ["ana menu", "ana menü", "giris secenek", "giriş seçenek", "modul adina", "modül adına"]):
            return "Proje Hafızası ekranında ana uygulama menüsü yeniden görünür hale getirilmeli."
        if any(k in text for k in ["baslik", "başlık", "issue", "kart", "format"]):
            return "Proje Hafızası kart başlık formatı profesyonel issue yapısına dönüştürülmeli."
        if any(k in text for k in ["geri bildirim", "feedback", "kullanici notu", "kullanıcı notu"]):
            return "Proje Hafızası kullanıcı geri bildirim merkezi olarak yapılandırılmalı."

    if "mahalle" in text or "semt" in text or "ilce" in text:
        if page == "Talep Tablosu":
            return "Talep lokasyon girişleri standart veri sözlüğüne bağlanmalı."
        if page == "Portföy Tablosu":
            return "Portföy lokasyon alanları standart mahalle/semt yapısıyla normalize edilmeli."

    if "filtre" in text:
        return f"{page} filtre yapısı ortak veri modeliyle standartlaştırılmalı."

    if "pdf" in text or "sunum" in text:
        return f"{page} çıktılarında danışman ve portföy sunum bilgileri güçlendirilmeli."

    # Fallback — tam metni başlık yap, max 100 karakter
    txt = raw_text.strip().rstrip(".")
    if len(txt) <= 80:
        return txt[0].upper() + txt[1:] + "."
    # Uzun metin: noktalamada kes
    for punct in [".", ",", " ve ", " ile "]:
        idx = txt.find(punct, 40)
        if 40 < idx < 90:
            short = txt[:idx].rstrip(",. ")
            return short[0].upper() + short[1:] + "."
    return (txt[:80] + "...")[0].upper() + (txt[:80] + "...")[1:]


def build_prompt_format(raw_text, page, category, refs):
    text = normalize_text(raw_text)
    refs_text = ", ".join(refs) if refs else "Belirtilmedi"

    if "mahalle" in text or "semt" in text or "ilce" in text or "ilçe" in raw_text.lower():
        if page == "Talep Tablosu":
            return f"""AMAÇ:
Talep Tablosu’nda serbest metinle gelen lokasyon bilgisini standart il/ilçe/mahalle/semt yapısına dönüştürmek.

BAĞLAM:
Kullanıcılar talep bilgisini çoğu zaman doğal dille giriyor. Örneğin “Yeşilyurt’ta 2+1 ev arıyoruz” gibi ifadelerde ilçe, mahalle ve semt bilgisi ayrı ayrı yapılandırılmayabiliyor. Daha önce İzmir Standart Mahalle Listesi Supabase’e yüklenmiş ancak filtrelerden kaldırılmış.

HEDEF YAPI:
- İlçe otomatik tahmin edilebilmeli.
- Mahalle kontrollü listeden eşleşmeli.
- Semt/muhit bilgisi ayrı alan olarak tutulabilmeli.
- Talep verisi eşleştirme motoruna temiz ve normalize edilmiş şekilde aktarılmalı.

ÖRNEK SENARYO:
“Yeşilyurt’ta 2+1 ev arıyoruz”
→ İlçe: Karabağlar
→ Semt/Muhit: Yeşilyurt
→ Mahalle: Belirsiz veya en yakın standart kayıt

TEKNİK HEDEF:
Talep Tablosu için lokasyon normalizasyon katmanı oluşturulmalı ve standart mahalle listesiyle yeniden ilişkilendirilmelidir.

İLGİLİ SAYFA:
Talep Tablosu

KATEGORİ:
{category}

REFERANS:
{refs_text}"""

        if page == "Portföy Tablosu":
            return f"""AMAÇ:
Portföy Tablosu’nda ilan lokasyon bilgisini standart il/ilçe/mahalle/semt yapısına bağlamak.

BAĞLAM:
Portföy girişlerinde lokasyon bilgisi serbest metin, mahalle adı, semt adı veya eksik alanlarla gelebiliyor. Talep Tablosu ile sağlıklı eşleşme yapılabilmesi için portföy tarafındaki lokasyon dili de aynı standart yapıya bağlanmalı.

HEDEF YAPI:
- İlçe, mahalle ve semt/muhit alanları ayrıştırılmalı.
- Serbest girilen lokasyon bilgisi normalize edilmeli.
- Talep Tablosu ile aynı lokasyon sözlüğü kullanılmalı.
- Portföy verisi eşleştirme motoruna temiz veri göndermeli.

ÖRNEK SENARYO:
“Alsancak Mimar Sinan’da kiralık ofis”
→ İlçe: Konak
→ Mahalle: Mimar Sinan Mah.
→ Semt/Muhit: Alsancak

TEKNİK HEDEF:
Portföy Tablosu için standart lokasyon veri modeli yeniden aktif hale getirilmeli ve Supabase’deki İzmir mahalle listesiyle ilişkilendirilmelidir.

İLGİLİ SAYFA:
Portföy Tablosu

KATEGORİ:
{category}

REFERANS:
{refs_text}"""

    if "filtre" in text:
        return f"""AMAÇ:
{page} filtre yapısını daha standart, karşılaştırılabilir ve eşleştirme motoruna uygun hale getirmek.

BAĞLAM:
Mevcut filtre yapısı sayfalar arasında tutarlı değil. Kullanıcı aynı kriteri farklı ekranlarda farklı biçimde aramak zorunda kalabiliyor. Bu durum hem kullanıcı deneyimini hem de talep-portföy eşleştirme kalitesini zayıflatıyor.

HEDEF YAPI:
- Filtre alanları standartlaştırılmalı.
- Oda sayısı, fiyat, m², site içi, kullanım durumu ve lokasyon alanları ortak mantıkla çalışmalı.
- Sayfa filtreleri ileride eşleştirme motoruna veri hazırlayacak şekilde tasarlanmalı.

TEKNİK HEDEF:
{page} için filtre modeli ortak veri alanlarıyla yeniden düzenlenmelidir.

İLGİLİ SAYFA:
{page}

KATEGORİ:
{category}

REFERANS:
{refs_text}"""

    # Generic — ham metni olduğu gibi yapıya yerleştir
    ozet_line = first_sentence(raw_text, 120)
    return f"""AMAÇ:
{page} sayfasında aşağıdaki geliştirme/iyileştirme isteğini hayata geçirmek.

BAĞLAM:
{raw_text.strip()}

HEDEF YAPI:
- {page} sayfasında bu değişiklik uygulanmalı.
- Kategori ve durum bilgisiyle takip edilmeli.
- Diğer sayfalarla tutarlılık korunmalı.

TEKNİK HEDEF:
{ozet_line} — bu gereksinim {page} için geliştirilmeli ve test edilmelidir.

İLGİLİ SAYFA:
{page}

KATEGORİ:
{category}

REFERANS:
{refs_text}"""



# =========================================================
# AI ZENGİNLEŞTİRME (isteğe bağlı)
# =========================================================

SAYFALAR_AI = [
    "Talep Tablosu", "Portföy Tablosu", "Ofis Paneli", "Mail İşlem",
    "Zeta Radar", "Sunum Merkezi", "Eşleştirme", "Dashboard",
    "Müşteri / CRM", "Raporlama", "Ayarlar", "Genel / Tümü",
]

def ai_zenginlestir(raw_text, kategori, sayfa):
    """
    Ham notu AI ile zenginleştirir.
    Offline parser çalıştıktan SONRA isteğe bağlı çağrılır.
    Döndürür: {"ozet": str, "oneri": str} veya None (hata durumunda)
    """
    sistem = f"""Sen STARTKEY adlı gayrimenkul CRM SaaS ürününün kıdemli ürün yöneticisi ve teknik analiz asistanısın.

ÜRÜN BAĞLAMI:
- Ana modüller: Proje Hafızası, Talep Tablosu, Portföy Tablosu, Ofis Paneli, Mail İşlem, Zeta Radar, Sunum Merkezi, Eşleştirme, Dashboard, Müşteri/CRM, Raporlama, Ayarlar.
- Talep Tablosu: alıcı/kiracı talepleri.
- Portföy Tablosu: satılık/kiralık ilanlar.
- Ofis Paneli: ofis portföyleri ve yönetici analizi.
- Proje Hafızası: fikir, hata, UX geri bildirimi ve teknik yapılacakların tutulduğu ürün geliştirme ekranı.

ÇOK KRİTİK AYRIM:
1. İLGİLİ SAYFA / HEDEF SAYFA = değişiklik yapılacak ekran.
2. REFERANS SAYFA = örnek alınacak ekran; bu sayfada değişiklik yapılmayacak.

ÖRNEKLER:
- "Talep Tablosu filtreleri Ofis Paneli gibi olsun"
  hedef_sayfa: Talep Tablosu
  referans_sayfalar: [Ofis Paneli]
  Ofis Paneli için ayrı kayıt açma.

- "Proje Hafızası ekranında ana menüde Talep Tablosu, Portföy Tablosu, Ofis Paneli görünmüyor"
  hedef_sayfa: Proje Hafızası
  referans_sayfalar: []
  Talep Tablosu / Portföy Tablosu / Ofis Paneli sadece menü öğesi olarak geçiyor; bunlara ayrı kayıt açma.

- "Talep ve Portföy ekranında mahalle alanları standartlaşsın"
  hedef_sayfa: Talep Tablosu ve Portföy Tablosu olabilir.

Sistem ön sınıflandırması:
- Kategori: {kategori}
- Hedef Sayfa: {sayfa}

GÖREV — 4 alan üret:
1. ozet: Jira/Linear issue başlığı. MAX 8 KELIME. "Fiil + nesne" formatı. Örnekler:
   DOĞRU: "Proje Hafızası sidebar navigasyonu yenilenmeli"
   DOĞRU: "Talep filtre yapısı standartlaştırılmalı"
   YANLIŞ: Ham metni kopyalamak, uzun cümle kurmak
2. aciklama: 2 cümle. İlki sorun/ihtiyacı, ikincisi beklenen faydayı açıklar.
3. kullanici_notu_duzelt: Ham notu sadece yazım/dil açısından düzelt.

PROMPT FORMATI:
AMAÇ: [Hedef sayfada yapılacak net değişiklik]
BAĞLAM: [Sorunun nedeni ve etkisi]
HEDEF YAPI:
- [Madde 1]
- [Madde 2]
- [Madde 3]
TEKNİK HEDEF: [Geliştirici için uygulanabilir görev]
İLGİLİ SAYFA: {sayfa}
KATEGORİ: {kategori}
REFERANS: [Varsa referans sayfa; yoksa Belirtilmedi]

Sadece JSON döndür, markdown kullanma:
{{"ozet": "<max 8 kelime Jira/Linear başlığı>", "aciklama": "<2-3 cümle bağlam özeti>", "kullanici_notu_duzelt": "<düzeltilmiş ham not>"}}"""

    try:
        try:
            anthropic_key = st.secrets["anthropic"]["api_key"]
        except Exception:
            try:
                anthropic_key = st.secrets["ANTHROPIC_API_KEY"]
            except Exception:
                anthropic_key = ""
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-sonnet-4-5",
                "max_tokens": 1200,
                "system": sistem,
                "messages": [{"role": "user", "content": raw_text}],
            },
            timeout=35,
        )
        resp_json = r.json()
        if "content" not in resp_json:
            return None
        raw = resp_json["content"][0]["text"].strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        d = json.loads(raw)
        st.session_state["ai_debug"] = {"ozet": d.get("ozet",""), "aciklama": d.get("aciklama",""), "keys": list(d.keys())}
        return {
            "ozet":       d.get("ozet", "").strip() or None,
            "aciklama":   d.get("aciklama", "").strip() or None,
            "kullanici_notu_duzelt": d.get("kullanici_notu_duzelt", "").strip() or None,
        }
    except Exception:
        return None


def parse_records(raw_text, manual_category="AI belirlesin", manual_page="AI belirlesin"):
    pages = detect_pages(raw_text)
    refs = detect_reference(raw_text)

    if manual_page != "AI belirlesin":
        pages = [manual_page]

    category = detect_category(raw_text)
    if manual_category != "AI belirlesin":
        category = manual_category

    records = []

    for page in pages[:8]:
        records.append({
            "id": str(uuid.uuid4()),
            "tarih": today_text(),
            "durum": st.session_state.get("add_dur", "Yeni"),
            "oncelik": st.session_state.get("add_oncelik", "Orta"),
            "kategori": category,
            "sayfalar": [page],
            "ozet": build_summary(raw_text, page),
            "oneri": build_prompt_format(raw_text, page, category, refs),
            "orijinal_not": raw_text.strip(),
            "orijinal_not_duzeltilmis": "",
            "referans_sayfalar": refs,
            "asama_gecmisi": [{
                "durum": "Yeni",
                "tarih": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "aciklama": "Kayıt oluşturuldu.",
            }],
        })

    return records



# =========================================================
# SUPABASE — REST API (supabase-py gerektirmez)
# =========================================================

def _sb():
    """Supabase bağlantı bilgilerini döndür."""
    cfg = st.secrets.get("supabase", {})
    url = cfg.get("url", "").rstrip("/")
    key = (
        cfg.get("key")
        or cfg.get("publishable_key")
        or cfg.get("anon_key")
        or cfg.get("service_role_key")
        or ""
    )
    return url, key


def _sb_service_key():
    """Storage işlemleri için service role key."""
    cfg = st.secrets.get("supabase", {})
    return (
        cfg.get("secret_key")
        or cfg.get("service_role_key")
        or cfg.get("key")
        or cfg.get("publishable_key")
        or ""
    )


def sb_headers():
    _, key = _sb()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def sb_connected() -> bool:
    url, key = _sb()
    return bool(url and key)


def sb_load_all() -> list:
    """Tüm kayıtları öncelik+tarih sıralamasıyla çek."""
    if not sb_connected():
        return []
    url, _ = _sb()
    try:
        r = requests.get(
            f"{url}/rest/v1/proje_hafizasi",
            headers=sb_headers(),
            params={
                "select": "*",
                "order": "guncelleme.desc",
            },
            timeout=8,
        )
        if r.status_code == 200:
            rows = r.json()
            seen_ids = set()
            deduped = []
            for row in rows:
                rid = row.get("id")
                if rid in seen_ids:
                    continue
                seen_ids.add(rid)
                if isinstance(row.get("sayfalar"), str):
                    try: row["sayfalar"] = json.loads(row["sayfalar"])
                    except: row["sayfalar"] = ["Genel / Tümü"]
                if isinstance(row.get("asama_gecmisi"), str):
                    try: row["asama_gecmisi"] = json.loads(row["asama_gecmisi"])
                    except: row["asama_gecmisi"] = []
                row.setdefault("asama_gecmisi", [])
                row.setdefault("oncelik", "Orta")
                row.setdefault("orijinal_not_duzeltilmis", "")
                row.setdefault("aciklama", "")
                # ekler alanını parse et
                if isinstance(row.get("ekler"), str):
                    try: row["ekler"] = json.loads(row["ekler"])
                    except: row["ekler"] = []
                row.setdefault("ekler", [])
                deduped.append(row)
            return deduped
        return []
    except Exception:
        return []


def sb_insert(note: dict) -> Optional[dict]:
    if not sb_connected():
        return None
    url, _ = _sb()
    payload = _note_to_row(note)
    try:
        r = requests.post(
            f"{url}/rest/v1/proje_hafizasi",
            headers=sb_headers(),
            json=payload,
            timeout=8,
        )
        if r.status_code in (200, 201):
            return r.json()[0] if r.json() else None
    except Exception:
        pass
    return None


def sb_update(note_id: str, fields: dict) -> bool:
    if not sb_connected():
        return False
    url, _ = _sb()
    payload = {k: v for k, v in fields.items()}
    # list alanlarını JSON'a çevir
    for k in ("sayfalar", "asama_gecmisi"):
        if k in payload and isinstance(payload[k], list):
            payload[k] = payload[k]  # Supabase REST array kabul eder
    payload["guncelleme"] = datetime.now().isoformat()
    try:
        r = requests.patch(
            f"{url}/rest/v1/proje_hafizasi",
            headers={**sb_headers(), "Prefer": "return=minimal"},
            params={"id": f"eq.{note_id}"},
            json=payload,
            timeout=8,
        )
        return r.status_code in (200, 201, 204)
    except Exception:
        return False


def sb_delete(note_id: str) -> bool:
    if not sb_connected():
        return False
    url, _ = _sb()
    try:
        r = requests.delete(
            f"{url}/rest/v1/proje_hafizasi",
            headers={**sb_headers(), "Prefer": "return=minimal"},
            params={"id": f"eq.{note_id}"},
            timeout=8,
        )
        return r.status_code in (200, 204)
    except Exception:
        return False


def sb_reorder(note_id: str, new_sira: int) -> bool:
    return sb_update(note_id, {"oncelik_sira": new_sira})


def sb_upload_file(file_bytes: bytes, file_name: str, mime_type: str) -> str:
    """Dosyayı Supabase Storage'a yükle, public URL döndür."""
    if not sb_connected():
        return ""
    url, _ = _sb()
    bucket = "hafiza-ekler"
    # Benzersiz dosya adı
    ext = file_name.rsplit(".", 1)[-1] if "." in file_name else "bin"
    unique_name = f"{uuid.uuid4()}.{ext}"
    try:
        svc_key = _sb_service_key()
        r = requests.post(
            f"{url}/storage/v1/object/{bucket}/{unique_name}",
            headers={
                "apikey": svc_key,
                "Authorization": f"Bearer {svc_key}",
                "Content-Type": mime_type,
                "x-upsert": "true",
            },
            data=file_bytes,
            timeout=20,
        )
        if r.status_code in (200, 201):
            public_url = f"{url}/storage/v1/object/public/{bucket}/{unique_name}"
            return public_url
        return ""
    except Exception:
        return ""


ONCELIK_SIRA = {"Kritik": 1, "Yüksek": 2, "Orta": 3, "Düşük": 4}


def _note_to_row(note: dict) -> dict:
    """Session state notunu DB satırına çevir."""
    oncelik = note.get("oncelik", "Orta")
    return {
        "id":                       note.get("id", str(uuid.uuid4())),
        "kategori":                 note.get("kategori", "Fikir"),
        "oncelik":                  oncelik,
        "oncelik_sira":             ONCELIK_SIRA.get(oncelik, 3),
        "durum":                    note.get("durum", "Yeni"),
        "sayfalar":                 note.get("sayfalar", ["Genel / Tümü"]),
        "ozet":                     note.get("ozet", ""),
        "aciklama":                 note.get("aciklama", ""),
        "oneri":                    note.get("oneri", ""),
        "orijinal_not":             note.get("orijinal_not", ""),
        "orijinal_not_duzeltilmis": note.get("orijinal_not_duzeltilmis", ""),
        "asama_gecmisi":            note.get("asama_gecmisi", []),
        "ekler":                    note.get("ekler", []),
        "guncelleme":               datetime.now().isoformat(),
    }


def asama_guncelle(note: dict, yeni_durum: str, aciklama: str = "") -> dict:
    """Nota yeni aşama ekle, DB'yi güncelle."""
    gecmis = note.get("asama_gecmisi", [])
    gecmis.append({
        "durum":    yeni_durum,
        "tarih":    datetime.now().strftime("%d.%m.%Y %H:%M"),
        "aciklama": aciklama,
    })
    note["durum"]          = yeni_durum
    note["asama_gecmisi"]  = gecmis
    sb_update(note["id"], {
        "durum":         yeni_durum,
        "asama_gecmisi": gecmis,
    })
    return note

# =========================================================
# STATE
# =========================================================

def example_notes():
    raw = "Talep ekranı ve portföy ekranında İzmir Standart Mahalle Listesini Supabase'e yüklemiştik ancak sonradan filtrelerden silindi. Amaç standart ilçe mahalle yapısına en uygun eşleşmeyi sağlamak."
    return parse_records(raw, "Teknik", "AI belirlesin")


def migrate_notes(notes):
    for n in notes:
        n.setdefault("id", str(uuid.uuid4()))
        n.setdefault("tarih", today_text())
        n.setdefault("durum", "Yeni")
        n.setdefault("kategori", "Fikir")
        n.setdefault("sayfalar", ["Genel / Tümü"])
        n.setdefault("oneri", "")
        n.setdefault("orijinal_not", n.get("oneri", ""))
        n.setdefault("ozet", first_sentence(n.get("oneri", ""), 100))

        if n["durum"] == "Tamamlandi":
            n["durum"] = "Tamamlandı"

        n["kategori"] = n["kategori"] if n["kategori"] in KATEGORILER else "Fikir"
        n["durum"] = n["durum"] if n["durum"] in DURUMLAR else "Yeni"
        n["sayfalar"] = [clean_page_name(s) for s in n["sayfalar"] if clean_page_name(s) in SAYFALAR]

        if not n["sayfalar"]:
            n["sayfalar"] = ["Genel / Tümü"]

        n.setdefault("oncelik", "Orta")
        n.setdefault("aciklama", "")
        n.setdefault("asama_gecmisi", [])
        n.setdefault("orijinal_not_duzeltilmis", "")
        n.setdefault("ekler", [])

    return notes


def init_state():
    # İlk yüklemede Supabase'den çek
    if "ph_notes" not in st.session_state:
        if sb_connected():
            rows = sb_load_all()
            st.session_state["ph_notes"] = migrate_notes(rows) if rows else example_notes()
        else:
            st.session_state["ph_notes"] = example_notes()

    st.session_state.setdefault("ph_view", ("tumu", None))
    st.session_state.setdefault("ph_ara", "")
    st.session_state.setdefault("ph_show_add", False)
    st.session_state.setdefault("ph_show_pages", True)
    st.session_state.setdefault("ph_show_cats", True)
    st.session_state.setdefault("ph_show_export", False)
    st.session_state.setdefault("ph_preview_records", [])


# =========================================================
# EXPORT
# =========================================================

def export_as_text(notes):
    lines = []
    lines.append("PROJE HAFIZASI ÇIKTISI")
    lines.append("=" * 60)
    lines.append(f"Tarih: {today_text()}")
    lines.append("")

    for i, n in enumerate(notes, start=1):
        lines.append(f"{i}. {n.get('ozet', '')}")
        lines.append(f"Sayfa: {', '.join(n.get('sayfalar', []))}")
        lines.append(f"Kategori: {n.get('kategori', '')}")
        lines.append(f"Durum: {n.get('durum', '')}")
        lines.append("")
        lines.append("ORİJİNAL HAM NOT:")
        lines.append(n.get("orijinal_not", ""))
        lines.append("-" * 60)

    return "\n".join(lines)


def export_as_html(notes):
    body = ""
    for i, n in enumerate(notes, start=1):
        body += f"""
        <div class="card">
            <h2>{i}. {n.get("ozet", "")}</h2>
            <p><b>Sayfa:</b> {", ".join(n.get("sayfalar", []))}</p>
            <p><b>Kategori:</b> {n.get("kategori", "")} | <b>Durum:</b> {n.get("durum", "")}</p>
            <h3>Orijinal Kullanıcı Notu</h3>
            <pre>{n.get("orijinal_not", "")}</pre>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
    <meta charset="UTF-8">
    <title>Proje Hafızası Çıktısı</title>
    <style>
        body {{ font-family: Arial, sans-serif; background:#f7f4ee; color:#222; padding:40px; }}
        h1 {{ font-size:28px; margin-bottom:5px; }}
        .sub {{ color:#777; margin-bottom:30px; }}
        .card {{ background:white; border:1px solid #ddd; border-radius:12px; padding:22px; margin-bottom:22px; page-break-inside:avoid; }}
        h2 {{ font-size:19px; margin-top:0; }}
        h3 {{ font-size:14px; margin-top:18px; color:#555; }}
        pre {{ white-space:pre-wrap; font-family: Arial, sans-serif; line-height:1.45; background:#fafafa; border:1px solid #eee; border-radius:8px; padding:12px; }}
        @media print {{ body {{ background:white; }} .card {{ page-break-inside:avoid; }} }}
    </style>
    </head>
    <body>
        <h1>Proje Hafızası Çıktısı</h1>
        <div class="sub">Tarih: {today_text()} · Kayıt Sayısı: {len(notes)}</div>
        {body}
    </body>
    </html>
    """


# =========================================================
# UI
# =========================================================

def render_export_panel(notes):
    show = st.session_state.get("ph_show_export", False)
    lbl  = "▾ Çıktı Al" if show else "▸ Çıktı Al"
    if st.button(lbl, key="toggle_export"):
        st.session_state["ph_show_export"] = not show
        st.rerun()
    if not show:
        return
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("Liste (.txt)", data=export_as_text(notes),
            file_name=f"hafiza_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain", use_container_width=True)
    with c2:
        st.download_button("PDF için HTML", data=export_as_html(notes),
            file_name=f"hafiza_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
            mime="text/html", use_container_width=True)
    st.caption("HTML'i tarayıcıda açıp Ctrl+P → PDF kaydedebilirsin.")


def sidebar_button(label, count, key, view_tuple):
    active = st.session_state["ph_view"] == view_tuple
    icon = "●" if active else "○"

    if st.button(f"{icon}  {label}  ({count})", key=key, use_container_width=True):
        st.session_state["ph_view"] = view_tuple
        st.rerun()


APP_MENU = [
    ("Talep Tablosu", "/Talep_Tablosu"),
    ("Portföy Tablosu", "/Portfoy_Tablosu"),
    ("AI Asistan", "/AI_Asistan"),
    ("Ofis Paneli", "/Ofis_Paneli"),
    ("Mail İşlem", "/Mail_Islem"),
    ("Zeta Radar", "/Zeta_Radar"),
    ("Veri Temizle", "/Veri_Temizle"),
    ("Mail Sunum Demosu", "/Mail_Sunum_Demosu"),
    ("WhatsApp Sunum Demosu", "/WhatsApp_Sunum_Demosu"),
    ("Kart Görsel Demosu", "/Kart_Gorsel_Demosu"),
    ("Proje Hafızası", "/proje_hafizasi_app_v2"),
]


def render_app_menu():
    st.markdown('<div class="side-section-title">Uygulama</div>', unsafe_allow_html=True)
    for label, href in APP_MENU:
        active_cls = " app-menu-active" if label == "Proje Hafızası" else ""
        st.markdown(
            f'<a class="app-menu-link{active_cls}" href="{href}" target="_self">{label}</a>',
            unsafe_allow_html=True,
        )


def render_sidebar(notes):
    with st.sidebar:
        sb_ok = sb_connected()
        sb_icon = "🟢" if sb_ok else "🔴"
        st.markdown('<div class="sidebar-title">📓 Proje Hafızası</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sidebar-sub">{len(notes)} kayıt toplam</div>', unsafe_allow_html=True)

        render_app_menu()

        st.markdown('<div class="side-section-title">Proje Hafızası Filtreleri</div>', unsafe_allow_html=True)
        st.text_input("", placeholder="🔍 Ara...", key="ph_ara", label_visibility="collapsed")

        st.write("")
        aktif_view = st.session_state.get("ph_view", ("tumu", None))
        icon_all = "●" if aktif_view == ("tumu", None) else "○"
        if st.button(f"{icon_all} Tüm Sayfalar ({len(notes)})", key="nav_all", use_container_width=True):
            st.session_state["ph_view"] = ("tumu", None)
            st.rerun()

        st.markdown('<div class="side-section-title">Sayfa / Modül</div>', unsafe_allow_html=True)

        for page in SAYFALAR:
            count = sum(1 for n in notes if page in n.get("sayfalar", []))
            if count:
                sidebar_button(page, count, f"nav_page_{safe_key(page)}", ("sayfa", page))

        st.markdown('<div class="side-section-title">Kategori</div>', unsafe_allow_html=True)

        for cat in KATEGORILER:
            count = sum(1 for n in notes if n.get("kategori") == cat)
            sidebar_button(cat, count, f"nav_cat_{safe_key(cat)}", ("kat", cat))


def render_note_card(note, context_page="", row_num=0, total=0):
    real_id = note["id"]
    ks      = safe_key(f"{real_id}_{context_page}")
    det_key = f"det_{ks}"
    not_key = f"not_{ks}"
    edt_key = f"edt_{ks}"
    mnu_key = f"mnu_{ks}"
    for k in (det_key, not_key, edt_key, mnu_key):
        st.session_state.setdefault(k, False)

    cat     = note.get("kategori", "Fikir")
    dur     = note.get("durum", "Yeni")
    oncelik = note.get("oncelik", "Orta")
    cat_col = CAT_DOT.get(cat, "#888")
    done    = dur == "Tamamlandı"

    chip_str = (
        f'<span class="chip-xs" style="color:#94a3b8;">{oncelik}</span> '
        f'<span class="chip-xs" style="color:{cat_col};opacity:0.75;">{cat}</span>'
        + "".join(f' <span class="chip-xs" style="color:#94a3b8;">{p}</span>'
                  for p in note.get("sayfalar", []))
        + f' <span class="chip-xs" style="color:#94a3b8;">{dur}</span>'
        + f' <span style="font-size:9px;color:#cbd5e1;">{note.get("tarih","")}</span>'
    )

    cat_cls_map   = {"UX":"cat-ux","Teknik":"cat-teknik","Operasyon":"cat-operasyon","Fikir":"cat-fikir"}
    cat_cls_val   = cat_cls_map.get(cat, "")
    border_style  = "border-left-color:#22c55e;" if done else ""
    opacity_style = "opacity:0.5;" if done else ""
    title_style   = "text-decoration:line-through;color:#94a3b8;" if done else "color:#0f172a;"
    chk_icon      = "✓" if done else "○"
    chk_color     = "#22c55e" if done else "#cbd5e1"
    title_text    = note.get("ozet", "Başlıksız kayıt")

    col_card, col_dot = st.columns([13, 0.55])

    with col_card:
        num_color    = "#22c55e" if done else "#94a3b8"
        aciklama_txt = note.get("aciklama", "")
        aciklama_blk = (
            '<div style="font-size:12.5px;color:#64748b;margin-top:5px;'
            'line-height:1.5;padding-left:26px;">' + aciklama_txt + '</div>'
        ) if aciklama_txt else ""

        card_html = (
            '<div class="note-card-wrap ' + cat_cls_val + '" style="' + border_style + opacity_style + '">'
            + '<div class="note-chips">' + chip_str + '</div>'
            + '<div style="display:flex;align-items:flex-start;gap:8px;">'
            + '<span style="font-size:13px;font-weight:700;color:' + num_color + ';'
            + 'min-width:22px;flex-shrink:0;padding-top:2px;">' + str(row_num) + '.</span>'
            + '<div style="flex:1;">'
            + '<div style="font-size:16px;font-weight:800;letter-spacing:-0.02em;'
            + 'line-height:1.4;' + title_style + '">' + title_text + '</div>'
            + aciklama_blk
            + '</div></div></div>'
        )
        # Ekler — sadece linkler, temiz görünüm
        ekler = note.get("ekler", [])
        if ekler:
            ek_html = " ".join(
                f'<a href="{e["url"]}" target="_blank" style="font-size:11px;color:#64748b;'
                f'background:#f1f5f9;border-radius:4px;padding:2px 8px;margin-right:4px;'
                f'text-decoration:none;">📎 {e["ad"]}</a>'
                for e in ekler
            )
            card_html = card_html.replace(
                "</div>",
                f'<div style="padding:5px 0 0 26px;">{ek_html}</div></div>',
                1
            )
        st.markdown(card_html, unsafe_allow_html=True)

    with col_dot:
        st.markdown("<div style='padding-top:14px'>", unsafe_allow_html=True)
        if st.button("⋯", key=f"mdot_{ks}", help="İşlemler"):
            st.session_state[mnu_key] = not st.session_state[mnu_key]
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state[mnu_key]:
        ma, mb, mc, md, me, mf = st.columns([1.3, 1.3, 1.3, 0.5, 0.5, 0.5])
        with ma:
            chk_lbl = "✓ Geri Al" if done else "✓ Tamamla"
            if st.button(chk_lbl, key=f"chk_{ks}"):
                yeni = "Yeni" if done else "Tamamlandı"
                note["durum"] = yeni
                gecmis = note.get("asama_gecmisi", [])
                gecmis.append({"durum": yeni,
                               "tarih": datetime.now().strftime("%d.%m.%Y %H:%M"),
                               "aciklama": "Manuel işaretlendi."})
                note["asama_gecmisi"] = gecmis
                if sb_connected():
                    sb_update(real_id, {"durum": yeni, "asama_gecmisi": gecmis})
                st.rerun()
        with mb:
            lbl = "▼ Notum" if st.session_state[not_key] else "▶ Notum"
            if st.button(lbl, key=f"nbt_{ks}"):
                st.session_state[not_key] = not st.session_state[not_key]; st.rerun()
        with mc:
            lbl = "▼ Düzenle" if st.session_state[edt_key] else "▶ Düzenle"
            if st.button(lbl, key=f"ebt_{ks}"):
                st.session_state[edt_key] = not st.session_state[edt_key]; st.rerun()
        with md:
            if row_num > 1 and st.button("↑", key=f"ubt_{ks}"):
                nl = st.session_state["ph_notes"]
                ix = next((j for j,n in enumerate(nl) if n["id"]==real_id), None)
                if ix: nl[ix-1], nl[ix] = nl[ix], nl[ix-1]; st.rerun()
        with me:
            if row_num < total and st.button("↓", key=f"dbt2_{ks}"):
                nl = st.session_state["ph_notes"]
                ix = next((j for j,n in enumerate(nl) if n["id"]==real_id), None)
                if ix is not None and ix < len(nl)-1: nl[ix+1], nl[ix] = nl[ix], nl[ix+1]; st.rerun()
        with mf:
            if st.button("✕", key=f"xbt_{ks}", help="Sil"):
                st.session_state["ph_notes"] = [n for n in st.session_state["ph_notes"] if n["id"] != real_id]
                if sb_connected(): sb_delete(real_id)
                st.rerun()


    if st.session_state[not_key]:
        st.text_area("", value=note.get("orijinal_not",""), height=100,
                     key=f"nta_{ks}", disabled=True, label_visibility="collapsed")

    if st.session_state[edt_key]:
        c1, c2 = st.columns(2)
        with c1:
            new_status = st.selectbox("Durum", DURUMLAR,
                index=DURUMLAR.index(note.get("durum","Yeni")), key=f"st_{ks}")
        with c2:
            new_oncelik = st.selectbox("Öncelik", ONCELIKLER,
                index=ONCELIKLER.index(note.get("oncelik","Orta")), key=f"oc_{ks}")
        new_cat = st.selectbox("Kategori", KATEGORILER,
            index=KATEGORILER.index(note.get("kategori","Fikir")), key=f"ct_{ks}")
        new_pages = st.multiselect("Sayfalar", SAYFALAR,
            default=note.get("sayfalar",[]), key=f"pg_{ks}")
        new_ozet  = st.text_input("Özet", value=note.get("ozet",""), key=f"oz_{ks}")
        new_ham   = st.text_area("Kullanıcı Notu", value=note.get("orijinal_not",""), height=80, key=f"hm_{ks}")
        asama_not = st.text_input("Aşama notu", key=f"an_{ks}", placeholder="opsiyonel...")
        # Ek dosya silme
        ekler = note.get("ekler", [])
        if ekler:
            st.markdown("<div style='font-size:12px;font-weight:700;color:#64748b;margin-top:4px;'>📎 Ekler</div>", unsafe_allow_html=True)
            for ei, ek in enumerate(ekler):
                ec1, ec2 = st.columns([5, 1])
                with ec1:
                    st.markdown(f'<a href="{ek["url"]}" target="_blank" style="font-size:12px;color:#64748b;text-decoration:none;">📎 {ek["ad"]}</a>', unsafe_allow_html=True)
                with ec2:
                    if st.button("Sil", key=f"del_ek_{ks}_{ei}", type="secondary"):
                        yeni_ekler = [e for j, e in enumerate(ekler) if j != ei]
                        note["ekler"] = yeni_ekler
                        if sb_connected():
                            sb_update(real_id, {"ekler": yeni_ekler})
                        st.rerun()
        if st.button("Kaydet", key=f"sv_{ks}", type="primary"):
            eski = note.get("durum","")
            note.update({"durum":new_status,"oncelik":new_oncelik,"kategori":new_cat,
                         "sayfalar":new_pages or ["Genel / Tümü"],"ozet":new_ozet,
                         "orijinal_not":new_ham})
            if new_status != eski or asama_not.strip():
                gecmis = note.get("asama_gecmisi",[])
                gecmis.append({"durum":new_status,
                               "tarih":datetime.now().strftime("%d.%m.%Y %H:%M"),
                               "aciklama":asama_not.strip() or f"{eski} → {new_status}"})
                note["asama_gecmisi"] = gecmis
            if sb_connected():
                sb_update(real_id, {"durum":new_status,"oncelik":new_oncelik,
                    "oncelik_sira":ONCELIK_SIRA.get(new_oncelik,3),
                    "kategori":new_cat,"sayfalar":new_pages or ["Genel / Tümü"],
                    "ozet":new_ozet,"aciklama":note.get("aciklama",""),
                    "orijinal_not":new_ham,
                    "asama_gecmisi":note.get("asama_gecmisi",[])})
            st.session_state[edt_key] = False
            st.rerun()


def render_add_panel():
    if not st.session_state["ph_show_add"]:
        if st.button("＋  Yeni Öneri Ekle",
                     key="open_add", type="primary", use_container_width=True):
            st.session_state["ph_show_add"] = True
            st.rerun()
        return

    with st.container(border=True):
        st.markdown("**Yeni Öneri** — doğal metni yaz, sistem yapılandırır.")
        raw = st.text_area("", height=120, key="add_raw_text",
            placeholder="Örn: Talep tablosunda mahalle filtresi çalışmıyor...",
            label_visibility="collapsed")

        uploaded_files = st.file_uploader(
            "📎 Dosya ekle (ekran görüntüsü, HTML, PDF...)",
            accept_multiple_files=True,
            type=["png","jpg","jpeg","gif","webp","pdf","csv","txt","zip"],
            key="add_files",
        )

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.selectbox("Durum", DURUMLAR, key="add_dur")
        with c2: st.selectbox("Öncelik", ONCELIKLER, index=2, key="add_oncelik")
        with c3: manual_cat  = st.selectbox("Kategori", ["AI belirlesin"]+KATEGORILER, key="add_manual_cat")
        with c4: manual_page = st.selectbox("Sayfa",    ["AI belirlesin"]+SAYFALAR,    key="add_manual_page")

        if st.session_state.get("ai_son_hata"):
            st.error(f"Son AI hatası: {st.session_state['ai_son_hata']}")
        if st.session_state.get("ai_debug"):
            st.info(f"AI debug: {st.session_state['ai_debug']}")
        b1, b2, b3, b4 = st.columns([1.2, 1.2, 1.6, 0.9])
        with b1:
            if st.button("Önizle", key="preview_parse"):
                if raw.strip():
                    st.session_state["ph_preview_records"] = parse_records(raw, manual_cat, manual_page)
                else:
                    st.warning("Boş olamaz.")
        with b2:
            if st.button("Ekle", key="add_parsed"):
                if raw.strip():
                    recs = parse_records(raw, manual_cat, manual_page)
                    # Dosyaları yükle
                    ek_urls = []
                    if uploaded_files:
                        with st.spinner("Dosyalar yükleniyor..."):
                            for f in uploaded_files:
                                url = sb_upload_file(f.read(), f.name, f.type or "application/octet-stream")
                                if url:
                                    ek_urls.append({"ad": f.name, "url": url, "tip": f.type or ""})
                    for r in recs:
                        r["ekler"] = ek_urls
                        st.session_state["ph_notes"].insert(0, r)
                        if sb_connected(): sb_insert(r)
                    st.session_state.update({"ph_preview_records":[], "ph_show_add":False})
                    st.rerun()
                else:
                    st.warning("Boş olamaz.")
        with b3:
            if st.button("🤖 AI ile Ekle", key="add_ai", type="primary"):
                if raw.strip():
                    recs = parse_records(raw, manual_cat, manual_page)
                    with st.spinner("AI analiz ediyor..."):
                        for r in recs:
                            s = ai_zenginlestir(r["orijinal_not"], r["kategori"],
                                r["sayfalar"][0] if r["sayfalar"] else "Genel / Tümü")
                            if s:
                                if s.get("ozet"):     r["ozet"]     = s["ozet"]
                                if s.get("aciklama"): r["aciklama"] = s["aciklama"]
                                if s.get("kullanici_notu_duzelt"):
                                    r["orijinal_not"] = s["kullanici_notu_duzelt"]
                    # Dosyaları yükle
                    ek_urls = []
                    if uploaded_files:
                        with st.spinner("Dosyalar yükleniyor..."):
                            for f in uploaded_files:
                                url = sb_upload_file(f.read(), f.name, f.type or "application/octet-stream")
                                if url:
                                    ek_urls.append({"ad": f.name, "url": url, "tip": f.type or ""})
                    for r in recs:
                        r["ekler"] = ek_urls
                        st.session_state["ph_notes"].insert(0, r)
                        if sb_connected(): sb_insert(r)
                    st.session_state.update({"ph_preview_records":[], "ph_show_add":False})
                    st.rerun()
                else:
                    st.warning("Boş olamaz.")
        with b4:
            if st.button("İptal", key="cancel_add"):
                st.session_state.update({"ph_preview_records":[], "ph_show_add":False})
                st.rerun()

        if st.session_state.get("ph_preview_records"):
            for rec in st.session_state["ph_preview_records"]:
                st.markdown(f"**{rec['sayfalar'][0]}** · `{rec['kategori']}`  \n{rec['ozet']}")


def render_page_block(page_notes, page_name):
    """Tek sayfa bloğu — alışveriş listesi gibi alt alta."""
    if not page_notes:
        view = st.session_state.get("ph_view", ("tumu", None))
        kat_msg = (view[1] + " kategorisinde") if (view[0] == "kat" and view[1]) else "Bu sayfada"
        st.markdown(
            "<div style='color:#94a3b8;font-size:13px;padding:24px;text-align:center;'>" +
            "\U0001f4eb " + kat_msg + " henüz kayıt yok.</div>",
            unsafe_allow_html=True,
        )
        return

    # Blok başlığı
    st.markdown(f"""
    <div class="page-block-header">
        <span class="page-block-name">{page_name}</span>
        <span class="page-block-count">{len(page_notes)} öğe</span>
    </div>""", unsafe_allow_html=True)

    for i, note in enumerate(page_notes, 1):
        render_note_card(note, context_page=page_name, row_num=i, total=len(page_notes))


# =========================================================
# GÖRÜNÜM MOD CSS EKLENTİSİ
# =========================================================

VIEW_MODE_CSS = """
<style>
/* Görünüm geçiş butonları */
.view-switcher {
    display: flex;
    gap: 4px;
    background: #e5e9f0;
    border: 1px solid #d8dee8;
    border-radius: 10px;
    padding: 4px;
    width: fit-content;
}
.view-btn-active {
    background: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #d8dee8 !important;
    border-radius: 7px !important;
    padding: 5px 14px !important;
    font-size: 12px !important;
    font-weight: 800 !important;
    cursor: pointer;
    box-shadow: 0 1px 3px rgba(15,23,42,0.08) !important;
}
.view-btn-passive {
    background: transparent !important;
    color: #64748b !important;
    border: 1px solid transparent !important;
    border-radius: 7px !important;
    padding: 5px 14px !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    cursor: pointer;
}

/* Timeline görünümü */
.tl-group-header {
    font-size: 11px;
    font-weight: 800;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: #94a3b8;
    padding: 18px 0 8px 0;
    border-bottom: 1px solid #e2e8f0;
    margin-bottom: 2px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.tl-count-pill {
    background: #e8eef7;
    color: #64748b;
    border-radius: 999px;
    padding: 1px 8px;
    font-size: 10px;
    font-weight: 800;
}
.tl-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid #f1f5f9;
    position: relative;
}
.tl-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-top: 6px;
    flex-shrink: 0;
}
.tl-date {
    font-size: 10px;
    color: #94a3b8;
    font-weight: 700;
    min-width: 62px;
    padding-top: 3px;
    flex-shrink: 0;
}
.tl-body {
    flex: 1;
    min-width: 0;
}
.tl-title {
    font-size: 14px;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.4;
    margin-bottom: 3px;
}
.tl-chips {
    display: flex;
    gap: 5px;
    flex-wrap: wrap;
}
.tl-chip {
    font-size: 9px;
    font-weight: 800;
    padding: 1px 6px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: .35px;
}

/* Tablo görünümü */
.ph-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}
.ph-table thead th {
    background: #f1f5f9;
    color: #475569;
    font-size: 10px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .1em;
    padding: 8px 12px;
    border-bottom: 2px solid #d8dee8;
    text-align: left;
    white-space: nowrap;
    cursor: pointer;
    user-select: none;
}
.ph-table thead th:hover { background: #e8eef7; }
.ph-table tbody tr {
    border-bottom: 1px solid #f1f5f9;
    transition: background .08s;
}
.ph-table tbody tr:hover { background: #f8fafc; }
.ph-table tbody td {
    padding: 9px 12px;
    vertical-align: top;
    color: #0f172a;
}
.ph-table tbody td.td-ozet {
    max-width: 340px;
    font-weight: 600;
    line-height: 1.4;
}
.ph-table tbody td.td-meta {
    white-space: nowrap;
}
.ph-table .td-pill {
    display: inline-block;
    border-radius: 4px;
    padding: 1px 7px;
    font-size: 10px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .3px;
}

/* Kanban görünümü */
.kanban-board {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    padding-bottom: 12px;
    align-items: flex-start;
}
.kanban-col {
    flex: 0 0 240px;
    background: #f1f5f9;
    border-radius: 12px;
    border: 1px solid #d8dee8;
    padding: 12px 10px;
    min-height: 120px;
}
.kanban-col-header {
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .1em;
    color: #475569;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.kanban-col-count {
    background: #dde3ed;
    color: #64748b;
    border-radius: 999px;
    padding: 1px 8px;
    font-size: 10px;
    font-weight: 800;
}
.kanban-card {
    background: #fff;
    border-radius: 8px;
    border: 1px solid #d8dee8;
    border-left: 4px solid #cbd5e1;
    padding: 10px 12px;
    margin-bottom: 8px;
    box-shadow: 0 1px 4px rgba(15,23,42,0.04);
}
.kanban-card.cat-ux        { border-left-color: #3b82f6; }
.kanban-card.cat-teknik    { border-left-color: #f97316; }
.kanban-card.cat-operasyon { border-left-color: #ef4444; }
.kanban-card.cat-fikir     { border-left-color: #8b5cf6; }
.kanban-card-title {
    font-size: 12px;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.4;
    margin-bottom: 6px;
}
.kanban-card-meta {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
}
.kanban-chip {
    font-size: 9px;
    font-weight: 800;
    padding: 1px 5px;
    border-radius: 3px;
    text-transform: uppercase;
    letter-spacing: .3px;
}
</style>
"""

# =========================================================
# GÖRÜNÜM: TİMELİNE
# =========================================================

def _parse_tarih(tarih_str: str):
    """Tarih string'ini datetime'a çevirir; parse edilemezse çok eski döndürür."""
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(tarih_str[:10], fmt)
        except Exception:
            pass
    return datetime(2000, 1, 1)


def _tarih_grubu(dt: datetime) -> str:
    now = datetime.now()
    delta = (now - dt).days
    if delta == 0:
        return "Bugün"
    elif delta <= 7:
        return "Bu Hafta"
    elif delta <= 30:
        return "Bu Ay"
    elif delta <= 90:
        return "Son 3 Ay"
    else:
        return "Daha Önce"


GRUP_SIRA = ["Bugün", "Bu Hafta", "Bu Ay", "Son 3 Ay", "Daha Önce"]


def render_timeline(notes, kat_filtre=None):
    """Kronolojik zaman akışı görünümü."""
    filtreli = [n for n in notes if not kat_filtre or n.get("kategori") == kat_filtre]
    if not filtreli:
        st.markdown('<div class="empty-state">📭<br>Kayıt yok.</div>', unsafe_allow_html=True)
        return

    # Tarihe göre sırala (yeniden eskiye)
    filtreli.sort(key=lambda n: _parse_tarih(n.get("tarih", "")), reverse=True)

    # Grupla
    from collections import defaultdict
    gruplar = defaultdict(list)
    for n in filtreli:
        g = _tarih_grubu(_parse_tarih(n.get("tarih", "")))
        gruplar[g].append(n)

    for grup in GRUP_SIRA:
        items = gruplar.get(grup)
        if not items:
            continue

        # Grup başlığı
        st.markdown(
            f'<div class="tl-group-header">{grup}'
            f'<span class="tl-count-pill">{len(items)}</span></div>',
            unsafe_allow_html=True,
        )

        for i, note in enumerate(items):
            cat      = note.get("kategori", "Fikir")
            dur      = note.get("durum", "Yeni")
            oncelik  = note.get("oncelik", "Orta")
            sayfalar = note.get("sayfalar", [])
            done     = dur == "Tamamlandı"
            dot_color = CAT_DOT.get(cat, "#888")

            dur_chip_cls   = DUR_CHIP.get(dur, "chip-bekle")
            onc_cls_map    = {"Kritik":"chip-kritik","Yüksek":"chip-yuksek","Orta":"chip-orta","Düşük":"chip-dusuk"}
            onc_chip_cls   = onc_cls_map.get(oncelik, "chip-orta")
            sayfa_label    = sayfalar[0] if sayfalar else "—"

            title_style = "text-decoration:line-through;color:#94a3b8;" if done else ""
            aciklama    = note.get("aciklama", "")

            col_tl, col_act = st.columns([11, 0.5])
            with col_tl:
                st.markdown(f"""
                <div class="tl-row">
                    <div class="tl-dot" style="background:{dot_color};"></div>
                    <div class="tl-date">{note.get("tarih","")}</div>
                    <div class="tl-body">
                        <div class="tl-title" style="{title_style}">{note.get("ozet","Başlıksız")}</div>
                        {"<div style='font-size:11.5px;color:#64748b;margin:2px 0 4px;line-height:1.4;'>" + aciklama + "</div>" if aciklama else ""}
                        <div class="tl-chips">
                            <span class="tl-chip {onc_chip_cls}">{oncelik}</span>
                            <span class="tl-chip {CAT_CHIP.get(cat,'chip-page')}">{cat}</span>
                            <span class="tl-chip chip-page">{sayfa_label}</span>
                            <span class="tl-chip {dur_chip_cls}">{dur}</span>
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)

            with col_act:
                st.markdown("<div style='padding-top:8px'>", unsafe_allow_html=True)
                ks = safe_key(f"{note['id']}_tl")
                mnu_key = f"mnu_{ks}"
                st.session_state.setdefault(mnu_key, False)
                if st.button("⋯", key=f"tl_dot_{ks}", help="İşlemler"):
                    st.session_state[mnu_key] = not st.session_state[mnu_key]
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            if st.session_state.get(mnu_key):
                render_note_card(note, context_page="tl", row_num=i+1, total=len(filtreli))
                st.session_state[mnu_key] = False


# =========================================================
# GÖRÜNÜM: TABLO
# =========================================================

def render_table(notes, kat_filtre=None, sort_key="tarih", sort_asc=False):
    """Sütun bazlı tablo görünümü."""
    filtreli = [n for n in notes if not kat_filtre or n.get("kategori") == kat_filtre]
    if not filtreli:
        st.markdown('<div class="empty-state">📭<br>Kayıt yok.</div>', unsafe_allow_html=True)
        return

    # Sıralama
    sk = st.session_state.get("ph_tbl_sort", ("tarih", False))
    sort_col, sort_asc = sk

    def sort_val(n):
        if sort_col == "tarih":
            return _parse_tarih(n.get("tarih", ""))
        elif sort_col == "oncelik":
            return ONCELIK_SIRA.get(n.get("oncelik", "Orta"), 3)
        elif sort_col == "durum":
            return n.get("durum", "")
        elif sort_col == "kategori":
            return n.get("kategori", "")
        elif sort_col == "sayfa":
            return n.get("sayfalar", [""])[0]
        return n.get("ozet", "")

    filtreli.sort(key=sort_val, reverse=not sort_asc)

    def sort_btn(col_id, label):
        arrow = ""
        if sort_col == col_id:
            arrow = " ↑" if sort_asc else " ↓"
        btn_label = label + arrow
        return btn_label

    # Sütun sıralama butonları
    th_cols = st.columns([0.7, 0.8, 4.5, 1.0, 1.0, 0.9, 0.5])
    headers = [
        ("oncelik",  "Öncelik"),
        ("tarih",    "Tarih"),
        ("ozet",     "Özet"),
        ("sayfa",    "Sayfa"),
        ("kategori", "Kategori"),
        ("durum",    "Durum"),
        ("",         ""),
    ]
    st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stButton"] > button {
        background:#f1f5f9 !important; border-bottom:2px solid #d8dee8 !important;
        border-radius:0 !important; font-size:10px !important; font-weight:800 !important;
        text-transform:uppercase; letter-spacing:.08em; color:#475569 !important;
        padding:6px 8px !important;
    }
    </style>""", unsafe_allow_html=True)

    for col, (cid, clabel) in zip(th_cols, headers):
        with col:
            if cid:
                if st.button(sort_btn(cid, clabel), key=f"th_{cid}", use_container_width=True):
                    if sort_col == cid:
                        st.session_state["ph_tbl_sort"] = (cid, not sort_asc)
                    else:
                        st.session_state["ph_tbl_sort"] = (cid, False)
                    st.rerun()

    st.markdown("<div style='border-bottom:2px solid #d8dee8;margin-bottom:4px;'></div>",
                unsafe_allow_html=True)

    onc_cls_map = {"Kritik":"chip-kritik","Yüksek":"chip-yuksek","Orta":"chip-orta","Düşük":"chip-dusuk"}

    for i, note in enumerate(filtreli):
        cat     = note.get("kategori", "Fikir")
        dur     = note.get("durum", "Yeni")
        oncelik = note.get("oncelik", "Orta")
        done    = dur == "Tamamlandı"
        dot_clr = CAT_DOT.get(cat, "#888")

        row_cols = st.columns([0.7, 0.8, 4.5, 1.0, 1.0, 0.9, 0.5])
        with row_cols[0]:
            _onc_cls = onc_cls_map.get(oncelik, 'chip-orta')
            st.markdown(
                f'<div style="padding-top:8px"><span class="chip td-pill {_onc_cls}">'
                f'{oncelik[:3]}</span></div>',
                unsafe_allow_html=True)
        with row_cols[1]:
            st.markdown(
                f'<div style="font-size:11px;color:#94a3b8;padding-top:10px;font-weight:600;">'
                f'{note.get("tarih","")}</div>',
                unsafe_allow_html=True)
        with row_cols[2]:
            title_style = "text-decoration:line-through;color:#94a3b8;" if done else "color:#0f172a;"
            aciklama    = note.get("aciklama", "")
            st.markdown(
                f'<div style="font-size:13px;font-weight:700;{title_style};padding-top:6px;line-height:1.4;">'
                f'{note.get("ozet","Başlıksız")}</div>'
                + (f'<div style="font-size:11px;color:#94a3b8;margin-top:2px;">{aciklama[:80]}{"…" if len(aciklama)>80 else ""}</div>'
                   if aciklama else ""),
                unsafe_allow_html=True)
        with row_cols[3]:
            sayfa = (note.get("sayfalar") or ["—"])[0]
            pg_dot = PAGE_DOT.get(sayfa, "#bbb")
            st.markdown(
                f'<div style="font-size:11px;padding-top:10px;color:#475569;font-weight:600;">'
                f'<span style="color:{pg_dot};margin-right:4px;">●</span>{sayfa}</div>',
                unsafe_allow_html=True)
        with row_cols[4]:
            _cat_cls = CAT_CHIP.get(cat, 'chip-page')
            st.markdown(
                '<div style="padding-top:8px"><span class="chip td-pill ' + _cat_cls + '">'
                + cat + '</span></div>',
                unsafe_allow_html=True)
        with row_cols[5]:
            _dur_cls = DUR_CHIP.get(dur, 'chip-bekle')
            st.markdown(
                '<div style="padding-top:8px"><span class="chip td-pill ' + _dur_cls + '">'
                + dur + '</span></div>',
                unsafe_allow_html=True)
        with row_cols[6]:
            ks = safe_key(f"{note['id']}_tbl")
            det_key = f"det_tbl_{ks}"
            st.session_state.setdefault(det_key, False)
            lbl = "▼" if st.session_state[det_key] else "▶"
            if st.button(lbl, key=f"tbl_exp_{ks}"):
                st.session_state[det_key] = not st.session_state[det_key]
                st.rerun()

        if st.session_state.get(det_key):
            with st.container():
                render_note_card(note, context_page="tbl", row_num=i+1, total=len(filtreli))

        st.markdown("<div style='border-bottom:1px solid #f1f5f9;'></div>", unsafe_allow_html=True)


# =========================================================
# GÖRÜNÜM: KANBAN
# =========================================================

KANBAN_SUTUNLAR = ["Yeni", "İnceleniyor", "Geliştiriliyor", "Test", "Tamamlandı", "Beklemede"]

KANBAN_DUR_COLOR = {
    "Yeni":           "#22c55e",
    "İnceleniyor":    "#f59e0b",
    "Geliştiriliyor": "#3b82f6",
    "Test":           "#8b5cf6",
    "Tamamlandı":     "#64748b",
    "Beklemede":      "#94a3b8",
}


# =========================================================
# GÖRÜNÜM: REHBER
# =========================================================

import random as _random

def render_rehber(notes):
    """İlham ve rehber ana yüzeyi."""
    if not notes:
        st.markdown('<div class="empty-state">📭<br>Henüz kayıt yok.</div>', unsafe_allow_html=True)
        return

    # ── 1. Projenin durumu ─────────────────────────────────
    toplam    = len(notes)
    aktif_dur = {"Yeni", "İnceleniyor", "Geliştiriliyor", "Test"}
    aktif     = sum(1 for n in notes if n.get("durum","") in aktif_dur)
    tamam     = sum(1 for n in notes if n.get("durum","") == "Tamamlandı")
    bekle     = sum(1 for n in notes if n.get("durum","") == "Beklemede")

    st.markdown('''
    <div class="rehber-grid">
      <div class="rehber-blok full">
        <div class="rehber-blok-label">
          <div class="rehber-label-dot" style="background:#3b82f6;"></div>
          Projenin durumu
        </div>
        <div class="durum-row">
          <div class="durum-stat">
            <div class="durum-sayi">__TOPLAM__</div>
            <div class="durum-etiket">toplam kayıt</div>
          </div>
          <div class="durum-stat">
            <div class="durum-sayi s-amber">__AKTIF__</div>
            <div class="durum-etiket">aktif</div>
          </div>
          <div class="durum-stat">
            <div class="durum-sayi s-green">__TAMAM__</div>
            <div class="durum-etiket">tamamlandı</div>
          </div>
          <div class="durum-stat">
            <div class="durum-sayi s-muted">__BEKLE__</div>
            <div class="durum-etiket">beklemede</div>
          </div>
        </div>
      </div>
    </div>
    '''.replace("__TOPLAM__", str(toplam))
      .replace("__AKTIF__",  str(aktif))
      .replace("__TAMAM__",  str(tamam))
      .replace("__BEKLE__",  str(bekle)),
    unsafe_allow_html=True)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── 2. Son eklediğin + 3. Yarım kalanlar — yan yana ───
    col_son, col_yarim = st.columns(2)

    # ── Sol: Son eklediğin ─────────────────────────────────
    with col_son:
        son_3 = sorted(notes, key=lambda n: _parse_tarih(n.get("tarih","")), reverse=True)[:3]

        items_html = ""
        for note in son_3:
            cat       = note.get("kategori", "Fikir")
            sayfalar  = note.get("sayfalar", [])
            ham       = note.get("orijinal_not", note.get("ozet","")).strip()
            tarih_str = note.get("tarih","")
            cat_cls   = CAT_CHIP.get(cat, "chip-page")
            sayfa_lbl = sayfalar[0] if sayfalar else "Genel"

            # Tarihi insancıl hale getir
            try:
                dt = _parse_tarih(tarih_str)
                delta = (datetime.now() - dt).days
                if delta == 0:   gun = "Bugün"
                elif delta == 1: gun = "Dün"
                else:            gun = tarih_str
            except Exception:
                gun = tarih_str

            items_html += (
                '<div class="ham-item">' +
                '<div class="ham-meta">' +
                '<span class="ham-tarih">' + gun + '</span>' +
                '<span class="chip chip-xs ' + cat_cls + '">' + cat + '</span>' +
                '<span class="chip chip-xs chip-page">' + sayfa_lbl[:14] + '</span>' +
                '</div>' +
                '<div class="ham-text">&ldquo;' + ham[:160] + ("…" if len(ham)>160 else "") + '&rdquo;</div>' +
                '</div>'
            )

        st.markdown(
            '<div class="rehber-blok" style="height:100%;">' +
            '<div class="rehber-blok-label">' +
            '<div class="rehber-label-dot" style="background:#22c55e;"></div>' +
            'Son eklediğin</div>' +
            items_html +
            '</div>',
            unsafe_allow_html=True
        )

    # ── Sağ: Yarım kalanlar ────────────────────────────────
    with col_yarim:
        yarim_dur = {"İnceleniyor", "Geliştiriliyor", "Test"}
        yarimlar  = [n for n in notes if n.get("durum","") in yarim_dur]
        yarimlar  = sorted(yarimlar, key=lambda n: _parse_tarih(n.get("tarih","")), reverse=True)[:3]

        DUR_BAR_COLOR = {
            "Geliştiriliyor": "#3b82f6",
            "İnceleniyor":    "#f59e0b",
            "Test":           "#8b5cf6",
        }

        items_html = ""
        if not yarimlar:
            items_html = '<div style="font-size:13px;color:#94a3b8;padding:20px 0;text-align:center;">Aktif iş yok 🎉</div>'
        else:
            for note in yarimlar:
                dur      = note.get("durum","")
                cat      = note.get("kategori","Fikir")
                ozet     = note.get("ozet","Başlıksız")
                ham      = note.get("orijinal_not","").strip()
                bar_clr  = DUR_BAR_COLOR.get(dur, "#94a3b8")
                dur_cls  = DUR_CHIP.get(dur, "chip-bekle")
                cat_cls  = CAT_CHIP.get(cat, "chip-page")

                items_html += (
                    '<div class="yarim-item">' +
                    '<div class="yarim-bar" style="background:' + bar_clr + ';"></div>' +
                    '<div style="flex:1;">' +
                    '<div class="yarim-ozet">' + ozet + '</div>' +
                    '<div style="display:flex;gap:4px;margin:3px 0;">' +
                    '<span class="chip chip-xs ' + dur_cls + '">' + dur + '</span>' +
                    '<span class="chip chip-xs ' + cat_cls + '">' + cat + '</span>' +
                    '</div>' +
                    '<div class="yarim-ham">&ldquo;' + ham[:120] + ("…" if len(ham)>120 else "") + '&rdquo;</div>' +
                    '</div></div>'
                )

        st.markdown(
            '<div class="rehber-blok" style="height:100%;">' +
            '<div class="rehber-blok-label">' +
            '<div class="rehber-label-dot" style="background:#f59e0b;"></div>' +
            'Yarım kalanlar</div>' +
            items_html +
            '</div>',
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── 4. Bunu unuttun mu? ────────────────────────────────
    bugun = datetime.now()
    unututlanlar = [
        n for n in notes
        if n.get("durum","") == "Yeni"
        and (bugun - _parse_tarih(n.get("tarih",""))).days >= 14
    ]

    # Seed: gün bazlı — aynı gün aynı kayıt, her gün değişir
    if unututlanlar:
        gun_seed = bugun.year * 10000 + bugun.month * 100 + bugun.day
        _random.seed(gun_seed)
        secilen = _random.choice(unututlanlar)
        _random.seed()  # reset

        delta_gun  = (bugun - _parse_tarih(secilen.get("tarih",""))).days
        ham_text   = secilen.get("orijinal_not", secilen.get("ozet","")).strip()
        cat        = secilen.get("kategori","Fikir")
        sayfalar   = secilen.get("sayfalar",[])
        cat_cls    = CAT_CHIP.get(cat,"chip-page")
        sayfa_lbl  = sayfalar[0] if sayfalar else "Genel"
        dur_cls    = DUR_CHIP.get(secilen.get("durum","Yeni"),"chip-yeni")

        st.markdown(
            '<div class="rehber-blok unutulan-blok">' +
            '<div class="rehber-blok-label">' +
            '<div class="rehber-label-dot" style="background:#8b5cf6;"></div>' +
            'Bunu unuttun mu?' +
            '<span class="unutulan-yas">' + str(delta_gun) + ' gün önce eklendi</span>' +
            '</div>' +
            '<div class="unutulan-text">&ldquo;' + ham_text[:280] + ("…" if len(ham_text)>280 else "") + '&rdquo;</div>' +
            '<div style="display:flex;gap:5px;align-items:center;">' +
            '<span class="chip chip-xs ' + cat_cls + '">' + cat + '</span>' +
            '<span class="chip chip-xs chip-page">' + sayfa_lbl + '</span>' +
            '<span class="chip chip-xs ' + dur_cls + '">' + secilen.get("durum","Yeni") + '</span>' +
            '</div>' +
            '</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="rehber-blok unutulan-blok">' +
            '<div class="rehber-blok-label">' +
            '<div class="rehber-label-dot" style="background:#8b5cf6;"></div>' +
            'Bunu unuttun mu?</div>' +
            '<div style="font-size:13px;color:#94a3b8;padding:8px 0;">Tüm yeni kayıtlar taze — bekleyen eski öneri yok.</div>' +
            '</div>',
            unsafe_allow_html=True
        )



def render_kanban(notes, kat_filtre=None):
    """Durum bazlı Kanban görünümü."""
    filtreli = [n for n in notes if not kat_filtre or n.get("kategori") == kat_filtre]
    if not filtreli:
        st.markdown('<div class="empty-state">📭<br>Kayıt yok.</div>', unsafe_allow_html=True)
        return

    cols = st.columns(len(KANBAN_SUTUNLAR))
    for col_el, dur in zip(cols, KANBAN_SUTUNLAR):
        dur_notes = [n for n in filtreli if n.get("durum") == dur]
        hdr_color = KANBAN_DUR_COLOR.get(dur, "#888")

        with col_el:
            st.markdown(
                f'<div style="font-size:10px;font-weight:800;text-transform:uppercase;'
                f'letter-spacing:.1em;color:{hdr_color};border-bottom:2px solid {hdr_color};'
                f'padding-bottom:6px;margin-bottom:10px;display:flex;'
                f'align-items:center;justify-content:space-between;">'
                f'{dur} <span style="background:#e8eef7;color:#64748b;border-radius:999px;'
                f'padding:1px 8px;font-size:10px;">{len(dur_notes)}</span></div>',
                unsafe_allow_html=True,
            )

            for note in dur_notes:
                cat      = note.get("kategori", "Fikir")
                oncelik  = note.get("oncelik", "Orta")
                sayfalar = note.get("sayfalar", [])
                dot_clr  = CAT_DOT.get(cat, "#888")
                onc_cls_map = {"Kritik":"chip-kritik","Yüksek":"chip-yuksek","Orta":"chip-orta","Düşük":"chip-dusuk"}
                cat_cls_map = {"UX":"cat-ux","Teknik":"cat-teknik","Operasyon":"cat-operasyon","Fikir":"cat-fikir"}

                ks = safe_key(f"{note['id']}_kb")
                det_key = f"det_kb_{ks}"
                st.session_state.setdefault(det_key, False)

                _kcat_cls = cat_cls_map.get(cat, "")
                _konc_cls = onc_cls_map.get(oncelik, "chip-orta")
                _kcat_chip = CAT_CHIP.get(cat, "chip-page")
                _sayfa_html = "".join(
                    '<span class="kanban-chip chip-page">' + p[:8] + '</span>'
                    for p in sayfalar[:1]
                )
                _khtml = (
                    '<div class="kanban-card ' + _kcat_cls + '">'
                    '<div class="kanban-card-title">' + note.get("ozet","Başlıksız") + '</div>'
                    '<div class="kanban-card-meta">'
                    '<span class="kanban-chip ' + _konc_cls + '">' + oncelik[:3] + '</span>'
                    '<span class="kanban-chip ' + _kcat_chip + '">' + cat + '</span>'
                    + _sayfa_html
                    + '<span style="font-size:9px;color:#cbd5e1;padding-top:1px;">' + note.get("tarih","") + '</span>'
                    '</div></div>'
                )
                st.markdown(_khtml, unsafe_allow_html=True)
                if st.button("▶ Detay", key=f"kb_det_{ks}", use_container_width=True):
                    st.session_state[det_key] = not st.session_state[det_key]
                    st.rerun()

                if st.session_state[det_key]:
                    render_note_card(note, context_page="kb", row_num=1, total=1)


# =========================================================
# ANA FONKSİYON
# =========================================================

def main():
    init_state()
    notes = st.session_state["ph_notes"]
    render_navbar(
        user_role=st.session_state.get("user_role", "danisan"),
        user_name=st.session_state.get("user_name", ""),
        user_initials=st.session_state.get("user_initials", ""),
    )
    render_sidebar(notes)

    # CSS enjeksiyonu
    st.markdown(VIEW_MODE_CSS, unsafe_allow_html=True)

    # ── Başlık satırı ──────────────────────────────────────
    col_h, col_sb = st.columns([7, 2])
    with col_h:
        sb_ok   = sb_connected()
        sb_icon = "🟢" if sb_ok else "🔴"
        st.markdown(
            f'<div class="hero-title">Proje Hafızası '
            f'<span style="font-size:13px;vertical-align:middle;">{sb_icon}</span></div>',
            unsafe_allow_html=True,
        )
    with col_sb:
        st.markdown("<div style='padding-top:8px'>", unsafe_allow_html=True)
        render_export_panel(notes)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Yeni öneri ─────────────────────────────────────────
    render_add_panel()

    # ── Arama ──────────────────────────────────────────────
    ara = st.session_state.get("ph_ara", "").lower().strip()

    if not notes:
        st.markdown('<div class="empty-state">📭<br>Henüz kayıt yok.</div>', unsafe_allow_html=True)
        return

    # Arama modunda görünüm seçici kapalı — düz liste
    if ara:
        filtreli = [n for n in notes if ara in n.get("ozet","").lower()
                    or ara in n.get("oneri","").lower()
                    or ara in n.get("orijinal_not","").lower()]
        st.markdown(
            f'<div style="font-size:12px;color:#aaa;margin-bottom:10px;">{len(filtreli)} sonuç</div>',
            unsafe_allow_html=True,
        )
        for i, note in enumerate(filtreli, 1):
            render_note_card(note, context_page="ara", row_num=i, total=len(filtreli))
        return

    # ── Görünüm modu seçici ────────────────────────────────
    st.session_state.setdefault("ph_view_mode", "rehber")
    st.session_state.setdefault("ph_tbl_sort", ("tarih", False))

    VIEW_MODES = [
        ("rehber",   "🧭 Rehber"),
        ("timeline", "⏱ Zaman Akışı"),
        ("tablo",    "☰ Tablo"),
        ("kanban",   "▦ Kanban"),
        ("sayfa",    "⊞ Sayfa Bazlı"),
    ]

    vm_cols = st.columns([1, 1, 1, 1, 1, 3])
    for col_el, (mode_id, mode_label) in zip(vm_cols, VIEW_MODES):
        with col_el:
            is_active = st.session_state["ph_view_mode"] == mode_id
            btn_type  = "primary" if is_active else "secondary"
            if st.button(mode_label, key=f"vm_{mode_id}", type=btn_type, use_container_width=True):
                st.session_state["ph_view_mode"] = mode_id
                st.rerun()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Sidebar kategori/sayfa filtresi ────────────────────
    mode, mode_val = st.session_state.get("ph_view", ("tumu", None))
    kat_filtre = mode_val if mode == "kat" else None

    if kat_filtre:
        st.markdown(
            "<div style='font-size:11px;font-weight:700;color:#3b82f6;"
            "letter-spacing:0.08em;text-transform:uppercase;margin-bottom:8px;'>"
            "● " + kat_filtre + " kategorisi</div>",
            unsafe_allow_html=True,
        )

    current_vm = st.session_state["ph_view_mode"]

    # ── Sayfa bazlı (eski davranış) ────────────────────────
    if current_vm == "sayfa":
        # Sidebar'dan belirli sayfa seçilmişse
        if mode == "sayfa" and mode_val:
            page_notes = [n for n in notes if mode_val in n.get("sayfalar", [])]
            if kat_filtre:
                page_notes = [n for n in page_notes if n.get("kategori") == kat_filtre]
            st.markdown(
                f'<div class="section-divider">{mode_val}'
                f'<span class="section-count">{len(page_notes)} öğe</span></div>',
                unsafe_allow_html=True,
            )
            render_page_block(page_notes, mode_val)
        else:
            aktif_sayfalar = [p for p in SAYFALAR
                              if any(p in n.get("sayfalar", []) for n in notes)]
            if not aktif_sayfalar:
                st.markdown('<div class="empty-state">📭<br>Henüz kayıt yok.</div>', unsafe_allow_html=True)
                return
            tabs = st.tabs(aktif_sayfalar)
            for tab, page_name in zip(tabs, aktif_sayfalar):
                with tab:
                    page_notes = [n for n in notes if page_name in n.get("sayfalar", [])]
                    if kat_filtre:
                        page_notes = [n for n in page_notes if n.get("kategori") == kat_filtre]
                    render_page_block(page_notes, page_name)

    elif current_vm == "rehber":
        render_rehber(notes)

    elif current_vm == "timeline":
        render_timeline(notes, kat_filtre=kat_filtre)

    elif current_vm == "tablo":
        render_table(notes, kat_filtre=kat_filtre)

    elif current_vm == "kanban":
        render_kanban(notes, kat_filtre=kat_filtre)


if __name__ == "__main__":
    main()
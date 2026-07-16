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
from core.auth import oturum_kontrol

if not oturum_kontrol():
    st.switch_page("pages/giris.py")

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
    """ISO 8601 (mikrosaniye/timezone/Z dahil) ve RFC2822 (mail) formatlarını destekler.
    DÜZELTME: Eski strptime[:len(fmt)] deseni format string'inin karakter sayısını
    tarih uzunluğu sanıyordu, bu yüzden gerçek ISO tarihleri ayrıştırılamıyordu."""
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


def en_iyi_tarih(v):
    """DÜZELTME: Eskiden yalnızca mail_tarihi/kayit_tarihi/olusturma_tarihi'ya
    bakıyordu — bu, 3_Portfoy_Tablosu.py'deki aynı fonksiyondan farklıydı ve
    ilan_tarihi/paylasim_tarihi/gonderim_tarihi/tarih alanlarını hiç kontrol
    etmiyordu. Artık Portföy Tablosu ile birebir aynı öncelik sırasını
    kullanıyor. Talep kayıtlarında bu ek alanlar zaten boş olduğu için
    (tablo şemasında yok) davranış talep tarafında değişmez, sadece
    portföy tarafında doğru tarihi bulabiliyor."""
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
    if not d:
        return 9999
    _d = d.date() if hasattr(d, 'date') and callable(d.date) else d
    return (date.today() - _d).days


def _kayit_arsive_uygun_mu(v, esik):
    """Bir kaydın arşive taşınmaya uygun olup olmadığını belirler.

    DÜZELTME (kritik bug): Eskiden `tarih_gun_farki(en_iyi_tarih(v)) > ESIK`
    doğrudan kullanılıyordu. tarih_gun_farki(), tarih hiç parse edilemediğinde
    9999 döndürüyor — bu, "9999 gün önce" değil "yaşını bilmiyoruz" demek.
    Ama 9999 > 60 hep True olduğu için, tarih alanlarının HİÇBİRİ dolu
    olmayan kayıtlar (ör. ilan_tarihi'i olmayan Zeta kaynaklı portföyler)
    otomatik olarak "kesin eski" sayılıp yanlışlıkla arşive düşüyordu.
    Artık tarihi belirlenemeyen kayıtlar arşive UYGUN SAYILMIYOR — yaşı
    bilinmeyen bir kaydı arşive atmaktansa aktif havuzda bırakmak daha
    güvenli, çünkü Zeta gibi kaynaklarda "yayından kalkma" kavramı zaten yok."""
    ham_tarih = en_iyi_tarih(v)
    if not ham_tarih:
        return False
    if tarih_parse(ham_tarih) is None:
        return False
    return tarih_gun_farki(ham_tarih) > esik


def _arsiv_sayfali_cek(builder_fn):
    """DÜZELTME: Eskiden `.limit(2000)` vardı — tablo 2000 satırı geçince
    en yeni 2000 kayıt çekilip ONDAN SONRA 60 gün filtresi uygulanıyordu.
    Bu, gerçekten 60 günden eski ama en-yeni-2000'e girmeyen kayıtların
    (yani tam arşivin konusu olan kayıtların) sorgudan hiç dönmemesine yol
    açabiliyordu. Artık 2_Talep_Tablosu.py / 3_Portfoy_Tablosu.py'deki
    `verileri_yukle()` ile aynı desen: `.range()` ile tüm kayıtlar sayfa
    sayfa çekiliyor, tavan yok."""
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

# ════════════════════════════════════════════════════════════════════════════
# MAİL İÇERİĞİ POPUP — hem Talep hem Portföy sekmesi tarafından kullanılır
# ════════════════════════════════════════════════════════════════════════════

@st.dialog("Mail İçeriği")
def _mail_icerik_popup(kayit):
    _konu = kayit.get("mail_konusu") or "(konu yok)"
    _danisman = isim_ayikla(kayit.get("talep_eden_danisan", "")) or "-"
    _tarih = (en_iyi_tarih(kayit) or "-")[:10]
    st.markdown(f"**Konu:** {_konu}")
    st.caption(f"{_danisman} · {_tarih}")
    st.divider()
    _icerik = html_temizle(kayit.get("mail_icerigi") or "")
    if _icerik:
        st.text_area("İçerik", _icerik, height=400, disabled=True, label_visibility="collapsed")
    else:
        st.info("Bu kayıt için mail içeriği bulunamadı.")


tab_talep, tab_portfoy = st.tabs(["📋 Talep Arşivi", "🏠 Portföy Arşivi"])


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  TALEP ARŞİVİ                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

with tab_talep:

    # ── Veri çekme (P0-3 düzeltmesiyle: .range() sayfalama + güvenli arşiv filtresi) ──
    @st.cache_data(ttl=30)
    def talep_verileri_yukle(kaynak_filtre=None):
        """ARŞİV MODU: 60 günden eski talep kayıtları."""
        ESIK = 60
        try:
            if kaynak_filtre == "startkey_mail":
                def _q1():
                    return (
                        get_client().table("alici_talepleri")
                        .select("*").eq("kategori", "alici_talebi")
                        .eq("kaynak", "startkey_mail")
                        .order("olusturma_tarihi", desc=True)
                    )
                def _q2():
                    return (
                        get_client().table("alici_talepleri")
                        .select("*").eq("kategori", "alici_talebi")
                        .is_("kaynak", "null")
                        .order("olusturma_tarihi", desc=True)
                    )
                tum = _arsiv_sayfali_cek(_q1) + _arsiv_sayfali_cek(_q2)
            elif isinstance(kaynak_filtre, list):
                def _q():
                    return (
                        get_client().table("alici_talepleri")
                        .select("*").eq("kategori", "alici_talebi")
                        .in_("kaynak", kaynak_filtre)
                        .order("olusturma_tarihi", desc=True)
                    )
                tum = _arsiv_sayfali_cek(_q)
            elif kaynak_filtre:
                def _q():
                    return (
                        get_client().table("alici_talepleri")
                        .select("*").eq("kategori", "alici_talebi")
                        .eq("kaynak", kaynak_filtre)
                        .order("olusturma_tarihi", desc=True)
                    )
                tum = _arsiv_sayfali_cek(_q)
            else:
                def _q():
                    return (
                        get_client().table("alici_talepleri")
                        .select("*").eq("kategori", "alici_talebi")
                        .order("olusturma_tarihi", desc=True)
                    )
                tum = _arsiv_sayfali_cek(_q)
            return [v for v in tum if _kayit_arsive_uygun_mu(v, ESIK)]
        except Exception as e:
            st.error(f"Talep verisi yüklenemedi: {e}")
            return []

    with st.spinner("Talep arşivi yükleniyor..."):
        ta_veriler = talep_verileri_yukle(None)

    if not ta_veriler:
        st.info("60 günden eski talep kaydı bulunamadı.")
    else:
        # ── Filtreler ─────────────────────────────────────────────────────
        tc1, tc2, tc3, tc4 = st.columns([1.2, 1.4, 1.3, 2.3])
        with tc1:
            _ta_iller = ["Tümü"] + sorted(set(il_grubu(v) for v in ta_veriler if il_grubu(v)))
            ta_il_secim = st.selectbox("İl", _ta_iller, key="ta_arsiv_il")
        with tc2:
            _ta_ilceler = ["Tümü"] + sorted(set(i for v in ta_veriler for i in kayit_ilce_listesi(v)))
            ta_ilce_secim = st.selectbox("İlçe", _ta_ilceler, key="ta_arsiv_ilce")
        with tc3:
            ta_islem_secim = st.selectbox(
                "İşlem Tipi", ["Tümü", "Satılık", "Kiralık", "Belirsiz", "Belirtilmemiş"],
                key="ta_arsiv_islem"
            )
        with tc4:
            ta_arama = st.text_input(
                "Ara", placeholder="Danışman, ilçe, özet...", key="ta_arsiv_arama"
            )

        ta_f = ta_veriler
        if ta_il_secim != "Tümü":
            ta_f = [v for v in ta_f if il_grubu(v) == ta_il_secim]
        if ta_ilce_secim != "Tümü":
            ta_f = [v for v in ta_f if ta_ilce_secim in kayit_ilce_listesi(v)]
        if ta_islem_secim != "Tümü":
            if ta_islem_secim in ("Belirsiz", "Belirtilmemiş"):
                ta_f = [v for v in ta_f if (v.get("islem_tipi") or "") in ("", "Belirsiz", "Belirtilmemiş", None)]
            else:
                ta_f = [v for v in ta_f if (v.get("islem_tipi") or "") == ta_islem_secim]
        if ta_arama:
            _q = ta_arama.strip().lower()
            ta_f = [
                v for v in ta_f
                if _q in str(v.get("talep_eden_danisan", "")).lower()
                or _q in str(v.get("ozet", "")).lower()
                or _q in str(v.get("ozel_kriterler", "")).lower()
                or _q in " ".join(v.get("ilceler") or []).lower()
            ]

        st.caption(f"**{len(ta_f)}** / {len(ta_veriler)} arşivlenmiş talep")

        # ── Satılık / Kiralık dağılımı ────────────────────────────────────
        _ta_satilik = sum(1 for v in ta_f if (v.get("islem_tipi") or "") == "Satılık")
        _ta_kiralik = sum(1 for v in ta_f if (v.get("islem_tipi") or "") == "Kiralık")
        _ta_belirsiz = len(ta_f) - _ta_satilik - _ta_kiralik
        tm1, tm2, tm3 = st.columns(3)
        tm1.metric("Satılık", _ta_satilik)
        tm2.metric("Kiralık", _ta_kiralik)
        tm3.metric("Belirsiz", _ta_belirsiz)

        # ── Düz tablo (Excel benzeri, salt görüntüleme) ──────────────────
        _ta_sirali = sorted(ta_f, key=lambda x: tarih_gun_farki(en_iyi_tarih(x)))
        _ta_satirlar = []
        for v in _ta_sirali:
            _ta_satirlar.append({
                "İlçe": ", ".join(kayit_ilce_listesi(v)) or "-",
                "İşlem Tipi": v.get("islem_tipi") or "Belirsiz",
                "Danışman": isim_ayikla(v.get("talep_eden_danisan", "")) or "-",
                "Bütçe": v.get("max_butce") or "-",
                "Özet": (v.get("ozet") or v.get("ozel_kriterler") or "")[:150],
                "Gün": tarih_gun_farki(en_iyi_tarih(v)),
                "Tarih": (en_iyi_tarih(v) or "-")[:10],
                "Kaynak": v.get("kaynak") or "-",
            })

        st.caption("💡 Mail içeriğini görmek için bir satıra tıklayın.")
        try:
            _ta_secim = st.dataframe(
                pd.DataFrame(_ta_satirlar),
                use_container_width=True,
                hide_index=True,
                height=620,
                column_config={
                    "Gün": st.column_config.NumberColumn("Gün", help="Kaydın üzerinden geçen gün sayısı"),
                },
                on_select="rerun",
                selection_mode="single-row",
                key="ta_arsiv_dataframe",
            )
            _ta_secili_satirlar = []
            if hasattr(_ta_secim, "selection"):
                try:
                    _ta_secili_satirlar = _ta_secim.selection["rows"]
                except (TypeError, KeyError):
                    _ta_secili_satirlar = getattr(_ta_secim.selection, "rows", [])
            if _ta_secili_satirlar:
                _ta_secili_idx = _ta_secili_satirlar[0]
                # DÜZELTME: Seçim, kullanıcı başka bir satır seçene kadar
                # session'da kalıcı kalıyor. Bunu kontrol etmeden popup'ı her
                # rerun'da yeniden açmak, kullanıcıyı modal'ın arkasında
                # kilitliyordu (tıklamalar hedefe ulaşamayıp "yasak işareti"
                # gösteriyordu). Artık yalnızca YENİ bir satır seçildiğinde açılır.
                if st.session_state.get("_ta_son_gosterilen_satir") != _ta_secili_idx:
                    st.session_state["_ta_son_gosterilen_satir"] = _ta_secili_idx
                    _mail_icerik_popup(_ta_sirali[_ta_secili_idx])
            else:
                st.session_state["_ta_son_gosterilen_satir"] = None
        except TypeError:
            # Streamlit sürümü satır seçimini (on_select) desteklemiyor —
            # sürüm yükseltilene kadar salt görüntüleme tabloya düş.
            st.dataframe(
                pd.DataFrame(_ta_satirlar),
                use_container_width=True,
                hide_index=True,
                height=620,
                column_config={
                    "Gün": st.column_config.NumberColumn("Gün", help="Kaydın üzerinden geçen gün sayısı"),
                },
            )
            st.caption("⚠ Mail popup için Streamlit sürümünüzün güncellenmesi gerekiyor.")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  PORTFÖY ARŞİVİ                                                         ║
# ╚══════════════════════════════════════════════════════════════════════════╝

with tab_portfoy:

    @st.cache_data(ttl=30)
    def portfoy_verileri_yukle(kaynak_filtre=None):
        """ARŞİV MODU: 60 günden eski portföy kayıtları."""
        ESIK = 60
        try:
            if kaynak_filtre == "startkey_mail":
                def _q1():
                    return (
                        get_client().table("portfoyler")
                        .select("*").eq("kaynak", "startkey_mail")
                        .order("olusturma_tarihi", desc=True)
                    )
                def _q2():
                    return (
                        get_client().table("portfoyler")
                        .select("*").is_("kaynak", "null")
                        .order("olusturma_tarihi", desc=True)
                    )
                tum = _arsiv_sayfali_cek(_q1) + _arsiv_sayfali_cek(_q2)
            elif isinstance(kaynak_filtre, list):
                def _q():
                    return (
                        get_client().table("portfoyler")
                        .select("*").in_("kaynak", kaynak_filtre)
                        .order("olusturma_tarihi", desc=True)
                    )
                tum = _arsiv_sayfali_cek(_q)
            elif kaynak_filtre:
                def _q():
                    return (
                        get_client().table("portfoyler")
                        .select("*").eq("kaynak", kaynak_filtre)
                        .order("olusturma_tarihi", desc=True)
                    )
                tum = _arsiv_sayfali_cek(_q)
            else:
                def _q():
                    return (
                        get_client().table("portfoyler")
                        .select("*")
                        .order("olusturma_tarihi", desc=True)
                    )
                tum = _arsiv_sayfali_cek(_q)
            return [v for v in tum if _kayit_arsive_uygun_mu(v, ESIK)]
        except Exception as e:
            st.error(f"Portföy verisi yüklenemedi: {e}")
            return []

    with st.spinner("Portföy arşivi yükleniyor..."):
        pf_veriler = portfoy_verileri_yukle(None)

    if not pf_veriler:
        st.info("60 günden eski portföy kaydı bulunamadı.")
    else:
        # ── Filtreler ─────────────────────────────────────────────────────
        pc1, pc2, pc3, pc4 = st.columns([1.2, 1.4, 1.3, 2.3])
        with pc1:
            _pf_iller = ["Tümü"] + sorted(set(il_grubu(v) for v in pf_veriler if il_grubu(v)))
            pf_il_secim = st.selectbox("İl", _pf_iller, key="pf_arsiv_il")
        with pc2:
            _pf_ilceler = ["Tümü"] + sorted(set(i for v in pf_veriler for i in kayit_ilce_listesi(v)))
            pf_ilce_secim = st.selectbox("İlçe", _pf_ilceler, key="pf_arsiv_ilce")
        with pc3:
            pf_islem_secim = st.selectbox(
                "İşlem Tipi", ["Tümü", "Satılık", "Kiralık", "Belirsiz", "Belirtilmemiş"],
                key="pf_arsiv_islem"
            )
        with pc4:
            pf_arama = st.text_input(
                "Ara", placeholder="Danışman, ilçe, özet...", key="pf_arsiv_arama"
            )

        pf_f = pf_veriler
        if pf_il_secim != "Tümü":
            pf_f = [v for v in pf_f if il_grubu(v) == pf_il_secim]
        if pf_ilce_secim != "Tümü":
            pf_f = [v for v in pf_f if pf_ilce_secim in kayit_ilce_listesi(v)]
        if pf_islem_secim != "Tümü":
            if pf_islem_secim in ("Belirsiz", "Belirtilmemiş"):
                pf_f = [v for v in pf_f if (v.get("islem_tipi") or "") in ("", "Belirsiz", "Belirtilmemiş", None)]
            else:
                pf_f = [v for v in pf_f if (v.get("islem_tipi") or "") == pf_islem_secim]
        if pf_arama:
            _q = pf_arama.strip().lower()
            pf_f = [
                v for v in pf_f
                if _q in str(v.get("talep_eden_danisan", "")).lower()
                or _q in str(v.get("ozet", "")).lower()
                or _q in str(v.get("baslik", "")).lower()
                or _q in " ".join(v.get("ilceler") or []).lower()
            ]

        st.caption(f"**{len(pf_f)}** / {len(pf_veriler)} arşivlenmiş portföy")

        # ── Satılık / Kiralık dağılımı ────────────────────────────────────
        _pf_satilik = sum(1 for v in pf_f if (v.get("islem_tipi") or "") == "Satılık")
        _pf_kiralik = sum(1 for v in pf_f if (v.get("islem_tipi") or "") == "Kiralık")
        _pf_belirsiz = len(pf_f) - _pf_satilik - _pf_kiralik
        pm1, pm2, pm3 = st.columns(3)
        pm1.metric("Satılık", _pf_satilik)
        pm2.metric("Kiralık", _pf_kiralik)
        pm3.metric("Belirsiz", _pf_belirsiz)

        # ── Düz tablo (Excel benzeri, salt görüntüleme) ──────────────────
        _pf_sirali = sorted(pf_f, key=lambda x: tarih_gun_farki(en_iyi_tarih(x)))
        _pf_satirlar = []
        for v in _pf_sirali:
            _pf_satirlar.append({
                "İlçe": ", ".join(kayit_ilce_listesi(v)) or "-",
                "İşlem Tipi": v.get("islem_tipi") or "Belirsiz",
                "Mülk Tipi": v.get("mulk_tipi") or "-",
                "Danışman": isim_ayikla(v.get("talep_eden_danisan", "")) or "-",
                "Fiyat": v.get("fiyat") or "-",
                "Oda/M²": v.get("oda_sayisi_m2") or "-",
                "Özet": (v.get("ozet") or v.get("baslik") or "")[:150],
                "Gün": tarih_gun_farki(en_iyi_tarih(v)),
                "Tarih": (en_iyi_tarih(v) or "-")[:10],
                "Kaynak": v.get("kaynak") or "-",
            })

        st.caption("💡 Mail içeriğini görmek için bir satıra tıklayın.")
        try:
            _pf_secim = st.dataframe(
                pd.DataFrame(_pf_satirlar),
                use_container_width=True,
                hide_index=True,
                height=620,
                column_config={
                    "Gün": st.column_config.NumberColumn("Gün", help="Kaydın üzerinden geçen gün sayısı"),
                },
                on_select="rerun",
                selection_mode="single-row",
                key="pf_arsiv_dataframe",
            )
            _pf_secili_satirlar = []
            if hasattr(_pf_secim, "selection"):
                try:
                    _pf_secili_satirlar = _pf_secim.selection["rows"]
                except (TypeError, KeyError):
                    _pf_secili_satirlar = getattr(_pf_secim.selection, "rows", [])
            if _pf_secili_satirlar:
                _pf_secili_idx = _pf_secili_satirlar[0]
                if st.session_state.get("_pf_son_gosterilen_satir") != _pf_secili_idx:
                    st.session_state["_pf_son_gosterilen_satir"] = _pf_secili_idx
                    _mail_icerik_popup(_pf_sirali[_pf_secili_idx])
            else:
                st.session_state["_pf_son_gosterilen_satir"] = None
        except TypeError:
            st.dataframe(
                pd.DataFrame(_pf_satirlar),
                use_container_width=True,
                hide_index=True,
                height=620,
                column_config={
                    "Gün": st.column_config.NumberColumn("Gün", help="Kaydın üzerinden geçen gün sayısı"),
                },
            )
            st.caption("⚠ Mail popup için Streamlit sürümünüzün güncellenmesi gerekiyor.")

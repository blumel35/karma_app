# pages/gd_calisma_alani.py
# GD Çalışma Alanı — Alıcılarım / Satıcılarım / FSBO / Müşteri Rehberi kokpiti
#
# YOL A (hafif başlatıcı): Bu sayfa taleplerim.py / portfoylerím.py'nin içeriğini
# GÖMMÜYOR — sadece canlı sayıları ve Takip Listem'i gösterip, karta tıklanınca
# ilgili sayfaya yönlendiriyor (ana_sayfa.py'deki "Çalışma Kokpiti" ile aynı
# ?nav= deseni). Eşleştirme motoru netleşince, panel bazında (tüm sayfayı
# yeniden yazmadan) gerçek gömme değerlendirilecek.

import streamlit as st
import sys, os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.ui_helpers import render_navbar, render_page_header
from core.supabase_client import get_client

# ── Session sync ──────────────────────────────────────────────────────────
_k = st.session_state.get("kullanici", {})
if _k:
    _ad = _k.get("ad_soyad") or _k.get("ad", "")
    st.session_state["user_role"] = _k.get("rol", "danisan")
    st.session_state["user_name"] = _ad
    st.session_state["user_initials"] = "".join(w[0].upper() for w in _ad.split()[:2] if w)

if not st.session_state.get("kullanici"):
    st.switch_page("pages/giris.py")

render_navbar(
    user_role=st.session_state.get("user_role", "danisan"),
    user_name=st.session_state.get("user_name", ""),
    user_initials=st.session_state.get("user_initials", ""),
)

ROOT_DIR = Path(__file__).resolve().parent.parent
ROUTES = {
    "taleplerim": "pages/taleplerim.py",
    "portfoylerim": "pages/portfoylerím.py",
}

# ── ?nav= yönlendirme (ana_sayfa.py ile aynı desen) ───────────────────────
# Takip Listem'den bir kayda tıklanınca ?sel= ve ?tur= ile birlikte geliyor —
# hedef sayfaya geçmeden önce o kaydı SEÇİLİ hale getiriyoruz (deep-link).
nav_target = st.query_params.get("nav")
sel_target = st.query_params.get("sel")
sel_tur = st.query_params.get("tur")

if nav_target and nav_target in ROUTES:
    st.query_params.clear()
    if sel_target:
        if sel_tur == "talep":
            st.session_state["tm_selected_id"] = sel_target
            st.session_state["tm_aktif_sekme"] = "detay"
        elif sel_tur == "portfoy":
            st.session_state["pm_selected_id"] = sel_target
            st.session_state["pm_aktif_sekme"] = "detay"
    page_path = ROUTES[nav_target]
    if (ROOT_DIR / page_path).exists():
        st.switch_page(page_path)
    else:
        st.toast("Bu modül henüz aktif değil.", icon="ℹ️")

_k = st.session_state.get("kullanici", {})
user_id = _k.get("id", "")
user_name = _k.get("ad_soyad") or _k.get("ad", "")


# ── Hafif sayım sorguları (taleplerim.py/portfoylerím.py'yi İMPORT ETMİYOR —
#    onları import etmek tüm sayfa içeriğini yan etki olarak çalıştırırdı) ──
def _isim_esles(a, b):
    a = (a or "").strip().lower()
    b = (b or "").strip().lower()
    return bool(a) and bool(b) and (a in b or b in a)


@st.cache_data(ttl=60)
def _alicilarim_sayisi(user_id, user_name):
    try:
        rows = (
            get_client().table("alici_talepleri").select("*")
            .eq("kategori", "alici_talebi").limit(1000).execute().data or []
        )
        say = 0
        for v in rows:
            if user_id and v.get("user_id") == user_id:
                say += 1
                continue
            if _isim_esles(user_name, v.get("giren_gd", "")) or _isim_esles(user_name, v.get("talep_eden_danisan", "")):
                say += 1
        return say
    except Exception:
        return 0


@st.cache_data(ttl=60)
def _saticilarim_sayisi(user_id, user_name):
    try:
        rows = get_client().table("portfoyler").select("*").limit(1500).execute().data or []
        say = 0
        for v in rows:
            # portfoyler tablosunda user_id sütunu YOK — sadece isim eşleşmesi
            if _isim_esles(user_name, v.get("giren_gd", "")) or _isim_esles(user_name, v.get("talep_eden_danisan", "")):
                say += 1
        return say
    except Exception:
        return 0


alici_sayi = _alicilarim_sayisi(user_id, user_name)
satici_sayi = _saticilarim_sayisi(user_id, user_name)

# ── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.gd-takip-strip{
    display:flex; gap:10px; overflow-x:auto; padding:12px 16px;
    background:#fff; border-radius:14px; box-shadow:0 1px 6px rgba(30,58,95,0.08);
    margin-bottom:20px; align-items:center; border:1px solid #E8EAED;
}
.gd-takip-strip.empty{
    color:#9CA3AF; font-size:13px; justify-content:center; padding:16px;
}
.gd-takip-lbl{
    font-size:11px;font-weight:700;color:#5b7a99;text-transform:uppercase;
    letter-spacing:.08em;white-space:nowrap;padding-right:10px;
    border-right:1px solid #E8EAED; flex-shrink:0;
}
.gd-takip-pill{
    display:flex;align-items:center;gap:6px;background:#EEF3F9;
    border-radius:999px;padding:6px 12px;font-size:12.5px;white-space:nowrap;
    flex-shrink:0; text-decoration:none !important; color:#1E3A5F !important;
    transition:transform .12s ease;
}
.gd-takip-pill:hover{transform:translateY(-1px);}
.gd-takip-pill .dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;display:inline-block;}

.gd-tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px;}
.gd-tile{
    background:#fff; border-radius:16px; padding:20px 18px;
    box-shadow:0 1px 3px rgba(0,0,0,.04); border:1px solid #E8EAED;
    text-decoration:none !important; display:block; position:relative;
    transition:all .15s ease;
}
.gd-tile:hover{box-shadow:0 6px 16px rgba(30,58,95,0.12); transform:translateY(-2px);}
.gd-tile.soon{cursor:default; opacity:0.72;}
.gd-tile.soon:hover{transform:none; box-shadow:0 1px 3px rgba(0,0,0,.04);}
.gd-tile-icon{font-size:22px;margin-bottom:10px;}
.gd-tile-num{font-size:26px;font-weight:800;color:#1E3A5F;line-height:1;}
.gd-tile-lbl{font-size:12.5px;color:#7B8794;margin-top:4px;}
.gd-tile-soon-badge{
    position:absolute; top:14px; right:14px; background:#FFF4E5; color:#D97706;
    font-size:10px; font-weight:700; padding:3px 8px; border-radius:999px;
}
@media(max-width:900px){ .gd-tiles{grid-template-columns:repeat(2,1fr);} }
</style>
""", unsafe_allow_html=True)

render_page_header("🧭 GD Çalışma Alanı", f"Alıcılarım · Satıcılarım · FSBO · Müşteri Rehberi · {user_name}")

# ── TAKİP LİSTEM ŞERİDİ ────────────────────────────────────────────────────
_TUR_IKON = {"talep": "👤", "portfoy": "🏠", "fsbo": "🔑"}
_TUR_RENK = {"talep": "#2563EB", "portfoy": "#16A34A", "fsbo": "#D97706"}
_TUR_NAV = {"talep": "taleplerim", "portfoy": "portfoylerim", "fsbo": "portfoylerim"}

takip = st.session_state.get("takip_listesi", {}) or {}

if takip:
    pills = ""
    for k, v in list(takip.items())[:14]:
        kaynak = v.get("_takip_kaynak", "")
        tur = "talep" if "talep" in kaynak else ("fsbo" if "fsbo" in kaynak else "portfoy")
        ozet = str(v.get("ozet") or v.get("mail_konusu") or "Kayıt")[:34].replace("<", "").replace(">", "")
        pills += (
            f'<a class="gd-takip-pill" href="?nav={_TUR_NAV[tur]}&sel={k}&tur={tur}">'
            f'<span class="dot" style="background:{_TUR_RENK[tur]}"></span>'
            f'{_TUR_IKON[tur]} {ozet}</a>'
        )
    st.markdown(f'<div class="gd-takip-strip"><span class="gd-takip-lbl">📌 Takip Listem</span>{pills}</div>',
                unsafe_allow_html=True)
else:
    st.markdown(
        '<div class="gd-takip-strip empty">Henüz takip listende bir kayıt yok — '
        'Taleplerim/Portföylerim\'de bir kaydı favoriye alınca burada görünür.</div>',
        unsafe_allow_html=True,
    )

# ── 4 KOKPİT KARTI ─────────────────────────────────────────────────────────
st.markdown(f'''
<div class="gd-tiles">
  <a class="gd-tile" href="?nav=taleplerim">
    <div class="gd-tile-icon">👤</div>
    <div class="gd-tile-num">{alici_sayi}</div>
    <div class="gd-tile-lbl">Alıcılarım — aktif talep</div>
  </a>
  <a class="gd-tile" href="?nav=portfoylerim">
    <div class="gd-tile-icon">🏠</div>
    <div class="gd-tile-num">{satici_sayi}</div>
    <div class="gd-tile-lbl">Satıcılarım — portföy</div>
  </a>
  <div class="gd-tile soon">
    <div class="gd-tile-soon-badge">🚧 Yakında</div>
    <div class="gd-tile-icon">🔑</div>
    <div class="gd-tile-num">—</div>
    <div class="gd-tile-lbl">FSBO Takip</div>
  </div>
  <div class="gd-tile soon">
    <div class="gd-tile-soon-badge">🚧 Yakında</div>
    <div class="gd-tile-icon">📇</div>
    <div class="gd-tile-num">—</div>
    <div class="gd-tile-lbl">Müşteri Rehberi</div>
  </div>
</div>
''', unsafe_allow_html=True)

st.caption(
    "ℹ️ Bu, kokpitin ilk sürümü (Yol A) — kartlara tıklamak ilgili sayfaya götürür. "
    "Takip Listem'deki bir kayda tıklamak, o kaydı doğrudan seçili olarak açar."
)

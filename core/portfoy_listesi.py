# pages/portfoy_listesi.py
# Zeta İlanları — Startkey.com.tr kaynaklı
# Veri: Supabase startkey_portfoyler tablosu
# Fotoğraflar, GD bilgisi, il/ilçe/mahalle dahil

import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.ui_helpers import render_navbar, render_page_header
from core.supabase_client import get_client
import pandas as pd
import html as _html
import streamlit.components.v1 as components
from datetime import datetime
import json, re

# ── GLOBAL CSS ────────────────────────────────────────────────────────────────
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
    --border: #DCE4EE;
    --chip-bg: #EEF4FA;
    --hover-bg: #F8FBFF;
}
.stApp { background: var(--bg); }
.block-container { padding-top: 0.5rem; padding-bottom: 2rem; max-width: 1520px; }

div[data-testid="stButton"] > button {
    white-space: normal; line-height: 1.2; border-radius: 8px;
    border: 1px solid var(--border); min-height: 30px;
    padding: 6px 12px; font-size: 12px; font-weight: 600;
    background: var(--chip-bg); color: var(--text);
    transition: all 0.16s ease-in-out;
}
div[data-testid="stButton"] > button:hover {
    border-color: #c8d7e5; box-shadow: 0 1px 4px rgba(53,92,125,0.08);
}
div[data-testid="stButton"] > button[kind="primary"] {
    background: var(--primary) !important; border-color: var(--primary) !important;
    color: #ffffff !important; box-shadow: 0 2px 8px rgba(53,92,125,0.18) !important;
}
div[data-baseweb="select"] > div {
    border-radius: 6px !important; border-color: var(--border) !important;
    min-height: 32px !important; font-size: 12px !important;
}
input { border-radius: 6px !important; font-size: 12px !important; }
input::placeholder { color: #94a3b8 !important; opacity: 1 !important; }
label, .stSelectbox label, .stTextInput label {
    color: #475569 !important; font-weight: 600 !important; font-size: 11px !important;
}

/* HTML Tablo */
.ht { border-collapse: collapse; width: 100%; font-size: 13px; }
.ht th {
    background: #f8fafc; font-size: 10px; font-weight: 800;
    text-transform: uppercase; letter-spacing: .05em; color: #64748b;
    padding: 9px 12px; border-bottom: 2px solid #e2e8f0;
    white-space: nowrap; text-align: left;
}
.ht td { padding: 9px 12px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }
.ht tr:hover td { background: #f8fafc; }
.type-satilik { color: #0f172a; font-weight: 700; }
.type-kiralik  { color: #0d9488; font-weight: 700; }
.cell-top    { font-weight: 600; font-size: 13px; color: #111827; }
.cell-bottom { font-size: 11px; color: #64748b; margin-top: 2px; }
.cell-wrap   { line-height: 1.35; }
.rbadge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 700; }
.rbadge-green  { background: #dcfce7; color: #166534; }
.rbadge-yellow { background: #fef3c7; color: #92400e; }
.rbadge-orange { background: #ffedd5; color: #c2410c; }
.rbadge-red    { background: #fee2e2; color: #991b1b; }
.rbadge-gray   { background: #f1f5f9; color: #475569; }
.dur-wrap { line-height: 1.4; }
.dur-date { font-size: 10px; color: #64748b; margin-top: 2px; }
.dur-line { display: flex; gap: 6px; align-items: center; }
.rlink-btn {
    display: inline-block; background: #eff6ff; color: #2563eb;
    border: 1px solid #bfdbfe; padding: 3px 10px; border-radius: 8px;
    font-size: 12px; font-weight: 700; text-decoration: none;
}
.rlink-btn:hover { background: #dbeafe; }
.rlink-none { color: #64748b; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# ── NAVBAR ────────────────────────────────────────────────────────────────────
render_navbar(
    user_role=st.session_state.get("user_role", "danisan"),
    user_name=st.session_state.get("user_name", ""),
    user_initials=st.session_state.get("user_initials", ""),
)

# ── YARDIMCI FONKSİYONLAR ────────────────────────────────────────────────────

def _safe(v):
    if v is None: return "-"
    s = str(v).strip()
    # HTML tag içeriyorsa temizle (yanlış parse edilmiş alanlar)
    if "<" in s and ">" in s:
        s = re.sub(r"<[^>]+>", "", s).strip()
    return _html.escape(s) if s else "-" 

def fiyat_formatla(v):
    try:
        f = float(str(v).replace(".", "").replace(",", ".").replace("₺", "").replace("TL", "").strip())
        return f"{f:,.0f} ₺".replace(",", ".")
    except Exception:
        return str(v) if v else "—"

def baslik_formatla(metin):
    if not metin: return "—"
    s = str(metin).strip()
    return s if not (s.isupper() or s.islower()) else s.title()

def parse_fiyat_num(v):
    try:
        return float(str(v).replace(".", "").replace(",", ".").replace("₺", "").replace("TL", "").strip())
    except Exception:
        return None

def aks_bul(ilce):
    if not ilce: return "DİĞER"
    ilce = str(ilce).strip().upper()
    merkez   = {"KONAK","BORNOVA","BAYRAKLI","KARABAĞLAR","BUCA"}
    kuzey    = {"KARŞIYAKA","KARSIYAKA","ÇİĞLİ","CİĞLİ","CIGLI","MENEMEN","ALİAĞA","ALIAĞA","FOÇA","FOCA"}
    yarimada = {"ÇEŞME","CESME","URLA","SEFERİHİSAR","SEFERIHISAR","GÜZELBAHÇE","GUZELBAHCE","NARLIDERE","BALÇOVA","BALCOVA"}
    guney    = {"TORBALI","MENDERES","GAZİEMİR","GAZIEMIR","TİRE","TIRE","SELÇUK","SELCUK"}
    if ilce in merkez:    return "İZMİR MERKEZ"
    if ilce in kuzey:     return "KUZEY AKSI"
    if ilce in yarimada:  return "YARIMADA"
    if ilce in guney:     return "GÜNEY AKSI"
    return "DİĞER"

def _sure_cell(guncelleme_tarihi):
    """Güncelleme tarihinden kaç gün önce güncellendiğini göster."""
    if not guncelleme_tarihi or str(guncelleme_tarihi).strip() in ("", "None", "nan"):
        return '<span class="rbadge rbadge-gray">— gün</span>'
    try:
        # "20.06.2026" veya "2026-06-20" formatları
        s = str(guncelleme_tarihi).strip()
        for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
            try:
                t = datetime.strptime(s[:len(fmt)], fmt)
                gun = (datetime.today() - t).days
                if gun <= 7:   return f'<div class="dur-wrap"><div class="dur-date">Güncellendi: <b>{s}</b></div><div class="dur-line"><span class="rbadge rbadge-green">🟢 {gun} gün</span></div></div>'
                elif gun <= 30: return f'<div class="dur-wrap"><div class="dur-date">Güncellendi: <b>{s}</b></div><div class="dur-line"><span class="rbadge rbadge-yellow">🟡 {gun} gün</span></div></div>'
                elif gun <= 90: return f'<div class="dur-wrap"><div class="dur-date">Güncellendi: <b>{s}</b></div><div class="dur-line"><span class="rbadge rbadge-orange">🟠 {gun} gün</span></div></div>'
                else:           return f'<div class="dur-wrap"><div class="dur-date">Güncellendi: <b>{s}</b></div><div class="dur-line"><span class="rbadge rbadge-red">🔴 {gun} gün</span></div></div>'
            except Exception:
                continue
    except Exception:
        pass
    return f'<span class="rbadge rbadge-gray">{_html.escape(str(guncelleme_tarihi))}</span>'

def _type_cell(islem, mulk):
    tip = str(islem).strip().lower()
    cls = "type-satilik" if "sat" in tip else ("type-kiralik" if "kir" in tip else "")
    return (f'<div class="cell-wrap"><div class="cell-top {cls}">{_safe(islem)}</div>'
            f'<div class="cell-bottom">{_safe(mulk)}</div></div>')

def _konum_cell(il, ilce, mahalle):
    ust = _safe(ilce) if ilce and ilce != "-" else _safe(il)
    alt = _safe(mahalle)
    return (f'<div class="cell-wrap"><div class="cell-top">{ust}</div>'
            f'<div class="cell-bottom">{alt}</div></div>')

def _fiyat_cell(fiyat, brut_m2, net_m2):
    fiyat_num = parse_fiyat_num(fiyat)
    if fiyat_num:
        ust = f'<div style="font-size:13px;font-weight:700;color:#0f172a;white-space:nowrap;">{fiyat_formatla(fiyat)}</div>'
    else:
        ust = '<div style="font-size:13px;font-weight:700;color:#94a3b8;">-</div>'
    # m² birim fiyat
    m2_num = None
    for m2v in [brut_m2, net_m2]:
        try:
            m2_num = float(str(m2v).replace(",", ".").replace(" ", ""))
            if m2_num > 0: break
        except Exception:
            pass
    alt = ""
    if fiyat_num and m2_num and m2_num > 0:
        birim = round(fiyat_num / m2_num)
        alt = f'<div style="font-size:11px;color:#64748b;margin-top:2px;white-space:nowrap;">m²: {birim:,} ₺</div>'.replace(",", ".")
    return f"<div>{ust}{alt}</div>"

def _link_btn(url):
    if not url or str(url).strip() in ("", "None"):
        return '<span class="rlink-none">-</span>'
    u = _html.escape(str(url).strip(), quote=True)
    return f'<a class="rlink-btn" href="{u}" target="_blank">Aç</a>'

def _gd_cell(gd_adi, ofis_label):
    return (f'<div class="cell-wrap">'
            f'<div class="cell-top" style="font-size:12px;font-weight:700;color:#374151;">{_safe(ofis_label)}</div>'
            f'<div class="cell-bottom">{_safe(gd_adi)}</div></div>')

def _foto_urls_parse(v):
    """JSON string veya liste → Python listesi."""
    if not v:
        return []
    if isinstance(v, list):
        return v
    try:
        return json.loads(v) if isinstance(v, str) else []
    except Exception:
        return []

# ── VERİ ─────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def veri_yukle():
    try:
        r = get_client().table("startkey_portfoyler") \
            .select("*") \
            .in_("kaynak", ["zeta1", "zeta2"]) \
            .eq("aktif", True) \
            .order("sync_tarihi", desc=True) \
            .limit(1000) \
            .execute()
        return r.data or []
    except Exception as e:
        st.error(f"Veri yüklenemedi: {e}")
        return []

def veriyi_hazirla(veriler):
    if not veriler:
        return pd.DataFrame()
    df = pd.DataFrame(veriler)
    df["ofis_label"] = df["kaynak"].map({"zeta1": "ZETA 1", "zeta2": "ZETA 2"}).fillna("DİĞER")
    if "ilce" in df.columns:
        df["aks"] = df["ilce"].apply(aks_bul)
    # Fiyat numerik
    if "fiyat_num" not in df.columns and "fiyat" in df.columns:
        df["fiyat_num"] = df["fiyat"].apply(parse_fiyat_num)
    # m² → brut_m2 tercihli, net_m2 fallback
    df["m2_gosterim"] = df.get("brut_m2", pd.Series(dtype=str)).fillna("") \
                        .where(df.get("brut_m2", pd.Series(dtype=str)).fillna("") != "",
                               df.get("net_m2", pd.Series(dtype=str)).fillna(""))
    return df

# ── BANNER ───────────────────────────────────────────────────────────────────
components.html("""
<div style="
    background: linear-gradient(135deg, #1e3a5f 0%, #355c7d 60%, #4a7fa8 100%);
    border-radius: 12px; padding: 16px 24px; margin-bottom: 4px;
    display: flex; align-items: center; gap: 16px;">
  <div style="width:52px;height:52px;border-radius:50%;background:#2563eb;
    display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:24px;">🏢</div>
  <div>
    <div style="font-size:20px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;">Zeta İlanları</div>
    <div style="font-size:12px;color:#93c5fd;margin-top:3px;">STARTKEY ZETA · Tüm portföyler — ZETA 1 &amp; ZETA 2</div>
  </div>
</div>
""", height=90)

# ── VERİ YÜKLE ────────────────────────────────────────────────────────────────
c_yenile, c_sync, _ = st.columns([1, 1.5, 6])
with c_yenile:
    if st.button("🔄 Yenile", key="zilan_yenile", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with c_sync:
    if st.button("⚡ Startkey'den Sync Et", key="zilan_sync", use_container_width=True):
        st.session_state["sync_baslat"] = True
        st.rerun()

# Sync tetiklenmişse çalıştır
if st.session_state.pop("sync_baslat", False):
    try:
        from core.startkey_portfoy_sync import sync_tum
        log_kutusu = st.empty()
        loglar = []

        def log_cb(msg):
            loglar.append(msg)
            log_kutusu.text("\n".join(loglar[-15:]))

        with st.spinner("Startkey sync çalışıyor..."):
            toplam = sync_tum(log_fn=log_cb, limit=5)  # TEST: ilk 5 ilan
        st.success(f"✅ Sync tamamlandı — {toplam} ilan güncellendi")
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Sync hatası: {e}")

veriler = veri_yukle()

if not veriler:
    st.info("Henüz portföy verisi yok. 'Startkey'den Sync Et' ile veriyi çekebilirsiniz.")
    st.stop()

df = veriyi_hazirla(veriler)

# ── OFİS SEKMELERİ ───────────────────────────────────────────────────────────
sb1, sb2, sb3, _sp = st.columns([1, 1, 1, 5])
with sb1:
    if st.button("Tümü", key="zil_tumu", use_container_width=True):
        st.session_state["zil_ofis"] = "TÜMÜ"; st.rerun()
with sb2:
    if st.button("🏛 ZETA 1", key="zil_z1", use_container_width=True):
        st.session_state["zil_ofis"] = "ZETA 1"; st.rerun()
with sb3:
    if st.button("🏛 ZETA 2", key="zil_z2", use_container_width=True):
        st.session_state["zil_ofis"] = "ZETA 2"; st.rerun()

zil_ofis = st.session_state.get("zil_ofis", "TÜMÜ")
_renk_map = {
    "TÜMÜ":   ("#374151", "#f1f5f9", "Tümü"),
    "ZETA 1": ("#1e40af", "#dbeafe", "🏛 ZETA 1"),
    "ZETA 2": ("#92400e", "#fef3c7", "🏛 ZETA 2"),
}
_fg, _bg, _lbl = _renk_map.get(zil_ofis, ("#374151", "#f1f5f9", zil_ofis))
components.html(
    f'<div style="font-size:11px;color:#64748b;margin:4px 0 10px 0;">'
    f'Aktif: <span style="background:{_bg};color:{_fg};padding:2px 10px;'
    f'border-radius:999px;font-weight:700;">{_lbl}</span>'
    f' &nbsp;·&nbsp; {len(df)} toplam portföy</div>',
    height=28
)

filtered = df.copy()
if zil_ofis == "ZETA 1":
    filtered = filtered[filtered["ofis_label"] == "ZETA 1"]
elif zil_ofis == "ZETA 2":
    filtered = filtered[filtered["ofis_label"] == "ZETA 2"]


# ── GELİŞMİŞ FİLTRELER ───────────────────────────────────────────────────────
GF_KEYS = ["zilgf_islem", "zilgf_mulk", "zilgf_m2_min", "zilgf_m2_max",
           "zilgf_fiyat_min", "zilgf_fiyat_max", "zilgf_oda",
           "zilgf_kat", "zilgf_bina_yasi", "zilgf_asansor", "zilgf_otopark"]

def gf_aktif_say():
    return sum(1 for k in GF_KEYS
               if st.session_state.get(k) not in ("Tümü", "", 0, None))

gf_say = gf_aktif_say()
with st.expander(f"Gelişmiş Filtreler{f' ({gf_say} aktif)' if gf_say else ''}", expanded=False):
    gc1, gc2, gc3 = st.columns(3)

    with gc1:
        st.markdown("**İşlem & Mülk**")
        islem_opts = ["Tümü"] + sorted(filtered["islem_tipi"].dropna().unique().tolist()) if "islem_tipi" in filtered.columns else ["Tümü"]
        st.selectbox("İşlem Tipi", islem_opts,
            index=islem_opts.index(st.session_state.get("zilgf_islem", "Tümü")) if st.session_state.get("zilgf_islem", "Tümü") in islem_opts else 0,
            key="zilgf_islem")
        mulk_opts = ["Tümü"] + sorted(filtered["mulk_tipi"].dropna().unique().tolist()) if "mulk_tipi" in filtered.columns else ["Tümü"]
        st.selectbox("Mülk Tipi", mulk_opts,
            index=mulk_opts.index(st.session_state.get("zilgf_mulk", "Tümü")) if st.session_state.get("zilgf_mulk", "Tümü") in mulk_opts else 0,
            key="zilgf_mulk")
        oda_opts = ["Tümü"] + sorted(filtered["oda_sayisi"].dropna().unique().tolist()) if "oda_sayisi" in filtered.columns else ["Tümü"]
        st.selectbox("Oda Sayısı", oda_opts,
            index=oda_opts.index(st.session_state.get("zilgf_oda", "Tümü")) if st.session_state.get("zilgf_oda", "Tümü") in oda_opts else 0,
            key="zilgf_oda")

    with gc2:
        st.markdown("**M² & Fiyat**")
        m2c1, m2c2 = st.columns(2)
        with m2c1:
            st.number_input("M² Alt", min_value=0,
                value=int(st.session_state.get("zilgf_m2_min") or 0),
                step=10, key="zilgf_m2_min")
        with m2c2:
            st.number_input("M² Üst", min_value=0,
                value=int(st.session_state.get("zilgf_m2_max") or 0),
                step=10, key="zilgf_m2_max")
        fc1, fc2 = st.columns(2)
        with fc1:
            st.number_input("Fiyat Alt (₺)", min_value=0,
                value=int(st.session_state.get("zilgf_fiyat_min") or 0),
                step=100000, key="zilgf_fiyat_min", format="%d")
        with fc2:
            st.number_input("Fiyat Üst (₺)", min_value=0,
                value=int(st.session_state.get("zilgf_fiyat_max") or 0),
                step=100000, key="zilgf_fiyat_max", format="%d")

    with gc3:
        st.markdown("**Yapı Bilgileri**")
        kat_opts = ["Tümü"] + sorted(filtered["bulundugu_kat"].dropna().unique().tolist()) if "bulundugu_kat" in filtered.columns else ["Tümü"]
        st.selectbox("Bulunduğu Kat", kat_opts,
            index=kat_opts.index(st.session_state.get("zilgf_kat", "Tümü")) if st.session_state.get("zilgf_kat", "Tümü") in kat_opts else 0,
            key="zilgf_kat")
        yas_opts = ["Tümü"] + sorted(filtered["bina_yasi"].dropna().unique().tolist()) if "bina_yasi" in filtered.columns else ["Tümü"]
        st.selectbox("Bina Yaşı", yas_opts,
            index=yas_opts.index(st.session_state.get("zilgf_bina_yasi", "Tümü")) if st.session_state.get("zilgf_bina_yasi", "Tümü") in yas_opts else 0,
            key="zilgf_bina_yasi")
        asansor_opts = ["Tümü", "Var", "Yok"]
        st.selectbox("Asansör", asansor_opts,
            index=asansor_opts.index(st.session_state.get("zilgf_asansor", "Tümü")) if st.session_state.get("zilgf_asansor", "Tümü") in asansor_opts else 0,
            key="zilgf_asansor")
        otopark_opts = ["Tümü", "Var", "Yok"]
        st.selectbox("Otopark", otopark_opts,
            index=otopark_opts.index(st.session_state.get("zilgf_otopark", "Tümü")) if st.session_state.get("zilgf_otopark", "Tümü") in otopark_opts else 0,
            key="zilgf_otopark")
        if gf_say > 0:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            if st.button("✕ Filtreleri Temizle", key="zilgf_temizle", use_container_width=True):
                for k in GF_KEYS:
                    st.session_state.pop(k, None)
                st.rerun()

# Gelişmiş filtreler uygula
liste_df = filtered.copy()

if st.session_state.get("zilgf_islem", "Tümü") != "Tümü" and "islem_tipi" in liste_df.columns:
    liste_df = liste_df[liste_df["islem_tipi"] == st.session_state["zilgf_islem"]]
if st.session_state.get("zilgf_mulk", "Tümü") != "Tümü" and "mulk_tipi" in liste_df.columns:
    liste_df = liste_df[liste_df["mulk_tipi"] == st.session_state["zilgf_mulk"]]
if st.session_state.get("zilgf_oda", "Tümü") != "Tümü" and "oda_sayisi" in liste_df.columns:
    liste_df = liste_df[liste_df["oda_sayisi"] == st.session_state["zilgf_oda"]]
if st.session_state.get("zilgf_kat", "Tümü") != "Tümü" and "bulundugu_kat" in liste_df.columns:
    liste_df = liste_df[liste_df["bulundugu_kat"] == st.session_state["zilgf_kat"]]
if st.session_state.get("zilgf_bina_yasi", "Tümü") != "Tümü" and "bina_yasi" in liste_df.columns:
    liste_df = liste_df[liste_df["bina_yasi"] == st.session_state["zilgf_bina_yasi"]]
if st.session_state.get("zilgf_asansor", "Tümü") != "Tümü" and "asansor" in liste_df.columns:
    liste_df = liste_df[liste_df["asansor"].str.strip().str.lower() ==
                        st.session_state["zilgf_asansor"].lower()]
if st.session_state.get("zilgf_otopark", "Tümü") != "Tümü" and "otopark" in liste_df.columns:
    liste_df = liste_df[liste_df["otopark"].str.strip().str.lower() ==
                        st.session_state["zilgf_otopark"].lower()]
if st.session_state.get("zilgf_m2_min", 0):
    m2_col = "brut_m2" if "brut_m2" in liste_df.columns else "net_m2"
    if m2_col in liste_df.columns:
        liste_df = liste_df[pd.to_numeric(liste_df[m2_col], errors="coerce").fillna(0) >= st.session_state["zilgf_m2_min"]]
if st.session_state.get("zilgf_m2_max", 0):
    m2_col = "brut_m2" if "brut_m2" in liste_df.columns else "net_m2"
    if m2_col in liste_df.columns:
        liste_df = liste_df[pd.to_numeric(liste_df[m2_col], errors="coerce").fillna(99999) <= st.session_state["zilgf_m2_max"]]
if st.session_state.get("zilgf_fiyat_min", 0) and "fiyat_num" in liste_df.columns:
    liste_df = liste_df[liste_df["fiyat_num"].fillna(0) >= st.session_state["zilgf_fiyat_min"]]
if st.session_state.get("zilgf_fiyat_max", 0) and "fiyat_num" in liste_df.columns:
    liste_df = liste_df[liste_df["fiyat_num"].fillna(float("inf")) <= st.session_state["zilgf_fiyat_max"]]


# ── FİLTRE BAR + SIRALAMA + GÖRÜNÜM ─────────────────────────────────────────
lf1, lf2, lf3, lf4, lf_sir, lf5, lg1, lg2, lg3 = st.columns([1.5, 1.3, 1.3, 1.3, 1.5, 0.5, 0.7, 0.7, 0.7])

dan_list  = ["Tümü"] + sorted(liste_df["gd_adi"].dropna().unique().tolist()) if "gd_adi" in liste_df.columns else ["Tümü"]
ilce_list = ["Tümü"] + sorted(liste_df["ilce"].dropna().unique().tolist()) if "ilce" in liste_df.columns else ["Tümü"]
mah_list  = ["Tümü"] + sorted(liste_df["mahalle"].dropna().unique().tolist()) if "mahalle" in liste_df.columns else ["Tümü"]
_SIR_OPTS = ["Güncelleme ↓ (Yeni→Eski)", "Güncelleme ↑ (Eski→Yeni)",
              "Fiyat ↑", "Fiyat ↓", "M² ↑", "M² ↓", "m² Fiyatı ↑", "m² Fiyatı ↓"]

with lf1:
    ara = st.text_input("Ara", placeholder="Başlık, ilçe, GD...", key="zil_ara", label_visibility="collapsed")
with lf2:
    dan_sec = st.selectbox("Danışman", dan_list,
        index=dan_list.index(st.session_state.get("zil_dan", "Tümü")) if st.session_state.get("zil_dan", "Tümü") in dan_list else 0,
        key="zil_dan", label_visibility="collapsed")
with lf3:
    ilce_sec = st.selectbox("İlçe", ilce_list,
        index=ilce_list.index(st.session_state.get("zil_ilce", "Tümü")) if st.session_state.get("zil_ilce", "Tümü") in ilce_list else 0,
        key="zil_ilce", label_visibility="collapsed")
with lf4:
    mah_sec = st.selectbox("Mahalle", mah_list,
        index=mah_list.index(st.session_state.get("zil_mah", "Tümü")) if st.session_state.get("zil_mah", "Tümü") in mah_list else 0,
        key="zil_mah", label_visibility="collapsed")
with lf_sir:
    _cur = st.session_state.get("zil_siralama", _SIR_OPTS[0])
    st.selectbox("Sırala", _SIR_OPTS,
        index=_SIR_OPTS.index(_cur) if _cur in _SIR_OPTS else 0,
        key="zil_siralama", label_visibility="collapsed")
with lf5:
    filtre_aktif = bool(
        st.session_state.get("zil_ara") or
        st.session_state.get("zil_dan", "Tümü") != "Tümü" or
        st.session_state.get("zil_ilce", "Tümü") != "Tümü" or
        st.session_state.get("zil_mah", "Tümü") != "Tümü"
    )
    if filtre_aktif:
        if st.button("✕", key="zil_filtre_temizle", use_container_width=True):
            for k in ["zil_ara", "zil_dan", "zil_ilce", "zil_mah"]:
                st.session_state.pop(k, None)
            st.rerun()

with lg1:
    if st.button("☰ Liste", key="zil_liste", use_container_width=True):
        st.session_state["zil_gorunum"] = "liste"; st.rerun()
with lg2:
    if st.button("▦ Kart", key="zil_kart", use_container_width=True):
        st.session_state["zil_gorunum"] = "kart"; st.rerun()
with lg3:
    if st.button("▤ Tablo", key="zil_tablo_btn", use_container_width=True):
        st.session_state["zil_gorunum"] = "tablo"; st.rerun()

# Filtreler uygula
if ara:
    ara_l = ara.lower()
    liste_df = liste_df[liste_df.apply(
        lambda r: any(ara_l in str(r.get(c, "")).lower()
                      for c in ["baslik", "gd_adi", "ilce", "mahalle", "il"]), axis=1)]
if dan_sec != "Tümü" and "gd_adi" in liste_df.columns:
    liste_df = liste_df[liste_df["gd_adi"] == dan_sec]
if ilce_sec != "Tümü" and "ilce" in liste_df.columns:
    liste_df = liste_df[liste_df["ilce"] == ilce_sec]
if mah_sec != "Tümü" and "mahalle" in liste_df.columns:
    liste_df = liste_df[liste_df["mahalle"] == mah_sec]

# Sıralama
def _sf(v):
    try: return float(str(v).replace(".", "").replace(",", ".").replace("₺", "").replace("TL", "").strip())
    except: return float("inf")

_sir = st.session_state.get("zil_siralama", "Güncelleme ↓ (Yeni→Eski)")
if not liste_df.empty:
    if "Güncelleme ↓" in _sir and "guncelleme_tarihi" in liste_df.columns:
        liste_df = liste_df.sort_values("guncelleme_tarihi", ascending=False, na_position="last")
    elif "Güncelleme ↑" in _sir and "guncelleme_tarihi" in liste_df.columns:
        liste_df = liste_df.sort_values("guncelleme_tarihi", ascending=True, na_position="last")
    elif "Fiyat" in _sir and "fiyat_num" in liste_df.columns:
        liste_df = liste_df.sort_values("fiyat_num", ascending="↑" in _sir, na_position="last")
    elif "M²" in _sir and "Fiyat" not in _sir:
        m2_col = "brut_m2" if "brut_m2" in liste_df.columns else "net_m2"
        if m2_col in liste_df.columns:
            _t = liste_df.copy()
            _t["__s"] = pd.to_numeric(_t[m2_col], errors="coerce")
            liste_df = _t.sort_values("__s", ascending="↑" in _sir, na_position="last").drop(columns=["__s"])
    elif "m² Fiyat" in _sir and "fiyat_num" in liste_df.columns:
        _t = liste_df.copy()
        m2_col = "brut_m2" if "brut_m2" in liste_df.columns else "net_m2"
        def _mf(r):
            try:
                f = r.get("fiyat_num") or 0
                m = float(str(r.get(m2_col, "0")).replace(",", "."))
                return f / m if m > 0 and f > 0 else float("inf")
            except: return float("inf")
        _t["__s"] = _t.apply(_mf, axis=1)
        liste_df = _t.sort_values("__s", ascending="↑" in _sir, na_position="last").drop(columns=["__s"])

gorunum = st.session_state.get("zil_gorunum", "liste")


# ── ÜST BAR ──────────────────────────────────────────────────────────────────
hd1, hd2 = st.columns([5, 1])
with hd1:
    st.caption(f"{len(liste_df)} portföy gösteriliyor")
with hd2:
    if not liste_df.empty:
        from io import BytesIO
        output = BytesIO()
        export_cols = {
            "ofis_label": "Ofis", "gd_adi": "Danışman",
            "baslik": "Başlık", "islem_tipi": "İşlem", "mulk_tipi": "Mülk",
            "il": "İl", "ilce": "İlçe", "mahalle": "Mahalle",
            "fiyat": "Fiyat", "oda_sayisi": "Oda",
            "brut_m2": "Brüt m²", "net_m2": "Net m²",
            "bulundugu_kat": "Kat", "bina_yasi": "Bina Yaşı",
            "asansor": "Asansör", "otopark": "Otopark",
            "guncelleme_tarihi": "Güncelleme", "startkey_url": "Link",
        }
        ex_df = liste_df[[c for c in export_cols if c in liste_df.columns]].rename(columns=export_cols)
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            ex_df.to_excel(writer, index=False, sheet_name="Zeta İlanları")
        output.seek(0)
        st.download_button(
            "📥 Excel", data=output.getvalue(),
            file_name="zeta_ilanlar.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

if liste_df.empty:
    st.info("Gösterilecek portföy bulunamadı.")
    if st.button("✕ Filtreleri Temizle", key="zil_bos_temizle"):
        for k in ["zil_ara", "zil_dan", "zil_ilce", "zil_mah"]:
            st.session_state.pop(k, None)
        st.rerun()
    st.stop()


# ── GÖRÜNÜM: LİSTE ───────────────────────────────────────────────────────────
if gorunum == "liste":
    satirlar = ""
    for sira, (_, row) in enumerate(liste_df.iterrows(), 1):
        ofis      = row.get("ofis_label", "") or ""
        gd        = baslik_formatla(row.get("gd_adi", "")) or "-"
        baslik    = baslik_formatla(str(row.get("baslik", "") or ""))
        islem     = row.get("islem_tipi", "") or ""
        mulk      = row.get("mulk_tipi", "") or ""
        il        = str(row.get("il", "") or "").title()
        ilce      = str(row.get("ilce", "") or "").title()
        mahalle   = str(row.get("mahalle", "") or "").title()
        oda       = str(row.get("oda_sayisi", "") or "-")
        brut_m2   = str(row.get("brut_m2", "") or "")
        net_m2    = str(row.get("net_m2", "") or "")
        kat       = str(row.get("bulundugu_kat", "") or "")
        bina_yasi = str(row.get("bina_yasi", "") or "")
        fiyat     = row.get("fiyat", "") or ""
        link      = row.get("startkey_url", "") or ""
        guncelleme = row.get("guncelleme_tarihi", "") or ""
        asansor   = str(row.get("asansor", "") or "")
        otopark   = str(row.get("otopark", "") or "")

        tip = str(islem).strip().lower()
        bdr = "#1e3a5f" if "sat" in tip else ("#0d9488" if "kir" in tip else "#e2e8f0")
        m2_html = (brut_m2 + " m²") if brut_m2 and brut_m2 not in ("", "None", "nan") else (
                   (net_m2 + " m²") if net_m2 and net_m2 not in ("", "None", "nan") else "-")

        # Özellik tag'leri (Asansör, Otopark)
        tags = ""
        if asansor.lower() in ("var", "evet", "1", "true"):
            tags += '<span style="background:#eff6ff;color:#2563eb;padding:1px 7px;border-radius:4px;font-size:10px;font-weight:600;margin-right:3px;">🛗 Asansör</span>'
        if otopark.lower() in ("var", "evet", "1", "true"):
            tags += '<span style="background:#f0fdf4;color:#166534;padding:1px 7px;border-radius:4px;font-size:10px;font-weight:600;margin-right:3px;">🅿 Otopark</span>'

        baslik_cell = (
            f'<div style="font-size:13px;font-weight:700;color:#0f172a;line-height:1.35;margin-bottom:3px;">{_html.escape(baslik)}</div>'
            + (f'<div style="margin-top:2px;">{tags}</div>' if tags else "")
        )

        t_cell  = _type_cell(islem, mulk)
        k_cell  = _konum_cell(il, ilce, mahalle)
        f_cell  = _fiyat_cell(fiyat, brut_m2, net_m2)
        s_cell  = _sure_cell(guncelleme)
        l_btn   = _link_btn(link)
        ofis_html = (f'<div style="font-size:11px;font-weight:700;color:#374151;">{_html.escape(ofis)}</div>'
                     f'<div style="font-size:11px;color:#94a3b8;margin-top:2px;">{_html.escape(gd)}</div>')

        kat_yas = ""
        if kat and kat not in ("", "None", "nan", "-"):
            kat_yas = kat
        if bina_yasi and bina_yasi not in ("", "None", "nan", "-", "0"):
            kat_yas += (" · " + bina_yasi + " yaş") if kat_yas else (bina_yasi + " yaş")

        td0 = f"padding:9px 4px 9px 0;border-left:3px solid {bdr};"
        td_s = "padding:9px 12px;"
        satirlar += ("<tr>"
            + f'<td style="{td0}width:3px;"></td>'
            + f'<td style="{td_s}color:#94a3b8;font-size:11px;white-space:nowrap;">{sira}</td>'
            + f'<td style="{td_s}max-width:280px;min-width:220px;">{baslik_cell}</td>'
            + f'<td style="{td_s}">{t_cell}</td>'
            + f'<td style="{td_s}">{k_cell}</td>'
            + f'<td style="{td_s}white-space:nowrap;color:#475569;">{m2_html}</td>'
            + f'<td style="{td_s}white-space:nowrap;">{f_cell}</td>'
            + f'<td style="{td_s}color:#475569;white-space:nowrap;">{oda}</td>'
            + f'<td style="{td_s}color:#475569;font-size:11px;white-space:nowrap;">{_html.escape(kat_yas)}</td>'
            + f'<td style="{td_s}">{s_cell}</td>'
            + f'<td style="{td_s}">{l_btn}</td>'
            + f'<td style="{td_s}white-space:nowrap;">{ofis_html}</td>'
            + "</tr>")

    BSLKLAR = ["", "#", "Başlık / Özellikler", "İşlem / Mülk",
               "İlçe / Mah.", "M²", "Fiyat / m²",
               "Oda", "Kat / Yaş", "Güncelleme", "İlan", "Ofis / GD"]
    ths = ("padding:9px 12px;text-align:left;font-size:10px;font-weight:800;"
           "text-transform:uppercase;letter-spacing:.05em;color:#64748b;"
           "border-bottom:2px solid #e2e8f0;background:#f8fafc;white-space:nowrap;")
    bh = "".join(f'<th style="{ths}">{b}</th>' for b in BSLKLAR)
    html_tablo = (
        "<style>.ht tbody tr:hover td{background:#f0f4ff!important;}</style>"
        + '<div style="background:white;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;">'
        + '<div style="overflow-x:auto;">'
        + f'<table class="ht"><thead><tr>{bh}</tr></thead>'
        + f"<tbody>{satirlar}</tbody></table></div></div>"
    )
    components.html(html_tablo, height=min(800, 90 + len(liste_df) * 56), scrolling=True)


# ── GÖRÜNÜM: KART ────────────────────────────────────────────────────────────
elif gorunum == "kart":
    # ── BADGE + AKS renk haritası (talep tablosuyla aynı dil) ────────────────
    BADGE_P = {
        "Satılık": ("#FCEBEB", "#A32D2D", "#f5c0c0"),
        "Kiralık": ("#FAEEDA", "#854F0B", "#f0d0a0"),
        "Daire":   ("#f1f5f9", "#475569", "#e2e8f0"),
        "Villa":   ("#f0fdf4", "#166534", "#bbf7d0"),
        "Arsa":    ("#fffbeb", "#92400e", "#fde68a"),
        "Tarla":   ("#fffbeb", "#92400e", "#fde68a"),
        "İşyeri":  ("#eff6ff", "#1e40af", "#bfdbfe"),
        "Dükkan":  ("#eff6ff", "#1e40af", "#bfdbfe"),
        "Ofis":    ("#eff6ff", "#1e40af", "#bfdbfe"),
    }
    AKS_R = {
        "İZMİR MERKEZ": {"bg":"#EEF4FA","text":"#1E3A5F","bar":"#355C7D"},
        "KUZEY AKSI":   {"bg":"#E6F4F1","text":"#0F6E56","bar":"#0F6E56"},
        "YARIMADA":     {"bg":"#FDF2E9","text":"#935116","bar":"#E67E22"},
        "GÜNEY AKSI":   {"bg":"#F5EEF8","text":"#7D3C98","bar":"#8E44AD"},
        "DİĞER":        {"bg":"#F2F3F4","text":"#566573","bar":"#808B96"},
    }

    def _badge(etiket, palette):
        if not etiket or etiket in ("—", "Belirsiz", "Belirtilmemiş", "nan", "None"):
            return ""
        bg, fg, bdr = palette.get(etiket, ("#f1f5f9","#475569","#e2e8f0"))
        return (f'<span style="background:{bg};color:{fg};border:1px solid {bdr};'+
                f'padding:3px 9px;border-radius:5px;font-size:10.5px;font-weight:700;'+
                f'margin-right:4px;display:inline-block;">{_html.escape(etiket)}</span>')

    def _pkart_html(row):
        """Portföy kartı — talep tablosuyla aynı stil dili, üstte fotoğraf bandı."""
        ofis      = str(row.get("ofis_label","") or "")
        gd        = baslik_formatla(str(row.get("gd_adi","") or "")) or "—"
        baslik    = baslik_formatla(str(row.get("baslik","") or ""))
        islem     = str(row.get("islem_tipi","") or "")
        mulk      = str(row.get("mulk_tipi","") or "")
        ilce      = str(row.get("ilce","") or "").title()
        mahalle   = str(row.get("mahalle","") or "").title()
        fiyat_str = fiyat_formatla(row.get("fiyat",""))
        brut_m2   = str(row.get("brut_m2","") or "")
        net_m2    = str(row.get("net_m2","") or "")
        oda       = str(row.get("oda_sayisi","") or "")
        kat       = str(row.get("bulundugu_kat","") or "")
        bina_yasi = str(row.get("bina_yasi","") or "")
        asansor   = str(row.get("asansor","") or "").lower()
        otopark   = str(row.get("otopark","") or "").lower()
        guncelleme= str(row.get("guncelleme_tarihi","") or "")
        link      = str(row.get("startkey_url","") or "")
        ilk_foto  = str(row.get("ilk_foto_url","") or "")
        gd_foto   = str(row.get("gd_foto_url","") or "")

        # ── Fotoğraf bandı ──────────────────────────────────────────────────
        if ilk_foto and ilk_foto not in ("", "None", "nan"):
            foto_html = (
                f'<div style="width:100%;height:190px;overflow:hidden;'
                f'border-top-left-radius:16px;border-top-right-radius:16px;flex-shrink:0;">'
                f'<img src="{_html.escape(ilk_foto,quote=True)}" '
                f'style="width:100%;height:190px;object-fit:cover;display:block;" /></div>'
            )
        else:
            foto_html = (
                '<div style="width:100%;height:190px;display:flex;align-items:center;'+
                'justify-content:center;background:#f8fafc;color:#cbd5e1;font-size:28px;'+
                'border-top-left-radius:16px;border-top-right-radius:16px;flex-shrink:0;">🏠</div>'
            )

        # ── Ofis rengi ──────────────────────────────────────────────────────
        ofis_bdr = "#1e40af" if "ZETA 1" in ofis else "#92400e" if "ZETA 2" in ofis else "#355C7D"

        # ── Badge satırı ─────────────────────────────────────────────────────
        aks_label = aks_bul(ilce.upper())
        aks_r     = AKS_R.get(aks_label, AKS_R["DİĞER"])
        lokasyon_lbl = ilce if ilce and ilce not in ("—","") else ""

        badges = ""
        if lokasyon_lbl:
            badges += (f'<span style="background:{aks_r["bg"]};color:{aks_r["text"]};'+
                       f'padding:3px 9px;border-radius:5px;font-size:10.5px;font-weight:700;'+
                       f'letter-spacing:0.06em;text-transform:uppercase;margin-right:4px;'+
                       f'display:inline-block;">{_html.escape(lokasyon_lbl)}</span>')
        badges += _badge(islem, BADGE_P)
        badges += _badge(mulk, BADGE_P)
        if asansor in ("var","evet","1","true"):
            badges += ('<span style="background:#eff6ff;color:#2563eb;border:1px solid #bfdbfe;'+
                       'padding:3px 7px;border-radius:5px;font-size:10px;font-weight:600;'+
                       'margin-right:4px;display:inline-block;">🛗 Asansör</span>')
        if otopark in ("var","evet","1","true"):
            badges += ('<span style="background:#f0fdf4;color:#166534;border:1px solid #bbf7d0;'+
                       'padding:3px 7px;border-radius:5px;font-size:10px;font-weight:600;'+
                       'margin-right:4px;display:inline-block;">🅿 Otopark</span>')

        # ── Başlık ──────────────────────────────────────────────────────────
        baslik_goster = baslik if baslik and baslik not in ("—","") else (
            " ".join(filter(None,[islem,oda,mulk])) or "Portföy"
        )

        # ── Özet satır (m² · oda · kat) ─────────────────────────────────────
        m2_str = (brut_m2+" m²") if brut_m2 and brut_m2 not in ("","None","nan") else (
                  (net_m2+" m²") if net_m2 and net_m2 not in ("","None","nan") else "")
        ozet_parts = [p for p in [oda, m2_str] if p and p not in ("—","")]
        if kat and kat not in ("","None","nan","—"):
            ozet_parts.append(f"{kat}. kat")
        if bina_yasi and bina_yasi not in ("","None","nan","—","0"):
            ozet_parts.append(f"{bina_yasi} yaş")
        ozet_str = "  ·  ".join(ozet_parts)

        # ── GD footer ───────────────────────────────────────────────────────
        if gd_foto and gd_foto not in ("","None","nan"):
            gd_avatar = (f'<img src="{_html.escape(gd_foto,quote=True)}" '
                         f'style="width:20px;height:20px;border-radius:50%;object-fit:cover;'+
                         f'margin-right:6px;vertical-align:middle;flex-shrink:0;" />')
        else:
            initials = "".join(w[0].upper() for w in gd.split()[:2] if w) if gd != "—" else "?"
            gd_avatar = (f'<span style="width:20px;height:20px;border-radius:50%;'+
                         f'background:#355C7D;color:#fff;display:inline-flex;'+
                         f'align-items:center;justify-content:center;'+
                         f'font-size:8px;font-weight:700;margin-right:6px;flex-shrink:0;">'+
                         f'{initials}</span>')

        ofis_chip = (f'<span style="background:#EEF4FA;color:{ofis_bdr};font-size:10px;'+
                     f'font-weight:700;padding:1px 7px;border-radius:4px;">{_html.escape(ofis)}</span>')

        guncelleme_html = (f'<span style="font-size:10px;color:#94a3b8;">{_html.escape(guncelleme)}</span>'
                           if guncelleme and guncelleme not in ("","None","nan") else "")

        # ── Kart HTML ───────────────────────────────────────────────────────
        return (
            f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;'+
            f'box-shadow:0 2px 10px rgba(15,23,42,0.06);overflow:hidden;'+
            f'display:flex;flex-direction:column;margin-bottom:0;">'+
            foto_html +
            f'<div style="padding:16px 18px 14px;display:flex;flex-direction:column;gap:9px;">'+
            # Badge satırı
            f'<div style="display:flex;flex-wrap:wrap;gap:3px;">{badges}</div>'+
            # Başlık
            f'<div style="font-size:15px;font-weight:800;color:#0F172A;line-height:1.35;'+
            f'display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;'+
            f'overflow:hidden;">{_html.escape(baslik_goster)}</div>'+
            # Özet
            (f'<div style="font-size:11.5px;color:#64748B;">{_html.escape(ozet_str)}</div>'
             if ozet_str else "") +
            # Fiyat
            (f'<div style="font-size:19px;font-weight:800;color:#0F172A;letter-spacing:-0.5px;">{fiyat_str}</div>'
             if fiyat_str and fiyat_str != "—" else
             '<div style="font-size:13px;color:#94a3b8;font-style:italic;">Fiyat belirtilmedi</div>') +
            # Divider
            f'<div style="border-top:1px solid #f1f5f9;"></div>'+
            # Footer: GD + ofis + güncelleme
            f'<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">'+
            gd_avatar +
            f'<span style="font-size:12px;font-weight:600;color:#374151;flex:1;min-width:0;'+
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{_html.escape(gd)}</span>'+
            f'<span style="color:#d1d5db;font-size:10px;">·</span>'+
            ofis_chip +
            (f'<span style="color:#d1d5db;font-size:10px;">·</span>' + guncelleme_html
             if guncelleme_html else "") +
            f'</div>'+
            f'</div>'+
            f'</div>'
        )

    # ── 2 sütunlu grid ───────────────────────────────────────────────────────
    for i in range(0, len(liste_df), 2):
        cols2 = st.columns(2, gap="medium")
        for j, col in enumerate(cols2):
            if i + j >= len(liste_df):
                break
            row = liste_df.iloc[i + j]
            link = str(row.get("startkey_url","") or "")
            with col:
                st.markdown(_pkart_html(row), unsafe_allow_html=True)
                _k1, _k2 = st.columns([4, 1])
                with _k1:
                    if link:
                        st.link_button(
                            "Startkey'de Gör →",
                            url=link,
                            use_container_width=True,
                            type="primary",
                        )
                with _k2:
                    portfoy_id = str(row.get("portfoy_id","") or "")
                    if st.button("⋯", key=f"pkart_more_{i}_{j}", use_container_width=True):
                        st.session_state[f"pkart_open_{i}_{j}"] = not st.session_state.get(f"pkart_open_{i}_{j}", False)
                        st.rerun()
                if st.session_state.get(f"pkart_open_{i}_{j}", False):
                    st.caption(f"Portföy No: {portfoy_id}")


# ── GÖRÜNÜM: TABLO ───────────────────────────────────────────────────────────
else:
    tablo_cols = {
        "ofis_label": "Ofis", "gd_adi": "Danışman",
        "baslik": "Başlık", "islem_tipi": "İşlem", "mulk_tipi": "Mülk",
        "il": "İl", "ilce": "İlçe", "mahalle": "Mahalle",
        "fiyat": "Fiyat", "oda_sayisi": "Oda",
        "brut_m2": "Brüt m²", "net_m2": "Net m²",
        "bulundugu_kat": "Kat", "bina_yasi": "Bina Yaşı",
        "asansor": "Asansör", "otopark": "Otopark",
        "guncelleme_tarihi": "Güncelleme", "startkey_url": "Link",
    }
    tablo_df = liste_df[[c for c in tablo_cols if c in liste_df.columns]].copy()
    tablo_df.rename(columns=tablo_cols, inplace=True)
    if "Fiyat" in tablo_df.columns:
        tablo_df["Fiyat"] = tablo_df["Fiyat"].apply(fiyat_formatla)
    if "Başlık" in tablo_df.columns:
        tablo_df["Başlık"] = tablo_df["Başlık"].apply(baslik_formatla)

    col_config = {}
    if "Link" in tablo_df.columns:
        col_config["Link"] = st.column_config.LinkColumn("Link", display_text="Startkey'de Gör")
    if "Başlık" in tablo_df.columns:
        col_config["Başlık"] = st.column_config.TextColumn("Başlık", width="large")
    if "Danışman" in tablo_df.columns:
        col_config["Danışman"] = st.column_config.TextColumn("Danışman", width="medium")

    st.dataframe(tablo_df, hide_index=True, use_container_width=True,
                 height=min(700, 55 + len(tablo_df) * 38),
                 column_config=col_config)


# ── ALT BAR ──────────────────────────────────────────────────────────────────
st.markdown("---")
alt1, alt2 = st.columns([4, 1])
with alt1:
    st.caption(f"Toplam {len(liste_df)} portföy gösteriliyor · Kaynak: startkey.com.tr")
with alt2:
    if st.button("✕ Filtreleri Temizle", key="zil_alt_temizle", use_container_width=True):
        for k in ["zil_ara", "zil_dan", "zil_ilce", "zil_mah", "zil_ofis"]:
            st.session_state.pop(k, None)
        st.rerun()

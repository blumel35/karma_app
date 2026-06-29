"""
pages/pazar_analiz.py
─────────────────────
Karma App — Pazar Analiz modülü
Revy.com.tr'den İzmir pazar verisi çeker, analiz eder.

Gerekli dosyalar (core/ klasöründe):
  core/revy_pazar_cek.py
  core/ofis_duzeltme.json
  core/izmir_mahalleler.json
  ayarlar.txt (karma_app kökünde)
"""

import streamlit as st
import sys, os, json, importlib
from pathlib import Path
from io import BytesIO
from datetime import datetime
import pandas as pd
import plotly.express as px
import html as _html
import streamlit.components.v1 as components

# Karma App kök dizinini path'e ekle
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "core"))

# ── Auth kontrolü ──────────────────────────────────────────────────────────────
from core.auth import oturum_kontrol
from core.ui_helpers import render_navbar, render_page_header

if not oturum_kontrol():
    st.switch_page("pages/giris.py")

_k = st.session_state.get("kullanici", {})
render_navbar(
    user_role=_k.get("rol", "danisan"),
    user_name=_k.get("ad_soyad") or _k.get("ad", ""),
)

render_page_header(
    "Pazar Radar",
    "İzmir gayrimenkul pazar verisi — ilçe, mülk ve marka bazlı analiz"
)

# ─────────────────────────────────────────
# SUPABASE & REVY HESAP YÖNETİMİ
# ─────────────────────────────────────────
def _supa():
    try:
        from supabase import create_client
        url = st.secrets.get("SUPABASE_URL","") or st.secrets.get("supabase",{}).get("url","")
        key = st.secrets.get("SUPABASE_KEY","") or st.secrets.get("supabase",{}).get("secret_key","") or st.secrets.get("supabase",{}).get("publishable_key","")
        if url and key:
            return create_client(url, key)
    except Exception:
        pass
    return None

def revy_kimlik_al() -> dict | None:
    """Secrets'tan Revy kimlik bilgilerini al."""
    try:
        rv = st.secrets.get("revy", {})
        if rv.get("kullanici") and rv.get("sifre"):
            return {
                "revy1_kullanici": rv["kullanici"],
                "revy1_sifre":     rv["sifre"],
                "revy_giris_url":  rv.get("giris_url","https://revy.com.tr"),
            }
    except Exception:
        pass
    # ayarlar.txt fallback
    try:
        import core.revy_pazar_cek as rpc
        return rpc.ayarlari_oku(ROOT / "ayarlar.txt")
    except Exception:
        pass
    return None

# ── Aramaları Supabase'e kaydet / yükle ───────────────────────────────────────
def arama_kaydet(isim: str, filtre: dict, ilan_df: pd.DataFrame | None = None) -> str | None:
    supa = _supa()
    if not supa: return None
    try:
        r = supa.table("pazar_aramalar").upsert({
            "kullanici_id": uid,
            "isim": isim,
            "filtre_json": json.dumps(filtre, ensure_ascii=False, default=str),
            "son_cekme_tarihi": datetime.now().isoformat(),
            "ilan_sayisi": len(ilan_df) if ilan_df is not None else 0,
        }).execute()
        arama_id = r.data[0]["id"] if r.data else None
        # İlanları kaydet
        if arama_id and ilan_df is not None and not ilan_df.empty:
            url_col = next((c for c in ilan_df.columns if "url" in c.lower()), None)
            baslik_col = "İlan Başlığı" if "İlan Başlığı" in ilan_df.columns else None
            fiyat_col  = "Fiyat" if "Fiyat" in ilan_df.columns else None
            kayitlar = []
            for _, row in ilan_df.iterrows():
                ilan_url = str(row.get(url_col,"")) if url_col else ""
                if not ilan_url or ilan_url in ("nan","None",""): continue
                fiyat_val = None
                if fiyat_col:
                    try:
                        fiyat_val = parse_num(row.get(fiyat_col))
                    except: fiyat_val = None
                kayitlar.append({
                    "arama_id": arama_id,
                    "ilan_url": ilan_url,
                    "ilan_baslik": str(row.get(baslik_col,""))[:200] if baslik_col else "",
                    "fiyat": fiyat_val,
                    "durum": "aktif",
                    "ilan_data": json.dumps(row.to_dict(), ensure_ascii=False, default=str),
                })
            if kayitlar:
                supa.table("pazar_ilanlar").upsert(kayitlar, on_conflict="arama_id,ilan_url").execute()
        return arama_id
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")
        return None

uid = _k.get("id","") or _k.get("user_key","")

def aramalarim_yukle() -> list:
    supa = _supa()
    if not supa or not uid: return []
    try:
        r = supa.table("pazar_aramalar").select("*").eq("kullanici_id", uid).order("son_cekme_tarihi", desc=True).limit(20).execute()
        return r.data or []
    except Exception:
        return []

# ─────────────────────────────────────────
# CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
:root {
    --bg:#F8F9FA; --card:#FFFFFF; --text:#0F172A; --muted:#64748B;
    --primary:#1e2d3d; --primary-hover:#2a3f56; --accent:#E87722;
    --success:#22C55E; --warning:#F59E0B; --border:#DCE4EE;
    --chip-bg:#EEF4FA; --hover-bg:#F8FBFF;
}
.stApp { background: var(--bg); }
.block-container { padding-top:0.8rem; padding-bottom:2rem; max-width:1520px; }

div[data-testid="stButton"] > button {
    white-space:normal; line-height:1.2; border-radius:8px;
    border:1px solid var(--border); min-height:34px; padding:6px 12px;
    font-size:12px; font-weight:600; background:var(--chip-bg); color:var(--text);
    transition:all 0.16s ease-in-out;
}
div[data-testid="stButton"] > button[kind="primary"] {
    background:var(--primary) !important; border-color:var(--primary) !important;
    color:#fff !important; box-shadow:0 2px 8px rgba(30,45,61,0.18) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover { background:var(--primary-hover) !important; }
div[data-baseweb="select"] > div { border-radius:8px !important; border-color:var(--border) !important; min-height:34px !important; }
input { border-radius:8px !important; }

/* Multiselect tag - sade gri/mavi */
span[data-baseweb="tag"] {
    background-color: var(--chip-bg) !important;
    color: var(--primary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
}
span[data-baseweb="tag"] svg { fill: var(--primary) !important; }



.filtre-panel {
    background:white; border:1px solid var(--border);
    border-radius:12px; padding:16px 20px; margin-bottom:14px;
}
.filtre-baslik {
    font-size:11px; font-weight:800; color:var(--muted);
    text-transform:uppercase; letter-spacing:0.8px;
    margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid var(--border);
}
.filtre-grup-baslik {
    font-size:10px; font-weight:800; color:var(--primary);
    text-transform:uppercase; letter-spacing:0.08em;
    margin:0.2rem 0 0.5rem 0;
}
hr.filtre-ayrac {
    border:none; border-top:1px solid #E2E8F0;
    margin:0.6rem 0 0.8rem 0;
}
[data-testid="stExpander"] > div:last-child {
    padding:1rem 1.2rem 0.5rem 1.2rem !important;
}
.section-title {
    font-size:11px; font-weight:800; color:var(--muted);
    text-transform:uppercase; letter-spacing:0.6px;
    margin:14px 0 8px 0; padding-bottom:5px; border-bottom:2px solid var(--border);
}
.kpi-card {
    background:white; border:1px solid var(--border);
    border-radius:10px; padding:12px 16px;
    box-shadow:0 2px 6px rgba(15,23,42,0.04);
}
.kpi-label { font-size:10px; font-weight:700; color:var(--muted); text-transform:uppercase; letter-spacing:0.8px; margin-bottom:4px; }
.kpi-value { font-size:1.6rem; font-weight:800; color:var(--text); line-height:1.1; }
.kpi-sub   { font-size:11px; color:var(--muted); margin-top:2px; }
.kpi-blue  { color:var(--primary) !important; }
.kpi-green { color:var(--success) !important; }
.kpi-amber { color:var(--warning) !important; }
.kpi-red   { color:var(--accent) !important; }

.durum-banner {
    background:#EEF4FA; border:1px solid #C8D7E5; border-radius:10px;
    padding:12px 20px; margin:10px 0; color:var(--primary);
    font-size:13px; font-weight:600; text-align:center;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# VERİ
# ─────────────────────────────────────────
@st.cache_data
def mahalle_yukle():
    yol = Path(__file__).parent.parent / "core" / "izmir_mahalleler.json"
    if yol.exists():
        return json.load(open(yol, encoding="utf-8"))
    return {}

@st.cache_data
def ofis_duzeltme_yukle():
    yol = Path(__file__).parent.parent / "core" / "ofis_duzeltme.json"
    if yol.exists():
        return json.load(open(yol, encoding="utf-8"))
    return {}

MAHALLELER = mahalle_yukle()
OFIS_DUZELTME = ofis_duzeltme_yukle()
IZMIR_ILCELER = sorted(MAHALLELER.keys()) if MAHALLELER else [
    "Aliağa","Balçova","Bayındır","Bayraklı","Bergama","Beydağ","Bornova","Buca",
    "Çeşme","Çiğli","Dikili","Foça","Gaziemir","Güzelbahçe","Karabağlar",
    "Karaburun","Karşıyaka","Kemalpaşa","Kınık","Kiraz","Konak","Menderes",
    "Menemen","Narlıdere","Ödemiş","Seferihisar","Selçuk","Tire","Torbalı","Urla"
]

MULK_SEC  = {"Konut":"konut","Ticari":"ticari","Arsa":"arsa"}
ISLEM_SEC = {"Satılık":"satilik","Kiralık":"kiralik"}
DURUM_SEC = {"Aktif İlanlar":"aktif","Yayından Kalkanlar":"yayindan_kalkan"}

MARKA_RENK = {
    "startkey":"#355C7D","remax":"#E85D75","turpa":"#F59E0B",
    "turyap":"#8B5CF6","coldwell":"#06B6D4","kw":"#10B981",
    "alesta":"#F97316","viya":"#EC4899","orsa":"#84CC16",
    "century21":"#6366F1","bagimsiz":"#94A3B8","mulk_sahibi":"#CBD5E1",
}

MARKA_ETIKET = {"bagimsiz": "Yerel Ofis", "mulk_sahibi": "Mülk Sahibi"}
def marka_etiket(m):
    return MARKA_ETIKET.get(m, m.upper())

def parse_num(v):
    try: return float(str(v).replace(".","").replace(",",".").replace("₺","").replace("TL","").strip())
    except: return None

import re as _re
def ad_normalize(v):
    """Ofis / GD adlarını karşılaştırma için normalize eder: Türkçe İ/ı varyasyonları,
    baş/son boşluk, fazla boşluk ve büyük/küçük harf farklarını eşitler.
    'Dialog Tower' ve 'DİALOG TOWER' aynı gruba düşer."""
    if pd.isna(v): return None
    s = str(v).strip()
    if not s: return None
    s = s.replace("İ","I").replace("ı","i")
    s = _re.sub(r"\s+", " ", s)
    return s.upper()

def ofis_duzelt(v):
    """ad_normalize sonrası, revy_ofis_adi_duzeltme.xlsx'ten gelen manuel eşleme tablosuyla
    yazım/şube-isim farklılıklarını standart ofis adına çevirir."""
    n = ad_normalize(v)
    if n is None: return None
    return OFIS_DUZELTME.get(n, n)

for k,v in [("pazar_veri",{}),("pazar_filtre",{}),("pazar_last_filtre",{})]:
    if k not in st.session_state: st.session_state[k] = v

# Ofis / GD filtre seçenekleri — daha önce çekilmiş veriden (varsa) çıkar
_pv = st.session_state.get("pazar_veri") or {}
_df_onizleme = pd.concat([v for v in _pv.values() if not v.empty], ignore_index=True) if _pv else pd.DataFrame()
OFIS_OPTS = sorted({n for n in _df_onizleme.get("Ofis", pd.Series(dtype=object)).apply(ofis_duzelt) if n}) if not _df_onizleme.empty else []
GD_OPTS   = sorted({n for n in _df_onizleme.get("İlan sahibi", pd.Series(dtype=object)).apply(ad_normalize) if n}) if not _df_onizleme.empty else []


# ─────────────────────────────────────────
# FİLTRE PANELİ — tek panel
# ─────────────────────────────────────────
# ─────────────────────────────────────────
# FİLTRE PANELİ — accordion gruplar
# ─────────────────────────────────────────
from datetime import date, timedelta as _td

# ── Kaydedilen arama yüklenecekse widget'lardan ÖNCE session_state'e yaz ──
if st.session_state.get("_pz_yukle_bekliyor"):
    _yf = st.session_state.pop("_pz_yukle_bekliyor")
    if "ilce" in _yf:
        st.session_state["pz_ilce"] = _yf["ilce"]
    if "mulk" in _yf:
        _mulk_ters = {v:k for k,v in MULK_SEC.items()}
        st.session_state["pz_mulk"] = [_mulk_ters.get(m,m) for m in _yf["mulk"]]
    if "islem" in _yf:
        _islem_ters = {v:k for k,v in ISLEM_SEC.items()}
        st.session_state["pz_islem"] = [_islem_ters.get(i,i) for i in _yf["islem"]]
    if "durum" in _yf:
        _durum_ters = {v:k for k,v in DURUM_SEC.items()}
        st.session_state["pz_durum"] = [_durum_ters.get(d,d) for d in _yf["durum"]]
    if "mahalle" in _yf:
        st.session_state["pz_mah"] = _yf["mahalle"]
    for _key in ["pz_ofis_filtre","pz_gd_filtre","pz_oda","pz_kat","pz_yas"]:
        st.session_state[_key] = []

with st.expander("🔍 Pazar Filtresi", expanded=True):

    # ── GRUP 1: KONUM ──
    st.markdown('<div class="filtre-grup-baslik">📍 Konum</div>', unsafe_allow_html=True)
    g1a, g1b = st.columns([2, 3])
    with g1a:
        secili_ilceler = st.multiselect("İlçe", IZMIR_ILCELER,
            placeholder="İlçe seçin...", key="pz_ilce")
    with g1b:
        mah_opts = []
        for ilce in secili_ilceler:
            mah_opts.extend(MAHALLELER.get(ilce, []))
        mah_opts = sorted(set(mah_opts))
        secili_mahalleler = st.multiselect("Mahalle", mah_opts,
            placeholder="Tümü (opsiyonel)", key="pz_mah")

    st.markdown('<hr class="filtre-ayrac">', unsafe_allow_html=True)

    # ── GRUP 2: İLAN ÖZELLİKLERİ ──
    st.markdown('<div class="filtre-grup-baslik">📋 İlan Özellikleri</div>', unsafe_allow_html=True)
    g2a, g2b, g2c, g2d = st.columns([1.5, 1.5, 1.5, 1.5])
    with g2a:
        secili_islemler = st.multiselect("İşlem Tipi", list(ISLEM_SEC.keys()),
            default=["Satılık","Kiralık"], key="pz_islem")
    with g2b:
        secili_mulkler = st.multiselect("Mülk Tipi", list(MULK_SEC.keys()),
            default=["Konut","Ticari","Arsa"], key="pz_mulk")
    with g2c:
        MULK_TURU_FILTRE_OPTS = [
            "Daire","Apartman Dairesi","Konut","Toplu Konut","Ticari Konut",
            "Villa","Müstakil Ev","Bina","Komple Bina",
            "Dükkan & Mağaza","Büro & Ofis","Depo & Antrepo",
            "Fabrika","Büfe","Restoran & Lokanta","Pazar Yeri",
            "Tarla","Arazi","Bağ","Zeytinlik","Diğer",
        ]
        mulk_turu_filtre2 = st.multiselect("Mülk Türü", MULK_TURU_FILTRE_OPTS,
            placeholder="Tümü", key="pz_mulk_turu2")
    with g2d:
        secili_durumlar = st.multiselect("İlan Durumu", list(DURUM_SEC.keys()),
            default=["Aktif İlanlar"], key="pz_durum")

    # ── Dinamik Tarih Filtreleri (duruma göre) ──
    aktif_sec = "Aktif İlanlar" in secili_durumlar
    pasif_sec = "Yayından Kalkanlar" in secili_durumlar

    if aktif_sec or pasif_sec:
        st.markdown('<div style="margin-top:8px;"></div>', unsafe_allow_html=True)
        tarih_cols = st.columns([2, 2, 2])

        with tarih_cols[0]:
            if aktif_sec or pasif_sec:
                ilan_giris_tarihi = st.date_input(
                    "İlan Giriş Tarihi" + (" (Aktif + Pasif)" if aktif_sec and pasif_sec else " (Aktif)" if aktif_sec else " (Pasif)"),
                    value=[], format="DD.MM.YYYY", key="pz_giris_tarihi")
                if isinstance(ilan_giris_tarihi, (list, tuple)) and len(ilan_giris_tarihi) == 2:
                    bas_tarih, bit_tarih = ilan_giris_tarihi[0], ilan_giris_tarihi[1]
                else:
                    bas_tarih, bit_tarih = None, None
            else:
                bas_tarih, bit_tarih = None, None

        with tarih_cols[1]:
            if pasif_sec:
                KALKMA_OPTS = {
                    "Tümü": None,
                    "Son 1 hafta": 7,
                    "Son 1 ay": 30,
                    "Son 2 ay": 60,
                    "Son 3 ay": 90,
                    "Son 6 ay": 180,
                    "Son 12 ay": 365,
                }
                kalkma_sec = st.selectbox("İlandan Kalkma Tarihi",
                    list(KALKMA_OPTS.keys()), key="pz_kalkma_tarihi")
                kalkma_gun = KALKMA_OPTS[kalkma_sec]
            else:
                kalkma_gun = None
    else:
        bas_tarih, bit_tarih, kalkma_gun = None, None, None

    st.markdown('<hr class="filtre-ayrac">', unsafe_allow_html=True)

    # ── GRUP 3: GELİŞMİŞ ──
    st.markdown('<div class="filtre-grup-baslik">⚙️ Gelişmiş</div>', unsafe_allow_html=True)
    g3a, g3b, g3c, g3d = st.columns([1.5, 1.5, 1.5, 1.5])
    with g3a:
        secili_markalar = st.multiselect("Marka", ["Tümü"] + sorted(MARKA_RENK.keys()),
            default=["Tümü"], format_func=lambda x: x if x=="Tümü" else marka_etiket(x),
            key="pz_marka")
    with g3b:
        secili_ofisler = st.multiselect("Ofis", OFIS_OPTS,
            placeholder="Tümü (veri çekildikten sonra dolar)", key="pz_ofis_filtre")
    with g3c:
        secili_gdler = st.multiselect("GD Adı", GD_OPTS,
            placeholder="Tümü (veri çekildikten sonra dolar)", key="pz_gd_filtre")
    with g3d:
        oda_filtre = st.multiselect("Oda", ["1+0","1+1","2+1","2+2","3+1","3+2","4+1","4+2","5+1","5+2","6+"],
            placeholder="Tümü", key="pz_oda")

    g4a, g4b, g4c, g4d = st.columns([1.5, 1.5, 1.5, 1.5])
    with g4a:
        kat_filtre = st.multiselect("Kat", ["Zemin","Bahçe Katı","1. Kat","2. Kat","3. Kat","4. Kat",
            "5. Kat","Yüksek Giriş","Müstakil","30 üstü"], placeholder="Tümü", key="pz_kat")
    with g4b:
        yas_filtre = st.multiselect("Bina Yaşı", ["0","1","2","3","4","5","6-10","11-15","16-20","21-25","26-30","30 üstü"],
            placeholder="Tümü", key="pz_yas")
    with g4c:
        kullanim_filtre = st.multiselect("Kullanım Durumu", ["Boş","Kiracılı","Mülk Sahibi"],
            placeholder="Tümü", key="pz_kullanim")

    g5a, g5b, g5c, g5d, g5e = st.columns([1.5, 1.5, 1, 1, 1])
    with g5a:
        m2_min = st.number_input("M² Alt", min_value=0, value=0, step=10, key="pz_m2_min")
    with g5b:
        m2_max = st.number_input("M² Üst", min_value=0, value=0, step=10, key="pz_m2_max")
    with g5c:
        fiyat_min = st.number_input("Fiyat Alt (₺M)", min_value=0.0, value=0.0, step=0.5,
            format="%.1f", key="pz_fiyat_min")
    with g5d:
        esyali_filtre = st.selectbox("Eşyalı", ["Tümü","Evet","Hayır"], key="pz_esyali")
    with g5e:
        site_filtre = st.selectbox("Site İçi", ["Tümü","Evet","Hayır"], key="pz_site")

    ILAN_KAYNAK_OPTS = [
        "Sahibinden.com","Hepsi Emlak","Emlakjet","Zingat",
        "Revy","Diğer",
    ]
    kaynak_filtre = st.multiselect("İlan Kaynağı", ILAN_KAYNAK_OPTS,
        placeholder="Tümü", key="pz_kaynak")

# ── KAYDEDİLEN ARAMALARIM PANELİ ──────────────────────────────────────────────
_aramalar = aramalarim_yukle()
if _aramalar:
    with st.expander(f"📋 Kaydedilen Aramalarım ({len(_aramalar)})", expanded=False):
        for _a in _aramalar:
            tarih_str = ""
            try:
                tarih_str = datetime.fromisoformat(_a["son_cekme_tarihi"]).strftime("%d.%m.%Y %H:%M")
            except Exception:
                pass
            ac1, ac2, ac3, ac4, ac5 = st.columns([3, 1, 1.5, 1, 1])
            with ac1:
                st.markdown(
                    f'<div style="font-size:13px;font-weight:600;color:#1e293b;padding:6px 0;">'
                    f'{_a["isim"]}</div>',
                    unsafe_allow_html=True)
            with ac2:
                st.markdown(
                    f'<div style="font-size:12px;color:#64748b;padding:6px 0;">'
                    f'{_a["ilan_sayisi"]} ilan</div>',
                    unsafe_allow_html=True)
            with ac3:
                st.markdown(
                    f'<div style="font-size:11px;color:#94a3b8;padding:6px 0;">'
                    f'🕐 {tarih_str}</div>',
                    unsafe_allow_html=True)
            with ac4:
                if st.button("📂 Yükle", key=f"yukle_{_a['id']}", use_container_width=True):
                    try:
                        _f = json.loads(_a["filtre_json"])
                        st.session_state["_pz_yukle_bekliyor"] = _f
                        st.toast(f"'{_a['isim']}' filtresi yüklendi — Listele'ye basın ✓")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Filtre yüklenemedi: {e}")
            with ac5:
                if st.button("🗑", key=f"sil_{_a['id']}", use_container_width=True,
                             help="Bu aramayı sil"):
                    try:
                        _supa_inst = _supa()
                        if _supa_inst:
                            _supa_inst.table("pazar_aramalar").delete().eq("id", _a["id"]).execute()
                            st.toast(f"'{_a['isim']}' silindi ✓")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Silme hatası: {e}")
            st.divider()

# ── AKSİYON ÇUBUĞU ──────────────────────────────────────────────────────────
ak1, ak2 = st.columns([1, 1])
with ak1:
    kaydet_btn = st.button("💾 Aramayı Kaydet", use_container_width=True, key="pz_kaydet_arama",
        disabled=not bool(st.session_state.get("pazar_veri")))
with ak2:
    listele_btn = st.button("🔍 Listele", type="primary", use_container_width=True, key="pz_listele")

# ── Aramayı Kaydet dialog ──────────────────────────────────────────────────────
if kaydet_btn:
    @st.dialog("💾 Aramayı Kaydet")
    def kaydet_dialog():
        isim = st.text_input("Arama adı", placeholder="örn: Ayşe Hanım - Karşıyaka 2+1 Kiralık")
        _df_kayit = st.session_state.get("pazar_df_filtrelenmis", pd.DataFrame())
        st.caption(f"{len(_df_kayit):,} ilan kaydedilecek (ekranda gösterilen)")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 Kaydet", type="primary", use_container_width=True):
                if not isim.strip():
                    st.error("Arama adı zorunlu.")
                else:
                    _filtre = st.session_state.get("pazar_last_filtre", {})
                    _filtre["mahalle"] = st.session_state.pazar_filtre.get("mahalle", [])
                    _id = arama_kaydet(isim.strip(), _filtre, _df_kayit)
                    if _id:
                        st.success(f"✅ '{isim}' kaydedildi!")
                        st.rerun()
        with c2:
            if st.button("İptal", use_container_width=True):
                st.rerun()
    kaydet_dialog()

# ─────────────────────────────────────────
# VERİ ÇEKME
# ─────────────────────────────────────────
if listele_btn:
    if not secili_ilceler:
        st.error("En az bir ilçe seçin.")
    elif not secili_mulkler or not secili_islemler or not secili_durumlar:
        st.error("Mülk, işlem ve durum seçimi zorunlu.")
    else:
        # Revy'ye gönderilecek filtre (mahalle YOK — lokal filtre)
        filtre_dict = {
            "ilce":  secili_ilceler,
            "mulk":  [MULK_SEC[m] for m in secili_mulkler],
            "islem": [ISLEM_SEC[i] for i in secili_islemler],
            "durum": [DURUM_SEC[d] for d in secili_durumlar],
        }
        if bas_tarih: filtre_dict["baslangic"] = bas_tarih.strftime("%Y-%m-%d")
        if bit_tarih: filtre_dict["bitis"] = bit_tarih.strftime("%Y-%m-%d")

        lokal_filtre = {"mahalle": secili_mahalleler}

        # Aynı veri-çekme filtresiyle daha önce çekildiyse, Revy'ye tekrar gitme.
        _last = st.session_state.get("pazar_last_filtre", {})
        def _filtre_esit(a, b):
            return (sorted(a.get("ilce",[])) == sorted(b.get("ilce",[]))
                and sorted(a.get("mulk",[])) == sorted(b.get("mulk",[]))
                and sorted(a.get("islem",[])) == sorted(b.get("islem",[]))
                and sorted(a.get("durum",[])) == sorted(b.get("durum",[]))
                and a.get("baslangic") == b.get("baslangic")
                and a.get("bitis") == b.get("bitis"))

        ayni_filtre = bool(st.session_state.get("pazar_veri")) and _filtre_esit(_last, filtre_dict)
        if ayni_filtre:
            st.session_state.pazar_filtre = lokal_filtre
            st.rerun()

        durum_placeholder = st.empty()

        def progress_cb(msg):
            durum_placeholder.markdown(
                '<div class="durum-banner">🔄 İşleminiz devam ediyor, lütfen bekleyiniz...</div>',
                unsafe_allow_html=True)

        try:
            import core.revy_pazar_cek as rpc
            importlib.reload(rpc)

            ayarlar = revy_kimlik_al()
            if not ayarlar:
                durum_placeholder.error("❌ Revy hesabınız bağlı değil. Lütfen sayfanın üstünden Revy hesabınızı bağlayın.")
                st.stop()

            progress_cb("🌐 Revy'ye bağlanılıyor...")

            cookies = rpc.selenium_cookie_al(
                kullanici=ayarlar["revy1_kullanici"],
                sifre=ayarlar["revy1_sifre"],
                giris_url=ayarlar.get("revy_giris_url","https://revy.com.tr"),
                headless=True,
                progress_cb=progress_cb,
            )

            cikti = rpc.pazar_cek(
                cookies, filtre_dict,
                cikti_klasor=Path(__file__).parent.parent / "revy_pazar_cikti",
                progress_cb=progress_cb,
            )

            st.session_state.pazar_veri = cikti
            st.session_state.pazar_filtre = lokal_filtre
            st.session_state.pazar_last_filtre = filtre_dict
            durum_placeholder.success(f"✅ Veri hazır! {sum(len(v) for v in cikti.values()):,} kayıt")
            st.rerun()

        except Exception as e:
            durum_placeholder.error(f"Hata: {e}")

# ─────────────────────────────────────────
# ANALİZ
# ─────────────────────────────────────────
pazar_veri = st.session_state.pazar_veri
if not pazar_veri:
    st.markdown("""
    <div style="text-align:center;padding:50px 20px;color:#64748b;">
        <div style="font-size:2.5rem;margin-bottom:12px;">🏙️</div>
        <div style="font-size:1rem;font-weight:600;margin-bottom:6px;">Filtreleri seçin ve Listele'ye basın</div>
        <div style="font-size:12px;">Revy'den otomatik veri çekilecek ve burada analiz edilecek</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

df = pd.concat([v for v in pazar_veri.values() if not v.empty], ignore_index=True) if pazar_veri else pd.DataFrame()
if df.empty:
    st.info("Seçilen filtrelere uygun kayıt bulunamadı.")
    st.stop()

secili_mah = st.session_state.pazar_filtre.get("mahalle", [])
if secili_mah and "Mahalle" in df.columns:
    df = df[df["Mahalle"].isin(secili_mah)]
if "Tümü" not in secili_markalar and "MARKA" in df.columns:
    df = df[df["MARKA"].isin(secili_markalar)]
if secili_ofisler and "Ofis" in df.columns:
    df = df[df["Ofis"].apply(ofis_duzelt).isin(secili_ofisler)]
if secili_gdler and "İlan sahibi" in df.columns:
    df = df[df["İlan sahibi"].apply(ad_normalize).isin(secili_gdler)]
if mulk_turu_filtre2 and "Mülk türü" in df.columns:
    df = df[df["Mülk türü"].isin(mulk_turu_filtre2)]

# İlandan Kalkma Tarihi lokal filtresi (pasif ilanlar için)
if kalkma_gun and "Yayından Kalkış Tarihi" in df.columns:
    from datetime import datetime as _dt2
    _kalkma_bas = pd.Timestamp(_dt2.now()) - pd.Timedelta(days=kalkma_gun)
    df = df[df["Yayından Kalkış Tarihi"] >= _kalkma_bas]
if kaynak_filtre and "İlan Kaynağı" in df.columns:
    df = df[df["İlan Kaynağı"].isin(kaynak_filtre)]
if oda_filtre and "Oda sayısı" in df.columns:
    df = df[df["Oda sayısı"].isin(oda_filtre)]
if kat_filtre and "Bulunduğu kat" in df.columns:
    df = df[df["Bulunduğu kat"].isin(kat_filtre)]
if yas_filtre and "Bina Yaşı" in df.columns:
    df = df[df["Bina Yaşı"].astype(str).isin(yas_filtre)]
if kullanim_filtre and "Kullanım Durumu" in df.columns:
    df = df[df["Kullanım Durumu"].isin(kullanim_filtre)]
if esyali_filtre != "Tümü" and "Eşyalı" in df.columns:
    hedef = "evet" if esyali_filtre == "Evet" else "hayır"
    df = df[df["Eşyalı"].astype(str).str.lower().str.strip() == hedef]
if site_filtre != "Tümü" and "Site içerisinde" in df.columns:
    hedef = "evet" if site_filtre == "Evet" else "hayır"
    df = df[df["Site içerisinde"].astype(str).str.lower().str.strip() == hedef]
if m2_min > 0 and "M2" in df.columns:
    df = df[pd.to_numeric(df["M2"], errors="coerce").fillna(0) >= m2_min]
if m2_max > 0 and "M2" in df.columns:
    df = df[pd.to_numeric(df["M2"], errors="coerce").fillna(99999) <= m2_max]
if fiyat_min > 0 and "Fiyat" in df.columns:
    df = df[df["Fiyat"].apply(lambda v: parse_num(v) or 0) >= fiyat_min * 1_000_000]

# Filtrelenmiş df'i kaydet butonu için session_state'e al
st.session_state["pazar_df_filtrelenmis"] = df
toplam = len(df)

# ── MÜKERRER İLAN TESPİTİ ──────────────────────────────────────────────────
# Aynı Fiyat + M2 + Mahalle kombinasyonu → muhtemel mükerrer
if all(c in df.columns for c in ["Fiyat","M2","Mahalle"]):
    df["_dupe_key"] = (df["Fiyat"].astype(str) + "_" +
                       df["M2"].astype(str) + "_" +
                       df["Mahalle"].astype(str))
    dupe_keys = df["_dupe_key"][df["_dupe_key"].duplicated(keep=False)]
    df["_is_dupe"] = df["_dupe_key"].isin(dupe_keys)
    dupe_sayisi = df["_is_dupe"].sum()
    # İstatistikler için tekilleştirilmiş df (her mükerrer gruptan ilk kayıt)
    df_tekil = df.drop_duplicates(subset=["_dupe_key"]).copy()
else:
    df["_is_dupe"] = False
    df_tekil = df.copy()
    dupe_sayisi = 0
sk_n   = len(df[df["MARKA"]=="startkey"]) if "MARKA" in df.columns else 0
rakip_n = len(df[df["MARKA"].isin([m for m in MARKA_RENK if m not in ("startkey","bagimsiz","mulk_sahibi")])]) if "MARKA" in df.columns else 0
bag_n  = len(df[df["MARKA"]=="bagimsiz"]) if "MARKA" in df.columns else 0
mulk_n = len(df[df["MARKA"]=="mulk_sahibi"]) if "MARKA" in df.columns else 0

k1,k2,k3,k4,k5 = st.columns(5)
for col, lbl, val, sub, cls in [
    (k1,"Toplam İlan", toplam,
        f"tüm kayıtlar · <span style='color:#f59e0b;font-weight:700;'>🔁 {dupe_sayisi} mükerrer</span>" if dupe_sayisi > 0 else "tüm kayıtlar",
        "kpi-blue"),
    (k2,"Startkey", sk_n, f"%{sk_n/toplam*100:.1f} pazar payı" if toplam else "-","kpi-blue"),
    (k3,"Diğer Kurumsal", rakip_n, f"%{rakip_n/toplam*100:.1f} pazar payı" if toplam else "-","kpi-amber"),
    (k4,"Yerel Ofis", bag_n, f"%{bag_n/toplam*100:.1f} pazar payı" if toplam else "-","kpi-green"),
    (k5,"Mülk Sahibi", mulk_n, f"%{mulk_n/toplam*100:.1f} pazar payı" if toplam else "-","kpi-amber"),
]:
    with col:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">{lbl}</div>
            <div class="kpi-value {cls}">{val:,}</div>
            <div class="kpi-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)

with st.expander("📊 İstatistikler ve Grafikler", expanded=False):
    g1, g2 = st.columns(2)
    with g1:
        st.markdown('<div class="section-title">Marka Dağılımı</div>', unsafe_allow_html=True)
        if "MARKA" in df.columns:
            mdf = df["MARKA"].value_counts().reset_index()
            mdf.columns = ["Marka","Kayıt"]
            mdf["Marka_etiket"] = mdf["Marka"].apply(marka_etiket)
            fig = px.bar(mdf, x="Kayıt", y="Marka_etiket", orientation="h",
                color="Marka", color_discrete_map={r["Marka"]: MARKA_RENK.get(r["Marka"],"#94A3B8") for _,r in mdf.iterrows()},
                text="Kayıt")
            fig.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=0,r=10,t=5,b=0), height=180,
                yaxis=dict(categoryorder="total ascending", title=""), font=dict(size=10))
            fig.update_traces(textposition="outside", textfont_size=9)
            st.plotly_chart(fig, use_container_width=True)

    with g2:
        st.markdown('<div class="section-title">İlçe Dağılımı</div>', unsafe_allow_html=True)
        if "İlçe" in df.columns:
            idf = df["İlçe"].value_counts().head(12).reset_index()
            idf.columns = ["İlçe","Kayıt"]
            fig2 = px.bar(idf, x="Kayıt", y="İlçe", orientation="h",
                color_discrete_sequence=["#355C7D"], text="Kayıt")
            fig2.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=0,r=10,t=5,b=0), height=180,
                yaxis=dict(categoryorder="total ascending"), font=dict(size=10))
            fig2.update_traces(textposition="outside", textfont_size=9)
            st.plotly_chart(fig2, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── PAZAR İSTATİSTİKLERİ ──
with st.expander("📈 Pazar İstatistikleri (filtrelenmiş veriye göre)", expanded=False):
    if len(df) == 0:
        st.caption("Gösterilecek veri yok — filtreleri genişletin.")
    else:
        if dupe_sayisi > 0:
            st.caption(f"📊 İstatistikler **{len(df_tekil):,} tekil ilan** üzerinden hesaplanmaktadır ({dupe_sayisi} mükerrer tekilleştirildi).")
        df_num = df_tekil.copy()
        df_num["__fiyat"] = df_num.get("Fiyat", pd.Series(dtype=float)).apply(lambda v: parse_num(v))
        df_num["__m2"] = pd.to_numeric(df_num.get("M2", pd.Series(dtype=float)), errors="coerce")
        df_num["__birim"] = df_num["__fiyat"] / df_num["__m2"].replace(0, pd.NA)
        df_num["__sure"] = pd.to_numeric(df_num.get("İlan Yayın Süresi", pd.Series(dtype=float)), errors="coerce")

        ort_m2    = df_num["__m2"].mean()
        ort_fiyat = df_num["__fiyat"].mean()
        ort_birim = df_num["__birim"].mean()
        ort_sure  = df_num["__sure"].mean()
        ref_100m2 = ort_birim * 100 if pd.notna(ort_birim) else None

        yeni_orani = None
        if "Bina Yaşı" in df.columns and len(df):
            yas_str = df["Bina Yaşı"].astype(str).str.strip()
            yeni_orani = yas_str.isin(["0","1-5","6-10"]).mean() * 100

        i1,i2,i3,i4 = st.columns(4)
        with i1:
            val = f"{ref_100m2:,.0f} ₺".replace(",",".") if ref_100m2 else "-"
            st.markdown(f"""<div class="kpi-card"><div class="kpi-label">100 m² Referans Fiyatı</div>
                <div class="kpi-value kpi-blue">{val}</div>
                <div class="kpi-sub">ort. m² fiyatı × 100</div></div>""", unsafe_allow_html=True)
        with i2:
            val2 = f"{ort_birim:,.0f} ₺".replace(",",".") if pd.notna(ort_birim) else "-"
            st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Ort. m² Fiyatı</div>
                <div class="kpi-value kpi-blue">{val2}</div>
                <div class="kpi-sub">birim fiyat</div></div>""", unsafe_allow_html=True)
        with i3:
            val3 = f"%{yeni_orani:.0f}" if yeni_orani is not None else "-"
            st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Yeni Bina Oranı</div>
                <div class="kpi-value kpi-green">{val3}</div>
                <div class="kpi-sub">0-10 yaş</div></div>""", unsafe_allow_html=True)
        with i4:
            val4 = f"{ort_sure:,.0f}".replace(",",".") if pd.notna(ort_sure) else "-"
            st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Ort. İlan Süresi</div>
                <div class="kpi-value kpi-amber">{val4}</div>
                <div class="kpi-sub">gün</div></div>""", unsafe_allow_html=True)

        # ── DOM SEGMENTASYONu — Reel Piyasa Analizi ──────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">🎯 Reel Piyasa Analizi — İlan Süresi Segmentasyonu</div>', unsafe_allow_html=True)
        st.caption("İlandaki gün sayısına göre gruplar — 31-60 gün penceresi genellikle en gerçekçi piyasa fiyatını yansıtır.")

        if df_num["__sure"].notna().any():
            dom_bins   = [0, 30, 60, 90, 180, float("inf")]
            dom_labels = ["0-30 gün 🟢", "31-60 gün 🟡", "61-90 gün 🟠", "91-180 gün 🔴", "180+ gün ⚫"]
            df_num["__dom_seg"] = pd.cut(df_num["__sure"], bins=dom_bins, labels=dom_labels, right=True)

            dom_grp = df_num.groupby("__dom_seg", observed=True).agg(
                Adet=("__birim","count"),
                Ort_m2=("__m2","mean"),
                Ort_Fiyat=("__fiyat","mean"),
                Ort_m2_Fiyat=("__birim","mean"),
            ).reset_index().rename(columns={"__dom_seg":"İlan Süresi"})
            dom_grp["Ref_100m2"] = dom_grp["Ort_m2_Fiyat"] * 100
            dom_grp = dom_grp[dom_grp["Adet"] > 0]
            dom_grp["Ort_m2"]      = dom_grp["Ort_m2"].round(0)
            dom_grp["Ort_Fiyat"]   = dom_grp["Ort_Fiyat"].round(0)
            dom_grp["Ort_m2_Fiyat"]= dom_grp["Ort_m2_Fiyat"].round(0)
            dom_grp["Ref_100m2"]   = dom_grp["Ref_100m2"].round(0)

            st.dataframe(dom_grp, use_container_width=True, hide_index=True,
                column_config={
                    "İlan Süresi":   st.column_config.TextColumn("İlan Süresi"),
                    "Adet":          st.column_config.NumberColumn("Adet", format="%d"),
                    "Ort_m2":        st.column_config.NumberColumn("Ort. M²", format="%.0f m²"),
                    "Ort_Fiyat":     st.column_config.NumberColumn("Ort. Fiyat", format="%.0f ₺"),
                    "Ort_m2_Fiyat":  st.column_config.NumberColumn("Ort. m² Fiyatı", format="%.0f ₺"),
                    "Ref_100m2":     st.column_config.NumberColumn("100 m² Ref. Fiyatı", format="%.0f ₺"),
                })

            # En aktif segmentin (31-60 gün) referans fiyatını öne çıkar
            _aktif = dom_grp[dom_grp["İlan Süresi"] == "31-60 gün 🟡"]
            if not _aktif.empty:
                _aktif_fiyat = _aktif.iloc[0]["Ref_100m2"]
                _aktif_adet  = _aktif.iloc[0]["Adet"]
                st.info(
                    f"**Aktif Satış Penceresi (31-60 gün):** {_aktif_adet} ilan — "
                    f"100 m² referans fiyatı **{_aktif_fiyat:,.0f} ₺**".replace(",",".")
                )
        else:
            st.caption("İlan süresi verisi mevcut değil.")

        # ── BİNA YAŞI ANALİZİ ────────────────────────────────────────────────────
        if "Bina Yaşı" in df.columns and df_num["__birim"].notna().any():
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="section-title">🏗 Yeni / Eski Bina Fiyat Analizi</div>', unsafe_allow_html=True)

            YAS_GRUPLARI = {
                "Yeni (0-5 yıl)":  ["0","1","2","3","4","5"],
                "Genç (6-15 yıl)": ["6-10","11-15"],
                "Orta (16-25 yıl)":["16-20","21-25"],
                "Eski (26+ yıl)":  ["26-30","30 üstü"],
            }
            def yas_grup(v):
                s = str(v).strip()
                for grup, vals in YAS_GRUPLARI.items():
                    if s in vals: return grup
                return None

            df_num["__yas_grp"] = df_num["Bina Yaşı"].apply(yas_grup)
            yas_grp_df = df_num[df_num["__yas_grp"].notna()].groupby("__yas_grp").agg(
                Adet=("__birim","count"),
                Ort_m2=("__m2","mean"),
                Ort_Fiyat=("__fiyat","mean"),
                Ort_m2_Fiyat=("__birim","mean"),
            ).reset_index().rename(columns={"__yas_grp":"Bina Yaşı Grubu"})
            yas_grp_df["Ref_100m2"] = yas_grp_df["Ort_m2_Fiyat"] * 100
            # Sırala
            yas_sirasi = list(YAS_GRUPLARI.keys())
            yas_grp_df["_sira"] = yas_grp_df["Bina Yaşı Grubu"].map({v:i for i,v in enumerate(yas_sirasi)})
            yas_grp_df = yas_grp_df.sort_values("_sira").drop(columns=["_sira"])
            for col in ["Ort_m2","Ort_Fiyat","Ort_m2_Fiyat","Ref_100m2"]:
                yas_grp_df[col] = yas_grp_df[col].round(0)

            st.dataframe(yas_grp_df[yas_grp_df["Adet"]>0], use_container_width=True, hide_index=True,
                column_config={
                    "Bina Yaşı Grubu": st.column_config.TextColumn("Bina Yaşı Grubu"),
                    "Adet":            st.column_config.NumberColumn("Adet", format="%d"),
                    "Ort_m2":          st.column_config.NumberColumn("Ort. M²", format="%.0f m²"),
                    "Ort_Fiyat":       st.column_config.NumberColumn("Ort. Fiyat", format="%.0f ₺"),
                    "Ort_m2_Fiyat":    st.column_config.NumberColumn("Ort. m² Fiyatı", format="%.0f ₺"),
                    "Ref_100m2":       st.column_config.NumberColumn("100 m² Ref. Fiyatı", format="%.0f ₺"),
                })

            # Yeni vs Eski premium hesapla
            _yeni = yas_grp_df[yas_grp_df["Bina Yaşı Grubu"]=="Yeni (0-5 yıl)"]
            _eski = yas_grp_df[yas_grp_df["Bina Yaşı Grubu"]=="Eski (26+ yıl)"]
            if not _yeni.empty and not _eski.empty:
                _yeni_fiyat = _yeni.iloc[0]["Ort_m2_Fiyat"]
                _eski_fiyat = _eski.iloc[0]["Ort_m2_Fiyat"]
                if _eski_fiyat and _eski_fiyat > 0:
                    _premium = ((_yeni_fiyat - _eski_fiyat) / _eski_fiyat) * 100
                    _yon = "daha pahalı" if _premium > 0 else "daha ucuz"
                    st.info(
                        f"**Yeni/Eski Bina Farkı:** Yeni binalar (0-5 yıl) eski binalara (26+ yıl) göre "
                        f"m² bazında **%{abs(_premium):.1f} {_yon}** "
                        f"({_yeni_fiyat:,.0f} ₺ vs {_eski_fiyat:,.0f} ₺)".replace(",",".")
                    )

        st.markdown("<br>", unsafe_allow_html=True)
        sc1, sc2 = st.columns(2)

        with sc1:
            st.markdown('<div class="section-title">Oda Tipine Göre Ort. m² Fiyatı</div>', unsafe_allow_html=True)
            if "Oda sayısı" in df.columns and df_num["__birim"].notna().any():
                oda_grp = df_num.groupby("Oda sayısı").agg(
                    Kayıt=("__birim","count"),
                    Ort_m2=("__m2","mean"),
                    Ort_Birim_Fiyat=("__birim","mean"),
                ).reset_index().sort_values("Kayıt", ascending=False)
                oda_grp["Ort_m2"] = oda_grp["Ort_m2"].round(0)
                oda_grp["Ort_Birim_Fiyat"] = oda_grp["Ort_Birim_Fiyat"].round(0)
                st.dataframe(oda_grp, use_container_width=True, hide_index=True, height=240,
                    column_config={
                        "Ort_m2": st.column_config.NumberColumn("Ort. M²", format="%.0f"),
                        "Ort_Birim_Fiyat": st.column_config.NumberColumn("Ort. m² Fiyatı", format="%.0f ₺"),
                    })

        with sc2:
            st.markdown('<div class="section-title">Mahalle Bazlı Özet (ilk 12)</div>', unsafe_allow_html=True)
            if "Mahalle" in df.columns and df_num["__birim"].notna().any():
                mah_grp = df_num.groupby("Mahalle").agg(
                    Kayıt=("__birim","count"),
                    Ort_Fiyat=("__fiyat","mean"),
                    Ort_m2=("__m2","mean"),
                    Ort_Birim_Fiyat=("__birim","mean"),
                ).reset_index().sort_values("Kayıt", ascending=False).head(12)
                mah_grp["Ort_Fiyat"] = mah_grp["Ort_Fiyat"].round(0)
                mah_grp["Ort_m2"] = mah_grp["Ort_m2"].round(0)
                mah_grp["Ort_Birim_Fiyat"] = mah_grp["Ort_Birim_Fiyat"].round(0)
                st.dataframe(mah_grp, use_container_width=True, hide_index=True, height=240,
                    column_config={
                        "Ort_Fiyat": st.column_config.NumberColumn("Ort. Fiyat", format="%.0f ₺"),
                        "Ort_m2": st.column_config.NumberColumn("Ort. M²", format="%.0f"),
                        "Ort_Birim_Fiyat": st.column_config.NumberColumn("Ort. m² Fiyatı", format="%.0f ₺"),
                    })

        st.markdown("<br>", unsafe_allow_html=True)

        # ── OFİS BAZLI DAĞILIM ──
        st.markdown('<div class="section-title">Ofis Bazlı Dağılım (ilk 20)</div>', unsafe_allow_html=True)
        if "Ofis" in df.columns and len(df):
            df_num["__ofis_norm"] = df_num["Ofis"].apply(ofis_duzelt)
            ofis_grp = df_num.groupby(["__ofis_norm","MARKA"], dropna=False).agg(
                Kayıt=("__birim","count"),
                Ort_Fiyat=("__fiyat","mean"),
                Ort_m2=("__m2","mean"),
                Ort_Birim_Fiyat=("__birim","mean"),
                Ort_Sure=("__sure","mean"),
            ).reset_index().sort_values("Kayıt", ascending=False).head(20)
            ofis_grp["Ort_Fiyat"] = ofis_grp["Ort_Fiyat"].round(0)
            ofis_grp["Ort_m2"] = ofis_grp["Ort_m2"].round(0)
            ofis_grp["Ort_Birim_Fiyat"] = ofis_grp["Ort_Birim_Fiyat"].round(0)
            ofis_grp["Ort_Sure"] = ofis_grp["Ort_Sure"].round(0)
            ofis_grp["MARKA"] = ofis_grp["MARKA"].apply(marka_etiket)
            ofis_grp["__ofis_norm"] = ofis_grp["__ofis_norm"].fillna("Mülk Sahibi")
            ofis_grp = ofis_grp.rename(columns={"MARKA":"Marka","__ofis_norm":"Ofis Adı"})

            oc1, oc2 = st.columns([1.3, 1])
            with oc1:
                st.dataframe(ofis_grp, use_container_width=True, hide_index=True, height=420,
                    column_config={
                        "Ort_Fiyat": st.column_config.NumberColumn("Ort. Fiyat", format="%.0f ₺"),
                        "Ort_m2": st.column_config.NumberColumn("Ort. M²", format="%.0f"),
                        "Ort_Birim_Fiyat": st.column_config.NumberColumn("Ort. m² Fiyatı", format="%.0f ₺"),
                        "Ort_Sure": st.column_config.NumberColumn("Ort. Süre (gün)", format="%.0f"),
                    })
            with oc2:
                top_ofis = ofis_grp.head(15).sort_values("Kayıt")
                fig3 = px.bar(top_ofis, x="Kayıt", y="Ofis Adı", orientation="h",
                    color="Marka",
                    color_discrete_map={marka_etiket(k): v for k,v in MARKA_RENK.items()},
                    text="Kayıt")
                fig3.update_layout(showlegend=True, plot_bgcolor="white", paper_bgcolor="white",
                    margin=dict(l=0,r=10,t=5,b=0), height=420, font=dict(size=10),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
                fig3.update_traces(textposition="outside", textfont_size=9)
                st.plotly_chart(fig3, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── GD (GAYRİMENKUL DANIŞMANI) BAZLI DAĞILIM ──
        st.markdown('<div class="section-title">GD Bazlı Dağılım (ilk 20)</div>', unsafe_allow_html=True)
        if "İlan sahibi" in df.columns and len(df):
            def _mode_or_none(s):
                s = s.dropna()
                return s.mode().iloc[0] if not s.empty else None

            df_num["__gd_norm"] = df_num["İlan sahibi"].apply(ad_normalize)
            gd_grp = df_num.groupby("__gd_norm", dropna=False).agg(
                Ofis=("Ofis", _mode_or_none),
                Marka=("MARKA", _mode_or_none),
                Kayıt=("__birim","count"),
                Ort_Fiyat=("__fiyat","mean"),
                Ort_m2=("__m2","mean"),
                Ort_Birim_Fiyat=("__birim","mean"),
                Ort_Sure=("__sure","mean"),
            ).reset_index().sort_values("Kayıt", ascending=False).head(20)
            gd_grp["Ort_Fiyat"] = gd_grp["Ort_Fiyat"].round(0)
            gd_grp["Ort_m2"] = gd_grp["Ort_m2"].round(0)
            gd_grp["Ort_Birim_Fiyat"] = gd_grp["Ort_Birim_Fiyat"].round(0)
            gd_grp["Ort_Sure"] = gd_grp["Ort_Sure"].round(0)
            gd_grp["Marka"] = gd_grp["Marka"].apply(lambda m: marka_etiket(m) if pd.notna(m) else "-")
            gd_grp["Ofis"] = gd_grp["Ofis"].apply(ofis_duzelt).fillna("Mülk Sahibi")
            gd_grp["__gd_norm"] = gd_grp["__gd_norm"].fillna("Belirtilmemiş")
            gd_grp = gd_grp.rename(columns={"__gd_norm":"GD Adı"})
            gd_grp = gd_grp[["GD Adı","Ofis","Marka","Kayıt","Ort_Fiyat","Ort_m2","Ort_Birim_Fiyat","Ort_Sure"]]

            gc1, gc2 = st.columns([1.3, 1])
            with gc1:
                st.dataframe(gd_grp, use_container_width=True, hide_index=True, height=420,
                    column_config={
                        "Ort_Fiyat": st.column_config.NumberColumn("Ort. Fiyat", format="%.0f ₺"),
                        "Ort_m2": st.column_config.NumberColumn("Ort. M²", format="%.0f"),
                        "Ort_Birim_Fiyat": st.column_config.NumberColumn("Ort. m² Fiyatı", format="%.0f ₺"),
                        "Ort_Sure": st.column_config.NumberColumn("Ort. Süre (gün)", format="%.0f"),
                    })
            with gc2:
                top_gd = gd_grp.head(15).sort_values("Kayıt")
                fig4 = px.bar(top_gd, x="Kayıt", y="GD Adı", orientation="h",
                    color="Marka",
                    color_discrete_map={marka_etiket(k): v for k,v in MARKA_RENK.items()},
                    text="Kayıt")
                fig4.update_layout(showlegend=True, plot_bgcolor="white", paper_bgcolor="white",
                    margin=dict(l=0,r=10,t=5,b=0), height=420, font=dict(size=10),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
                fig4.update_traces(textposition="outside", textfont_size=9)
                st.plotly_chart(fig4, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

# Liste
st.markdown('<div class="section-title">İLAN LİSTESİ</div>', unsafe_allow_html=True)

SIR = ["Tarih ↓","Tarih ↑","Fiyat ↑","Fiyat ↓","M² ↑","M² ↓"]
sb1, sb2, sb3 = st.columns([3, 2, 1])
with sb1:
    ara = st.text_input("Ara", placeholder="Başlık, mahalle, ofis...", label_visibility="collapsed", key="pz_ara")
with sb2:
    sir = st.selectbox("Sırala", SIR, label_visibility="collapsed", key="pz_sir")
with sb3:
    buf = BytesIO(); df.to_excel(buf, index=False)
    st.download_button("📥 Excel", data=buf.getvalue(), file_name=f"pazar_{datetime.now().strftime('%Y%m%d')}.xlsx", use_container_width=True)

tablo = df.copy()
if ara:
    al = ara.lower()
    cols_ara = [c for c in ["İlan Başlığı","Mahalle","İlçe","Ofis"] if c in tablo.columns]
    tablo = tablo[tablo.apply(lambda r: any(al in str(r.get(c,"")).lower() for c in cols_ara), axis=1)]

if not tablo.empty:
    if "Tarih" in sir and "İlan tarihi" in tablo.columns:
        tablo["__t"] = pd.to_datetime(tablo["İlan tarihi"], dayfirst=True, errors="coerce")
        tablo = tablo.sort_values("__t", ascending="↑" in sir).drop(columns=["__t"])
    elif "Fiyat" in sir and "Fiyat" in tablo.columns:
        tablo["__f"] = tablo["Fiyat"].apply(lambda v: parse_num(v) or 0)
        tablo = tablo.sort_values("__f", ascending="↑" in sir).drop(columns=["__f"])
    elif "M²" in sir and "M2" in tablo.columns:
        tablo = tablo.sort_values("M2", ascending="↑" in sir)

# ── Görünüm toggle ──
if "pz_secim_modu" not in st.session_state:
    st.session_state["pz_secim_modu"] = False
if "pz_secili_ilanlar" not in st.session_state:
    st.session_state["pz_secili_ilanlar"] = set()

tog1, tog2 = st.columns([6, 1])
with tog1:
    st.caption(f"{len(tablo):,} ilan gösteriliyor")
with tog2:
    if st.button(
        "☑ Seçim Modu" if not st.session_state["pz_secim_modu"] else "⚡ Hızlı Liste",
        key="pz_toggle_mod", use_container_width=True
    ):
        st.session_state["pz_secim_modu"] = not st.session_state["pz_secim_modu"]
        st.rerun()


def _s(v, fallback="-"):
    if v is None: return fallback
    s = str(v).strip()
    if s in ("nan","None","NaN","","-"): return fallback
    return _html.escape(s)

def _ofis(v):
    """Ofis adı boş/nan → Mülk Sahibi"""
    if v is None: return "Mülk Sahibi"
    s = str(v).strip()
    return "Mülk Sahibi" if s in ("nan","None","NaN","") else _html.escape(s[:28])

def _oda(v, mulk_tipi=""):
    """Oda sayısı: arsa/tarla → boş, konut → çizgi"""
    s = str(v).strip() if v is not None else ""
    if s in ("nan","None","NaN",""):
        arsa = any(k in str(mulk_tipi).lower() for k in ("arsa","tarla","bahçe"))
        return "" if arsa else "—"
    return _html.escape(s)

def _yas(v, mulk_tipi=""):
    """Bina yaşı: arsa/tarla → boş, konut → çizgi"""
    s = str(v).strip() if v is not None else ""
    if s in ("nan","None","NaN",""):
        arsa = any(k in str(mulk_tipi).lower() for k in ("arsa","tarla","bahçe"))
        return "" if arsa else "—"
    return _html.escape(s)

def _fiyat(fiyat, m2, m2b=None):
    try:
        f = parse_num(fiyat)
        ust = f'<div style="font-size:12px;font-weight:700;color:#0f172a;white-space:nowrap;">{f:,.0f} ₺</div>'.replace(",",".")
    except: ust = '<div style="font-size:12px;color:#94a3b8;">-</div>'
    try:
        m = float(str(m2).replace(",","."))
        b = parse_num(m2b) if m2b and str(m2b) not in ("","nan","None") else (f/m if m>0 else 0)
        alt = f'<div style="font-size:10px;color:#64748b;margin-top:1px;">m²: {b:,.0f} ₺</div>'.replace(",",".")
    except: alt = ""
    return "<div>"+ust+alt+"</div>"

def _sure(t):
    try:
        dt = pd.to_datetime(t, dayfirst=True, errors="coerce")
        if pd.isna(dt): raise ValueError()
        g = (pd.Timestamp.today().normalize()-dt.normalize()).days
        ts = dt.strftime("%d.%m.%Y")
        if g<=7:    r,d="#166534","🟢"
        elif g<=30: r,d="#854d0e","🟡"
        elif g<=90: r,d="#9a3412","🟠"
        elif g<=180:r,d="#991b1b","🔴"
        else:       r,d="#475569","⚫"
        return f'<div style="font-size:10px;color:#64748b;">İlan: <b>{ts}</b></div><div style="font-size:10px;color:{r};font-weight:700;">{d} {g} gün</div>'
    except: return '<div style="font-size:10px;color:#94a3b8;">-</div>'

def _badge(marka):
    r = MARKA_RENK.get(marka,"#94A3B8")
    return f'<span style="display:inline-block;padding:1px 6px;border-radius:999px;font-size:9px;font-weight:700;background:{r}22;color:{r};">{marka_etiket(marka)}</span>'

KULLANIM_MAP = {
    "bos":("#166534","#dcfce7","Boş"), "boş":("#166534","#dcfce7","Boş"),
    "kiracilik":("#92400e","#fef3c7","Kiracılı"), "kiraci":("#92400e","#fef3c7","Kiracılı"),
    "kiracili":("#92400e","#fef3c7","Kiracılı"), "kiracılı":("#92400e","#fef3c7","Kiracılı"),
    "mulk sahibi":("#1e40af","#dbeafe","Mülk Sah."), "mülk sahibi":("#1e40af","#dbeafe","Mülk Sah."),
}

def _durum_badges(row):
    tags = []
    # FSBO — ilan sahibi türü mülk sahibi ise
    sahip_turu = str(row.get("İlan sahibi türü","")).strip().lower()
    if "mülk" in sahip_turu or "mulk" in sahip_turu:
        tags.append('<span style="background:#0f172a;color:#fff;padding:1px 6px;border-radius:4px;font-size:9px;font-weight:700;letter-spacing:.03em;">FSBO</span>')
    kullanim = str(row.get("Kullanım Durumu","")).strip().lower()
    if kullanim in KULLANIM_MAP:
        fg,bg,lbl = KULLANIM_MAP[kullanim]
        tags.append(f'<span style="background:{bg};color:{fg};padding:1px 6px;border-radius:999px;font-size:9px;font-weight:700;">{lbl}</span>')
    esyali = str(row.get("Eşyalı","")).strip().lower()
    if esyali in ("evet","esyali","eşyalı","var","true","1"):
        tags.append('<span style="background:#dcfce7;color:#166534;padding:1px 6px;border-radius:999px;font-size:9px;font-weight:700;">Eşyalı</span>')
    site = str(row.get("Site içerisinde","")).strip().lower()
    if site in ("evet","var","true","1"):
        tags.append('<span style="background:#fef3c7;color:#92400e;padding:1px 6px;border-radius:999px;font-size:9px;font-weight:700;">Site İçi</span>')
    return "".join(tags)


if st.session_state["pz_secim_modu"]:
    secili = st.session_state["pz_secili_ilanlar"]
    sc1, sc2, sc3, sc4 = st.columns([3, 1.5, 1.5, 1])
    with sc1:
        if secili:
            st.info(f"**{len(secili)}** ilan seçildi")
        else:
            st.caption("Kaydetmek istediğiniz ilanları seçin")
    with sc2:
        if st.button("💾 Genel Kaydet", disabled=not secili, use_container_width=True, key="pz_kaydet_genel"):
            st.toast(f"{len(secili)} ilan genel listeye kaydedildi ✓", icon="💾")
    with sc3:
        if st.button("👤 Müşteriye Kaydet", disabled=not secili, use_container_width=True, key="pz_kaydet_musteri"):
            st.toast(f"{len(secili)} ilan müşteri listesine eklendi ✓", icon="👤")
    with sc4:
        if st.button("✕ Temizle", disabled=not secili, use_container_width=True, key="pz_secim_temizle"):
            st.session_state["pz_secili_ilanlar"] = set()
            st.rerun()

    CR = [0.3, 3.5, 1.5, 1.5, 1, 1.8, 0.8, 1.2, 0.8]
    for col, hdr in zip(st.columns(CR), ["","Başlık / Marka","İşlem / Mülk","İlçe / Mah","M²","Fiyat / m²","Oda","Kat / Yaş","İlan"]):
        col.markdown(f'<div style="font-size:9px;font-weight:800;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em;padding:6px 0 5px;border-bottom:2px solid #e2e8f0;">{hdr}</div>', unsafe_allow_html=True)

    LIMIT_SECIM = 150
    gosterilen = tablo.head(LIMIT_SECIM)
    if len(tablo) > LIMIT_SECIM:
        st.caption(f"⚡ Seçim Modu'nda ilk {LIMIT_SECIM} ilan — filtreyi daraltarak tümüne ulaşın.")

    for idx, (_, row) in enumerate(gosterilen.iterrows()):
        ilan_url = str(row.get("İlan Url","") or "")
        uid = ilan_url or str(idx)
        islem = row.get("İşlem tipi","") or ""
        tip = str(islem).lower()
        bdr_c = "#1e3a5f" if "sat" in tip else ("#0d9488" if "kir" in tip else "#e2e8f0")
        mulk_tipi = str(row.get("Mülk tipi",""))
        marka = row.get("MARKA","bagimsiz")
        secili_mi = uid in st.session_state["pz_secili_ilanlar"]
        RS = "border-bottom:0.5px solid #f1f5f9;padding:7px 0;"
        rc = st.columns(CR)
        with rc[0]:
            checked = st.checkbox("", value=secili_mi, key=f"pz_cb_{idx}", label_visibility="collapsed")
            if checked != secili_mi:
                if checked: st.session_state["pz_secili_ilanlar"].add(uid)
                else:       st.session_state["pz_secili_ilanlar"].discard(uid)
                st.rerun()
        with rc[1]:
            marka_r = MARKA_RENK.get(marka,"#94A3B8")
            bg_row = "#f0f4ff" if secili_mi else "transparent"
            st.markdown(f'<div style="{RS}background:{bg_row};border-left:3px solid {bdr_c};padding-left:6px;"><div style="font-size:11px;font-weight:700;color:#1e293b;">{_s(row.get("İlan Başlığı",""))[:65]}</div><div style="margin-top:2px;display:flex;gap:3px;flex-wrap:wrap;"><span style="background:{marka_r}22;color:{marka_r};padding:1px 5px;border-radius:999px;font-size:9px;font-weight:700;">{marka_etiket(marka)}</span>{_durum_badges(row)}</div></div>', unsafe_allow_html=True)
        with rc[2]:
            islem_c = "#1e3a5f" if "sat" in tip else "#0d9488"
            st.markdown(f'<div style="{RS}"><div style="font-size:11px;font-weight:700;color:{islem_c};">{_s(islem)}</div><div style="font-size:9px;color:#94a3b8;">{_s(mulk_tipi)}</div></div>', unsafe_allow_html=True)
        with rc[3]:
            st.markdown(f'<div style="{RS}"><div style="font-size:11px;font-weight:600;color:#1e293b;">{_s(row.get("İlçe",""))}</div><div style="font-size:9px;color:#94a3b8;">{_s(row.get("Mahalle",""))}</div></div>', unsafe_allow_html=True)
        with rc[4]:
            st.markdown(f'<div style="{RS}font-size:11px;color:#475569;">{_s(row.get("M2",""))} m²</div>', unsafe_allow_html=True)
        with rc[5]:
            try:
                f_val = parse_num(row.get("Fiyat",""))
                fiyat_str = f'{f_val:,.0f} ₺'.replace(",",".")
                m2v = float(str(row.get("M2","")).replace(",","."))
                birim_str = f'm²: {f_val/m2v:,.0f} ₺'.replace(",",".") if m2v>0 else ""
            except: fiyat_str,birim_str = "—",""
            st.markdown(f'<div style="{RS}"><div style="font-size:11px;font-weight:700;color:#0f172a;">{fiyat_str}</div><div style="font-size:9px;color:#64748b;">{birim_str}</div></div>', unsafe_allow_html=True)
        with rc[6]:
            st.markdown(f'<div style="{RS}font-size:11px;color:#475569;">{_oda(row.get("Oda sayısı",""), mulk_tipi)}</div>', unsafe_allow_html=True)
        with rc[7]:
            st.markdown(f'<div style="{RS}"><div style="font-size:10px;color:#475569;">{_s(row.get("Bulunduğu kat",""))}</div><div style="font-size:9px;color:#94a3b8;">{_yas(row.get("Bina Yaşı",""), mulk_tipi)}</div></div>', unsafe_allow_html=True)
        with rc[8]:
            link_v = str(row.get("İlan Url","") or "")
            if link_v and link_v not in ("-","nan","None"):
                st.link_button("Aç", url=link_v, use_container_width=True)

else:  # ── HIZLI LİSTE ──
    
    rows = ""
    for i,(_, row) in enumerate(tablo.head(500).iterrows(), 1):
        islem = row.get("İşlem tipi","") or ""
        tip   = str(islem).lower()
        bdr   = "#1e3a5f" if "sat" in tip else ("#0d9488" if "kir" in tip else "#e2e8f0")
        link  = row.get("İlan Url","") or ""
        link_b = (f'<a href="{_html.escape(str(link))}" target="_blank" style="display:inline-block;padding:2px 8px;border-radius:6px;background:#f1f5f9;border:1px solid #e2e8f0;font-size:10px;font-weight:700;color:#374151;text-decoration:none;">Aç</a>' if link and link!="-" else "-")
        td = "padding:8px 10px;"
        marka = row.get("MARKA","bagimsiz")
        mulk_tipi = str(row.get("Mülk tipi",""))
        is_dupe = bool(row.get("_is_dupe", False))
        dupe_badge = ' <span title="Mükerrer — farklı portallarda aynı mülk" style="color:#f59e0b;">🔁</span>' if is_dupe else ""
        # Yayından Kalkış Tarihi — sadece pasif/yayından kalkan ilanlar için
        kalktı_str = ""
        ilan_durumu = str(row.get("İlan Durumu","")).strip().lower()
        if ilan_durumu in ("pasif","suspended","yayindan_kalkan"):
            yk = row.get("Yayından Kalkış Tarihi")
            if yk is not None and str(yk) not in ("nan","NaT","None",""):
                try: kalktı_str = pd.Timestamp(yk).strftime("%d.%m.%Y")
                except: pass

        # İlan Kaynağı badge
        kaynak_raw = row.get("İlan Kaynağı","") or ""
        kaynak_val = str(kaynak_raw).strip() if str(kaynak_raw) not in ("nan","None","") else ""
        KAYNAK_STIL = {
            "sahibinden.com": ("white", "#eab308"),
            "hepsi emlak":    ("white", "#ef4444"),
            "emlakjet":       ("white", "#8b5cf6"),
            "zingat":         ("white", "#06b6d4"),
            "revy":           ("white", "#1e2d3d"),
        }
        _kv = kaynak_val.lower()
        _txt, _bg = KAYNAK_STIL.get(_kv, ("white", "#94a3b8"))
        kaynak_badge = (
            f'<span style="background:{_bg};color:{_txt};padding:2px 6px;'
            f'border-radius:4px;font-size:9px;font-weight:700;white-space:nowrap;">'
            f'{_html.escape(kaynak_val)}</span>'
            if kaynak_val else ""
        )
        rows += ("<tr>"
        +f'<td style="padding:8px 3px 8px 0;border-left:3px solid {bdr};width:3px;"></td>'
        +f'<td style="{td}color:#94a3b8;font-size:10px;">{i}</td>'
        +f'<td style="{td}max-width:260px;min-width:200px;"><div style="font-size:11px;font-weight:700;color:#0f172a;line-height:1.3;">{_s(row.get("İlan Başlığı",""))[:75]}{dupe_badge}</div><div style="margin-top:3px;display:flex;gap:3px;flex-wrap:wrap;align-items:center;">{_badge(marka)}{_durum_badges(row)}</div></td>'
        +f'<td style="{td}"><div style="font-size:11px;font-weight:700;color:{"#1e3a5f" if "sat" in tip else "#0d9488"};">{_s(islem)}</div><div style="font-size:10px;color:#64748b;">{_s(row.get("Mülk türü",""))} / {_s(mulk_tipi)}</div></td>'
        +f'<td style="{td}"><div style="font-size:11px;font-weight:600;color:#1e293b;">{_s(row.get("İlçe",""))}</div><div style="font-size:10px;color:#64748b;">{_s(row.get("Mahalle",""))}</div></td>'
        +f'<td style="{td}font-size:11px;color:#475569;white-space:nowrap;">{_s(row.get("M2",""))} m²</td>'
        +f'<td style="{td}">{_fiyat(row.get("Fiyat",""), row.get("M2",""), row.get("m2/Birim Fiyatı",""))}</td>'
        +f'<td style="{td}font-size:11px;color:#475569;">{_oda(row.get("Oda sayısı",""), mulk_tipi)}</td>'
        +f'<td style="{td}"><div style="font-size:10px;color:#475569;">{_s(row.get("Bulunduğu kat",""))}</div><div style="font-size:10px;color:#94a3b8;">{_yas(row.get("Bina Yaşı",""), mulk_tipi)}</div></td>'
        +f'<td style="{td}">{_sure(row.get("İlan tarihi",""))}'
            +(f'<div style="font-size:9px;color:#ef4444;margin-top:2px;">Kalktı: {kalktı_str}</div>' if kalktı_str else "")
        +'</td>'
        +f'<td style="{td}">{link_b}</td>'
        +f'<td style="{td}"><div style="font-size:10px;color:#374151;white-space:nowrap;">{_ofis(row.get("Ofis",""))}</div>'
            +f'<div style="margin-top:2px;">{kaynak_badge}</div></td>'
        +"</tr>")
    ths = "padding:8px 10px;text-align:left;font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:#64748b;border-bottom:2px solid #e2e8f0;background:#f8fafc;white-space:nowrap;"
    cols_h = ["","#","Başlık / Marka","İşlem / Mülk","İlçe / Mah","M²","Fiyat / m²","Oda","Kat / Yaş","Süre / Tarih","İlan","Ofis"]
    bh = "".join(f'<th style="{ths}">{c}</th>' for c in cols_h)
    html_t = ("<style>.ht tbody tr:hover td{background:#f0f4ff!important;}</style>"
    +'<div style="background:white;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;">'
    +'<div style="overflow-x:auto;">'
    +f'<table class="ht"><thead><tr>{bh}</tr></thead><tbody>{rows}</tbody></table>'
    +"</div></div>")
    components.html(html_t, height=min(850, 80+len(tablo.head(500))*52), scrolling=True)

st.markdown("---")
st.markdown('<div class="section-title">📥 Excel İndir</div>', unsafe_allow_html=True)
d1,d2,d3,d4,d5 = st.columns(5)
def xls(data):
    b = BytesIO(); data.to_excel(b, index=False); return b.getvalue()
with d1: st.download_button("📊 Genel", data=xls(df), file_name="pazar_genel.xlsx", use_container_width=True)
with d2:
    sk = df[df["MARKA"]=="startkey"] if "MARKA" in df.columns else df.iloc[0:0]
    st.download_button(f"🔑 Startkey ({len(sk):,})", data=xls(sk), file_name="pazar_startkey.xlsx", use_container_width=True)
with d3:
    rk = df[df["MARKA"].isin([m for m in MARKA_RENK if m not in ("startkey","bagimsiz","mulk_sahibi")])] if "MARKA" in df.columns else df.iloc[0:0]
    st.download_button(f"🏢 Rakipler ({len(rk):,})", data=xls(rk), file_name="pazar_rakip.xlsx", use_container_width=True)
with d4:
    bg = df[df["MARKA"]=="bagimsiz"] if "MARKA" in df.columns else df.iloc[0:0]
    st.download_button(f"🏠 Yerel Ofis ({len(bg):,})", data=xls(bg), file_name="pazar_yerel_ofis.xlsx", use_container_width=True)
with d5:
    ms = df[df["MARKA"]=="mulk_sahibi"] if "MARKA" in df.columns else df.iloc[0:0]
    st.download_button(f"🙋 Mülk Sahibi ({len(ms):,})", data=xls(ms), file_name="pazar_mulk_sahibi.xlsx", use_container_width=True)

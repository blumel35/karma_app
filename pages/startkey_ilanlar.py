"""
startkey_ilanlar.py
--------------------
Startkey İlanları — Revy'den keyword=startkey ile çekim
Bağımsız: streamlit run startkey_ilanlar.py
Karma App: pages/startkey_ilanlar.py
"""

import streamlit as st
import sys, json, importlib
from pathlib import Path
from io import BytesIO
from datetime import datetime, date, timedelta
import pandas as pd
import plotly.express as px
import html as _html
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).parent))

# Karma App içinde set_page_config app.py'de yapılır
# Bağımsız çalıştırma için: streamlit run startkey_ilanlar.py
try:
    st.set_page_config(
        page_title="Startkey İlanları",
        page_icon="🔑",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
except Exception:
    pass

# ─────────────────────────────────────────
# CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
:root {
    --bg:#F4F7FB; --card:#FFFFFF; --text:#0F172A; --muted:#64748B;
    --primary:#355C7D; --primary-hover:#446B8B; --accent:#E85D75;
    --success:#22C55E; --warning:#F59E0B; --border:#DCE4EE;
    --chip-bg:#EEF4FA;
}
.stApp { background:var(--bg); }
section[data-testid="stSidebar"] { display:none; }
.block-container { padding-top:0.8rem; padding-bottom:2rem; max-width:1520px; }

div[data-testid="stButton"] > button {
    border-radius:8px; border:1px solid var(--border);
    min-height:34px; padding:6px 12px;
    font-size:12px; font-weight:600;
    background:var(--chip-bg); color:var(--text);
    transition:all 0.15s;
}
div[data-testid="stButton"] > button[kind="primary"] {
    background:var(--primary) !important; border-color:var(--primary) !important;
    color:#fff !important; box-shadow:0 2px 8px rgba(53,92,125,0.18) !important;
}
div[data-baseweb="select"] > div {
    border-radius:8px !important; border-color:var(--border) !important; min-height:34px !important;
}
span[data-baseweb="tag"] {
    background-color:var(--chip-bg) !important; color:var(--primary) !important;
    border:1px solid var(--border) !important; border-radius:6px !important;
}
span[data-baseweb="tag"] svg { fill:var(--primary) !important; }
input { border-radius:8px !important; }

.page-header {
    background:linear-gradient(135deg,#1e293b 0%,#355C7D 100%);
    border-radius:14px; padding:18px 28px; margin-bottom:14px; color:white;
}
.page-header h1 { color:white !important; font-size:1.4rem; font-weight:800; margin:0; }
.page-header p { color:#94a3b8; margin:4px 0 0 0; font-size:13px; }

.filtre-panel {
    background:white; border:1px solid var(--border);
    border-radius:12px; padding:16px 20px; margin-bottom:14px;
}
.filtre-baslik {
    font-size:11px; font-weight:800; color:var(--muted);
    text-transform:uppercase; letter-spacing:0.8px;
    margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid var(--border);
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
# VERİ / YARDIMCI
# ─────────────────────────────────────────
@st.cache_data
def mahalle_yukle():
    yol = Path(__file__).parent / "izmir_mahalleler.json"
    if yol.exists():
        return json.load(open(yol, encoding="utf-8"))
    return {}

MAHALLELER   = mahalle_yukle()
IZMIR_ILCELER = sorted(MAHALLELER.keys()) if MAHALLELER else []

ISLEM_SEC = {"Satılık":"satilik","Kiralık":"kiralik"}
DURUM_SEC = {"Aktif İlanlar":"aktif","Yayından Kalkanlar":"yayindan_kalkan"}

# Startkey ofis renk paleti (mavi tonlar)
SK_RENKLER = [
    "#355C7D","#446B8B","#537A99","#6289A7","#7198B5",
    "#80A7C3","#8FB6D1","#9EC5DF","#ADD4ED","#BCE3FB",
]

def parse_num(v):
    try: return float(str(v).replace(".","").replace(",",".").replace("₺","").replace("TL","").strip())
    except: return None

for k,v in [("sk_veri",{}),("sk_last_filtre",{})]:
    if k not in st.session_state: st.session_state[k] = v

# ─────────────────────────────────────────
# BAŞLIK
# ─────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <h1>🔑 Startkey İlanları</h1>
    <p>Revy'deki tüm Startkey ilanları — ofis bazlı analiz ve filtreleme</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# FİLTRE PANELİ
# ─────────────────────────────────────────
st.markdown('<div class="filtre-panel">', unsafe_allow_html=True)
st.markdown('<div class="filtre-baslik">🔍 Filtreler</div>', unsafe_allow_html=True)

# Satır 1 — Konum + Tarih
r1a, r1b, r1c = st.columns([2, 2.5, 1.5])
with r1a:
    secili_ilceler = st.multiselect("İlçe", IZMIR_ILCELER, placeholder="Tümü", key="sk_ilce")
with r1b:
    mah_opts = []
    for ilce in secili_ilceler:
        mah_opts.extend(MAHALLELER.get(ilce, []))
    mah_opts = sorted(set(mah_opts))
    secili_mahalleler = st.multiselect("Mahalle", mah_opts, placeholder="Tümü (opsiyonel)", key="sk_mah")
with r1c:
    varsayilan_aralik = (date.today() - timedelta(days=90), date.today())
    tarih_aralik = st.date_input("Tarih Aralığı", value=varsayilan_aralik, format="DD.MM.YYYY", key="sk_tarih")
    if isinstance(tarih_aralik, tuple) and len(tarih_aralik) == 2:
        bas_tarih, bit_tarih = tarih_aralik
    else:
        bas_tarih, bit_tarih = varsayilan_aralik

# Satır 2 — İşlem / Durum / Yapı filtreleri
r2a, r2b, r2c, r2d, r2e = st.columns([1.5, 1.5, 1.2, 1.2, 1.2])
with r2a:
    secili_islemler = st.multiselect("İşlem Tipi", list(ISLEM_SEC.keys()), default=["Satılık","Kiralık"], key="sk_islem")
with r2b:
    secili_durumlar = st.multiselect("İlan Durumu", list(DURUM_SEC.keys()), default=["Aktif İlanlar"], key="sk_durum")
with r2c:
    oda_filtre = st.multiselect("Oda", ["1+0","1+1","2+1","2+2","3+1","3+2","4+1","4+2","5+1","5+2"], placeholder="Tümü", key="sk_oda")
with r2d:
    kat_filtre = st.multiselect("Kat", ["Zemin","Bahçe Katı","1. Kat","2. Kat","3. Kat","4. Kat","5. Kat","Yüksek Giriş","Müstakil"], placeholder="Tümü", key="sk_kat")
with r2e:
    yas_filtre = st.multiselect("Bina Yaşı", ["0","1-5","6-10","11-15","16-20","21-25","26-30","30 üstü"], placeholder="Tümü", key="sk_yas")

# Satır 3 — Sayısal + Durum + Listele
r3a, r3b, r3c, r3d, r3e, r3f = st.columns([1, 1, 1, 1.2, 1.2, 0.8])
with r3a:
    m2_min = st.number_input("M² Alt", min_value=0, value=0, step=10, key="sk_m2_min")
with r3b:
    m2_max = st.number_input("M² Üst", min_value=0, value=0, step=10, key="sk_m2_max")
with r3c:
    fiyat_min = st.number_input("Fiyat Alt (₺M)", min_value=0.0, value=0.0, step=0.5, format="%.1f", key="sk_fiyat_min")
with r3d:
    kullanim_filtre = st.multiselect("Kullanım", ["Boş","Kiracılı","Mülk Sahibi"], placeholder="Tümü", key="sk_kullanim")
with r3e:
    esyali_filtre = st.selectbox("Eşyalı", ["Tümü","Evet","Hayır"], key="sk_esyali")
with r3f:
    st.write("")
    listele_btn = st.button("🔍 Listele", type="primary", use_container_width=True, key="sk_listele")

st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────
# VERİ ÇEKME
# ─────────────────────────────────────────
if listele_btn:
    if not secili_durumlar:
        st.error("En az bir ilan durumu seçin.")
    else:
        filtre_dict = {
            "durum":     [DURUM_SEC[d] for d in secili_durumlar],
            "baslangic": bas_tarih.strftime("%Y-%m-%d"),
            "bitis":     bit_tarih.strftime("%Y-%m-%d"),
        }

        ayni_filtre = (
            st.session_state.sk_veri
            and st.session_state.sk_last_filtre == filtre_dict
        )
        if ayni_filtre:
            st.rerun()

        durum_ph = st.empty()
        def progress_cb(msg):
            durum_ph.markdown(f'<div class="durum-banner">{msg}</div>', unsafe_allow_html=True)

        try:
            import revy_pazar_cek as rpc
            importlib.reload(rpc)

            # Karma App: ayarlar.txt kök dizinde; bağımsız: aynı klasörde
            ayarlar_yol = Path(__file__).parent / "ayarlar.txt"
            if not ayarlar_yol.exists():
                ayarlar_yol = Path(__file__).parent.parent / "ayarlar.txt"
            ayarlar = rpc.ayarlari_oku(ayarlar_yol)
            progress_cb("🌐 Revy'ye bağlanılıyor (arka planda)...")

            cookies = rpc.selenium_cookie_al(
                kullanici=ayarlar["revy1_kullanici"],
                sifre=ayarlar["revy1_sifre"],
                giris_url=ayarlar.get("revy_giris_url","https://revy.com.tr"),
                headless=True,
                progress_cb=progress_cb,
            )

            cikti = rpc.startkey_ilan_cek(
                cookies, filtre_dict,
                cikti_klasor=Path(__file__).parent / "revy_startkey_cikti",
                progress_cb=progress_cb,
            )

            st.session_state.sk_veri = cikti
            st.session_state.sk_last_filtre = filtre_dict
            durum_ph.success(f"✅ {sum(len(v) for v in cikti.values()):,} Startkey ilanı hazır!")
            st.rerun()

        except Exception as e:
            durum_ph.error(f"Hata: {e}")

# ─────────────────────────────────────────
# ANALİZ
# ─────────────────────────────────────────
sk_veri = st.session_state.sk_veri
if not sk_veri:
    st.markdown("""
    <div style="text-align:center;padding:50px 20px;color:#64748b;">
        <div style="font-size:2.5rem;margin-bottom:12px;">🔑</div>
        <div style="font-size:1rem;font-weight:600;margin-bottom:6px;">Filtreleri seçin ve Listele'ye basın</div>
        <div style="font-size:12px;">Revy'deki tüm Startkey ilanları otomatik çekilecek</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Tüm durumları birleştir
df = pd.concat([v for v in sk_veri.values() if not v.empty], ignore_index=True) if sk_veri else pd.DataFrame()
if df.empty:
    st.info("Veri bulunamadı.")
    st.stop()

# ── Lokal filtreler ──
if secili_ilceler and "İlçe" in df.columns:
    df = df[df["İlçe"].isin(secili_ilceler)]
if secili_mahalleler and "Mahalle" in df.columns:
    df = df[df["Mahalle"].isin(secili_mahalleler)]
if secili_islemler and "İşlem tipi" in df.columns:
    islem_vals = [ISLEM_SEC[i] for i in secili_islemler]
    df = df[df["İşlem tipi"].str.lower().str.strip().isin([v.lower() for v in ["Satılık","Kiralık"][:len(islem_vals)]])]
    # daha güvenli:
    islem_tr = {"satilik":["Satılık","satilik","satılık"], "kiralik":["Kiralık","kiralik","kiralık"]}
    secilen = []
    for i in secili_islemler:
        secilen.extend(islem_tr.get(ISLEM_SEC[i],[]))
    df = df[df["İşlem tipi"].isin(secilen)] if secilen else df
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
if m2_min > 0 and "M2" in df.columns:
    df = df[pd.to_numeric(df["M2"], errors="coerce").fillna(0) >= m2_min]
if m2_max > 0 and "M2" in df.columns:
    df = df[pd.to_numeric(df["M2"], errors="coerce").fillna(99999) <= m2_max]
if fiyat_min > 0 and "Fiyat" in df.columns:
    df = df[df["Fiyat"].apply(lambda v: parse_num(v) or 0) >= fiyat_min * 1_000_000]

# ── KPI KARTLARI ──
toplam    = len(df)
aktif_n   = len(df[df["_durum"]=="aktif"]) if "_durum" in df.columns else toplam
kalkan_n  = len(df[df["_durum"]=="yayindan_kalkan"]) if "_durum" in df.columns else 0
ofis_n    = df["Ofis"].nunique() if "Ofis" in df.columns else 0
df_num    = df.copy()
df_num["__fiyat"] = df_num.get("Fiyat", pd.Series()).apply(lambda v: parse_num(v))
df_num["__m2"]    = pd.to_numeric(df_num.get("M2", pd.Series()), errors="coerce")
df_num["__birim"] = df_num["__fiyat"] / df_num["__m2"].replace(0, pd.NA)
ort_birim = df_num["__birim"].mean()

k1,k2,k3,k4,k5 = st.columns(5)
for col, lbl, val, sub, cls in [
    (k1,"Toplam İlan", toplam, "tüm startkey", "kpi-blue"),
    (k2,"Aktif", aktif_n, f"%{aktif_n/toplam*100:.0f}" if toplam else "-", "kpi-green"),
    (k3,"Yayından Kalkan", kalkan_n, f"%{kalkan_n/toplam*100:.0f}" if toplam else "-", "kpi-amber"),
    (k4,"Ofis Sayısı", ofis_n, "farklı startkey ofisi", "kpi-blue"),
    (k5,"Ort. m² Fiyatı", f"{ort_birim:,.0f} ₺".replace(",",".") if not pd.isna(ort_birim) else "-", "", "kpi-blue"),
]:
    with col:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">{lbl}</div>
            <div class="kpi-value {cls}">{val}</div>
            <div class="kpi-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── OFİS BAZLI ANALİZ ──
with st.expander("📊 Ofis Bazlı Analiz", expanded=True):
    if "Ofis" in df.columns:
        oc1, oc2 = st.columns([1.2, 1])
        with oc1:
            st.markdown('<div class="section-title">Ofis Bazlı Dağılım (ilk 20)</div>', unsafe_allow_html=True)
            ofis_grp = df_num.groupby("Ofis", dropna=False).agg(
                Kayıt=("__birim","count"),
                Ort_Fiyat=("__fiyat","mean"),
                Ort_m2=("__m2","mean"),
                Ort_Birim=("__birim","mean"),
            ).reset_index().sort_values("Kayıt", ascending=False).head(20)
            ofis_grp["Ort_Fiyat"] = ofis_grp["Ort_Fiyat"].round(0)
            ofis_grp["Ort_m2"]    = ofis_grp["Ort_m2"].round(0)
            ofis_grp["Ort_Birim"] = ofis_grp["Ort_Birim"].round(0)
            st.dataframe(ofis_grp, use_container_width=True, hide_index=True, height=400,
                column_config={
                    "Ort_Fiyat": st.column_config.NumberColumn("Ort. Fiyat", format="%.0f ₺"),
                    "Ort_m2":    st.column_config.NumberColumn("Ort. M²", format="%.0f"),
                    "Ort_Birim": st.column_config.NumberColumn("Ort. m² Fiyatı", format="%.0f ₺"),
                })
        with oc2:
            st.markdown('<div class="section-title">Ofis Grafiği (ilk 15)</div>', unsafe_allow_html=True)
            top15 = ofis_grp.head(15).sort_values("Kayıt")
            renkler = SK_RENKLER[:len(top15)]
            fig = px.bar(top15, x="Kayıt", y="Ofis", orientation="h",
                color="Ofis", color_discrete_sequence=renkler, text="Kayıt")
            fig.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=0,r=10,t=5,b=0), height=400, font=dict(size=10))
            fig.update_traces(textposition="outside", textfont_size=9)
            st.plotly_chart(fig, use_container_width=True)

# ── İLAN LİSTESİ ──
st.markdown('<div class="section-title">İLAN LİSTESİ</div>', unsafe_allow_html=True)

SIR = ["Tarih ↓","Tarih ↑","Fiyat ↑","Fiyat ↓","M² ↑","M² ↓"]
sb1, sb2, sb3 = st.columns([3, 2, 1])
with sb1:
    ara = st.text_input("Ara", placeholder="Başlık, mahalle, ofis...", label_visibility="collapsed", key="sk_ara")
with sb2:
    sir = st.selectbox("Sırala", SIR, label_visibility="collapsed", key="sk_sir")
with sb3:
    buf = BytesIO(); df.to_excel(buf, index=False)
    st.download_button("📥 Excel", data=buf.getvalue(),
        file_name=f"startkey_ilanlar_{datetime.now().strftime('%Y%m%d')}.xlsx",
        use_container_width=True)

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

st.caption(f"{len(tablo):,} ilan gösteriliyor")

def _s(v):
    if v is None: return "-"
    s = str(v).strip()
    return _html.escape(s) if s else "-"

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
        return f'<div style="font-size:10px;color:#64748b;">İlan:<b>{ts}</b></div><div style="font-size:10px;color:{r};font-weight:700;">{d} {g} gün</div>'
    except: return '<div style="font-size:10px;color:#94a3b8;">-</div>'

KULLANIM_MAP = {
    "bos":("#166534","#dcfce7","Boş"),"boş":("#166534","#dcfce7","Boş"),
    "kiraci":("#92400e","#fef3c7","Kiracılı"),"kiracılı":("#92400e","#fef3c7","Kiracılı"),
    "kiracili":("#92400e","#fef3c7","Kiracılı"),
    "mulk sahibi":("#1e40af","#dbeafe","Mülk Sahibi"),"mülk sahibi":("#1e40af","#dbeafe","Mülk Sahibi"),
}

def _durum_badges(row):
    tags = []
    k = str(row.get("Kullanım Durumu","")).strip().lower()
    if k in KULLANIM_MAP:
        fg,bg,lbl = KULLANIM_MAP[k]
        tags.append(f'<span style="background:{bg};color:{fg};padding:1px 5px;border-radius:999px;font-size:9px;font-weight:700;">{lbl}</span>')
    if str(row.get("Eşyalı","")).strip().lower() in ("evet","var","true","1"):
        tags.append('<span style="background:#dcfce7;color:#166534;padding:1px 5px;border-radius:999px;font-size:9px;font-weight:700;">Eşyalı</span>')
    if str(row.get("Site içerisinde","")).strip().lower() in ("evet","var","true","1"):
        tags.append('<span style="background:#fef3c7;color:#92400e;padding:1px 5px;border-radius:999px;font-size:9px;font-weight:700;">Site İçi</span>')
    return "".join(tags)

rows = ""
for i,(_, row) in enumerate(tablo.head(500).iterrows(), 1):
    islem = row.get("İşlem tipi","") or ""
    tip   = str(islem).lower()
    bdr   = "#1e3a5f" if "sat" in tip else ("#0d9488" if "kir" in tip else "#e2e8f0")
    link  = row.get("İlan Url","") or ""
    link_b = (f'<a href="{_html.escape(str(link))}" target="_blank" style="display:inline-block;padding:2px 8px;border-radius:6px;background:#f1f5f9;border:1px solid #e2e8f0;font-size:10px;font-weight:700;color:#374151;text-decoration:none;">Aç</a>' if link and link!="-" else "-")
    td = "padding:8px 10px;"
    rows += ("<tr>"
        +f'<td style="padding:8px 3px 8px 0;border-left:3px solid {bdr};width:3px;"></td>'
        +f'<td style="{td}color:#94a3b8;font-size:10px;">{i}</td>'
        +f'<td style="{td}max-width:240px;min-width:180px;"><div style="font-size:11px;font-weight:700;color:#0f172a;line-height:1.3;">{_s(row.get("İlan Başlığı",""))[:75]}</div><div style="margin-top:3px;display:flex;gap:3px;flex-wrap:wrap;">{_durum_badges(row)}</div></td>'
        +f'<td style="{td}"><div style="font-size:11px;font-weight:700;color:{"#1e3a5f" if "sat" in tip else "#0d9488"};">{_s(islem)}</div><div style="font-size:10px;color:#64748b;">{_s(row.get("Mülk türü",""))} / {_s(row.get("Mülk tipi",""))}</div></td>'
        +f'<td style="{td}"><div style="font-size:11px;font-weight:600;color:#1e293b;">{_s(row.get("İlçe",""))}</div><div style="font-size:10px;color:#64748b;">{_s(row.get("Mahalle",""))}</div></td>'
        +f'<td style="{td}font-size:11px;color:#475569;white-space:nowrap;">{_s(row.get("M2",""))} m²</td>'
        +f'<td style="{td}">{_fiyat(row.get("Fiyat",""), row.get("M2",""), row.get("m2/Birim Fiyatı",""))}</td>'
        +f'<td style="{td}font-size:11px;color:#475569;">{_s(row.get("Oda sayısı",""))}</td>'
        +f'<td style="{td}"><div style="font-size:10px;color:#475569;">{_s(row.get("Bulunduğu kat",""))}</div><div style="font-size:10px;color:#94a3b8;">{_s(row.get("Bina Yaşı",""))}</div></td>'
        +f'<td style="{td}">{_sure(row.get("İlan tarihi",""))}</td>'
        +f'<td style="{td}">{link_b}</td>'
        +f'<td style="{td}font-size:10px;color:#355C7D;font-weight:600;white-space:nowrap;">{_s(str(row.get("Ofis",""))[:30])}</td>'
        +"</tr>")

ths = "padding:8px 10px;text-align:left;font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:#64748b;border-bottom:2px solid #e2e8f0;background:#f8fafc;white-space:nowrap;"
cols_h = ["","#","Başlık / Durum","İşlem / Mülk","İlçe / Mah","M²","Fiyat / m²","Oda","Kat / Yaş","Süre / Tarih","İlan","Ofis"]
bh = "".join(f'<th style="{ths}">{c}</th>' for c in cols_h)
html_t = ("<style>.ht tbody tr:hover td{background:#EEF4FA!important;}</style>"
    +'<div style="background:white;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;">'
    +'<div style="overflow-x:auto;">'
    +f'<table class="ht"><thead><tr>{bh}</tr></thead><tbody>{rows}</tbody></table>'
    +"</div></div>")
components.html(html_t, height=min(850, 80+len(tablo.head(500))*52), scrolling=True)

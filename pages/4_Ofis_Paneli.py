import streamlit as st
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from core.ui_helpers import render_navbar, render_page_title_selector, render_page_header
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.supabase_client import get_client
import pandas as pd
import plotly.express as px
from datetime import datetime
import streamlit.components.v1 as components
import ast, difflib, html, re


st.markdown("""
<style>
:root {
    --sidebar: #0f1623;
    --charcoal: #2B2F36;
    --accent-red: #ff4d4f;
    --border: #d9dee7;
    --bg: #f5f7fb;
    --card: #ffffff;
    --text: #111827;
    --muted: #64748b;
    --green: #22c55e;
    --amber: #f59e0b;
    --blue: #2563eb;
}
.stApp { background: var(--bg); }
.block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1520px; }
div[data-testid="stButton"] > button {
    white-space: normal; line-height: 1.25; border-radius: 11px;
    border: 1px solid var(--border); min-height: 39px; font-weight: 650;
    background: #ffffff; color: #1f2937;
    transition: all 0.16s ease-in-out;
}
div[data-testid="stButton"] > button:hover {
    border-color: #9ca3af; color: #111827;
    box-shadow: inset 0 -1px 0 rgba(255,77,79,0.32), 0 2px 8px rgba(15,23,42,0.06);
}
div[data-testid="stButton"] > button[kind="primary"] {
    background: #374151 !important; border-color: #374151 !important;
    color: #ffffff !important;
    box-shadow: inset 0 -2px 0 var(--accent-red), 0 1px 3px rgba(15,23,42,0.14) !important;
}

div[data-baseweb="select"] > div {
    border-radius: 10px !important; border-color: var(--border) !important; min-height: 39px !important;
}
input { border-radius: 10px !important; }

.kpi-card {
    background: white; border: 1px solid var(--border);
    border-radius: 14px; padding: 16px 20px;
    box-shadow: 0 2px 8px rgba(15,23,42,0.04);
}
.kpi-label { font-size: 11px; color: var(--muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 4px; }
.kpi-value { font-size: 2rem; font-weight: 800; color: var(--text); line-height: 1.1; margin: 4px 0; }
.kpi-sub { font-size: 12px; color: var(--muted); }
.kpi-red { color: var(--accent-red) !important; }
.kpi-green { color: var(--green) !important; }
.kpi-amber { color: var(--amber) !important; }
.kpi-blue { color: var(--blue) !important; }

.section-title {
    font-size: 14px; font-weight: 750; color: var(--text);
    margin: 18px 0 10px 0; padding-bottom: 8px;
    border-bottom: 2px solid var(--border);
    text-transform: uppercase; letter-spacing: 0.5px;
}

h1 { color: var(--text); letter-spacing: -0.7px; }
h2, h3, h4 { color: #1f2937; letter-spacing: -0.2px; }

.red-accent { color: var(--accent-red); font-weight: 750; }
.red-badge {
    display: inline-block; background: #fff1f1; color: #d92d30;
    border: 1px solid #ffd1d1; padding: 1px 7px; border-radius: 999px;
    font-size: 11px; font-weight: 750; margin-left: 4px;
}

.ht{border-collapse:collapse;width:100%;font-size:13px;}
.ht th{background:#f8fafc;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:#64748b;padding:9px 12px;border-bottom:2px solid #e2e8f0;white-space:nowrap;text-align:left;}
.ht td{padding:9px 12px;border-bottom:1px solid #f1f5f9;vertical-align:top;}
.ht tr:hover td{background:#f8fafc;}
.type-satilik{color:#0f172a;font-weight:700;}.type-kiralik{color:#0d9488;font-weight:700;}
.cell-top{font-weight:600;font-size:13px;color:#111827;}.cell-bottom{font-size:11px;color:#64748b;margin-top:2px;}.cell-wrap{line-height:1.35;}
.rtag{display:inline-block;padding:1px 7px;border-radius:999px;font-size:10px;font-weight:600;margin:1px 2px 1px 0;}
.rtag-blue{background:#dbeafe;color:#1e40af;}.rtag-green{background:#dcfce7;color:#166534;}
.rtag-amber{background:#fef3c7;color:#92400e;}.rtag-gray{background:#f1f5f9;color:#475569;}
.rtag-empty{color:#64748b;}.rtag-wrap{line-height:1.6;}
.rbadge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;}
.rbadge-green{background:#dcfce7;color:#166534;}.rbadge-yellow{background:#fef3c7;color:#92400e;}
.rbadge-orange{background:#ffedd5;color:#c2410c;}.rbadge-red{background:#fee2e2;color:#991b1b;}
.rbadge-gray{background:#f1f5f9;color:#475569;}
.rbadge-blue{background:#dbeafe;color:#1e40af;}
.dur-wrap{line-height:1.4;}.dur-line{display:flex;gap:6px;align-items:center;}
.dur-date{font-size:10px;color:#64748b;margin-top:2px;}
.rlink-btn{display:inline-block;background:#eff6ff;color:#2563eb;border:1px solid #bfdbfe;padding:3px 10px;border-radius:8px;font-size:12px;font-weight:700;text-decoration:none;}
.rlink-btn:hover{background:#dbeafe;}.rlink-none{color:#64748b;font-size:12px;}
</style>
""", unsafe_allow_html=True)


# ── Yardımcı ──────────────────────────────────────────────────────────────

def aks_bul(ilce):
    if not ilce:
        return "DİĞER"
    ilce = str(ilce).strip().upper()
    merkez = {"KONAK","BORNOVA","BAYRAKLI","KARABAĞLAR","BUCA"}
    kuzey  = {"KARŞIYAKA","KARSIYAKA","ÇİĞLİ","CİĞLİ","CIGLI","MENEMEN","ALİAĞA","ALIAĞA","FOÇA","FOCA"}
    yarimada = {"ÇEŞME","CESME","URLA","SEFERİHİSAR","SEFERIHISAR","GÜZELBAHÇE","GUZELBAHCE","NARLIDERE","BALÇOVA","BALCOVA"}
    guney = {"TORBALI","MENDERES","GAZİEMİR","GAZIEMIR","TİRE","TIRE","SELÇUK","SELCUK"}
    if ilce in merkez:   return "İZMİR MERKEZ"
    if ilce in kuzey:    return "KUZEY AKSI"
    if ilce in yarimada: return "YARIMADA"
    if ilce in guney:    return "GÜNEY AKSI"
    return "DİĞER"


@st.cache_data(ttl=60)
def veri_yukle():
    try:
        r = get_client().table("portfoyler")\
            .select("*")\
            .in_("kaynak", ["zeta1","zeta2"])\
            .order("ilan_tarihi", desc=True)\
            .limit(1000)\
            .execute()
        return r.data or []
    except Exception as e:
        st.error(f"Veri yüklenemedi: {e}")
        return []


def ilan_tarihi_parse(deger):
    """
    Revy'den gelen çeşitli tarih formatlarını güvenle parse eder.
    Desteklenen formatlar:
      - "15.03.2024"  (Revy standart)
      - "2024-03-15"  (ISO)
      - "15/03/2024"
      - "2024-03-15T10:30:00"  (ISO datetime)
      - "March 15, 2024" (nadiren)
    Başarısız → None (9999 gün yerine None döner, UI'da "—" gösterilir)
    """
    if not deger or str(deger).strip() in ("", "None", "null", "NaT"):
        return pd.NaT

    s = str(deger).strip()

    # Format denemesi sırası — en yaygından en nadir'e
    formatlar = [
        "%d.%m.%Y",       # 15.03.2024  ← Revy'nin ana formatı
        "%Y-%m-%d",        # 2024-03-15  ← ISO
        "%d/%m/%Y",        # 15/03/2024
        "%Y-%m-%dT%H:%M:%S",  # 2024-03-15T10:30:00
        "%Y-%m-%dT%H:%M:%S.%f",
        "%d-%m-%Y",        # 15-03-2024
        "%m/%d/%Y",        # 03/15/2024  ← ABD formatı (dikkatli)
        "%d.%m.%y",        # 15.03.24
        "%Y/%m/%d",        # 2024/03/15
    ]

    # Önce ISO prefix ile dene (timestamp olabilir)
    try:
        # "2024-03-15 10:30:00+03:00" gibi timezone'lu stringler
        ts = pd.to_datetime(s, utc=False, errors="raise")
        # Mantıklı tarih aralığı kontrolü: 2015-2030 arası
        if pd.Timestamp("2015-01-01") <= ts <= pd.Timestamp("2030-12-31"):
            return ts.normalize()
        return pd.NaT
    except Exception:
        pass

    # Manuel format dene
    for fmt in formatlar:
        try:
            ts = pd.Timestamp(datetime.strptime(s[:len(fmt)], fmt))
            if pd.Timestamp("2015-01-01") <= ts <= pd.Timestamp("2030-12-31"):
                return ts.normalize()
        except Exception:
            continue

    return pd.NaT


def veriyi_hazirla(veriler):
    if not veriler:
        return pd.DataFrame()

    df = pd.DataFrame(veriler)

    # ilan_tarihi — robust parse (9999 gün sorununu önler)
    if "ilan_tarihi" in df.columns:
        df["ilan_tarihi"] = df["ilan_tarihi"].apply(ilan_tarihi_parse)

    if "fiyat" in df.columns:
        df["fiyat_num"] = pd.to_numeric(
            df["fiyat"].astype(str).str.replace(r"[^\d.]","",regex=True),
            errors="coerce"
        )

    bugun = pd.Timestamp.today().normalize()

    if "ilan_tarihi" in df.columns:
        gun_fark = (bugun - df["ilan_tarihi"]).dt.days
        # Negatif veya aşırı büyük değerleri temizle
        # Negatif: tarih bugünden ileri (hatalı veri) → None
        # > 3650 (~10 yıl): parse hatası geçmiş ya da çok eski → None
        gun_fark = gun_fark.where((gun_fark >= 0) & (gun_fark <= 3650), other=pd.NA)
        df["ilan_suresi_gun"] = gun_fark
    elif "ilan_suresi" in df.columns:
        suresi = pd.to_numeric(df["ilan_suresi"], errors="coerce")
        suresi = suresi.where((suresi >= 0) & (suresi <= 3650), other=pd.NA)
        df["ilan_suresi_gun"] = suresi
    else:
        df["ilan_suresi_gun"] = pd.NA

    if "ilce" in df.columns:
        df["aks"] = df["ilce"].apply(aks_bul)

    # Ofis etiketi
    df["ofis_label"] = df["kaynak"].map({"zeta1":"ZETA 1","zeta2":"ZETA 2"}).fillna("DİĞER")

    return df


# ── Sync butonu ───────────────────────────────────────────────────────────

def revy_sync_calistir():
    """revy_sync.py'yi çağırır — aynı makinede çalışır."""
    import subprocess, sys
    sync_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "revy_sync.py"
    )
    if not os.path.exists(sync_path):
        st.error(f"revy_sync.py bulunamadı: {sync_path}")
        return

    log_placeholder = st.empty()
    loglar = []

    def log(msg):
        loglar.append(msg)
        log_placeholder.text("\n".join(loglar[-25:]))

    try:
        log("🚀 Revy Sync başlatılıyor...")
        # revy_sync modülünü import et ve çalıştır
        sys.path.insert(0, os.path.dirname(sync_path))
        import importlib.util
        spec = importlib.util.spec_from_file_location("revy_sync", sync_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        ayarlar = mod.ayarlari_oku()
        sonuclar = mod.sync_tum_ofisler(ayarlar=ayarlar, log_fn=log)

        log("─" * 40)
        for ofis, s in sonuclar.items():
            if "hata" in s:
                log(f"❌ {ofis.upper()}: {s['hata']}")
            else:
                log(f"✅ {ofis.upper()}: {s['eklenen']} yeni, {s['guncellenen']} güncellendi")

        log("✅ Sync tamamlandı!")
        st.cache_data.clear()

    except Exception as e:
        log(f"❌ Hata: {e}")
        import traceback
        log(traceback.format_exc())


# ── SAYFA ─────────────────────────────────────────────────────────────────

# Başlık + Güncelle butonu
h1, h2 = st.columns([5, 1])
with h1:
    render_navbar(
    user_role=st.session_state.get("user_role", "danisan"),
    user_name=st.session_state.get("user_name", ""),
    user_initials=st.session_state.get("user_initials", ""),
)
    render_page_title_selector(
        "🏛 Zeta Ofis Paneli",
        current_page_path="pages/4_Ofis_Paneli.py",
        panel="o",
    )
with h2:
    st.write("")
    if st.button("🔄 Yenile", key="yenile_btn", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Sync butonu
sync_col, _ = st.columns([2, 5])
with sync_col:
    if st.button("⚡ Zeta Portföylerini Güncelle (Revy Sync)", use_container_width=True, type="primary"):
        st.session_state["sync_calistirildi"] = True
        st.rerun()

if st.session_state.get("sync_calistirildi"):
    st.session_state["sync_calistirildi"] = False
    revy_sync_calistir()

# Veri yükle
veriler = veri_yukle()

if not veriler:
    st.info("Henüz Zeta portföy verisi yok. 'Zeta Portföylerini Güncelle' butonuna basarak Revy'den veri çekin.")
    st.stop()

df = veriyi_hazirla(veriler)

# ── Üst Zeta Sekmeleri ────────────────────────────────────────────────────
ust1, ust2, ust3, ust_sp = st.columns([1, 1, 1, 6])
with ust1:
    if st.button("Tümü", key="ust_tumu", use_container_width=True):
        st.session_state["ust_ofis"] = "TÜMÜ"
        st.session_state.pop("zeta_sekme", None)
        st.session_state.pop("op_filtre", None)
        st.rerun()
with ust2:
    if st.button("🏛 ZETA 1", key="ust_z1", use_container_width=True):
        st.session_state["ust_ofis"] = "ZETA 1"
        st.session_state["zeta_sekme"] = "zeta1"
        st.session_state.pop("op_filtre", None)
        st.rerun()
with ust3:
    if st.button("🏛 ZETA 2", key="ust_z2", use_container_width=True):
        st.session_state["ust_ofis"] = "ZETA 2"
        st.session_state["zeta_sekme"] = "zeta2"
        st.session_state.pop("op_filtre", None)
        st.rerun()

ust_ofis = st.session_state.get("ust_ofis", "TÜMÜ")

# Aktif sekme göstergesi — hangi sekme aktif olduğunu renkle göster
sekme_etiketleri = {
    "TÜMÜ": ("Tümü", "#374151", "#f1f5f9"),
    "ZETA 1": ("🏛 ZETA 1", "#5b21b6", "#ede9fe"),
    "ZETA 2": ("🏛 ZETA 2", "#92400e", "#fef3c7"),
}
_etiket, _renk, _bg = sekme_etiketleri.get(ust_ofis, ("Tümü", "#374151", "#f1f5f9"))
components.html(
    f'<div style="font-size:12px;color:#64748b;margin:2px 0 10px 0;">'
    f'Aktif filtre: <span style="background:{_bg};color:{_renk};'
    f'padding:2px 10px;border-radius:999px;font-weight:700;">{_etiket}</span>'
    f' — KPI, grafikler ve liste bu filtreden etkilenir</div>',
    height=32
)

# Filtre uygula — üst sekme KPI + grafik + liste hepsini etkiler
filtered = df.copy()
if ust_ofis == "ZETA 1":
    filtered = filtered[filtered["ofis_label"] == "ZETA 1"]
elif ust_ofis == "ZETA 2":
    filtered = filtered[filtered["ofis_label"] == "ZETA 2"]

# ── KPI Kartları ──────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Genel Durum</div>', unsafe_allow_html=True)

bugun = pd.Timestamp.today().normalize()
toplam = len(filtered)
yeni_7 = int((filtered["ilan_suresi_gun"] <= 7).sum()) if "ilan_suresi_gun" in filtered.columns else 0
yetki_3 = int(((filtered["ilan_suresi_gun"] >= 70) & (filtered["ilan_suresi_gun"] <= 90)).sum()) if "ilan_suresi_gun" in filtered.columns else 0
yetki_6 = int(((filtered["ilan_suresi_gun"] >= 160) & (filtered["ilan_suresi_gun"] <= 180)).sum()) if "ilan_suresi_gun" in filtered.columns else 0
ort_gun = int(filtered["ilan_suresi_gun"].dropna().mean()) if "ilan_suresi_gun" in filtered.columns and not filtered.empty else 0

z1_sayi = int((filtered["ofis_label"] == "ZETA 1").sum())
z2_sayi = int((filtered["ofis_label"] == "ZETA 2").sum())

k1, k2, k3, k4, k5, k6 = st.columns(6)

def kpi(col, label, value, sub="", color=""):
    with col:
        st.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value {color}">{value}</div>'
            f'<div class="kpi-sub">{sub}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

kpi(k1, "Toplam Portföy", toplam, f"Z1: {z1_sayi} · Z2: {z2_sayi}")
kpi(k2, "Son 7 Gün Yeni", yeni_7, "Bu hafta eklenen", "kpi-green" if yeni_7 > 0 else "")
kpi(k3, "Ort. İlan Süresi", f"{ort_gun} gün", "Ortalama yayın süresi", "kpi-amber" if ort_gun > 60 else "")
kpi(k4, "3 Ay Yetki Yaklaşan", yetki_3, "70-90 gün arası", "kpi-amber" if yetki_3 > 0 else "")
kpi(k5, "6 Ay Yetki Yaklaşan", yetki_6, "160-180 gün arası", "kpi-red" if yetki_6 > 0 else "")
kpi(k6, "ZETA 1 / ZETA 2", f"{z1_sayi} / {z2_sayi}", "Ofis dağılımı")

# ── Grafikler ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Analizler</div>', unsafe_allow_html=True)
g1, g2, g3 = st.columns(3)

with g1:
    st.markdown("##### İlçe Dağılımı")
    if "ilce" in filtered.columns and not filtered.empty:
        ilce_ozet = filtered.groupby("ilce").size().reset_index(name="Adet")\
            .sort_values("Adet", ascending=False).head(10)
        fig = px.bar(
            ilce_ozet, x="ilce", y="Adet", text="Adet",
            color_discrete_sequence=["#1e3a5f"]
        )
        fig.update_layout(
            height=320, xaxis_title="", yaxis_title="Adet",
            margin=dict(l=0, r=0, t=10, b=65),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(tickangle=-35, tickfont=dict(size=11)),
        )
        fig.update_xaxes(categoryorder="total descending")
        fig.update_traces(textposition="outside", cliponaxis=False,
                          textfont=dict(size=11, color="#1e3a5f"))
        st.plotly_chart(fig, use_container_width=True)

with g2:
    st.markdown("##### Bölgesel Dağılım (Aks)")
    if "aks" in filtered.columns and not filtered.empty:
        aks_ozet = filtered.groupby("aks").size().reset_index(name="Adet")\
            .sort_values("Adet", ascending=False)
        toplam_aks = aks_ozet["Adet"].sum()
        aks_ozet["Legend"] = aks_ozet.apply(
            lambda r: f'{r["aks"]} · %{round(r["Adet"]/toplam_aks*100,1)}', axis=1)
        KISALT = {
            "İZMİR MERKEZ": "MRK", "DİĞER": "DİĞER",
            "YARIMADA": "YARIMADA", "GÜNEY AKSI": "G.AKSI", "KUZEY AKSI": "K.AKSI",
        }
        aks_ozet["KisaAd"] = aks_ozet["aks"].apply(lambda x: KISALT.get(str(x).upper().strip(), str(x)[:8]))
        renk_paleti = ["#1e3a5f","#ff4d4f","#f59e0b","#22c55e","#8b5cf6","#06b6d4","#ec4899","#14b8a6"]
        fig2 = px.pie(
            aks_ozet, names="Legend", values="Adet", hole=0.42,
            color_discrete_sequence=renk_paleti,
            custom_data=["KisaAd", "Adet"]
        )
        fig2.update_layout(
            height=340,
            margin=dict(l=0, r=0, t=10, b=90),
            paper_bgcolor="white",
            legend=dict(
                orientation="h",
                yanchor="top", y=-0.05,
                xanchor="center", x=0.5,
                font=dict(size=10),
                itemwidth=40,
            ),
        )
        fig2.update_traces(
            texttemplate="%{customdata[0]}<br>%{customdata[1]}",
            textposition="inside",
            textfont=dict(size=10, color="white"),
            insidetextorientation="radial",
            pull=[0.025] * len(aks_ozet),
            hovertemplate="<b>%{label}</b><br>Adet: %{value}<br>Oran: %{percent}<extra></extra>",
        )
        st.plotly_chart(fig2, use_container_width=True)

with g3:
    st.markdown("##### Mülk Tipi Dağılımı")
    if "mulk_tipi" in filtered.columns and not filtered.empty:
        mulk_ozet = filtered.groupby("mulk_tipi").size().reset_index(name="Adet")\
            .sort_values("Adet", ascending=False)
        renk_map = {"Konut": "#94a3b8", "Ticari": "#1e3a5f", "Arsa": "#16a34a"}
        mulk_ozet["Renk"] = mulk_ozet["mulk_tipi"].map(renk_map).fillna("#64748b")
        fig3 = px.bar(
            mulk_ozet, x="mulk_tipi", y="Adet", text="Adet",
            color="mulk_tipi",
            color_discrete_map=renk_map,
        )
        fig3.update_layout(
            height=320, xaxis_title="", yaxis_title="Adet",
            margin=dict(l=0, r=0, t=10, b=40),
            plot_bgcolor="white", paper_bgcolor="white",
            showlegend=False,
        )
        fig3.update_xaxes(categoryorder="total descending")
        fig3.update_traces(textposition="outside", cliponaxis=False,
                           textfont=dict(size=12))
        st.plotly_chart(fig3, use_container_width=True)

# ── Danışman Performansı ──────────────────────────────────────────────────
st.markdown('<div class="section-title">Danışman Performansı</div>', unsafe_allow_html=True)
d1, d2 = st.columns(2)

def danisman_ozet(df_ofis, ofis_adi):
    if "talep_eden_danisan" not in df_ofis.columns or df_ofis.empty:
        return pd.DataFrame()
    ozet = df_ofis.groupby("talep_eden_danisan").size().reset_index(name="adet")
    ozet = ozet.sort_values("adet", ascending=False)
    toplam = ozet["adet"].sum()
    ozet["pay_raw"] = ozet["adet"].apply(lambda x: round((x/toplam)*100,1) if toplam>0 else 0)
    if "islem_tipi" in df_ofis.columns:
        sat_df = df_ofis[df_ofis["islem_tipi"].str.contains("Sat",case=False,na=False)]
        kir_df = df_ofis[df_ofis["islem_tipi"].str.contains("Kira",case=False,na=False)]
        sat_a = sat_df.groupby("talep_eden_danisan").size().reset_index(name="Satılık")
        kir_a = kir_df.groupby("talep_eden_danisan").size().reset_index(name="Kiralık")
        ozet = ozet.merge(sat_a,on="talep_eden_danisan",how="left")
        ozet = ozet.merge(kir_a,on="talep_eden_danisan",how="left")
        ozet["Satılık"] = ozet["Satılık"].fillna(0).astype(int)
        ozet["Kiralık"] = ozet["Kiralık"].fillna(0).astype(int)
        if "ilan_suresi_gun" in df_ofis.columns:
            so = sat_df.groupby("talep_eden_danisan")["ilan_suresi_gun"].mean().reset_index()
            so.columns = ["talep_eden_danisan","sat_ort"]
            ko = kir_df.groupby("talep_eden_danisan")["ilan_suresi_gun"].mean().reset_index()
            ko.columns = ["talep_eden_danisan","kir_ort"]
            ozet = ozet.merge(so,on="talep_eden_danisan",how="left")
            ozet = ozet.merge(ko,on="talep_eden_danisan",how="left")
            ozet["sat_ort"] = ozet["sat_ort"].fillna(0).round(0).astype(int)
            ozet["kir_ort"] = ozet["kir_ort"].fillna(0).round(0).astype(int)
        else:
            ozet["sat_ort"] = 0; ozet["kir_ort"] = 0
    else:
        ozet["Satılık"] = 0; ozet["Kiralık"] = 0
        ozet["sat_ort"] = 0; ozet["kir_ort"] = 0
    return ozet.rename(columns={"talep_eden_danisan":"Danışman"})


def _danisman_html_tablo(perf_df):
    if perf_df.empty: return None
    NS = '<span style="color:#94a3b8;font-size:11px;">—</span>'
    def ort_renk(g):
        if g==0: return '#94a3b8'
        if g<=30: return '#166534'
        if g<=90: return '#92400e'
        if g<=180: return '#991b1b'
        return '#475569'
    td = 'padding:7px 10px;border-bottom:1px solid #f1f5f9;'
    rows = []
    for _, r in perf_df.iterrows():
        dan   = str(r.get('Danışman','')).title()
        sat   = int(r.get('Satılık', 0))
        kir   = int(r.get('Kiralık', 0))
        toplam_dan = sat + kir
        sat_o = int(r.get('sat_ort', 0))
        kir_o = int(r.get('kir_ort', 0))
        pay   = float(r.get('pay_raw', 0))
        toplam_b = f'<span style="background:#f1f5f9;color:#0f172a;padding:1px 8px;border-radius:999px;font-size:11px;font-weight:800;">{toplam_dan}</span>'
        sat_b = (f'<span style="background:#e8edf5;color:#1e3a5f;padding:1px 8px;border-radius:999px;font-size:11px;font-weight:700;">{sat}</span>' if sat>0 else NS)
        kir_b = (f'<span style="background:#e6f7f5;color:#0d9488;padding:1px 8px;border-radius:999px;font-size:11px;font-weight:700;">{kir}</span>' if kir>0 else NS)
        so_h  = (f'<span style="font-size:11px;color:{ort_renk(sat_o)};font-weight:600;">{sat_o}g</span>' if sat_o>0 else NS)
        ko_h  = (f'<span style="font-size:11px;color:{ort_renk(kir_o)};font-weight:600;">{kir_o}g</span>' if kir_o>0 else NS)
        pay_s = f'<span style="font-size:12px;font-weight:700;color:#1e3a5f;">{pay}%</span>'
        rows.append(
            f'<tr>'
            f'<td style="{td}font-weight:600;color:#0f172a;font-size:12px;">{dan}</td>'
            f'<td style="{td}text-align:center;">{toplam_b}</td>'
            f'<td style="{td}text-align:center;">{sat_b}</td>'
            f'<td style="{td}text-align:center;">{kir_b}</td>'
            f'<td style="{td}text-align:center;">{so_h}</td>'
            f'<td style="{td}text-align:center;">{ko_h}</td>'
            f'<td style="{td}text-align:center;">{pay_s}</td>'
            f'</tr>'
        )
    th = 'padding:8px 10px;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:#64748b;border-bottom:2px solid #e2e8f0;background:#f8fafc;'
    bh = (f'<th style="{th}text-align:left;">Danışman</th>'
          f'<th style="{th}text-align:center;">Toplam</th>'
          f'<th style="{th}text-align:center;">Satılık</th>'
          f'<th style="{th}text-align:center;">Kiralık</th>'
          f'<th style="{th}text-align:center;">Sat.Ort</th>'
          f'<th style="{th}text-align:center;">Kir.Ort</th>'
          f'<th style="{th}text-align:center;">Pay %</th>')
    return ('<div style="background:white;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;">'
            '<div style="overflow-y:auto;max-height:340px;">'
            '<table style="width:100%;border-collapse:collapse;">'
            f'<thead><tr>{bh}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody>'
            '</table></div></div>')

with d1:
    st.markdown("**🏛 ZETA 1**")
    z1_df = filtered[filtered["ofis_label"] == "ZETA 1"] if "ofis_label" in filtered.columns else pd.DataFrame()
    perf1 = danisman_ozet(z1_df, "ZETA 1")
    html1 = _danisman_html_tablo(perf1)
    if html1:
        st.markdown(html1, unsafe_allow_html=True)
    else:
        st.info("Veri yok.")

with d2:
    st.markdown("**🏛 ZETA 2**")
    z2_df = filtered[filtered["ofis_label"] == "ZETA 2"] if "ofis_label" in filtered.columns else pd.DataFrame()
    perf2 = danisman_ozet(z2_df, "ZETA 2")
    html2 = _danisman_html_tablo(perf2)
    if html2:
        st.markdown(html2, unsafe_allow_html=True)
    else:
        st.info("Veri yok.")

# ── Operasyonel Takip ─────────────────────────────────────────────────────
st.markdown('<div class="section-title">Operasyonel Takip</div>', unsafe_allow_html=True)
op1, op2, op3 = st.columns(3)

with op1:
    if st.button(f"🆕 Yeni Gelenler ({yeni_7})", use_container_width=True):
        st.session_state["op_filtre"] = "yeni"
        st.rerun()

with op2:
    if st.button(f"⚠️ 3 Ay Yetki ({yetki_3})", use_container_width=True):
        st.session_state["op_filtre"] = "yetki3"
        st.rerun()

with op3:
    if st.button(f"🔥 6 Ay Yetki ({yetki_6})", use_container_width=True):
        st.session_state["op_filtre"] = "yetki6"
        st.rerun()

# ── İlan Listesi ─────────────────────────────────────────────────────────
st.markdown('<div class="section-title">İlan Listesi</div>', unsafe_allow_html=True)

# Operasyonel filtre uygula — filtered (ust_ofis'ten geliyor) üzerine
op_filtre = st.session_state.get("op_filtre", "")
liste_df = filtered.copy()

if op_filtre == "yeni":
    liste_df = liste_df[liste_df["ilan_suresi_gun"] <= 7]
elif op_filtre == "yetki3":
    liste_df = liste_df[(liste_df["ilan_suresi_gun"] >= 70) & (liste_df["ilan_suresi_gun"] <= 90)]
elif op_filtre == "yetki6":
    liste_df = liste_df[(liste_df["ilan_suresi_gun"] >= 160) & (liste_df["ilan_suresi_gun"] <= 180)]

# ── Gelişmiş Filtreler ────────────────────────────────────────────────────
GF_KEYS = ["gf_islem","gf_mulk_t","gf_kullanim","gf_esyali","gf_site",
           "gf_m2_min","gf_m2_max","gf_fiyat_min","gf_fiyat_max",
           "gf_oda","gf_kat","gf_bina_yasi","gf_gun_min","gf_gun_max"]

def gf_aktif_say():
    say = 0
    for k in GF_KEYS:
        v = st.session_state.get(k)
        if v and v not in ("Tümü", "", 0, None):
            say += 1
    return say

gf_say = gf_aktif_say()
exp_label = f"Gelişmiş Filtreler ({gf_say} aktif)" if gf_say > 0 else "Gelişmiş Filtreler"

with st.expander(exp_label, expanded=False):
    gc1, gc2, gc3 = st.columns(3)

    with gc1:
        st.markdown("**İşlem & Mülk**")
        islem_opts = ["Tümü"] + sorted(filtered["islem_tipi"].dropna().unique().tolist()) if "islem_tipi" in filtered.columns else ["Tümü"]
        st.selectbox("İşlem Tipi", islem_opts,
            index=islem_opts.index(st.session_state.get("gf_islem","Tümü")) if st.session_state.get("gf_islem","Tümü") in islem_opts else 0,
            key="gf_islem")

        mulkt_opts = ["Tümü"] + sorted(filtered["mulk_tipi"].dropna().unique().tolist()) if "mulk_tipi" in filtered.columns else ["Tümü"]
        st.selectbox("Mülk Tipi", mulkt_opts,
            index=mulkt_opts.index(st.session_state.get("gf_mulk_t","Tümü")) if st.session_state.get("gf_mulk_t","Tümü") in mulkt_opts else 0,
            key="gf_mulk_t")

        kull_opts = ["Tümü","Boş","Kiracılı","Mülk Sahibi"]
        st.selectbox("Kullanım Durumu", kull_opts,
            index=kull_opts.index(st.session_state.get("gf_kullanim","Tümü")) if st.session_state.get("gf_kullanim","Tümü") in kull_opts else 0,
            key="gf_kullanim")

        esyali_opts = ["Tümü","Evet","Hayır"]
        st.selectbox("Eşyalı", esyali_opts,
            index=esyali_opts.index(st.session_state.get("gf_esyali","Tümü")) if st.session_state.get("gf_esyali","Tümü") in esyali_opts else 0,
            key="gf_esyali")

        site_opts = ["Tümü","Evet","Hayır"]
        st.selectbox("Site İçi", site_opts,
            index=site_opts.index(st.session_state.get("gf_site","Tümü")) if st.session_state.get("gf_site","Tümü") in site_opts else 0,
            key="gf_site")

    with gc2:
        st.markdown("**M² & Fiyat**")
        m2_col1, m2_col2 = st.columns(2)
        with m2_col1:
            st.number_input("M² Alt", min_value=0, value=int(st.session_state.get("gf_m2_min") or 0), step=10, key="gf_m2_min")
        with m2_col2:
            st.number_input("M² Üst", min_value=0, value=int(st.session_state.get("gf_m2_max") or 0), step=10, key="gf_m2_max")

        f_col1, f_col2 = st.columns(2)
        with f_col1:
            st.number_input("Fiyat Alt (₺)", min_value=0, value=int(st.session_state.get("gf_fiyat_min") or 0), step=100000, key="gf_fiyat_min", format="%d")
        with f_col2:
            st.number_input("Fiyat Üst (₺)", min_value=0, value=int(st.session_state.get("gf_fiyat_max") or 0), step=100000, key="gf_fiyat_max", format="%d")

        st.markdown("İlan Süresi Aralığı (gün)")
        _gs1, _gs2 = st.columns(2)
        with _gs1:
            st.number_input("Alt", min_value=0, value=int(st.session_state.get("gf_gun_min") or 0), step=5, key="gf_gun_min")
        with _gs2:
            st.number_input("Üst", min_value=0, value=int(st.session_state.get("gf_gun_max") or 0), step=5, key="gf_gun_max")

    with gc3:
        st.markdown("**Yapı Bilgileri**")
        oda_opts = ["Tümü"] + sorted(filtered["oda_sayisi_m2"].dropna().unique().tolist()) if "oda_sayisi_m2" in filtered.columns else ["Tümü"]
        st.selectbox("Oda Sayısı", oda_opts,
            index=oda_opts.index(st.session_state.get("gf_oda","Tümü")) if st.session_state.get("gf_oda","Tümü") in oda_opts else 0,
            key="gf_oda")

        kat_opts = ["Tümü"] + sorted(filtered["kat"].dropna().unique().tolist()) if "kat" in filtered.columns else ["Tümü"]
        st.selectbox("Bulunduğu Kat", kat_opts,
            index=kat_opts.index(st.session_state.get("gf_kat","Tümü")) if st.session_state.get("gf_kat","Tümü") in kat_opts else 0,
            key="gf_kat")

        yas_opts = ["Tümü"] + sorted(filtered["bina_yasi"].dropna().unique().tolist()) if "bina_yasi" in filtered.columns else ["Tümü"]
        st.selectbox("Bina Yaşı", yas_opts,
            index=yas_opts.index(st.session_state.get("gf_bina_yasi","Tümü")) if st.session_state.get("gf_bina_yasi","Tümü") in yas_opts else 0,
            key="gf_bina_yasi")

        st.markdown("&nbsp;", unsafe_allow_html=True)
        if gf_say > 0:
            if st.button("✕ Gelişmiş Filtreleri Temizle", key="gf_temizle", use_container_width=True):
                for k in GF_KEYS:
                    st.session_state.pop(k, None)
                st.rerun()

# Gelişmiş filtreleri uygula
def parse_fiyat_num(v):
    try:
        return float(str(v).replace(".","").replace(",",".").replace("₺","").replace("TL","").strip())
    except Exception:
        return None

if st.session_state.get("gf_islem","Tümü") != "Tümü" and "islem_tipi" in liste_df.columns:
    liste_df = liste_df[liste_df["islem_tipi"] == st.session_state["gf_islem"]]
if st.session_state.get("gf_mulk_t","Tümü") != "Tümü" and "mulk_tipi" in liste_df.columns:
    liste_df = liste_df[liste_df["mulk_tipi"] == st.session_state["gf_mulk_t"]]
if st.session_state.get("gf_kullanim","Tümü") != "Tümü" and "kullanim_durumu" in liste_df.columns:
    liste_df = liste_df[liste_df["kullanim_durumu"] == st.session_state["gf_kullanim"]]
if st.session_state.get("gf_esyali","Tümü") != "Tümü" and "esyali" in liste_df.columns:
    liste_df = liste_df[liste_df["esyali"] == st.session_state["gf_esyali"]]
if st.session_state.get("gf_site","Tümü") != "Tümü" and "site_icerisinde" in liste_df.columns:
    liste_df = liste_df[liste_df["site_icerisinde"] == st.session_state["gf_site"]]
if st.session_state.get("gf_oda","Tümü") != "Tümü" and "oda_sayisi_m2" in liste_df.columns:
    liste_df = liste_df[liste_df["oda_sayisi_m2"] == st.session_state["gf_oda"]]
if st.session_state.get("gf_kat","Tümü") != "Tümü" and "kat" in liste_df.columns:
    liste_df = liste_df[liste_df["kat"] == st.session_state["gf_kat"]]
if st.session_state.get("gf_bina_yasi","Tümü") != "Tümü" and "bina_yasi" in liste_df.columns:
    liste_df = liste_df[liste_df["bina_yasi"] == st.session_state["gf_bina_yasi"]]
if st.session_state.get("gf_m2_min", 0) and "m2" in liste_df.columns:
    liste_df = liste_df[pd.to_numeric(liste_df["m2"], errors="coerce").fillna(0) >= st.session_state["gf_m2_min"]]
if st.session_state.get("gf_m2_max", 0) and "m2" in liste_df.columns:
    liste_df = liste_df[pd.to_numeric(liste_df["m2"], errors="coerce").fillna(99999) <= st.session_state["gf_m2_max"]]
if st.session_state.get("gf_fiyat_min", 0) and "fiyat" in liste_df.columns:
    liste_df = liste_df[liste_df["fiyat"].apply(parse_fiyat_num).fillna(0) >= st.session_state["gf_fiyat_min"]]
if st.session_state.get("gf_fiyat_max", 0) and "fiyat" in liste_df.columns:
    liste_df = liste_df[liste_df["fiyat"].apply(parse_fiyat_num).fillna(float("inf")) <= st.session_state["gf_fiyat_max"]]
gf_gun_min_v = int(st.session_state.get("gf_gun_min") or 0)
gf_gun_max_v = int(st.session_state.get("gf_gun_max") or 0)
if gf_gun_min_v > 0 and "ilan_suresi_gun" in liste_df.columns:
    liste_df = liste_df[liste_df["ilan_suresi_gun"].fillna(0) >= gf_gun_min_v]
if gf_gun_max_v > 0 and "ilan_suresi_gun" in liste_df.columns:
    liste_df = liste_df[liste_df["ilan_suresi_gun"].fillna(9999) <= gf_gun_max_v]

# İlan listesi filtreleri + sıralama + görünüm seçici
lf0, lf1, lf2, lf3, lf4, lf_sir, lf5, lg1, lg2, lg3 = st.columns([1.1, 1.3, 1.3, 1.3, 1.3, 1.5, 0.6, 0.7, 0.7, 0.7])
ofis_sec_opts = ['Tümü', 'ZETA 1', 'ZETA 2']
dan_list  = ['Tümü'] + sorted(filtered['talep_eden_danisan'].dropna().unique().tolist()) if 'talep_eden_danisan' in filtered.columns else ['Tümü']
ilce2_list = ['Tümü'] + sorted(filtered['ilce'].dropna().unique().tolist()) if 'ilce' in filtered.columns else ['Tümü']
tur_list  = ['Tümü'] + sorted(filtered['mulk_turu'].dropna().unique().tolist()) if 'mulk_turu' in filtered.columns else ['Tümü']

with lf0:
    ofis_filtre = st.selectbox("Ofis", ofis_sec_opts,
        index=ofis_sec_opts.index(st.session_state.get("liste_ofis","Tümü")) if st.session_state.get("liste_ofis","Tümü") in ofis_sec_opts else 0,
        key="liste_ofis", label_visibility="collapsed")
with lf1:
    ara = st.text_input("Ara", placeholder="Başlık, ilçe...",
        key="liste_ara", label_visibility="collapsed")
with lf2:
    dan_sec = st.selectbox("Danışman", dan_list,
        index=dan_list.index(st.session_state.get("liste_dan","Tümü")) if st.session_state.get("liste_dan","Tümü") in dan_list else 0,
        key="liste_dan", label_visibility="collapsed")
with lf3:
    ilce2_sec = st.selectbox("İlçe", ilce2_list,
        index=ilce2_list.index(st.session_state.get("liste_ilce","Tümü")) if st.session_state.get("liste_ilce","Tümü") in ilce2_list else 0,
        key="liste_ilce", label_visibility="collapsed")
with lf4:
    tur_sec = st.selectbox("Mülk Türü", tur_list,
        index=tur_list.index(st.session_state.get("liste_tur","Tümü")) if st.session_state.get("liste_tur","Tümü") in tur_list else 0,
        key="liste_tur", label_visibility="collapsed")
with lf_sir:
    _SIR_OPTS = ["Tarih ↓ (Yeni→Eski)","Tarih ↑ (Eski→Yeni)",
        "Fiyat ↑","Fiyat ↓","M² ↑","M² ↓",
        "m² Fiyatı ↑","m² Fiyatı ↓","Süre ↑","Süre ↓"]
    _cur = st.session_state.get("liste_siralama", _SIR_OPTS[0])
    st.selectbox("Sırala", _SIR_OPTS,
        index=_SIR_OPTS.index(_cur) if _cur in _SIR_OPTS else 0,
        key="liste_siralama", label_visibility="collapsed")
with lf5:
    filtre_aktif = bool(op_filtre or st.session_state.get("liste_ara","") or
        st.session_state.get("liste_ofis","Tümü") != "Tümü" or
        st.session_state.get("liste_dan","Tümü") != "Tümü" or
        st.session_state.get("liste_ilce","Tümü") != "Tümü" or
        st.session_state.get("liste_tur","Tümü") != "Tümü")
    if filtre_aktif:
        if st.button("✕", key="filtre_temizle_ust", use_container_width=True):
            for k in ["op_filtre","liste_ofis","liste_dan","liste_ilce","liste_tur"]:
                st.session_state.pop(k, None)
            st.rerun()

with lg1:
    if st.button("☰ Liste", key="gorunum_liste", use_container_width=True):
        st.session_state["liste_gorunum"] = "liste"; st.rerun()
with lg2:
    if st.button("▦ Kart", key="gorunum_kart", use_container_width=True):
        st.session_state["liste_gorunum"] = "kart"; st.rerun()
with lg3:
    if st.button("▤ Tablo", key="gorunum_tablo", use_container_width=True):
        st.session_state["liste_gorunum"] = "tablo"; st.rerun()

# Filtreleri uygula
if ofis_filtre != "Tümü" and "ofis_label" in liste_df.columns:
    liste_df = liste_df[liste_df["ofis_label"] == ofis_filtre]
if ara:
    ara_lower = ara.lower()
    liste_df = liste_df[liste_df.apply(
        lambda r: any(ara_lower in str(r.get(c,"")).lower()
                     for c in ["talep_eden_danisan","ozet","ilce","mahalle"]), axis=1)]
if dan_sec != "Tümü" and "talep_eden_danisan" in liste_df.columns:
    liste_df = liste_df[liste_df["talep_eden_danisan"] == dan_sec]
if ilce2_sec != "Tümü" and "ilce" in liste_df.columns:
    liste_df = liste_df[liste_df["ilce"] == ilce2_sec]
if tur_sec != "Tümü" and "mulk_turu" in liste_df.columns:
    liste_df = liste_df[liste_df["mulk_turu"] == tur_sec]

# Sıralama uygula
def _sf(v):
    try: return float(str(v).replace(".","").replace(",",".").replace("₺","").replace("TL","").strip())
    except: return float("inf")
_sir = st.session_state.get("liste_siralama","Tarih ↓ (Yeni→Eski)")
if not liste_df.empty:
    if "Tarih ↓" in _sir and "ilan_suresi_gun" in liste_df.columns:
        liste_df = liste_df.sort_values("ilan_suresi_gun", ascending=True, na_position="last")
    elif "Tarih ↑" in _sir and "ilan_suresi_gun" in liste_df.columns:
        liste_df = liste_df.sort_values("ilan_suresi_gun", ascending=False, na_position="last")
    elif "Fiyat" in _sir:
        _a = "↑" in _sir; _t = liste_df.copy(); _t["__s"] = _t.get("fiyat",pd.Series(dtype=str)).apply(_sf)
        liste_df = _t.sort_values("__s",ascending=_a,na_position="last").drop(columns=["__s"])
    elif "M²" in _sir and "Fiyat" not in _sir:
        _a = "↑" in _sir; _t = liste_df.copy(); _t["__s"] = pd.to_numeric(_t.get("m2",pd.Series(dtype=str)),errors="coerce")
        liste_df = _t.sort_values("__s",ascending=_a,na_position="last").drop(columns=["__s"])
    elif "m² Fiyat" in _sir:
        _a = "↑" in _sir
        def _mf(r):
            try: f=_sf(r.get("fiyat")); m=float(str(r.get("m2","0")).replace(",",".")); return f/m if m>0 and f<float("inf") else float("inf")
            except: return float("inf")
        _t = liste_df.copy(); _t["__s"] = _t.apply(_mf,axis=1)
        liste_df = _t.sort_values("__s",ascending=_a,na_position="last").drop(columns=["__s"])
    elif "Süre" in _sir and "ilan_suresi_gun" in liste_df.columns:
        _a = "↑" in _sir
        liste_df = liste_df.sort_values("ilan_suresi_gun",ascending=_a,na_position="last")

gorunum = st.session_state.get("liste_gorunum", "liste")

# Üst bar: sayı + Excel
hd1, hd2 = st.columns([5,1])
with hd1:
    etiket = {"yeni":"🆕 Yeni gelenler","yetki3":"⚠️ 3 ay yetki","yetki6":"🔥 6 ay yetki"}.get(op_filtre,"")
    st.caption(f"{len(liste_df)} portföy {('· ' + etiket) if etiket else ''}")
with hd2:
    if not liste_df.empty:
        from io import BytesIO
        output = BytesIO()
        export_cols = {
            "ofis_label":"Ofis","talep_eden_danisan":"Danışman",
            "ozet":"Başlık","mulk_tipi":"Mülk","mulk_turu":"Mülk Türü",
            "islem_tipi":"İşlem","ilce":"İlçe","mahalle":"Mahalle",
            "fiyat":"Fiyat","oda_sayisi_m2":"Oda/M²",
            "ilan_suresi_gun":"Gün","ilan_linki":"Link",
        }
        ex_df = liste_df[[c for c in export_cols if c in liste_df.columns]].rename(columns=export_cols)
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            ex_df.to_excel(writer, index=False, sheet_name="Zeta Portföy")
        output.seek(0)
        st.download_button("📥 Excel", data=output.getvalue(),
            file_name="zeta_portfoy.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)

if liste_df.empty:
    st.info("Gösterilecek portföy bulunamadı.")
    if st.button("✕ Filtreleri Temizle", key="filtre_temizle_bos"):
        for k in ["op_filtre","liste_ofis","liste_dan","liste_ilce","liste_tur"]:
            st.session_state.pop(k, None)
        st.rerun()
    st.stop()

# ── Görünüm: Liste (HTML) ─────────────────────────────────────────────────
import html as _html

def _safe(v):
    if v is None: return '-'
    s = str(v).strip()
    return _html.escape(s) if s else '-'

def _type_cell(islem, mulk_t, mulk_tip):
    tip = str(islem).strip().lower() if islem else ''
    cls = 'type-satilik' if 'sat' in tip else ('type-kiralik' if 'kir' in tip else '')
    alt = _safe(mulk_t)
    if _safe(mulk_tip) not in ('-', ''): alt = _safe(mulk_t) + ' / ' + _safe(mulk_tip)
    return '<div class="cell-wrap"><div class="cell-top ' + cls + '">' + _safe(islem) + '</div><div class="cell-bottom">' + alt + '</div></div>'

def _konum_cell(ilce, mah):
    return '<div class="cell-wrap"><div class="cell-top">' + _safe(ilce) + '</div><div class="cell-bottom">' + _safe(mah) + '</div></div>'

def _fiyat_cell(fiyat, m2_birim=None, m2=None):
    def parse_num(v):
        if not v or str(v).strip() in ("", "nan", "None", "-"):
            return None
        try:
            return float(str(v).replace(".", "").replace(",", ".").replace("\u20ba", "").replace("TL", "").strip())
        except Exception:
            return None

    fiyat_num = parse_num(fiyat)
    if fiyat_num is not None:
        ust = ('<div style="font-size:13px;font-weight:700;color:#0f172a;white-space:nowrap;">'
               + "{:,.0f} \u20ba".format(fiyat_num).replace(",", ".")
               + "</div>")
    else:
        ust = '<div style="font-size:13px;font-weight:700;color:#94a3b8;">-</div>'

    # m2 birim fiyati: once tablodaki deger, yoksa hesapla
    birim_num = parse_num(m2_birim)
    if birim_num is None:
        m2_num = parse_num(m2)
        if fiyat_num and m2_num and m2_num > 0:
            birim_num = round(fiyat_num / m2_num)

    alt = ""
    if birim_num is not None:
        alt = ('<div style="font-size:11px;color:#64748b;margin-top:2px;white-space:nowrap;">'
               + "m\u00b2: {:,.0f} \u20ba".format(birim_num).replace(",", ".")
               + "</div>")

    return "<div>" + ust + alt + "</div>"



def _ozellik_tags(kullanim=None, esyali=None, site_ici=None, baslik=None):
    import html as _hx

    def safe_esc(v):
        return _hx.escape(str(v).strip()) if v else ""

    # Supabase degerler: "Bos", "Kiracilik", "Mulk Sahibi", "Evet", "Hayir"
    KULLANIM_MAP = {
        "bos": ("#166534", "#dcfce7", "Bos"),
        "bo\u015f": ("#166534", "#dcfce7", "Bos"),
        "kiracilik": ("#92400e", "#fef3c7", "Kiracili"),
        "kiraci": ("#92400e", "#fef3c7", "Kiracili"),
        "kiracili": ("#92400e", "#fef3c7", "Kiracili"),
        "mulk sahibi": ("#1e40af", "#dbeafe", "Mulk Sahibi"),
    }

    tags = []

    def pill(text, fg, bg):
        return ('<span style="display:inline-block;padding:2px 8px;border-radius:999px;' +
                'font-size:10px;font-weight:700;margin-right:4px;' +
                'color:' + fg + ';background:' + bg + ';">' + text + '</span>')

    # Kullanim durumu
    if kullanim and str(kullanim).strip() not in ("", "nan", "None", "-"):
        ku = str(kullanim).strip()
        ku_key = ku.lower()
        if ku_key in KULLANIM_MAP:
            fg, bg, label = KULLANIM_MAP[ku_key]
            tags.append(pill(label, fg, bg))
        else:
            tags.append(pill(safe_esc(ku), "#475569", "#f1f5f9"))

    # Esyali -- sadece Evet goster, Hayir gizle
    if esyali and str(esyali).strip() not in ("", "nan", "None", "-"):
        es = str(esyali).strip().lower()
        if es in ("evet", "esyali", "var", "true", "1"):
            tags.append(pill("Esyali", "#166534", "#dcfce7"))

    # Site ici -- sadece Evet goster
    if site_ici and str(site_ici).strip() not in ("", "nan", "None", "-"):
        si = str(site_ici).strip().lower()
        if si in ("evet", "var", "true", "1"):
            tags.append(pill("Site Ici", "#92400e", "#fef3c7"))

    # Baslik: koyu, okunakli -- en uste
    baslik_html = ""
    if baslik and str(baslik).strip() not in ("", "nan", "None", "--"):
        b = safe_esc(str(baslik).strip()[:90])
        baslik_html = ('<div style="font-size:13px;color:#0f172a;font-weight:700;' +
                       'line-height:1.35;margin-bottom:5px;">' + b + '</div>')

    # Tag'ler basligin altinda -- inline blok, bosluklu
    tag_html = ""
    if tags:
        tag_html = '<div style="margin-top:2px;">' + "".join(tags) + '</div>'

    return baslik_html + tag_html



def _sure_cell(gun_val, ilan_tarihi=None):
    gun = None
    try:
        if gun_val is not None:
            g = float(gun_val)
            if 0 <= g <= 3650:
                gun = int(g)
    except Exception:
        pass
    if gun is None and ilan_tarihi:
        try:
            t = pd.to_datetime(ilan_tarihi, errors='coerce', dayfirst=True)
            if pd.notna(t):
                fark = int((pd.Timestamp.today().normalize() - t.normalize()).days)
                if 0 <= fark <= 3650:
                    gun = fark
        except Exception:
            pass
    if gun is None:
        gh = '<span class="rbadge rbadge-gray">— gün</span>'
    elif gun <= 7:
        gh = '<span class="rbadge rbadge-green"><span style="font-size:9px;">🟢</span> ' + str(gun) + ' gün</span>'
    elif gun <= 30:
        gh = '<span class="rbadge rbadge-yellow"><span style="font-size:9px;">🟡</span> ' + str(gun) + ' gün</span>'
    elif gun <= 90:
        gh = '<span class="rbadge rbadge-orange"><span style="font-size:9px;">🟠</span> ' + str(gun) + ' gün</span>'
    elif gun <= 180:
        gh = '<span class="rbadge rbadge-red"><span style="font-size:9px;">🔴</span> ' + str(gun) + ' gün</span>'
    else:
        gh = '<span class="rbadge rbadge-gray"><span style="font-size:9px;">⚫</span> ' + str(gun) + ' gün</span>'
    tarih_html = ''
    if ilan_tarihi:
        try:
            t = pd.to_datetime(ilan_tarihi, errors='coerce', dayfirst=True)
            if pd.notna(t):
                tarih_html = '<div class="dur-date">Ilan: <b>' + t.strftime('%d.%m.%Y') + '</b></div>'
        except Exception:
            pass
    return '<div class="dur-wrap">' + tarih_html + '<div class="dur-line">' + gh + '</div></div>'

def _kat_yas_cell(kat=None, bina_yasi=None):
    kat_s = _safe(kat) if kat and str(kat).strip() not in ('', 'nan', 'None', '-') else '-'
    yas_s = _safe(bina_yasi) if bina_yasi and str(bina_yasi).strip() not in ('', 'nan', 'None', '-') else '-'
    return '<div class="cell-wrap"><div class="cell-top">' + kat_s + '</div><div class="cell-bottom">' + yas_s + '</div></div>'


def _link_btn(url):
    if not url or str(url).strip() in ('', 'None'): return '<span class="rlink-none">-</span>'
    u = _html.escape(str(url).strip(), quote=True)
    return '<a class="rlink-btn" href="' + u + '" target="_blank">Ac</a>'

def _ofis_dan_cell(ofis_label, danisan):
    return '<div class="cell-wrap"><div class="cell-top" style="font-size:12px;font-weight:700;color:#374151;">' + _safe(ofis_label) + '</div><div class="cell-bottom">' + _safe(danisan) + '</div></div>'

def fiyat_formatla(fiyat):
    try:
        f = float(str(fiyat).replace(".","").replace(",",".").replace("₺","").replace("TL","").strip())
        return f"{f:,.0f} ₺".replace(",",".")
    except Exception:
        return str(fiyat) if fiyat else "—"

def baslik_formatla(metin):
    if not metin:
        return "—"
    s = str(metin).strip()
    return s.title() if s.isupper() or s.islower() else s


def normalize_match_text(text):
    if not text:
        return ""
    s = str(text).strip().lower()
    s = s.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    s = (s.replace("ç", "c").replace("ğ", "g").replace("ı", "i").replace("ö", "o")
          .replace("ş", "s").replace("ü", "u").replace("â", "a").replace("î", "i")
          .replace("û", "u").replace("ä", "a").replace("ë", "e"))
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\b(satilik|satış|satis|kiralik|kiralama|daire|konut|portfoy|portfolio|startkey|zeta1|zeta 1|zeta2|zeta 2)\b", " ", s)
    return " ".join(s.split())


def _numeric_value(value):
    if value is None:
        return None
    try:
        return float(str(value).replace(".", "").replace(",", ".").replace("₺", "").replace("TL", "").strip())
    except Exception:
        return None


def _relative_score(value_a, value_b, thresholds):
    if value_a is None or value_b is None or value_a <= 0 or value_b <= 0:
        return 0.0
    diff = abs(value_a - value_b) / max(value_a, value_b)
    for limit, score in thresholds:
        if diff <= limit:
            return score
    return 0.0


def _is_same_text(a, b):
    a = normalize_match_text(a)
    b = normalize_match_text(b)
    return bool(a and b and a == b)


def _token_overlap(a, b):
    a_tokens = set(normalize_match_text(a).split())
    b_tokens = set(normalize_match_text(b).split())
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / max(1, len(a_tokens | b_tokens))


def _parse_startkey_photo_list(value):
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if not value or str(value).strip().lower() in ("", "nan", "none"):
        return []
    try:
        parsed = ast.literal_eval(str(value))
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _ofis_label_to_kaynak(ofis_label):
    if not ofis_label:
        return ""
    label = str(ofis_label).strip().lower()
    if "zeta 1" in label or "zeta1" in label:
        return "zeta1"
    if "zeta 2" in label or "zeta2" in label:
        return "zeta2"
    return ""


@st.cache_data
def startkey_fotolari_yukle():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "core", "debug_startkey"))
    paths = [
        os.path.join(base, "startkey_zeta1_details.xlsx"),
        os.path.join(base, "startkey_zeta2_details.xlsx"),
    ]
    dfs = []
    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_excel(path)
        except Exception:
            continue
        if "foto_url_listesi" in df.columns:
            df["foto_url_listesi"] = df["foto_url_listesi"].apply(_parse_startkey_photo_list)
        else:
            df["foto_url_listesi"] = [[] for _ in range(len(df))]
        df["kaynak"] = df["kaynak"].astype(str).str.strip().str.lower()
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame(
        columns=["kaynak", "baslik", "ilk_foto_url", "foto_url_listesi", "startkey_detay_link"]
    )


def _ofis_label_to_kaynak(ofis_label):
    if not ofis_label:
        return ""
    label = str(ofis_label).strip().lower()
    if "zeta 1" in label or "zeta1" in label:
        return "zeta1"
    if "zeta 2" in label or "zeta2" in label:
        return "zeta2"
    return ""


def startkey_eslesme_bul(row, startkey_df):
    kaynak = _ofis_label_to_kaynak(row.get("ofis_label", ""))
    if not kaynak or startkey_df.empty:
        st.session_state["startkey_match_score"] = 0.0
        return {}

    hedef = normalize_match_text(row.get("ozet", "") or "")
    if not hedef:
        st.session_state["startkey_match_score"] = 0.0
        return {}

    row_ilce = normalize_match_text(row.get("ilce", "") or "")
    row_mah = normalize_match_text(row.get("mahalle", "") or "")
    row_islem = normalize_match_text(row.get("islem_tipi", "") or "")
    row_mulk_tipi = normalize_match_text(row.get("mulk_tipi", "") or "")
    row_mulk_turu = normalize_match_text(row.get("mulk_turu", "") or "")
    row_m2 = _numeric_value(row.get("m2", ""))
    row_fiyat = _numeric_value(row.get("fiyat_num", row.get("fiyat", "")))

    adaylar = startkey_df[startkey_df["kaynak"] == kaynak]
    if adaylar.empty:
        st.session_state["startkey_match_score"] = 0.0
        return {}

    best = None
    best_score = 0.0
    best_meta = {}
    best_sk_fiyat = None
    best_sk_m2 = None
    best_sk_ilce = ""
    for _, sk in adaylar.iterrows():
        baslik = normalize_match_text(sk.get("baslik", "") or "")
        if not baslik:
            continue

        sk_ilce = normalize_match_text(sk.get("ilce", "") or "")
        sk_mah = normalize_match_text(sk.get("mahalle", "") or "")
        sk_islem = normalize_match_text(sk.get("islem_tipi", "") or "")
        sk_mulk_tipi = normalize_match_text(sk.get("mulk_tipi", "") or "")
        sk_mulk_turu = normalize_match_text(sk.get("mulk_turu", "") or "")
        sk_m2 = _numeric_value(sk.get("m2", sk.get("metrekare", "")))
        sk_fiyat = _numeric_value(sk.get("fiyat_num", sk.get("fiyat", "")))

        title_score = difflib.SequenceMatcher(None, hedef, baslik).ratio()
        fiyat_score = _relative_score(row_fiyat, sk_fiyat, [(0.10, 1.0), (0.25, 0.75), (0.50, 0.5)])
        m2_score = _relative_score(row_m2, sk_m2, [(0.10, 1.0), (0.25, 0.75), (0.50, 0.5)])
        islem_score = 1.0 if row_islem and row_islem == sk_islem else 0.0
        mulk_score = max(
            _token_overlap(row_mulk_tipi, sk_mulk_tipi),
            _token_overlap(row_mulk_turu, sk_mulk_turu),
            _token_overlap(row_mulk_tipi + " " + row_mulk_turu, sk_mulk_tipi + " " + sk_mulk_turu),
        )
        ilce_match = 1.0 if row_ilce and row_ilce == sk_ilce else 0.0
        mah_match = 1.0 if row_mah and row_mah == sk_mah else 0.0

        score = (
            title_score * 0.45
            + fiyat_score * 0.15
            + ilce_match * 0.12
            + mah_match * 0.10
            + m2_score * 0.10
            + islem_score * 0.05
            + mulk_score * 0.03
        )

        if score > best_score:
            best_score = score
            best = sk
            best_sk_fiyat = sk_fiyat
            best_sk_m2 = sk_m2
            best_sk_ilce = sk_ilce
            best_meta = {
                "title_score": title_score,
                "fiyat_score": fiyat_score,
                "ilce_match": ilce_match,
                "mah_match": mah_match,
                "m2_score": m2_score,
                "islem_score": islem_score,
                "mulk_score": mulk_score,
            }

    accepted = False
    if best is not None:
        if best_score > 0.70:
            accepted = True
        elif 0.55 <= best_score <= 0.70:
            title_high = best_meta.get("title_score", 0.0) >= 0.75
            fiyat_close = (
                row_fiyat is not None
                and best_sk_fiyat is not None
                and _relative_score(row_fiyat, best_sk_fiyat, [(0.20, 1.0)]) == 1.0
            )
            ilce_same = bool(row_ilce and best_sk_ilce and row_ilce == best_sk_ilce)
            islem_same = best_meta.get("islem_score", 0.0) > 0.0

            if title_high and fiyat_close:
                accepted = True
            elif title_high and ilce_same:
                accepted = True
            elif fiyat_close and ilce_same and islem_same:
                accepted = True

    if not accepted:
        fallback_best = None
        fallback_score = 0.0
        for _, sk in adaylar.iterrows():
            baslik = normalize_match_text(sk.get("baslik", "") or "")
            if not baslik:
                continue
            title_score = difflib.SequenceMatcher(None, hedef, baslik).ratio()
            if title_score > fallback_score:
                fallback_score = title_score
                fallback_best = sk

        if fallback_best is not None and fallback_score >= 0.62:
            best = fallback_best
            best_score = fallback_score
            accepted = True

    st.session_state["startkey_match_score"] = round(best_score, 4)
    if not accepted or best is None:
        return {}

    foto_url = str(best.get("ilk_foto_url", "") or "").strip()
    if not foto_url:
        foto_urls = best.get("foto_url_listesi", [])
        if isinstance(foto_urls, (list, tuple)) and foto_urls:
            foto_url = str(foto_urls[0]).strip()

    return {
        "foto_url": foto_url,
        "startkey_detay_link": str(best.get("startkey_detay_link", "") or "").strip(),
        "foto_url_listesi": best.get("foto_url_listesi", []),
        "match_score": best_score,
        "match_meta": best_meta,
    }

if gorunum == "liste":
    satirlar = ""
    for sira, (_, row) in enumerate(liste_df.iterrows(), 1):
        ofis      = row.get("ofis_label","") or ""
        dan       = baslik_formatla(row.get("talep_eden_danisan","")) or "-"
        baslik    = baslik_formatla(str(row.get("ozet","") or ""))
        mulk_t    = row.get("mulk_tipi","") or ""
        mulk_r    = row.get("mulk_turu","") or ""
        islem     = row.get("islem_tipi","") or ""
        ilce      = str(row.get("ilce","") or "").title()
        mah       = str(row.get("mahalle","") or "").title()
        oda       = str(row.get("oda_sayisi_m2","") or "-")
        gun       = row.get("ilan_suresi_gun")
        link      = row.get("ilan_linki","") or ""
        ilan_t    = row.get("ilan_tarihi","") or ""
        kullanim  = row.get("kullanim_durumu","") or ""
        esyali    = row.get("esyali","") or ""
        site_ici  = row.get("site_icerisinde","") or ""
        fiyat     = row.get("fiyat","") or ""
        m2_birim  = row.get("m2_fiyat","") or row.get("birim_fiyat","") or ""
        m2        = str(row.get("m2","") or "")
        kat       = row.get("kat","") or ""
        bina_yasi = row.get("bina_yasi","") or ""
        # Sol border: Satilik=lacivert, Kiralik=teal -- ilk TD padding-left ile
        tip = str(islem).strip().lower()
        bdr = "#1e3a5f" if "sat" in tip else ("#0d9488" if "kir" in tip else "#e2e8f0")
        # M2
        m2_html = ("-" if not m2 or m2 in ("","None","nan") else m2 + " m²")
        # Hucreler
        oz_cell  = _ozellik_tags(kullanim, esyali, site_ici, baslik)
        f_cell   = _fiyat_cell(fiyat, m2_birim, m2)
        t_cell   = _type_cell(islem, mulk_r, mulk_t)
        k_cell   = _konum_cell(ilce, mah)
        ky_cell  = _kat_yas_cell(kat, bina_yasi)
        s_cell   = _sure_cell(gun, ilan_t)
        l_btn    = _link_btn(link)
        ofis_html = ("<div style=\"font-size:11px;font-weight:700;color:#374151;\">" + _safe(ofis) + "</div>"
                    + "<div style=\"font-size:11px;color:#94a3b8;margin-top:2px;\">" + _safe(dan) + "</div>")
        # Sol border: ilk TD nin sol kenarinda kalin cizgi
        td0 = ("padding:9px 4px 9px 0;border-left:3px solid " + bdr + ";")
        td_s = "padding:9px 12px;"
        satirlar += ("<tr>"
            + "<td style=\"" + td0 + "width:3px;\"></td>"
            + "<td style=\"" + td_s + "color:#94a3b8;font-size:11px;white-space:nowrap;\">" + str(sira) + "</td>"
            + "<td style=\"" + td_s + "max-width:280px;min-width:220px;\">" + oz_cell + "</td>"
            + "<td style=\"" + td_s + "\">" + t_cell + "</td>"
            + "<td style=\"" + td_s + "\">" + k_cell + "</td>"
            + "<td style=\"" + td_s + "white-space:nowrap;color:#475569;\">" + m2_html + "</td>"
            + "<td style=\"" + td_s + "white-space:nowrap;\">" + f_cell + "</td>"
            + "<td style=\"" + td_s + "color:#475569;white-space:nowrap;\">" + oda + "</td>"
            + "<td style=\"" + td_s + "\">" + ky_cell + "</td>"
            + "<td style=\"" + td_s + "\">" + s_cell + "</td>"
            + "<td style=\"" + td_s + "\">" + l_btn + "</td>"
            + "<td style=\"" + td_s + "white-space:nowrap;\">" + ofis_html + "</td>"
            + "</tr>")
    BSLKLAR = ["", "#", "Başlık / Özellikler", "İşlem / Mülk",
               "İlçe / Mah", "M²", "Fiyat / m²",
               "Oda", "Kat / Yaş", "Süre / Tarih", "İlan", "Ofis / Dan."]
    hover_css = ("<style>"
        + ".ht tbody tr:hover td{background:#f0f4ff!important;}"
        + "</style>")
    ths = "padding:9px 12px;text-align:left;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:#64748b;border-bottom:2px solid #e2e8f0;background:#f8fafc;white-space:nowrap;"
    bh = "".join("<th style=\"" + ths + "\">" + b + "</th>" for b in BSLKLAR)
    html_tablo = (hover_css
        + "<div style=\"background:white;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;\">"
        + "<div style=\"overflow-x:auto;\">"
        + "<table class=\"ht\"><thead><tr>" + bh + "</tr></thead>"
        + "<tbody>" + satirlar + "</tbody></table></div></div>")
    components.html(html_tablo, height=min(800, 90 + len(liste_df) * 56), scrolling=True)

# ── Görünüm: Kart ─────────────────────────────────────────────────────────
elif gorunum == "kart":
    startkey_df = startkey_fotolari_yukle()
    for i in range(0, len(liste_df), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            if i + j >= len(liste_df):
                break
            row = liste_df.iloc[i + j]
            ofis      = row.get("ofis_label","") or ""
            dan       = baslik_formatla(row.get("talep_eden_danisan","")) or "—"
            baslik    = baslik_formatla(str(row.get("ozet","") or "—"))[:70]
            mulk      = row.get("mulk_tipi","") or "—"
            islem     = row.get("islem_tipi","") or "—"
            ilce      = str(row.get("ilce","") or "—").title()
            mah       = str(row.get("mahalle","") or "").title()
            fiyat_raw = row.get("fiyat","") or ""
            fiyat     = fiyat_formatla(fiyat_raw)
            m2        = str(row.get("m2","") or "")
            m2_birim  = row.get("m2_fiyat","") or row.get("birim_fiyat","") or ""
            oda       = row.get("oda_sayisi_m2","") or "—"
            kat       = str(row.get("kat","") or "")
            bina_yasi = str(row.get("bina_yasi","") or "")
            kullanim  = str(row.get("kullanim_durumu","") or "")
            esyali    = str(row.get("esyali","") or "")
            site_ici  = str(row.get("site_icerisinde","") or "")
            gun       = row.get("ilan_suresi_gun")
            link      = row.get("ilan_linki","") or ""
            match     = startkey_eslesme_bul(row, startkey_df)
            foto_url  = match.get("foto_url", "") or ""
            startkey_detay_link = match.get("startkey_detay_link", "") or ""

            try: gun_int = int(float(gun)) if gun is not None else None
            except Exception: gun_int = None

            if gun_int is None:   g_bg,g_fg = "#f1f5f9","#475569"
            elif gun_int <= 7:    g_bg,g_fg = "#dcfce7","#166534"
            elif gun_int <= 30:   g_bg,g_fg = "#fef3c7","#92400e"
            elif gun_int <= 90:   g_bg,g_fg = "#ffedd5","#c2410c"
            else:                 g_bg,g_fg = "#fee2e2","#991b1b"
            gun_html = (f'<span style="background:{g_bg};color:{g_fg};padding:2px 8px;'
                        f'border-radius:999px;font-size:10px;font-weight:700;">'
                        f'{gun_int}g</span>') if gun_int else ""

            i_bg = "#0f172a" if "SAT" in str(islem).upper() else "#0d9488"
            i_fg = "#f8fafc" if "SAT" in str(islem).upper() else "#f0fdfa"
            islem_html = (f'<span style="background:{i_bg};color:{i_fg};padding:2px 8px;'
                          f'border-radius:999px;font-size:10px;font-weight:700;">{islem}</span>')
            mulk_html  = (f'<span style="background:#f1f5f9;color:#475569;padding:2px 8px;'
                          f'border-radius:999px;font-size:10px;font-weight:600;">{mulk}</span>')

            # Durum tag'leri
            KULLANIM_MAP = {
                "bos": ("#166534","#dcfce7","Boş"), "boş": ("#166534","#dcfce7","Boş"),
                "kiracilik": ("#92400e","#fef3c7","Kiracılı"),
                "kiraci": ("#92400e","#fef3c7","Kiracılı"),
                "kiracili": ("#92400e","#fef3c7","Kiracılı"),
                "kiracılı": ("#92400e","#fef3c7","Kiracılı"),
                "mulk sahibi": ("#1e40af","#dbeafe","Mülk Sahibi"),
                "mülk sahibi": ("#1e40af","#dbeafe","Mülk Sahibi"),
            }
            durum_tags = []
            ku_key = kullanim.strip().lower()
            if ku_key in KULLANIM_MAP:
                kfg,kbg,klbl = KULLANIM_MAP[ku_key]
                durum_tags.append(f'<span style="background:{kbg};color:{kfg};padding:2px 7px;border-radius:999px;font-size:10px;font-weight:700;">{klbl}</span>')
            if esyali.strip().lower() in ("evet","esyali","eşyalı","var","true","1"):
                durum_tags.append('<span style="background:#dcfce7;color:#166534;padding:2px 7px;border-radius:999px;font-size:10px;font-weight:700;">Eşyalı</span>')
            if site_ici.strip().lower() in ("evet","var","true","1"):
                durum_tags.append('<span style="background:#fef3c7;color:#92400e;padding:2px 7px;border-radius:999px;font-size:10px;font-weight:700;">Site İçi</span>')
            durum_html = ('<div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:7px;">'
                          + " ".join(durum_tags) + '</div>') if durum_tags else ""

            # M2 + birim fiyat hesapla
            m2_html = (m2 + " m²") if m2 and m2 not in ("","None","nan") else ""
            m2b_html = ""
            try:
                fn = float(str(fiyat_raw).replace(".","").replace(",",".").replace("₺","").replace("TL","").strip())
                mn = float(m2) if m2 and m2 not in ("","None","nan") else None
                mb = float(str(m2_birim).replace(".","").replace(",",".").strip()) if m2_birim and m2_birim not in ("","None","nan") else None
                if mb is None and fn and mn and mn > 0: mb = fn / mn
                if mb: m2b_html = "m²: {:,.0f} ₺".format(mb).replace(",",".")
            except Exception:
                pass

            # Kat / yaş
            kat_yas = ""
            if kat and kat not in ("","None","nan","-"): kat_yas = kat
            if bina_yasi and bina_yasi not in ("","None","nan","-","0","0.0"):
                kat_yas += (" · " + bina_yasi + " yaş") if kat_yas else (bina_yasi + " yaş")

            with col:
                if foto_url:
                    foto_html = (
                        '<div style="width:100%;height:220px;overflow:hidden;border-top-left-radius:12px;border-top-right-radius:12px;">'
                        + '<img src="' + html.escape(foto_url, quote=True) + '" '
                        + 'style="width:100%;height:220px;object-fit:cover;display:block;" />'
                        + '</div>'
                    )
                else:
                    foto_html = (
                        '<div style="width:100%;height:220px;display:flex;align-items:center;justify-content:center;'
                        + 'background:#f8fafc;color:#475569;font-size:13px;font-weight:700;'
                        + 'border-top-left-radius:12px;border-top-right-radius:12px;">'
                        + 'Fotoğraf eşleşmedi'
                        + '</div>'
                    )
                ilan_link_html = (f"<a href='{html.escape(link, quote=True)}' target='_blank' style='display:inline-block;margin-top:10px;background:#eff6ff;color:#2563eb;padding:8px 10px;border-radius:8px;font-size:12px;font-weight:700;text-decoration:none;border:1px solid #bfdbfe;'>İlana Git</a>") if link else ""
                st.markdown(f"""
<div style="background:white;border:1px solid #e2e8f0;border-radius:12px;
    padding:14px 16px;margin-bottom:8px;box-shadow:0 1px 4px rgba(15,23,42,0.05);">
  {foto_html}
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
    <span style="font-size:10px;font-weight:700;color:#374151;border:1px solid #e2e8f0;
      padding:2px 8px;border-radius:999px;">{ofis}</span>
    {gun_html}
  </div>
  <div style="font-weight:700;font-size:13px;color:#0f172a;line-height:1.4;margin-bottom:3px;">{baslik}</div>
  <div style="font-size:11px;color:#64748b;margin-bottom:8px;">{dan}</div>
  <div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:8px;">{islem_html} {mulk_html}</div>
  {durum_html}
  <div style="font-size:11px;color:#374151;margin-bottom:8px;">📍 {ilce}{(" · " + mah) if mah else ""}</div>
  <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:4px;">
    <div>
      <div style="font-weight:800;font-size:14px;color:#0f172a;">{fiyat}</div>
      <div style="font-size:11px;color:#64748b;margin-top:1px;">{m2b_html}</div>
    </div>
    <div style="text-align:right;">
      <div style="font-size:11px;color:#475569;">{oda}</div>
      <div style="font-size:11px;color:#94a3b8;">{m2_html}</div>
    </div>
  </div>
  {"<div style='font-size:10px;color:#94a3b8;margin-bottom:4px;'>" + kat_yas + "</div>" if kat_yas else ""}
  <div style="display:flex;flex-wrap:wrap;gap:8px;">{ilan_link_html}</div>
</div>""", unsafe_allow_html=True)
                _ofis_kid = str(row.get("id","") or i+j)
                _ofis_takip = st.session_state.get(f"takip_o_{_ofis_kid}", False)
                if st.button("⭐ Takipte" if _ofis_takip else "☆ Takibe Al",
                             key=f"ofis_takip_{_ofis_kid}",
                             use_container_width=True):
                    _takip_listesi = st.session_state.setdefault("takip_listesi", {})
                    _row_dict = row.to_dict() if hasattr(row, "to_dict") else dict(row)
                    if _ofis_takip:
                        _takip_listesi.pop(_ofis_kid, None)
                        st.session_state[f"takip_o_{_ofis_kid}"] = False
                        st.toast("Takipten çıkarıldı.")
                    else:
                        _takip_listesi[_ofis_kid] = _row_dict
                        _takip_listesi[_ofis_kid]["_takip_kaynak"] = "ofis_paneli"
                        st.session_state[f"takip_o_{_ofis_kid}"] = True
                        st.toast("✅ Takip listesine eklendi! Ana Sayfadan sunuma hazırlayabilirsiniz.")
                    st.rerun()

# ── Görünüm: Tablo (st.dataframe) ────────────────────────────────────────
else:
    tablo_cols = {
        "ofis_label":"Ofis","talep_eden_danisan":"Danışman",
        "ozet":"Başlık","islem_tipi":"İşlem","mulk_tipi":"Mülk",
        "mulk_turu":"Mülk Türü","ilce":"İlçe","mahalle":"Mahalle",
        "fiyat":"Fiyat","oda_sayisi_m2":"Oda/M²",
        "ilan_suresi_gun":"Gün","ilan_linki":"Link",
    }
    tablo_df = liste_df[[c for c in tablo_cols if c in liste_df.columns]].copy()
    tablo_df.rename(columns=tablo_cols, inplace=True)

    if "Fiyat" in tablo_df.columns:
        tablo_df["Fiyat"] = tablo_df["Fiyat"].apply(fiyat_formatla)
    if "Başlık" in tablo_df.columns:
        tablo_df["Başlık"] = tablo_df["Başlık"].apply(baslik_formatla)
    if "Pay %" in tablo_df.columns:
        tablo_df["Pay %"] = tablo_df["Pay %"].apply(lambda x: f"%{round(x)}" if pd.notna(x) else "")

    col_config = {}
    if "Link" in tablo_df.columns:
        col_config["Link"] = st.column_config.LinkColumn("Link", display_text="Aç")
    if "Başlık" in tablo_df.columns:
        col_config["Başlık"] = st.column_config.TextColumn("Başlık", width="large")
    if "Danışman" in tablo_df.columns:
        col_config["Danışman"] = st.column_config.TextColumn("Danışman", width="medium")

    st.dataframe(tablo_df, hide_index=True, use_container_width=True,
                height=min(700, 55 + len(tablo_df) * 38),
                column_config=col_config)

# Alt filtre temizle
st.markdown("---")
alt1, alt2 = st.columns([4,1])
with alt1:
    st.caption(f"Toplam {len(liste_df)} portföy gösteriliyor")
with alt2:
    if st.button("✕ Filtreleri Temizle", key="filtre_temizle_alt", use_container_width=True):
        for k in ["op_filtre","liste_ofis","liste_dan","liste_ilce","liste_tur"]:
            st.session_state.pop(k, None)
        st.rerun()


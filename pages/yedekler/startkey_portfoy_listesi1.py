"""
pages/startkey_portfoy_listesi.py
----------------------------------
Startkey İlanları — Revy'den keyword=startkey ile çekim
Karma App: pages/startkey_portfoy_listesi.py
"""

import streamlit as st
import sys, json, importlib, pickle
from pathlib import Path
from io import BytesIO
from datetime import datetime, date, timedelta
import pandas as pd
import plotly.express as px
import html as _html
import streamlit.components.v1 as components
import difflib, re

# Karma App'te core/ klasörünü path'e ekle
_core = Path(__file__).parent.parent / "core"
if str(_core) not in sys.path:
    sys.path.insert(0, str(_core))

try:
    st.set_page_config(
        page_title="Startkey İlanları",
        page_icon="🔑",
        layout="wide",
        initial_sidebar_state="expanded",
    )
except Exception:
    pass

# Karma App sidebar'ı (diğer sayfalarla aynı desen — bkz. pazar_raporu.py)
from core.auth import oturum_kontrol
from core.ui_helpers import render_navbar

if not oturum_kontrol():
    st.switch_page("pages/giris.py")

_k = st.session_state.get("kullanici", {})
render_navbar(
    user_role=_k.get("rol", "danisan"),
    user_name=_k.get("ad_soyad") or _k.get("ad", ""),
)

# ─────────────────────────────────────────
# CACHE — dosyaya kaydet/yükle
# ─────────────────────────────────────────
CACHE_DOSYA = Path(__file__).parent.parent / "revy_startkey_cikti" / "sk_cache.pkl"

def cache_yukle():
    try:
        if CACHE_DOSYA.exists():
            with open(CACHE_DOSYA, "rb") as f:
                return pickle.load(f)
    except Exception:
        pass
    return {}

def cache_kaydet(veri):
    try:
        CACHE_DOSYA.parent.mkdir(exist_ok=True)
        with open(CACHE_DOSYA, "wb") as f:
            pickle.dump(veri, f)
    except Exception:
        pass

# ─────────────────────────────────────────
# ARŞİV — her başarılı taramayı ayrı bir dosya olarak sakla, böylece
# yeni bir tarama (ör. sadece Karşıyaka) yapıldığında önceki (ör. tüm İzmir)
# sonuç kaybolmaz; "Arşiv" sekmesinden geri yüklenebilir.
# ─────────────────────────────────────────
GECMIS_KLASOR = Path(__file__).parent.parent / "revy_startkey_cikti" / "gecmis"
GECMIS_INDEX  = GECMIS_KLASOR / "index.json"

def gecmis_kaydet(veri: dict, ilceler: list, etiket: str = ""):
    try:
        GECMIS_KLASOR.mkdir(parents=True, exist_ok=True)
        zaman = datetime.now()
        dosya_adi = f"sk_{zaman.strftime('%Y%m%d_%H%M%S')}.pkl"
        with open(GECMIS_KLASOR / dosya_adi, "wb") as f:
            pickle.dump(veri, f)

        kayit_sayisi = sum(len(v) for v in veri.values())
        index = []
        if GECMIS_INDEX.exists():
            try:
                index = json.loads(GECMIS_INDEX.read_text(encoding="utf-8"))
            except Exception:
                index = []
        index.insert(0, {
            "dosya": dosya_adi,
            "zaman": zaman.strftime("%d.%m.%Y %H:%M"),
            "ilceler": ilceler,
            "kayit_sayisi": kayit_sayisi,
            "etiket": etiket or (", ".join(ilceler) if len(ilceler) <= 3 else f"{len(ilceler)} ilçe (Tüm İzmir)"),
        })
        GECMIS_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def gecmis_listele():
    if not GECMIS_INDEX.exists():
        return []
    try:
        return json.loads(GECMIS_INDEX.read_text(encoding="utf-8"))
    except Exception:
        return []

def gecmis_yukle(dosya_adi: str):
    try:
        with open(GECMIS_KLASOR / dosya_adi, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None

def gecmis_sil(dosya_adi: str):
    try:
        (GECMIS_KLASOR / dosya_adi).unlink(missing_ok=True)
        index = gecmis_listele()
        index = [k for k in index if k["dosya"] != dosya_adi]
        GECMIS_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
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
.block-container { padding-top:0.8rem; padding-bottom:2rem; max-width:1520px; }
div[data-testid="stButton"] > button {
    border-radius:8px; border:1px solid var(--border);
    min-height:34px; padding:6px 12px;
    font-size:12px; font-weight:600;
    background:var(--chip-bg); color:var(--text); transition:all 0.15s;
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
.durum-banner {
    background:#EEF4FA; border:1px solid #C8D7E5; border-radius:10px;
    padding:12px 20px; margin:10px 0; color:var(--primary);
    font-size:13px; font-weight:600; text-align:center;
}
.cache-bilgi {
    background:#f8fafc; border:1px solid var(--border); border-radius:8px;
    padding:8px 14px; font-size:11px; color:var(--muted); margin-bottom:10px;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# VERİ / YARDIMCI
# ─────────────────────────────────────────
@st.cache_data
def mahalle_yukle():
    for yol in [
        Path(__file__).parent / "izmir_mahalleler.json",
        Path(__file__).parent.parent / "core" / "izmir_mahalleler.json",
        Path(__file__).parent.parent / "izmir_mahalleler.json",
    ]:
        if yol.exists():
            return json.load(open(yol, encoding="utf-8"))
    return {}

MAHALLELER    = mahalle_yukle()
IZMIR_ILCELER = sorted(MAHALLELER.keys()) if MAHALLELER else []
MULK_SEC      = {"Konut":"konut","Ticari":"ticari","Arsa":"arsa"}
ISLEM_SEC     = {"Satılık":"satilik","Kiralık":"kiralik"}
DURUM_SEC     = {"Aktif İlanlar":"aktif","Yayından Kalkanlar":"yayindan_kalkan"}
SK_RENKLER    = ["#355C7D","#446B8B","#537A99","#6289A7","#7198B5",
                 "#80A7C3","#8FB6D1","#9EC5DF","#ADD4ED","#BCE3FB"]

def parse_num(v):
    try:
        s = str(v).replace("₺","").replace("TL","").strip()
        try: return float(s)
        except: pass
        return float(s.replace(".","").replace(",","."))
    except: return None

# ─────────────────────────────────────────
# REHBER — Supabase'den ofis/danışman
# ─────────────────────────────────────────
@st.cache_data(ttl=3600)
def rehber_yukle():
    """rehber_ofisler + rehber_danismanlar tablolarından çek."""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
        from supabase_client import get_client
        supa = get_client()
        ofis_res = supa.table("rehber_ofisler").select("ofis_adi,telefon,mail,bolge_aksi").eq("aktif", True).execute()
        dan_res  = supa.table("rehber_danismanlar").select("ofis_adi,isim,telefon,mail,profil_link").eq("aktif", True).execute()
        ofis_df  = pd.DataFrame(ofis_res.data or [])
        dan_df   = pd.DataFrame(dan_res.data or [])
        return ofis_df, dan_df
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame()


@st.cache_data(ttl=3600)
def ayrilan_danismanlar_yukle():
    """rehber_sync.py tarafından aktif=False yapılmış (ayrılmış/pasife alınmış)
    danışmanları çeker — en son güncellenen en üstte."""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
        from supabase_client import get_client
        supa = get_client()
        res = (
            supa.table("rehber_danismanlar")
            .select("ofis_adi,isim,telefon,mail,guncelleme_tar")
            .eq("aktif", False)
            .order("guncelleme_tar", desc=True)
            .execute()
        )
        return pd.DataFrame(res.data or [])
    except Exception:
        return pd.DataFrame()

# ── ELLE DÜZELTME TABLOSU ─────────────────────────────────────────────────
# Bazı Revy ofis adları, gerçek Startkey ofis adıyla METİN OLARAK hiç benzemiyor
# (ör. "Başlangıç ..." aslında bir Startkey ofisi, "Gökyüzü" = "Sky" ofisinin
# Türkçe takma adı). difflib fuzzy-match bunları YAKALAYAMAZ çünkü kelimeler
# gerçekten farklı, sadece "benzer yazım" değil. Bunları burada elle ekle:
# Sol taraf = Revy'de göründüğü HAM isim (birebir, büyük/küçük harf duyarsız),
# Sağ taraf = rehber_ofisler tablosundaki GERÇEK ofis_adi (birebir).
OFIS_ELLE_DUZELT = {
    # "başlangıç bsw star gayrimenkul": "STARTKEY BSW STAR GAYRİMENKUL",
    # "gökyüzü": "STARTKEY SKY GAYRİMENKUL",
    # ↑ örnekler — gerçek karşılıklarını rehberden teyit edip buraya ekle.
    # Aşağıdaki "eşleşmeyen ofisler" panelinde göreceğin ham isimleri
    # soldaki gibi küçük harfle, sağdaki gibi rehberdeki tam adla yaz.
}

def _tr_lower(s):
    """Python'ın standart .lower()'ı Türkçe büyük 'İ'yi YANLIŞ küçültüyor:
    'GAYRİMENKUL'.lower() -> 'gayri̇menkul' (aralarına görünmez bir nokta
    karakteri ekliyor), bu da 'gayrimenkul' ile hiç eşleşmiyor. Bu yüzden
    Türkçe büyük/küçük harf dönüşümünü kendimiz, elle yapıyoruz."""
    return str(s).replace("İ", "i").replace("I", "ı").lower()

def _tr_title(s):
    """Türkçe uyumlu 'Baş Harfleri Büyük' — Python'ın .title()'ı da aynı
    İ/I hatasına düşüyor. Danışman isimlerini (MUSTAFA YİĞİT / mustafa yiğit /
    Mustafa Yiğit gibi farklı yazımları) TEK bir görünüme normalize etmek
    için kullanılır."""
    kelimeler = re.sub(r"\s+", " ", str(s)).strip().split(" ")
    sonuc = []
    for k in kelimeler:
        if not k:
            continue
        kucuk = _tr_lower(k)
        ilk = "İ" if kucuk[0] == "i" else ("I" if kucuk[0] == "ı" else kucuk[0].upper())
        sonuc.append(ilk + kucuk[1:])
    return " ".join(sonuc)

def _norm(s):
    """Fuzzy match için metni normalize et — 'Startkey' ve 'Gayrimenkul' gibi
    sarmalayıcı kelimeleri KELİME SINIRINDA (substring değil) temizler, böylece
    'Startkey A Plus Gayrimenkul' ile rehberdeki çekirdek ad 'A Plus' çok daha
    yüksek benzerlikle eşleşir."""
    s = _tr_lower(s).strip()
    s = re.sub(r"[^a-z0-9ğüşıöçğ ]", " ", s)
    s = re.sub(r"\bstartkey\b", "", s)
    s = re.sub(r"\bgayr[ıi]menkul\b", "", s)  # hem doğru hem yanlış yazım (I/İ karışıklığı)
    s = re.sub(r"\bemlak\b", "", s)
    s = re.sub(r"\bdanışmanlık\b", "", s)
    s = re.sub(r"\bltd\b", "", s)
    s = re.sub(r"\bşti\b", "", s)
    s = re.sub(r"\bgyd\b", "", s)
    return re.sub(r"\s+", " ", s).strip()

@st.cache_data
def ofis_eslesme_haritasi(revy_ofis_listesi: tuple, rehber_ofis_listesi: tuple):
    """Revy ofis adlarını rehber ofis adlarına eşleştir. Sırasıyla dener:
    1) OFIS_ELLE_DUZELT tablosu (kesin/elle eşleme)
    2) Fuzzy match (difflib, normalize edilmiş metinler üzerinde)
    3) 'Rehberdeki çekirdek ad, Revy adının İÇİNDE tam kelime olarak geçiyor mu'
       kontrolü — ör. 'Startkey Anka Burhaniye' içinde 'anka' geçiyor, bu da
       rehberdeki 'Anka' ofisiyle eşleşir (lokasyon eki eklenmiş vakalar için).
    Döner: (harita, eslesmeyenler) — eslesmeyenler = hiçbir yöntemle rehberde
    karşılığı bulunamayan ham Revy ofis adları (tanı/hata ayıklama için)."""
    harita = {}
    eslesmeyenler = []
    rehber_norm = [_norm(r) for r in rehber_ofis_listesi]

    for revy_ad in revy_ofis_listesi:
        if not revy_ad or str(revy_ad).strip() in ("", "nan"): continue

        # 1) Elle düzeltme tablosu — kesin eşleşme
        elle = OFIS_ELLE_DUZELT.get(str(revy_ad).strip().lower())
        if elle and elle in rehber_ofis_listesi:
            harita[revy_ad] = elle
            continue

        norm_revy = _norm(revy_ad)

        # 2) Fuzzy match
        en_iyi = difflib.get_close_matches(norm_revy, rehber_norm, n=1, cutoff=0.55)
        if en_iyi:
            idx = rehber_norm.index(en_iyi[0])
            harita[revy_ad] = rehber_ofis_listesi[idx]
            continue

        # 3) "İçinde geçiyor mu" — lokasyon eki eklenmiş isimler için
        icinde_bulundu = None
        for idx, rn in enumerate(rehber_norm):
            if rn and re.search(rf"\b{re.escape(rn)}\b", norm_revy):
                icinde_bulundu = rehber_ofis_listesi[idx]
                break

        if icinde_bulundu:
            harita[revy_ad] = icinde_bulundu
        else:
            harita[revy_ad] = revy_ad  # eşleşme yoksa olduğu gibi bırak
            eslesmeyenler.append(revy_ad)
    return harita, tuple(eslesmeyenler)


# Session state — cache'den yükle
if "sk_veri" not in st.session_state:
    st.session_state.sk_veri = cache_yukle()
if "sk_last_filtre" not in st.session_state:
    st.session_state.sk_last_filtre = {}
if "sk_pazar_payi" not in st.session_state:
    st.session_state.sk_pazar_payi = None
if "sk_cache_zaman" not in st.session_state:
    zaman_yol = CACHE_DOSYA
    if zaman_yol.exists():
        st.session_state.sk_cache_zaman = datetime.fromtimestamp(
            zaman_yol.stat().st_mtime).strftime("%d.%m.%Y %H:%M")
    else:
        st.session_state.sk_cache_zaman = None

# ── Ham veri + Ofis normalize — erken hazırlanıyor, çünkü filtre panelindeki
#    "Ofis" seçim kutusunun seçeneklerini doldurmak için gerekiyor ──
sk_veri = st.session_state.sk_veri
df_ham = pd.concat([v for v in sk_veri.values() if not v.empty], ignore_index=True) if sk_veri else pd.DataFrame()

rehber_ofis_df, rehber_dan_df = rehber_yukle()
ESLESMEYEN_OFISLER = ()
if not df_ham.empty:
    if not rehber_ofis_df.empty and "Ofis" in df_ham.columns:
        rehber_ofis_listesi = tuple(rehber_ofis_df["ofis_adi"].dropna().unique().tolist())
        revy_ofis_listesi   = tuple(df_ham["Ofis"].dropna().unique().tolist())
        harita, ESLESMEYEN_OFISLER = ofis_eslesme_haritasi(revy_ofis_listesi, rehber_ofis_listesi)
        df_ham["Ofis_norm"] = df_ham["Ofis"].map(harita).fillna(df_ham["Ofis"])
    else:
        df_ham["Ofis_norm"] = df_ham.get("Ofis", "")

    # Bölge/Aks bilgisi — Ofis Paneli'ndeki aks_bul() ile BİREBİR aynı mantık:
    # mülkün KENDİ İLÇESİNE göre hesaplanır (satan ofisin kayıtlı bölgesine
    # göre DEĞİL). Örn. Bornova'daki bir ilan, onu hangi ofis sattığından
    # bağımsız olarak her zaman "İzmir Merkez" aksına girer.
    def _aks_bul(ilce):
        if not ilce:
            return "Diğer"
        ilce = str(ilce).strip().upper()
        merkez   = {"KONAK","BORNOVA","BAYRAKLI","KARABAĞLAR","BUCA"}
        kuzey    = {"KARŞIYAKA","KARSIYAKA","ÇİĞLİ","CİĞLİ","CIGLI","MENEMEN","ALİAĞA","ALIAĞA","FOÇA","FOCA"}
        yarimada = {"ÇEŞME","CESME","URLA","SEFERİHİSAR","SEFERIHISAR","GÜZELBAHÇE","GUZELBAHCE","NARLIDERE","BALÇOVA","BALCOVA"}
        guney    = {"TORBALI","MENDERES","GAZİEMİR","GAZIEMIR","TİRE","TIRE","SELÇUK","SELCUK"}
        if ilce in merkez:   return "İzmir Merkez"
        if ilce in kuzey:    return "Kuzey Aksı"
        if ilce in yarimada: return "Yarımada / Batı Aksı"
        if ilce in guney:    return "Güney Aksı"
        return "Diğer"

    df_ham["Aks"] = df_ham.get("İlçe", "").apply(_aks_bul)

OFIS_SECENEKLERI = (
    sorted(df_ham["Ofis_norm"].dropna().unique().tolist())
    if "Ofis_norm" in df_ham.columns else []
)

# ── Tıklanan ofisi filtreye uygula — widget ("sk_ofis") bu run'da HENÜZ
#    oluşturulmadan önce yapılmalı, aksi halde Streamlit
#    "widget oluşturulduktan sonra değiştirilemez" hatası verir. ──
if "_sk_ofis_pending" in st.session_state:
    st.session_state["sk_ofis"] = st.session_state.pop("_sk_ofis_pending")

if "_sk_ara_pending" in st.session_state:
    st.session_state["sk_ara"] = st.session_state.pop("_sk_ara_pending")

if "_sk_liste_dan_pending" in st.session_state:
    st.session_state["sk_liste_dan"] = st.session_state.pop("_sk_liste_dan_pending")

# ── Filtreleri sıfırlama bayrağı — arşivden farklı bir kayıt yüklendiğinde
#    ya da "Filtreleri Temizle" butonuna basıldığında, eski/kalıntı
#    seçimlerin (özellikle Ofis Adı) yeni veriye sessizce uygulanmaya devam
#    etmesini önlemek için widget'lar oluşturulmadan ÖNCE burada temizlenir. ──
if st.session_state.pop("_sk_filtre_sifirla", False):
    for _k in ["sk_ilce", "sk_mah", "sk_ofis", "sk_islem", "sk_mulk", "sk_durum",
               "sk_oda", "sk_kat", "sk_yas", "sk_kullanim", "sk_esyali", "sk_ara",
               "sk_m2_min", "sk_m2_max", "sk_fiyat_min", "sk_tarih",
               "sk_liste_ofis", "sk_liste_dan", "sk_liste_sayfa"]:
        st.session_state.pop(_k, None)

# ─────────────────────────────────────────
# BAŞLIK
# ─────────────────────────────────────────
baslik_col, sorgu_col = st.columns([4, 1.4])
with baslik_col:
    st.markdown("""
    <div class="page-header">
        <h1>🔑 Startkey İlanları</h1>
        <p>Revy'deki tüm Startkey ilanları — ofis bazlı analiz ve filtreleme</p>
    </div>
    """, unsafe_allow_html=True)
with sorgu_col:
    st.write("")
    listele_btn = st.button("🆕 Yeni Sorgu\n(Revy'den Çek)", type="primary", use_container_width=True, key="sk_listele",
                            help="Revy'den TAZE veri çeker — farklı bölge/tarih taramak ya da hiç çekilmemiş bir durumu "
                                 "(örn. Yayından Kalkanlar) getirmek istediğinde bas. Her tıklamada GERÇEKTEN yeniden "
                                 "sorgulanır, önceki veriyle karşılaştırma yapılmaz.")

# Cache bilgisi
if st.session_state.sk_cache_zaman:
    st.markdown(f'<div class="cache-bilgi">📦 Kayıtlı veri: <b>{st.session_state.sk_cache_zaman}</b> tarihli — yeni veri için yukarıdaki Yeni Sorgu\'ya basın</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────
# FİLTRE PANELİ
# ─────────────────────────────────────────
st.markdown('<div class="filtre-panel">', unsafe_allow_html=True)
st.markdown('<div class="filtre-baslik">🔍 Filtreler</div>', unsafe_allow_html=True)
st.caption(
    "ℹ️ Yukarıdaki **Yeni Sorgu**, Revy'den taze veri çeker (İlçe seçmezsen tüm İzmir taranır, birkaç dakika sürebilir). "
    "Aşağıdaki **Filtrele** ise Revy'ye hiç gitmeden, zaten çekilmiş veri üzerinde anında filtreler."
)

r1a, r1b, r1c, r1d = st.columns([1.7, 1.7, 1.5, 1.6])
with r1a:
    secili_ilceler = st.multiselect("İlçe", IZMIR_ILCELER, placeholder="Tümü", key="sk_ilce")
with r1b:
    mah_opts = []
    for ilce in secili_ilceler:
        mah_opts.extend(MAHALLELER.get(ilce, []))
    mah_opts = sorted(set(mah_opts))
    secili_mahalleler = st.multiselect("Mahalle", mah_opts, placeholder="Tümü (opsiyonel)", key="sk_mah")
with r1c:
    secili_ofisler = st.multiselect("Ofis Adı", OFIS_SECENEKLERI, placeholder="Tümü", key="sk_ofis")
with r1d:
    # Tarih aralığı boş başlar
    tarih_aralik = st.date_input("Tarih Aralığı _(yayından kalkanlar için)_",
        value=None, format="DD.MM.YYYY", key="sk_tarih")
    if isinstance(tarih_aralik, tuple) and len(tarih_aralik) == 2:
        bas_tarih, bit_tarih = tarih_aralik
    else:
        bas_tarih = bit_tarih = None

r2a, r2b, r2c, r2d, r2e, r2f = st.columns([1.3, 1.3, 1.3, 1.1, 1.1, 1.1])
with r2a:
    secili_islemler = st.multiselect("İşlem Tipi", list(ISLEM_SEC.keys()), default=["Satılık","Kiralık"], key="sk_islem")
with r2b:
    secili_mulkler = st.multiselect("Mülk Tipi", list(MULK_SEC.keys()), default=["Konut","Ticari","Arsa"], key="sk_mulk")
with r2c:
    secili_durumlar = st.multiselect("İlan Durumu", list(DURUM_SEC.keys()), default=["Aktif İlanlar"], key="sk_durum")
with r2d:
    oda_filtre = st.multiselect("Oda", ["1+0","1+1","2+1","2+2","3+1","3+2","4+1","4+2","5+1","5+2"], placeholder="Tümü", key="sk_oda")
with r2e:
    kat_filtre = st.multiselect("Kat", ["Zemin","Bahçe Katı","1. Kat","2. Kat","3. Kat","4. Kat","5. Kat","Yüksek Giriş","Müstakil"], placeholder="Tümü", key="sk_kat")
with r2f:
    yas_filtre = st.multiselect("Bina Yaşı", ["0","1-5","6-10","11-15","16-20","21-25","26-30","30 üstü"], placeholder="Tümü", key="sk_yas")

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
    filtrele_btn = st.button("🔍 Filtrele", type="primary", use_container_width=True, key="sk_filtrele_btn",
                             help="Revy'ye gitmez — zaten çekilmiş veri üzerinde seçtiğin filtreleri anında uygular.")

temizle_col, _bos = st.columns([1, 4])
with temizle_col:
    if st.button("🧹 Filtreleri Temizle", use_container_width=True, key="sk_filtre_temizle_btn",
                 help="Ofis Adı dahil tüm filtreleri sıfırlar — özellikle farklı ekranlarda/testlerde kalan eski seçimler için"):
        st.session_state["_sk_filtre_sifirla"] = True
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────
# VERİ ÇEKME
# ─────────────────────────────────────────
if listele_btn:
    if not secili_durumlar:
        st.error("En az bir ilan durumu seçin.")
    elif not secili_mulkler:
        st.error("En az bir Mülk Tipi seçin.")
    elif not secili_islemler:
        st.error("En az bir İşlem Tipi seçin.")
    else:
        # NOT: Eskiden rpc.startkey_ilan_cek() (keyword="startkey" global araması)
        # kullanılıyordu, ama bu arama muhtemelen hesabın kendi çalıştığı bölgeyle
        # ("bölgelerim") sınırlı çalışıyor ve pek çok Startkey ofisini (Zeta dahil)
        # hiç getirmiyordu. Bunun yerine — pazar_analiz.py'de zaten doğrulanmış
        # olan — rpc.pazar_cek()'i HER İLÇE için ayrı ayrı çağırıp birleştiriyoruz,
        # sonra sonucu MARKA == "startkey" ile filtreliyoruz. Daha yavaş ama eksiksiz.
        hedef_ilceler = secili_ilceler if secili_ilceler else IZMIR_ILCELER

        filtre_ana = {
            "mulk":  [MULK_SEC[m] for m in secili_mulkler],
            "islem": [ISLEM_SEC[i] for i in secili_islemler],
            "durum": [DURUM_SEC[d] for d in secili_durumlar],
        }
        if bas_tarih: filtre_ana["baslangic"] = bas_tarih.strftime("%Y-%m-%d")
        if bit_tarih: filtre_ana["bitis"]     = bit_tarih.strftime("%Y-%m-%d")

        filtre_karsilastirma = {"ilceler": sorted(hedef_ilceler), **filtre_ana}
        # NOT: Burada eskiden "istenen kapsam zaten yüklüyse Revy'ye gitme"
        # diye bir akıllı-atlama mantığı vardı. KALDIRILDI — çünkü Revy
        # tarafında (ya da kodda) bir düzeltme yapılıp AYNI filtrelerle
        # tekrar veri çekilmek istendiğinde bu mantık yanlışlıkla devreye
        # girip gerçek bir yeniden-çekmeyi engelliyordu. "Yeni Sorgu"
        # butonuna her basıldığında artık GERÇEKTEN Revy'ye gidilir.

        durum_ph = st.empty()
        def progress_cb(msg):
            durum_ph.markdown(f'<div class="durum-banner">{msg}</div>', unsafe_allow_html=True)

        try:
            import revy_pazar_cek as rpc
            importlib.reload(rpc)

            # ayarlar.txt: önce kök dizin, sonra pages/
            ayarlar_yol = Path(__file__).parent.parent / "ayarlar.txt"
            if not ayarlar_yol.exists():
                ayarlar_yol = Path(__file__).parent / "ayarlar.txt"
            ayarlar = rpc.ayarlari_oku(ayarlar_yol)

            progress_cb("🌐 Revy'ye bağlanılıyor (arka planda)...")

            cookies = rpc.selenium_cookie_al(
                kullanici=ayarlar["revy1_kullanici"],
                sifre=ayarlar["revy1_sifre"],
                giris_url=ayarlar.get("revy_giris_url","https://revy.com.tr"),
                headless=True,
                progress_cb=progress_cb,
            )

            birlesik = {}
            for i, ilce in enumerate(hedef_ilceler, 1):
                progress_cb(f"📍 [{i}/{len(hedef_ilceler)}] {ilce} taranıyor...")
                ilce_filtre = dict(filtre_ana)
                ilce_filtre["ilce"] = [ilce]
                parca = rpc.pazar_cek(
                    cookies, ilce_filtre,
                    cikti_klasor=Path(__file__).parent.parent / "revy_startkey_cikti",
                    progress_cb=progress_cb,
                )
                for anahtar, v in (parca or {}).items():
                    if v is None or v.empty:
                        continue
                    birlesik[anahtar] = (
                        pd.concat([birlesik[anahtar], v], ignore_index=True)
                        if anahtar in birlesik else v.copy()
                    )

            # ── Pazar payını Startkey'e filtrelemeden ÖNCE hesapla ──
            # (pazar_cek zaten tüm markaları getiriyor, sadece bunu atmadan
            # önce sayıyoruz — ekstra bir sorguya gerek yok.)
            pazar_payi = {"toplam": 0, "startkey": 0, "diger_kurumsal": 0, "yerel_ofis": 0, "mulk_sahibi": 0}
            if "aktif" in birlesik and "MARKA" in birlesik["aktif"].columns:
                _mk = birlesik["aktif"]["MARKA"].astype(str).str.lower()
                pazar_payi["toplam"] = len(_mk)
                pazar_payi["startkey"] = int((_mk == "startkey").sum())
                pazar_payi["yerel_ofis"] = int((_mk == "bagimsiz").sum())
                pazar_payi["mulk_sahibi"] = int((_mk == "mulk_sahibi").sum())
                pazar_payi["diger_kurumsal"] = pazar_payi["toplam"] - pazar_payi["startkey"] - pazar_payi["yerel_ofis"] - pazar_payi["mulk_sahibi"]

            # Sadece Startkey markasını bırak (pazar_cek tüm markaları getirir)
            for anahtar in list(birlesik.keys()):
                if "MARKA" in birlesik[anahtar].columns:
                    birlesik[anahtar] = birlesik[anahtar][
                        birlesik[anahtar]["MARKA"].astype(str).str.lower() == "startkey"
                    ].reset_index(drop=True)

            st.session_state.sk_veri = birlesik
            st.session_state.sk_pazar_payi = pazar_payi
            st.session_state.sk_last_filtre = filtre_karsilastirma
            st.session_state.sk_cache_zaman = datetime.now().strftime("%d.%m.%Y %H:%M")
            cache_kaydet(birlesik)  # "son kullanılan" — sayfa açılışında otomatik yüklenir
            gecmis_kaydet(birlesik, hedef_ilceler)  # arşive de ekle — üzerine yazılmaz

            durum_ph.success(
                f"✅ {sum(len(v) for v in birlesik.values()):,} Startkey ilanı hazır! "
                f"({len(hedef_ilceler)} ilçe tarandı)"
            )
            st.rerun()

        except Exception as e:
            durum_ph.error(f"Hata: {e}")

# ─────────────────────────────────────────
# ANALİZ
# ─────────────────────────────────────────
if not sk_veri:
    st.markdown("""
    <div style="text-align:center;padding:50px 20px;color:#64748b;">
        <div style="font-size:2.5rem;margin-bottom:12px;">🔑</div>
        <div style="font-size:1rem;font-weight:600;margin-bottom:6px;">Filtreleri seçin ve Yeni Sorgu'ya basın</div>
        <div style="font-size:12px;">Revy'deki tüm Startkey ilanları otomatik çekilecek</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

if df_ham.empty:
    st.info("Veri bulunamadı.")
    st.stop()

# ── SEKMELER ──
sekme1, sekme2, sekme3, sekme4 = st.tabs(["📋 İlan Listesi", "👤 Danışman Bazlı", "🚪 Ayrılan Danışmanlar", "📚 Arşiv"])

with sekme1:
    df = df_ham.copy()

# Lokal filtreler
if secili_ilceler and "İlçe" in df.columns:
    df = df[df["İlçe"].isin(secili_ilceler)]
if secili_mahalleler and "Mahalle" in df.columns:
    df = df[df["Mahalle"].isin(secili_mahalleler)]
if secili_ofisler and "Ofis_norm" in df.columns:
    df = df[df["Ofis_norm"].isin(secili_ofisler)]
if secili_islemler and "İşlem tipi" in df.columns:
    islem_tr = {"satilik":["Satılık","satilik","satılık"], "kiralik":["Kiralık","kiralik","kiralık"]}
    secilen = []
    for i in secili_islemler:
        secilen.extend(islem_tr.get(ISLEM_SEC[i],[]))
    if secilen:
        df = df[df["İşlem tipi"].isin(secilen)]
if secili_mulkler and "Mülk tipi" in df.columns:
    # NOT: Mülk Tipi eskiden sadece sorgu parametresiydi (Revy'den çekerken
    # kullanılıyordu) — zaten yüklü veri üzerinde filtre olarak hiç
    # uygulanmıyordu. Bu yüzden "Tüm İzmir"i çektikten sonra sadece "Arsa"
    # seçmek, yeni bir Revy sorgusu gerektirmeden hiçbir şeyi değiştirmiyordu.
    # Artık yerel olarak da filtreleniyor.
    mulk_tr = {"konut":["Konut","konut"], "ticari":["Ticari","ticari"], "arsa":["Arsa","arsa"]}
    secilen_mulk = []
    for m in secili_mulkler:
        secilen_mulk.extend(mulk_tr.get(MULK_SEC[m], []))
    if secilen_mulk:
        df = df[df["Mülk tipi"].isin(secilen_mulk)]
if secili_durumlar and "_durum" in df.columns:
    # Aynı şekilde İlan Durumu da artık yerel filtre — zaten çekilmiş
    # "aktif" + "yayından kalkan" verisinin içinden anında seçim yapılabilir.
    durum_tr = {"aktif":"aktif", "yayindan_kalkan":"yayindan_kalkan"}
    secilen_durum = [durum_tr[DURUM_SEC[d]] for d in secili_durumlar if DURUM_SEC[d] in durum_tr]
    if secilen_durum:
        df = df[df["_durum"].isin(secilen_durum)]
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

# KPI
toplam   = len(df)
aktif_n  = len(df[df["_durum"]=="aktif"]) if "_durum" in df.columns else toplam
kalkan_n = len(df[df["_durum"]=="yayindan_kalkan"]) if "_durum" in df.columns else 0
ofis_n   = df["Ofis_norm"].nunique() if "Ofis_norm" in df.columns else (df["Ofis"].nunique() if "Ofis" in df.columns else 0)
df_num   = df.copy()
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
    (k5,"Ort. m² Fiyatı", f"{ort_birim:,.0f} ₺".replace(",",".") if pd.notna(ort_birim) else "-", "", "kpi-blue"),
]:
    with col:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">{lbl}</div>
            <div class="kpi-value {cls}">{val}</div>
            <div class="kpi-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Pazar Payı — Pazar Radar'daki aynı istatistik, en son "Yeni Sorgu"
#    sırasında Startkey'e filtrelemeden önce hesaplanıp saklandı. ──
_pp = st.session_state.get("sk_pazar_payi")
if _pp and _pp.get("toplam", 0) > 0:
    with st.expander("📊 Pazar Payı (taranan bölgede, tüm markalar)", expanded=True):
        st.caption(
            "Bu, en son 'Yeni Sorgu' ile taranan ilçe(ler)deki TÜM ajans/mülk sahibi ilanlarına "
            "kıyasla Startkey'in payını gösterir — Pazar Radar sayfasındaki aynı istatistik."
        )
        t = _pp["toplam"]
        pk1, pk2, pk3, pk4, pk5 = st.columns(5)
        for col, lbl, val, cls in [
            (pk1, "Toplam İlan", f"{t:,}".replace(",","."), "kpi-blue"),
            (pk2, "Startkey", f'{_pp["startkey"]:,}'.replace(",",".") + f'  (%{_pp["startkey"]/t*100:.1f})', "kpi-green"),
            (pk3, "Diğer Kurumsal", f'{_pp["diger_kurumsal"]:,}'.replace(",",".") + f'  (%{_pp["diger_kurumsal"]/t*100:.1f})', "kpi-amber"),
            (pk4, "Yerel Ofis", f'{_pp["yerel_ofis"]:,}'.replace(",",".") + f'  (%{_pp["yerel_ofis"]/t*100:.1f})', "kpi-blue"),
            (pk5, "Mülk Sahibi", f'{_pp["mulk_sahibi"]:,}'.replace(",",".") + f'  (%{_pp["mulk_sahibi"]/t*100:.1f})', "kpi-blue"),
        ]:
            with col:
                st.markdown(f"""<div class="kpi-card">
                    <div class="kpi-label">{lbl}</div>
                    <div class="kpi-value {cls}" style="font-size:1.1rem;">{val}</div>
                </div>""", unsafe_allow_html=True)
else:
    st.caption("ℹ️ Pazar payı bilgisi sadece bir 'Yeni Sorgu' çalıştırdıktan sonra (o oturumda) görünür — arşivden yüklenen kayıtlarda henüz saklanmıyor.")

# ── Genel Durum (Ofis Paneli'ndeki KPI'ların Startkey-geneli versiyonu) ──
with st.expander("📈 Genel Durum (Yayın Süresi Analizi)", expanded=True):
    df_num["__gun"] = df_num["İlan tarihi"].apply(
        lambda t: (pd.Timestamp.today().normalize() - d).days
        if pd.notna(d := pd.to_datetime(t, dayfirst=True, errors="coerce")) else None
    ) if "İlan tarihi" in df_num.columns else None

    if "__gun" in df_num.columns and df_num["__gun"].notna().any():
        gun_seri = df_num["__gun"].dropna()
        yeni_7   = int((gun_seri <= 7).sum())
        yetki_3  = int(((gun_seri >= 70) & (gun_seri <= 90)).sum())
        yetki_6  = int(((gun_seri >= 160) & (gun_seri <= 180)).sum())
        ort_gun  = int(gun_seri.mean()) if len(gun_seri) else 0

        gk1, gk2, gk3, gk4 = st.columns(4)
        for col, lbl, val, sub, cls in [
            (gk1, "Son 7 Gün Yeni", yeni_7, "Bu hafta eklenen", "kpi-green" if yeni_7 > 0 else ""),
            (gk2, "Ort. İlan Süresi", f"{ort_gun} gün", "Ortalama yayın süresi", "kpi-amber" if ort_gun > 60 else ""),
            (gk3, "3 Ay Yetki Yaklaşan", yetki_3, "70-90 gün arası", "kpi-amber" if yetki_3 > 0 else ""),
            (gk4, "6 Ay Yetki Yaklaşan", yetki_6, "160-180 gün arası", "kpi-red" if yetki_6 > 0 else ""),
        ]:
            with col:
                st.markdown(f"""<div class="kpi-card">
                    <div class="kpi-label">{lbl}</div>
                    <div class="kpi-value {cls}">{val}</div>
                    <div class="kpi-sub">{sub}</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.info("İlan tarihi bilgisi bulunamadığı için yayın süresi analizi hesaplanamadı.")

    st.markdown("<br>", unsafe_allow_html=True)
    ga1, ga2, ga3 = st.columns(3)

    with ga1:
        st.markdown("##### İlçe Dağılımı (ilk 10)")
        if "İlçe" in df.columns and not df.empty:
            ilce_ozet = df.groupby("İlçe").size().reset_index(name="Adet")\
                .sort_values("Adet", ascending=False).head(10)
            fig_ilce = px.bar(ilce_ozet, x="İlçe", y="Adet", text="Adet",
                               color_discrete_sequence=["#1e3a5f"])
            fig_ilce.update_layout(height=320, xaxis_title="", yaxis_title="Adet",
                margin=dict(l=0,r=0,t=10,b=65), plot_bgcolor="white", paper_bgcolor="white",
                xaxis=dict(tickangle=-35, tickfont=dict(size=11)))
            fig_ilce.update_traces(textposition="outside", cliponaxis=False, textfont=dict(size=11))
            st.plotly_chart(fig_ilce, use_container_width=True)

    with ga2:
        st.markdown("##### Bölgesel Dağılım (Aks)")
        if "Aks" in df.columns and not df.empty:
            aks_ozet = df.groupby("Aks").size().reset_index(name="Adet").sort_values("Adet", ascending=False)
            renk_paleti = ["#1e3a5f","#ff4d4f","#f59e0b","#22c55e","#8b5cf6","#06b6d4","#ec4899","#14b8a6"]
            fig_aks = px.pie(aks_ozet, names="Aks", values="Adet", hole=0.42,
                              color_discrete_sequence=renk_paleti)
            fig_aks.update_layout(height=340, margin=dict(l=0,r=0,t=10,b=90), paper_bgcolor="white",
                legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5, font=dict(size=10)))
            fig_aks.update_traces(textposition="inside", textfont=dict(size=10, color="white"),
                hovertemplate="<b>%{label}</b><br>Adet: %{value}<br>Oran: %{percent}<extra></extra>")
            st.plotly_chart(fig_aks, use_container_width=True)

    with ga3:
        st.markdown("##### Mülk Tipi Dağılımı")
        if "Mülk tipi" in df.columns and not df.empty:
            mulk_ozet = df.groupby("Mülk tipi").size().reset_index(name="Adet").sort_values("Adet", ascending=False)
            renk_map = {"Konut":"#94a3b8","Ticari":"#1e3a5f","Arsa":"#16a34a"}
            fig_mulk = px.bar(mulk_ozet, x="Mülk tipi", y="Adet", text="Adet",
                               color="Mülk tipi", color_discrete_map=renk_map)
            fig_mulk.update_layout(height=320, xaxis_title="", yaxis_title="Adet",
                margin=dict(l=0,r=0,t=10,b=40), plot_bgcolor="white", paper_bgcolor="white", showlegend=False)
            fig_mulk.update_traces(textposition="outside", cliponaxis=False, textfont=dict(size=12))
            st.plotly_chart(fig_mulk, use_container_width=True)

# Ofis Bazlı Analiz
with st.expander("📊 Ofis Bazlı Analiz", expanded=True):
    if "Ofis_norm" in df.columns:
        oc1, oc2 = st.columns([1.2, 1])
        with oc1:
            st.markdown('<div class="section-title">Ofis Bazlı Dağılım (tüm ofisler)</div>', unsafe_allow_html=True)
            st.caption("🖱️ Bir ofis satırına tıklayınca aşağıdaki ilan listesi o ofise göre filtrelenir.")
            if ESLESMEYEN_OFISLER:
                if st.checkbox(
                    f"⚠️ Rehberle eşleşmeyen {len(ESLESMEYEN_OFISLER)} Revy ofis adını göster",
                    key="sk_eslesmeyen_goster",
                ):
                    st.caption(
                        "Bu ofis adları Startkey Rehberi'ndeki (Supabase `rehber_ofisler`) "
                        "hiçbir kayıtla yeterince benzeşmedi, bu yüzden Revy'deki ham metinleriyle "
                        "ayrı satırlar olarak görünüyorlar — aynı ofisin farklı yazımı olabilirler."
                    )
                    st.write(list(ESLESMEYEN_OFISLER))
            ofis_grp = df_num.groupby("Ofis_norm", dropna=False).agg(
                Kayıt=("__birim","count"),
                Ort_Fiyat=("__fiyat","mean"),
                Ort_m2=("__m2","mean"),
                Ort_Birim=("__birim","mean"),
            ).reset_index().sort_values("Kayıt", ascending=False).rename(columns={"Ofis_norm":"Ofis"})
            for c in ["Ort_Fiyat","Ort_m2","Ort_Birim"]:
                ofis_grp[c] = ofis_grp[c].round(0)

            ofis_tablo_col_config = {
                "Ofis":      st.column_config.TextColumn("Ofis"),
                "Ort_Fiyat": st.column_config.NumberColumn("Ort. Fiyat", format="%.0f ₺"),
                "Ort_m2":    st.column_config.NumberColumn("Ort. M²", format="%.0f"),
                "Ort_Birim": st.column_config.NumberColumn("Ort. m² Fiyatı", format="%.0f ₺"),
            }
            try:
                secim = st.dataframe(
                    ofis_grp, use_container_width=True, hide_index=True, height=400,
                    column_config=ofis_tablo_col_config,
                    on_select="rerun", selection_mode="single-row",
                    key="sk_ofis_tablo",
                )
                secilen_satirlar = getattr(secim, "selection", None)
                secilen_satirlar = secilen_satirlar.rows if secilen_satirlar else []
                if secilen_satirlar:
                    tiklanan_ofis = ofis_grp.iloc[secilen_satirlar[0]]["Ofis"]
                    if st.session_state.get("sk_ofis") != [tiklanan_ofis]:
                        st.session_state["_sk_ofis_pending"] = [tiklanan_ofis]
                        st.rerun()
            except TypeError:
                # Eski Streamlit sürümü on_select desteklemiyor olabilir — tıklama olmadan tabloyu göster
                st.dataframe(ofis_grp, use_container_width=True, hide_index=True, height=400,
                    column_config=ofis_tablo_col_config)
        with oc2:
            st.markdown('<div class="section-title">Ofis Grafiği (tüm ofisler)</div>', unsafe_allow_html=True)
            grafik_df = ofis_grp.sort_values("Kayıt")
            fig = px.bar(grafik_df, x="Kayıt", y="Ofis", orientation="h", text="Kayıt")
            fig.update_traces(marker_color="#355C7D", textposition="outside", textfont_size=9)
            fig.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=0,r=10,t=5,b=0), height=max(400, 24*len(grafik_df)+80), font=dict(size=10))
            st.plotly_chart(fig, use_container_width=True)

# Danışman Bazlı Analiz
with st.expander("👤 Danışman Bazlı Analiz", expanded=True):
    _dan_kolon = next((c for c in ["İlan sahibi","Danışman","İlan Sahibi"] if c in df.columns), None)
    if _dan_kolon:
        dc1, dc2 = st.columns([1.2, 1])
        with dc1:
            st.markdown('<div class="section-title">Danışman Bazlı Dağılım (tüm danışmanlar)</div>', unsafe_allow_html=True)
            st.caption("🖱️ Bir danışman satırına tıklayınca aşağıdaki ilan listesi ona göre filtrelenir.")

            dan_num = df_num.copy()
            # NOT: Aynı danışman "MUSTAFA YİĞİT", "mustafa yiğit", "Mustafa Yiğit"
            # gibi farklı yazımlarla gelebiliyor (Revy'ye kim nasıl girmişse).
            # _tr_title() ile hepsini TEK bir görünüme normalize ediyoruz,
            # aksi halde aynı kişi 2-3 ayrı satır olarak görünüyordu.
            dan_num["__dan"] = dan_num[_dan_kolon].astype(str).apply(_tr_title)
            dan_num = dan_num[dan_num["__dan"].str.lower().isin(["", "nan", "none"]) == False]
            _ofis_kolon_dan = "Ofis_norm" if "Ofis_norm" in dan_num.columns else ("Ofis" if "Ofis" in dan_num.columns else None)
            dan_num["__ofis"] = dan_num[_ofis_kolon_dan].astype(str).str.strip() if _ofis_kolon_dan else ""

            dan_grp = dan_num.groupby(["__dan", "__ofis"], dropna=False).agg(
                Kayıt=("__birim","count"),
                Ort_Fiyat=("__fiyat","mean"),
                Ort_m2=("__m2","mean"),
                Ort_Birim=("__birim","mean"),
            ).reset_index().sort_values("Kayıt", ascending=False).rename(
                columns={"__dan":"Danışman", "__ofis":"Ofis"})
            for c in ["Ort_Fiyat","Ort_m2","Ort_Birim"]:
                dan_grp[c] = dan_grp[c].round(0)
            dan_grp = dan_grp[["Danışman","Ofis","Kayıt","Ort_Fiyat","Ort_m2","Ort_Birim"]]

            dan_tablo_col_config = {
                "Danışman":  st.column_config.TextColumn("Danışman"),
                "Ofis":      st.column_config.TextColumn("Ofis"),
                "Ort_Fiyat": st.column_config.NumberColumn("Ort. Fiyat", format="%.0f ₺"),
                "Ort_m2":    st.column_config.NumberColumn("Ort. M²", format="%.0f"),
                "Ort_Birim": st.column_config.NumberColumn("Ort. m² Fiyatı", format="%.0f ₺"),
            }
            try:
                secim_dan = st.dataframe(
                    dan_grp, use_container_width=True, hide_index=True, height=400,
                    column_config=dan_tablo_col_config,
                    on_select="rerun", selection_mode="single-row",
                    key="sk_dan_tablo",
                )
                secilen_dan_satir = getattr(secim_dan, "selection", None)
                secilen_dan_satir = secilen_dan_satir.rows if secilen_dan_satir else []
                if secilen_dan_satir:
                    tiklanan_dan = dan_grp.iloc[secilen_dan_satir[0]]["Danışman"]
                    if st.session_state.get("sk_liste_dan") != tiklanan_dan:
                        st.session_state["_sk_liste_dan_pending"] = tiklanan_dan
                        st.rerun()
            except TypeError:
                st.dataframe(dan_grp, use_container_width=True, hide_index=True, height=400,
                    column_config=dan_tablo_col_config)
        with dc2:
            st.markdown('<div class="section-title">Danışman Grafiği (ilk 30)</div>', unsafe_allow_html=True)
            dan_grafik_df = dan_grp.head(30).sort_values("Kayıt")
            dan_grafik_df["Etiket"] = dan_grafik_df["Danışman"] + " (" + dan_grafik_df["Ofis"] + ")"
            fig_dan = px.bar(dan_grafik_df, x="Kayıt", y="Etiket", orientation="h", text="Kayıt")
            fig_dan.update_traces(marker_color="#D71920", textposition="outside", textfont_size=9)
            fig_dan.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=0,r=10,t=5,b=0), height=max(400, 24*len(dan_grafik_df)+80), font=dict(size=10),
                yaxis_title="")
            st.plotly_chart(fig_dan, use_container_width=True)
    else:
        st.info("Danışman bilgisi (İlan sahibi) sütunu bulunamadı.")

# İlan Listesi
st.markdown('<div class="section-title">İLAN LİSTESİ</div>', unsafe_allow_html=True)

SIR = ["Tarih ↓","Tarih ↑","Fiyat ↑","Fiyat ↓","M² ↑","M² ↓"]
sb1, sb2, sb3, sb4, sb5 = st.columns([2.2, 1.5, 1.5, 1.3, 1])
with sb1:
    ara = st.text_input("Ara", placeholder="Başlık, mahalle, ofis...", label_visibility="collapsed", key="sk_ara")
with sb2:
    _ofis_liste_opts = sorted(df["Ofis_norm"].dropna().unique().tolist()) if "Ofis_norm" in df.columns else []
    ofis_liste_filtre = st.selectbox("Ofis", ["Tüm Ofisler"] + _ofis_liste_opts, label_visibility="collapsed", key="sk_liste_ofis")
with sb3:
    _dan_kolon_liste = next((c for c in ["İlan sahibi","Danışman","İlan Sahibi"] if c in df.columns), None)
    _dan_liste_opts = sorted(set(df[_dan_kolon_liste].dropna().astype(str).apply(_tr_title))) if _dan_kolon_liste else []
    _dan_liste_opts = [d for d in _dan_liste_opts if d and d.lower() not in ("nan","none")]
    danisman_liste_filtre = st.selectbox("Danışman", ["Tüm Danışmanlar"] + _dan_liste_opts, label_visibility="collapsed", key="sk_liste_dan")
with sb4:
    sir = st.selectbox("Sırala", SIR, label_visibility="collapsed", key="sk_sir")
with sb5:
    buf = BytesIO(); df.to_excel(buf, index=False)
    st.download_button("📥 Excel", data=buf.getvalue(),
        file_name=f"startkey_{datetime.now().strftime('%Y%m%d')}.xlsx",
        use_container_width=True)

tablo = df.copy()
if ara:
    al = ara.lower()
    cols_ara = [c for c in ["İlan Başlığı","Mahalle","İlçe","Ofis"] if c in tablo.columns]
    tablo = tablo[tablo.apply(lambda r: any(al in str(r.get(c,"")).lower() for c in cols_ara), axis=1)]
if ofis_liste_filtre != "Tüm Ofisler" and "Ofis_norm" in tablo.columns:
    tablo = tablo[tablo["Ofis_norm"] == ofis_liste_filtre]
if danisman_liste_filtre != "Tüm Danışmanlar" and _dan_kolon_liste:
    tablo = tablo[tablo[_dan_kolon_liste].astype(str).apply(_tr_title) == danisman_liste_filtre]

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

# ── SAYFALAMA ────────────────────────────────────────────────────────────
# NOT: Binlerce satırı TEK bir HTML bloğu olarak components.html() ile
# iframe'e gömmek, tarayıcıda ciddi boyutlarda bir "srcdoc" oluşturuyor ve
# bazı durumlarda içerik bozuk/kesik render ediliyor (görsel çeviri hatasıyla
# karıştırılabilecek şekilde). Bu yüzden tablo artık sayfalara bölünüyor.
SAYFA_BOYUTU = 100
toplam_sayfa = max(1, (len(tablo) - 1) // SAYFA_BOYUTU + 1) if len(tablo) else 1
if st.session_state.get("sk_liste_sayfa", 1) > toplam_sayfa:
    st.session_state["sk_liste_sayfa"] = 1
pg1, pg2 = st.columns([1, 5])
with pg1:
    sayfa_no = st.number_input("Sayfa", min_value=1, max_value=toplam_sayfa, value=1,
                                step=1, key="sk_liste_sayfa", label_visibility="collapsed")
with pg2:
    st.caption(f"Sayfa {sayfa_no} / {toplam_sayfa} — sayfa başına {SAYFA_BOYUTU} ilan")

_bas = (sayfa_no - 1) * SAYFA_BOYUTU
tablo_sayfa = tablo.iloc[_bas:_bas + SAYFA_BOYUTU]

def _s(v):
    # NOT: "v is None" kontrolü pandas'ın boş (NaN) değerlerini yakalamıyordu —
    # bir float NaN, None değil, bu yüzden str(nan) = "nan" (boş olmayan bir
    # metin) direkt ekrana basılıyordu. pd.isna() ile düzeltildi.
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "-"
    s = str(v).strip()
    if s.lower() in ("nan", "none", "nat", "<na>"):
        return "-"
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
for i,(_, row) in enumerate(tablo_sayfa.iterrows(), _bas + 1):
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
        +f'<td style="{td}"><div style="font-size:10px;color:#355C7D;font-weight:600;white-space:nowrap;">{_s(str(row.get("Ofis_norm", row.get("Ofis","")))[:35])}</div><div style="font-size:10px;color:#94a3b8;margin-top:2px;">{_s(str(row.get("İlan sahibi", row.get("Danışman",""))).strip()[:25])}</div></td>'
        +"</tr>")

ths = "padding:8px 10px;text-align:left;font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:#64748b;border-bottom:2px solid #e2e8f0;background:#f8fafc;white-space:nowrap;"
cols_h = ["","#","Başlık / Durum","İşlem / Mülk","İlçe / Mah","M²","Fiyat / m²","Oda","Kat / Yaş","Süre / Tarih","İlan","Ofis / GD"]
bh = "".join(f'<th style="{ths}">{c}</th>' for c in cols_h)
html_t = ("<style>.ht tbody tr:hover td{background:#EEF4FA!important;}</style>"
    +'<div style="background:white;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;">'
    +'<div style="overflow-x:auto;">'
    +f'<table class="ht"><thead><tr>{bh}</tr></thead><tbody>{rows}</tbody></table>'
    +"</div></div>")
components.html(html_t, height=min(1200, 80+len(tablo_sayfa)*52), scrolling=True)


with sekme2:
    st.markdown('<div class="filtre-baslik">👤 Danışman Seçimi</div>', unsafe_allow_html=True)

    if rehber_dan_df.empty:
        st.info("Rehber verisi yüklenemedi. Supabase bağlantısını kontrol edin.")
    else:
        # Danışman listesi — ofis bazlı grupla
        s2a, s2b = st.columns([2, 2])
        with s2a:
            ofis_secenekleri = ["Tümü"] + sorted(rehber_dan_df["ofis_adi"].dropna().unique().tolist())
            ofis_sec2 = st.selectbox("Ofis Filtrele", ofis_secenekleri, key="s2_ofis")
        with s2b:
            if ofis_sec2 != "Tümü":
                dan_listesi = sorted(rehber_dan_df[rehber_dan_df["ofis_adi"]==ofis_sec2]["isim"].dropna().unique().tolist())
            else:
                dan_listesi = sorted(rehber_dan_df["isim"].dropna().unique().tolist())
            dan_sec2 = st.selectbox("Danışman", ["Seçin..."] + dan_listesi, key="s2_dan")

        if dan_sec2 and dan_sec2 != "Seçin...":
            # Danışmanın rehberdeki bilgileri
            dan_bilgi = rehber_dan_df[rehber_dan_df["isim"] == dan_sec2]
            if not dan_bilgi.empty:
                db = dan_bilgi.iloc[0]
                ofis_adi_rehber = db.get("ofis_adi","")
                telefon_str = db.get("telefon","")
                mail_str    = db.get("mail","")
                profil_link = db.get("profil_link","")

                # Danışman bilgi kartı
                bilgi_html = f"""
<div style="background:white;border:1px solid var(--border);border-radius:10px;
    padding:14px 18px;margin-bottom:14px;display:flex;gap:16px;align-items:center;">
    <div>
        <div style="font-size:14px;font-weight:800;color:#0f172a;">{_s(dan_sec2)}</div>
        <div style="font-size:12px;color:#355C7D;font-weight:600;margin-top:2px;">{_s(ofis_adi_rehber)}</div>
        <div style="font-size:11px;color:#64748b;margin-top:4px;">
            {"☎ " + _s(telefon_str) + " &nbsp;" if telefon_str else ""}
            {"✉ " + _s(mail_str) if mail_str else ""}
        </div>
    </div>
    {"<a href='" + profil_link + "' target='_blank' style='margin-left:auto;display:inline-block;padding:6px 14px;background:#EEF4FA;border:1px solid #C8D7E5;border-radius:8px;font-size:11px;font-weight:700;color:#355C7D;text-decoration:none;'>Startkey Profili</a>" if profil_link else ""}
</div>"""
                st.markdown(bilgi_html, unsafe_allow_html=True)

            # İlanları filtrele — danışman adını "İlan sahibi" veya "Danışman" kolonunda ara
            ilan_cols = [c for c in df_ham.columns if c.lower() in ("i̇lan sahibi","ilan sahibi","danışman","danishman","gd","talep_eden_danisan")]
            if ilan_cols:
                col_adi = ilan_cols[0]
                dan_ilanlar = df_ham[df_ham[col_adi].astype(str).str.lower().str.contains(dan_sec2.lower(), na=False)].copy()
            else:
                # Kolon bulunamazsa ofis adı üzerinden filtrele
                dan_ilanlar = df_ham[df_ham["Ofis_norm"].astype(str).str.lower().str.contains(
                    ofis_adi_rehber.lower()[:15] if ofis_adi_rehber else "", na=False)].copy()
                st.caption("⚠️ GD kolonu bulunamadı, ofis bazlı filtreleniyor.")

            toplam_s2 = len(dan_ilanlar)

            if toplam_s2 == 0:
                st.info(f"{dan_sec2} adına ait ilan bulunamadı.")
            else:
                # Mini KPI
                mk1, mk2, mk3 = st.columns(3)
                df_num2 = dan_ilanlar.copy()
                df_num2["__f"] = df_num2.get("Fiyat", pd.Series()).apply(lambda v: parse_num(v))
                df_num2["__m"] = pd.to_numeric(df_num2.get("M2", pd.Series()), errors="coerce")
                df_num2["__b"] = df_num2["__f"] / df_num2["__m"].replace(0, pd.NA)
                ort_b2 = df_num2["__b"].mean()

                aktif_n2  = len(dan_ilanlar[dan_ilanlar["_durum"]=="aktif"]) if "_durum" in dan_ilanlar.columns else toplam_s2
                kalkan_n2 = len(dan_ilanlar[dan_ilanlar["_durum"]=="yayindan_kalkan"]) if "_durum" in dan_ilanlar.columns else 0

                with mk1:
                    st.markdown(f"""<div class="kpi-card">
                        <div class="kpi-label">Toplam İlan</div>
                        <div class="kpi-value kpi-blue">{toplam_s2}</div>
                    </div>""", unsafe_allow_html=True)
                with mk2:
                    st.markdown(f"""<div class="kpi-card">
                        <div class="kpi-label">Aktif / Kalkan</div>
                        <div class="kpi-value kpi-green">{aktif_n2} <span style="font-size:1rem;color:#94a3b8;">/ {kalkan_n2}</span></div>
                    </div>""", unsafe_allow_html=True)
                with mk3:
                    st.markdown(f"""<div class="kpi-card">
                        <div class="kpi-label">Ort. m² Fiyatı</div>
                        <div class="kpi-value kpi-blue">{f"{ort_b2:,.0f} ₺".replace(",",".") if pd.notna(ort_b2) else "-"}</div>
                    </div>""", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Excel
                buf2 = BytesIO(); dan_ilanlar.to_excel(buf2, index=False)
                dl1, dl2 = st.columns([4,1])
                with dl1: st.caption(f"{toplam_s2} ilan")
                with dl2:
                    st.download_button("📥 Excel", data=buf2.getvalue(),
                        file_name=f"{dan_sec2.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        use_container_width=True)

                # Tablo
                dan_ilanlar = dan_ilanlar.sort_values(
                    "İlan tarihi", ascending=False, na_position="last"
                ) if "İlan tarihi" in dan_ilanlar.columns else dan_ilanlar

                rows2 = ""
                for i,(_, row) in enumerate(dan_ilanlar.iterrows(), 1):
                    islem = row.get("İşlem tipi","") or ""
                    tip   = str(islem).lower()
                    bdr   = "#1e3a5f" if "sat" in tip else ("#0d9488" if "kir" in tip else "#e2e8f0")
                    link  = row.get("İlan Url","") or ""
                    link_b = (f'<a href="{_html.escape(str(link))}" target="_blank" style="display:inline-block;padding:2px 8px;border-radius:6px;background:#f1f5f9;border:1px solid #e2e8f0;font-size:10px;font-weight:700;color:#374151;text-decoration:none;">Aç</a>' if link and link!="-" else "-")
                    td = "padding:8px 10px;"
                    rows2 += ("<tr>"
                        +f'<td style="padding:8px 3px 8px 0;border-left:3px solid {bdr};width:3px;"></td>'
                        +f'<td style="{td}color:#94a3b8;font-size:10px;">{i}</td>'
                        +f'<td style="{td}max-width:240px;min-width:180px;"><div style="font-size:11px;font-weight:700;color:#0f172a;line-height:1.3;">{_s(row.get("İlan Başlığı",""))[:75]}</div><div style="margin-top:3px;">{_durum_badges(row)}</div></td>'
                        +f'<td style="{td}"><div style="font-size:11px;font-weight:700;color:{"#1e3a5f" if "sat" in tip else "#0d9488"};">{_s(islem)}</div><div style="font-size:10px;color:#64748b;">{_s(row.get("Mülk türü",""))} / {_s(row.get("Mülk tipi",""))}</div></td>'
                        +f'<td style="{td}"><div style="font-size:11px;font-weight:600;">{_s(row.get("İlçe",""))}</div><div style="font-size:10px;color:#64748b;">{_s(row.get("Mahalle",""))}</div></td>'
                        +f'<td style="{td}font-size:11px;color:#475569;">{_s(row.get("M2",""))} m²</td>'
                        +f'<td style="{td}">{_fiyat(row.get("Fiyat",""), row.get("M2",""), row.get("m2/Birim Fiyatı",""))}</td>'
                        +f'<td style="{td}font-size:11px;color:#475569;">{_s(row.get("Oda sayısı",""))}</td>'
                        +f'<td style="{td}">{_sure(row.get("İlan tarihi",""))}</td>'
                        +f'<td style="{td}">{link_b}</td>'
                        +"</tr>")

                ths2 = "padding:8px 10px;text-align:left;font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:#64748b;border-bottom:2px solid #e2e8f0;background:#f8fafc;white-space:nowrap;"
                cols_h2 = ["","#","Başlık","İşlem / Mülk","İlçe / Mah","M²","Fiyat / m²","Oda","Tarih","İlan"]
                bh2 = "".join(f'<th style="{ths2}">{c}</th>' for c in cols_h2)
                html_t2 = ("<style>.ht2 tbody tr:hover td{background:#EEF4FA!important;}</style>"
                    +'<div style="background:white;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;">'
                    +'<div style="overflow-x:auto;">'
                    +f'<table class="ht2"><thead><tr>{bh2}</tr></thead><tbody>{rows2}</tbody></table>'
                    +"</div></div>")
                components.html(html_t2, height=min(800, 80+len(dan_ilanlar)*52), scrolling=True)
        else:
            st.info("Yukarıdan bir danışman seçin.")


with sekme3:
    st.markdown('<div class="filtre-baslik">🚪 Ayrılan / Pasife Alınan Danışmanlar</div>', unsafe_allow_html=True)
    st.caption(
        "Bu liste, `rehber_sync.py` çalıştırıldığında startkey.com.tr'de artık "
        "görünmeyen danışmanları gösterir (aktif=False yapılanlar). "
        "En son ayrılan en üstte."
    )

    ayrilanlar_df = ayrilan_danismanlar_yukle()

    if ayrilanlar_df.empty:
        st.info("Kayıtlı ayrılan/pasife alınmış danışman yok.")
    else:
        ay1, ay2 = st.columns([2, 2])
        with ay1:
            ay_ofis_opts = ["Tümü"] + sorted(ayrilanlar_df["ofis_adi"].dropna().unique().tolist())
            ay_ofis_sec = st.selectbox("Ofis Filtrele", ay_ofis_opts, key="sk_ayrilan_ofis")
        with ay2:
            ay_ara = st.text_input("İsim ara", placeholder="Danışman adı...", key="sk_ayrilan_ara")

        gosterilen = ayrilanlar_df.copy()
        if ay_ofis_sec != "Tümü":
            gosterilen = gosterilen[gosterilen["ofis_adi"] == ay_ofis_sec]
        if ay_ara:
            gosterilen = gosterilen[gosterilen["isim"].astype(str).str.contains(ay_ara, case=False, na=False)]

        st.caption(f"{len(gosterilen)} ayrılmış danışman gösteriliyor (toplam {len(ayrilanlar_df)})")

        def _tarih_fmt(v):
            try:
                dt = pd.to_datetime(v)
                return dt.strftime("%d.%m.%Y %H:%M")
            except Exception:
                return "-"

        gosterim_df = pd.DataFrame({
            "Ofis": gosterilen["ofis_adi"],
            "İsim": gosterilen["isim"],
            "Telefon": gosterilen.get("telefon", ""),
            "Mail": gosterilen.get("mail", ""),
            "Ayrıldığı Tarih": gosterilen["guncelleme_tar"].apply(_tarih_fmt) if "guncelleme_tar" in gosterilen.columns else "-",
        })

        st.dataframe(gosterim_df, use_container_width=True, hide_index=True, height=min(600, 80 + len(gosterim_df) * 36))

        buf3 = BytesIO()
        gosterim_df.to_excel(buf3, index=False)
        st.download_button(
            "📥 Excel'e Aktar",
            data=buf3.getvalue(),
            file_name=f"ayrilan_danismanlar_{datetime.now().strftime('%Y%m%d')}.xlsx",
            use_container_width=False,
        )


with sekme4:
    st.markdown('<div class="filtre-baslik">📚 Geçmiş Taramalar (Arşiv)</div>', unsafe_allow_html=True)
    st.caption(
        "Her başarılı 'Yeni Sorgu' taraması burada ayrı bir kayıt olarak saklanır. "
        "Yeni bir bölge taraması yapman, önceki (ör. tüm İzmir) sonucunu SİLMEZ — "
        "istediğin zaman buradan geri yükleyebilirsin."
    )

    gecmis_kayitlar = gecmis_listele()

    if not gecmis_kayitlar:
        st.info("Henüz arşivlenmiş bir tarama yok. 'Yeni Sorgu' ile bir arama yaptığında burada görünecek.")
    else:
        st.caption(f"{len(gecmis_kayitlar)} kayıtlı tarama")

        for kayit in gecmis_kayitlar:
            with st.container():
                ar1, ar2, ar3, ar4, ar5 = st.columns([2.5, 1.3, 1, 1, 1])
                with ar1:
                    st.markdown(
                        f'<div style="font-size:13px;font-weight:700;color:#0f172a;padding:6px 0;">{_html.escape(kayit.get("etiket",""))}</div>',
                        unsafe_allow_html=True)
                with ar2:
                    st.markdown(
                        f'<div style="font-size:11px;color:#64748b;padding:6px 0;">🕐 {kayit.get("zaman","-")}</div>',
                        unsafe_allow_html=True)
                with ar3:
                    st.markdown(
                        f'<div style="font-size:12px;color:#355C7D;font-weight:700;padding:6px 0;">{kayit.get("kayit_sayisi",0):,} ilan</div>',
                        unsafe_allow_html=True)
                with ar4:
                    if st.button("📂 Yükle", key=f"gecmis_yukle_{kayit['dosya']}", use_container_width=True):
                        _veri = gecmis_yukle(kayit["dosya"])
                        if _veri is not None:
                            st.session_state.sk_veri = _veri
                            st.session_state.sk_last_filtre = {}  # arşivden yüklendi, "aynı filtre" karşılaştırmasını sıfırla
                            st.session_state.sk_cache_zaman = kayit.get("zaman", "")
                            st.session_state["_sk_filtre_sifirla"] = True  # eski Ofis Adı vb. seçimleri temizle
                            st.toast(f"'{kayit.get('etiket','')}' yüklendi ✓")
                            st.rerun()
                        else:
                            st.error("Bu kayıt yüklenemedi (dosya bulunamadı veya bozuk).")
                with ar5:
                    if st.button("🗑", key=f"gecmis_sil_{kayit['dosya']}", use_container_width=True, help="Bu arşiv kaydını sil"):
                        gecmis_sil(kayit["dosya"])
                        st.toast("Kayıt silindi.")
                        st.rerun()
                st.divider()
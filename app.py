import streamlit as st

st.set_page_config(
    page_title="Startkey Zeta",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────
# SESSION RESTORE
# Local geliştirme ortamında dosya tabanlı session restore
# aktif. Cloud ortamında core/personel_manager.py içindeki
# load_login_session() kendini otomatik devre dışı bırakıyor
# (HOME path kontrolü), bu yüzden burada ek bir guard'a
# gerek yok. LOCAL_SESSION_RESTORE flag'i core/auth.py'de.
# ─────────────────────────────────────────────────────
if not st.session_state.get("kullanici"):
    try:
        from core.auth import LOCAL_SESSION_RESTORE
        from core.personel_manager import load_login_session, enrich_session_from_personel

        if LOCAL_SESSION_RESTORE:
            _saved = load_login_session()
            if _saved:
                _kullanici = enrich_session_from_personel(dict(_saved))
                if _kullanici.get("email") or _kullanici.get("user_key"):
                    st.session_state["kullanici"] = _kullanici
    except Exception as e:
        st.warning(f"Session restore hatası: {e}")

# ─────────────────────────────────────────────────────
# CLOUD GÜVENLİĞİ: impersonate flag'i tutarsız kalmışsa temizle
# ─────────────────────────────────────────────────────
if not st.session_state.get("kullanici", {}).get("_impersonated"):
    st.session_state.pop("_impersonate_active", None)
    st.session_state.pop("_impersonate_original", None)

# ─────────────────────────────────────────────────────
# USER SYNC — güvenli ad/rol üretimi (boş alan fallback'leri)
# ─────────────────────────────────────────────────────
_k = st.session_state.get("kullanici", {})

if _k:
    _ad = (
        _k.get("ad_soyad")
        or _k.get("ad")
        or _k.get("email", "").split("@")[0]
    )
    _rol = _k.get("rol") or "danisan"

    st.session_state["user_role"] = _rol
    st.session_state["user_name"] = _ad
    st.session_state["user_initials"] = "".join(
        w[0].upper() for w in _ad.split()[:2] if w
    )
    st.session_state["kullanici_id"] = _k.get("id", "")

# ─────────────────────────────────────────────────────
# PAGES
# ─────────────────────────────────────────────────────
giris = st.Page(
    "pages/giris.py",
    title="Giriş",
    icon=":material/login:",
    default=True,
)

ana = st.Page(
    "pages/ana_sayfa.py",
    title="Ana Sayfa",
    icon=":material/home:",
)

profil = st.Page(
    "pages/profil.py",
    title="Profilim",
    icon=":material/person:",
)

taleplerim = st.Page(
    "pages/taleplerim.py",
    title="Taleplerim",
    icon=":material/person_pin:",
)

gd_calisma_alani = st.Page(
    "pages/gd_calisma_alani.py",
    title="GD Çalışma Alanı",
    icon=":material/dashboard_customize:",
)

portfoylerím = st.Page(
    "pages/portfoylerím.py",
    title="Portföylerim",
    icon=":material/bookmark_heart:",
)

zeta_ilanlar = st.Page(
    "pages/portfoy_listesi.py",
    title="Zeta İlanları",
    icon=":material/home_work:",
)

talep = st.Page(
    "pages/2_Talep_Tablosu.py",
    title="Talep Merkezi",
    icon=":material/list_alt:",
)

portfoy = st.Page(
    "pages/3_Portfoy_Tablosu.py",
    title="Portföy Havuzu",
    icon=":material/home_work:",
)

eslestirme = st.Page(
    "pages/eslestirme_motoru.py",
    title="Eşleştirme",
    icon=":material/hub:",
)

sunum = st.Page(
    "pages/Sunum_Merkezi_V2_Demo.py",
    title="Sunum Merkezi",
    icon=":material/auto_awesome:",
)

ajandam = st.Page(
    "pages/ajandam.py",
    title="Ajandam",
    icon=":material/event:",
)

ofis = st.Page(
    "pages/4_Ofis_Paneli.py",
    title="Ofis Paneli",
    icon=":material/dashboard:",
)

operasyon_merkezi = st.Page(
    "pages/operasyon_merkezi.py",
    title="Operasyon Merkezi",
    icon=":material/settings:",
)

sozlesmeler_formlar = st.Page(
    "pages/sozlesmeler_ve_formlar.py",
    title="Sözleşmeler ve Formlar",
    icon=":material/description:",
)

mail = st.Page(
    "pages/5_Mail_Islem.py",
    title="Mail İşlem",
    icon=":material/move_to_inbox:",
)

proje = st.Page(
    "pages/proje_hafizasi_app_v2.py",
    title="Proje Hafızası",
    icon=":material/bookmark:",
)

kullanici = st.Page(
    "pages/kullanici_sec.py",
    title="Kullanıcı Görünümü",
    icon=":material/switch_account:",
)

pazar_analiz = st.Page(
    "pages/pazar_analiz.py",
    title="Pazar Radar",
    icon=":material/analytics:",
)

pazar_raporu = st.Page(
    "pages/pazar_raporu.py",
    title="Pazar Raporu",
    icon=":material/description:",
)

# ── Daha önce eksik olan sayfalar (ui_helpers.py ve ana_sayfa.py'de
#    route'ları tanımlıydı ama burada st.Page olarak kayıtlı değildi) ──
arsiv_merkezi = st.Page(
    "pages/arsiv_merkezi.py",
    title="Arşiv Merkezi",
    icon=":material/archive:",
)

rehber = st.Page(
    "pages/rehber_app.py",
    title="Startkey Rehberi",
    icon=":material/contacts:",
)

startkey_ilanlar = st.Page(
    "pages/startkey_portfoy_listesi.py",
    title="Startkey İlanları",
    icon=":material/travel_explore:",
)

# ─────────────────────────────────────────────────────
# NAVIGATION
# ─────────────────────────────────────────────────────
pg = st.navigation(
    {
        "": [
            giris,
            ana,
            profil,
        ],

        "Danışman": [
            gd_calisma_alani,
            taleplerim,
            portfoylerím,
            zeta_ilanlar,
            ajandam,
            talep,
            portfoy,
            arsiv_merkezi,
            rehber,
            eslestirme,
            sunum,
        ],

        "Ofis": [
            ofis,
            operasyon_merkezi,
            sozlesmeler_formlar,
        ],

        "Pazar & Analiz": [
            pazar_analiz,
            pazar_raporu,
            startkey_ilanlar,
        ],

        "Yönetici": [
            mail,
            proje,
            kullanici,
        ],
    },
    position="hidden"
)

pg.run()
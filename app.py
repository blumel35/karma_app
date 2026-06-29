import streamlit as st

st.set_page_config(
    page_title="Startkey Zeta",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────
# SESSION RESTORE (Cloud ortamında devre dışı)
# Local dosya sistemi cloud'da paylaşıldığı için
# kullanıcı oturumları birbirine karışıyor.
# ─────────────────────────────────────────────────────
# if not st.session_state.get("kullanici"):
#     try:
#         from core.personel_manager import (
#             load_login_session,
#             enrich_session_from_personel,
#         )
#         _saved = load_login_session()
#         if _saved:
#             ...
#     except Exception as e:
#         st.warning(f"Session restore hatası: {e}")

# ─────────────────────────────────────────────────────
# USER SYNC
# ─────────────────────────────────────────────────────
_k = st.session_state.get("kullanici", {})

if _k:
    _ad = _k.get("ad_soyad") or _k.get("ad", "")

    st.session_state["user_role"] = _k.get("rol", "danisan")
    st.session_state["user_name"] = _ad
    st.session_state["user_initials"] = "".join(
        w[0].upper() for w in _ad.split()[:2] if w
    )

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

talep_arsiv = st.Page(
    "pages/2_Talep_Arsiv.py",
    title="Talep Arşivi",
    icon=":material/inventory_2:",
)

portfoy = st.Page(
    "pages/3_Portfoy_Tablosu.py",
    title="Portföy Havuzu",
    icon=":material/home_work:",
)

portfoy_arsiv = st.Page(
    "pages/3_Portfoy_Arsiv.py",
    title="Portföy Arşivi",
    icon=":material/inventory_2:",
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
            taleplerim,
            portfoylerím,
            zeta_ilanlar,
            ajandam,
            talep,
            talep_arsiv,
            portfoy,
            portfoy_arsiv,
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
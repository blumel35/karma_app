import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Startkey Zeta",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────
# PWA (TELEFONDA "ANA EKRANA EKLE") DESTEĞİ — 2026-08-30
# Danışman Panosu'nu telefona simge olarak sabitleyip tarayıcı çubuğu
# olmadan, uygulama gibi açabilmek için. Streamlit'in kendi HTML <head>'ine
# resmi bir erişim yolu yok — bu yüzden bilinen bir teknik kullanılıyor:
# components.html ile aynı-origin bir script çalıştırıp
# window.parent.document.head'e manifest linkini + Apple'a özel meta
# etiketlerini elle ekliyoruz. height=0 olduğu için sayfada hiçbir görsel
# iz bırakmaz, HER sayfada (app.py tek giriş noktası olduğu için) bir kez
# çalışır. Gerekli dosyalar: static/manifest.json + static/icons/*.png
# (bkz. tools/generate_pwa_icons.py) — bunların servis edilebilmesi için
# .streamlit/config.toml'da [server] enableStaticServing = true şart.
components.html(
    """
    <script>
    (function () {
        var head = window.parent.document.head;
        if (head.querySelector('link[rel="manifest"]')) { return; }

        var manifest = document.createElement('link');
        manifest.rel = 'manifest';
        manifest.href = '/app/static/manifest.json';
        head.appendChild(manifest);

        var themeColor = document.createElement('meta');
        themeColor.name = 'theme-color';
        themeColor.content = '#1C2B47';
        head.appendChild(themeColor);

        var appleCapable = document.createElement('meta');
        appleCapable.name = 'apple-mobile-web-app-capable';
        appleCapable.content = 'yes';
        head.appendChild(appleCapable);

        var appleStatusBar = document.createElement('meta');
        appleStatusBar.name = 'apple-mobile-web-app-status-bar-style';
        appleStatusBar.content = 'black-translucent';
        head.appendChild(appleStatusBar);

        var appleTitle = document.createElement('meta');
        appleTitle.name = 'apple-mobile-web-app-title';
        appleTitle.content = 'Danışman Panosu';
        head.appendChild(appleTitle);

        var appleTouchIcon = document.createElement('link');
        appleTouchIcon.rel = 'apple-touch-icon';
        appleTouchIcon.href = '/app/static/icons/apple-touch-icon.png';
        head.appendChild(appleTouchIcon);
    })();
    </script>
    """,
    height=0,
)

# ─────────────────────────────────────────────────────
# DAVET LİNKİ (Supabase "Invite User") — DOĞRUDAN RENDER, SAYFA GEÇİŞİ YOK
# Supabase'in davet e-postasındaki link, belirli bir sayfa yoluna değil
# uygulamanın KÖK adresine (Site URL) auth_action/token_hash/type query
# parametreleriyle geliyor — örn. ".../?auth_action=invite&token_hash=
# ...&type=invite".
#
# DÜZELTME (2026-08-27, 4. ve son deneme): Üç ayrı st.switch_page()
# yaklaşımı sırayla denendi ve üçü de gerçek ortamda başarısız oldu:
# (1) string yol + st.navigation() henüz oturmadan çağrı → StreamlitAPIException
#     "Could not find page" (ekran görüntüsüyle doğrulandı, tekrarlandı);
# (2) nesne referansıyla, st.navigation() tanımlandıktan SONRA çağrı →
#     tarayıcı seviyesinde "Page not found" diyaloğu belirdi (ekran
#     görüntüsüyle doğrulandı) — sayfa geçişi sırasında oluşan URL,
#     Streamlit'in ürettiği urlPathname ile tam eşleşmiyordu;
# (3) session_state fallback'e rağmen token_hash bazen hedef sayfanın
#     ilk render'ında kayboluyordu.
# Kök sebep hep aynı: SAYFA GEÇİŞİ (switch_page) bu ortamda güvenilmez.
# Bu yüzden artık hiç sayfa geçişi YAPMIYORUZ — davet parametreleri kök
# URL'de görülür görülmez core/auth_ui.py:render_hesap_aktivasyon()
# doğrudan burada çağrılıyor. Aynı script çalışması olduğu için query
# params hiç kaybolmuyor, tarayıcı URL'i hiç değişmiyor (kök URL'de
# kalıyor), st.switch_page hiç devreye girmiyor.
if (
    st.query_params.get("auth_action") == "invite"
    and st.query_params.get("token_hash")
    and st.query_params.get("type") == "invite"
):
    from core.auth_ui import render_hesap_aktivasyon

    render_hesap_aktivasyon()
    st.stop()

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
        # Session restore başarısız olursa kullanıcıya ham hata gösterilmez —
        # sessizce normal giriş akışına düşülür. Detay terminale loglanır.
        import logging
        logging.getLogger(__name__).exception("Session restore hatası: %s", e)

# ─────────────────────────────────────────────────────
# CLOUD GÜVENLİĞİ: impersonate flag'i tutarsız kalmışsa temizle
# ─────────────────────────────────────────────────────
if not st.session_state.get("kullanici", {}).get("_impersonated"):
    st.session_state.pop("_impersonate_active", None)
    st.session_state.pop("_impersonate_original", None)

# ─────────────────────────────────────────────────────
# USER SYNC — merkezi fonksiyon üzerinden (core/auth.py)
# ─────────────────────────────────────────────────────
from core.auth import set_session_fields

_k = st.session_state.get("kullanici", {})

if _k:
    set_session_fields(_k)

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

# ── Pano Görüntüle — paylaşım linkleri için, GİRİŞ GEREKTİRMEZ ──
# NOT: pages/Pano_Goruntule.py bilerek oturum_kontrol() çağırmıyor —
# linki bilen herkes (Karma App hesabı olmadan) açabilsin diye.
pano_goruntule = st.Page(
    "pages/Pano_Goruntule.py",
    title="Pano Görüntüle",
    icon=":material/dashboard:",
)

# ── Senaryo Hesaplayıcı — müşteriye gönderilmek üzere, girişsiz/bağımsız
# link (14.08.2026). Pano Görüntüle ile AYNI desen: oturum_kontrol() yok.
senaryo_hesaplayici = st.Page(
    "pages/Senaryo_Hesaplayici.py",
    title="Senaryo Hesaplayıcı",
    icon=":material/calculate:",
)

# ── Senaryo Hesaplayıcı OLUŞTURMA ekranı — danışman GİRİŞ yapmış olarak
# burada müşteriye özel veri girer, link üretir. Yukarıdaki
# senaryo_hesaplayici (görüntüleme) sayfasından AYRI — biri girişli
# (oluşturma), biri girişsiz (görüntüleme/müşteri linki).
danisman_senaryo_olustur = st.Page(
    "pages/Danisman_SenaryoOlustur.py",
    title="Senaryo Oluştur",
    icon=":material/edit_calendar:",
)

# ── Hesap Aktivasyonu — Supabase "Invite User" davet linkinin açtığı
# TEK amaçlı, girişsiz/bağımsız sayfa (bkz. core/auth.py: davet_token_dogrula,
# davet_sifresi_guncelle). Menüde HİÇ görünmemeli — Pano Görüntüle ve Senaryo
# Hesaplayıcı ile AYNI desen: st.navigation() listesine eklenmeden bu sayfaya
# hiçbir URL ile erişilemiyor ("sayfa bulunamadı" hatası) — önceden burada
# eksikti, davet linkleri bu yüzden açılmıyordu.
hesap_aktivasyon = st.Page(
    "pages/Hesap_Aktivasyon.py",
    title="Hesap Aktivasyonu",
    icon=":material/vpn_key:",
)

# ── Danışman Panosu — Karma App'ten BAĞIMSIZ görünen, sade mini-arayüz ──
# NOT: Kendi giriş ekranı (Danisman_Giris) ve kendi sade görünümü
# (Danisman_Pano, render_navbar yok) var — aynı Supabase hesaplarını
# ve aynı veritabanı tablolarını kullanır, ama görsel olarak Karma
# App'in kalabalık menüsünden tamamen ayrı, tek amaçlı bir arayüzdür.
danisman_giris = st.Page(
    "pages/Danisman_Giris.py",
    title="Danışman Girişi",
    icon=":material/login:",
)

danisman_pano = st.Page(
    "pages/Danisman_Pano.py",
    title="Danışman Panosu",
    icon=":material/dashboard:",
)

# ── 2026-08 revizyonu: eski tek-sayfa Danisman_Pano.py mimarisi,
# ayrı bir seçim ekranı + bağlama göre ayrılmış panolar mimarisine
# taşındı. Danisman_Pano.py artık sadece Danisman_Secim.py'ye
# yönlendiren bir stub — geriye dönük uyumluluk için tutuluyor.
danisman_secim = st.Page(
    "pages/Danisman_Secim.py",
    title="Danışman Panosu",
    icon=":material/dashboard:",
)

danisman_talep = st.Page(
    "pages/Danisman_Talep.py",
    title="Danışman Talep Panosu",
    icon=":material/download:",
)

danisman_portfoy = st.Page(
    "pages/Danisman_Portfoy.py",
    title="Danışman Portföy Panosu",
    icon=":material/home_work:",
)

danisman_favoriler = st.Page(
    "pages/Danisman_Favoriler.py",
    title="Favori Listem",
    icon=":material/star:",
)

# ── Uzmanlık Bölgelerim — Favori Listem'in COĞRAFİ kardeşi (09.08.2026) ──
danisman_uzmanlik_bolgeleri = st.Page(
    "pages/Danisman_UzmanlikBolgeleri.py",
    title="Uzmanlık Bölgelerim",
    icon=":material/pin_drop:",
)

danisman_kayitlarim = st.Page(
    "pages/Danisman_Kayitlarim.py",
    title="Kendi Kayıtlarım",
    icon=":material/folder_open:",
)

danisman_paylasimlar = st.Page(
    "pages/Danisman_Paylasimlar.py",
    title="Zeta Paylaşımları",
    icon=":material/groups:",
)

# ── Zeta Portföyleri — Revy'den senkronize, portallarda YAYINLANAN
# resmi ilanlar (12.08.2026). "Zeta Paylaşımları"ndan BAĞIMSIZ — o
# ofis-içi elle paylaşımları gösterir, bu ise portaldeki canlı envanteri.
danisman_zeta_portfoyleri = st.Page(
    "pages/Danisman_ZetaPortfoyleri.py",
    title="Zeta Portföyleri",
    icon=":material/campaign:",
)

# ── Rehberim — kişisel kişi defteri (13.08.2026). Talep/Portföy
# eklerken girilen müşteri adı buraya otomatik senkronize olur, ama
# talep/portföy silinse de kişi kaydı KALICI kalır (bağımsız tablo).
danisman_musterilerim = st.Page(
    "pages/Danisman_Rehberim.py",
    title="Rehberim",
    icon=":material/contacts:",
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
            hesap_aktivasyon,
            pano_goruntule,
            senaryo_hesaplayici,
            danisman_senaryo_olustur,
            danisman_giris,
            danisman_pano,
            danisman_secim,
            danisman_talep,
            danisman_portfoy,
            danisman_favoriler,
            danisman_uzmanlik_bolgeleri,
            danisman_kayitlarim,
            danisman_paylasimlar,
            danisman_zeta_portfoyleri,
            danisman_musterilerim,
        ],

        "Danışman": [
            gd_calisma_alani,
            taleplerim,
            portfoylerím,
            ajandam,
            talep,
            portfoy,
            arsiv_merkezi,
            rehber,
            eslestirme,
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
            kullanici,
        ],
    },
    position="hidden"
)

pg.run()

"""
pages/Danisman_Bildirimlerim.py

YENİ (26.09.2026, Meltem: "bu bildirimlerin danışman panodaki bildirim
sayfasında da gösterilmesini istiyorum. kişi kendisi de uygulamaya girip
son bildirimleri görmeli"): telefon push bildirimlerinin (core/push_
bildirim.py, core/bildirim_tetikleyici.py) kalıcı bir izini — push
kaçırılsa/izin verilmemiş olsa bile içeriden görülebilen bir "gelen
kutusu" ekranı. bildirim_gonder() artık HER çağrıldığında (push başarılı
olsun olmasın) core/push_bildirim.py'deki bildirim_gecmisi tablosuna bir
satır yazıyor — bu sayfa o tabloyu su_anki_danisman()'a göre filtreleyip
listeliyor.

Diğer Danışman ekranlarıyla AYNI iskelet: oturum_kontrol + hide_sidebar_css
+ render_topbar (geri butonu Danışman Panosu'na).
"""

import streamlit as st
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.danisman_ortak import su_anki_danisman, render_topbar, hide_sidebar_css
from core.push_bildirim import bildirimlerimi_cek

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Bildirimlerim", ikon="🔔", geri_hedefi="pages/Danisman_Secim.py")


def _zaman_once(iso_str):
    """created_at (Supabase'den ISO 8601 timestamptz) → 'X dakika/saat/gün
    önce' gibi okunaklı bir metin. Ayrıştırma başarısız olursa (beklenmez
    ama best-effort) ham değeri olduğu gibi döner."""
    if not iso_str:
        return ""
    try:
        temiz = iso_str.replace("Z", "+00:00")
        zaman = datetime.fromisoformat(temiz)
        if zaman.tzinfo is None:
            zaman = zaman.replace(tzinfo=timezone.utc)
        fark = datetime.now(timezone.utc) - zaman
        saniye = fark.total_seconds()
        if saniye < 60:
            return "az önce"
        dakika = int(saniye // 60)
        if dakika < 60:
            return f"{dakika} dakika önce"
        saat = int(dakika // 60)
        if saat < 24:
            return f"{saat} saat önce"
        gun = int(saat // 24)
        if gun < 7:
            return f"{gun} gün önce"
        return zaman.strftime("%d.%m.%Y")
    except Exception:
        return iso_str


# DÜZELTME (01.10.2026, Meltem: "bildirimlerin üzerine tıklayınca o sf ya
# ve o günün ilanlarına gidebilmeliyiz") — kök sebep: "Görüntüle →" butonu
# st.link_button() ile TAM (dış) URL'e (https://startkey-zeta.streamlit.app/...)
# gidiyordu. Bu, zaten oturum açık olan Streamlit sekmesinde bile TAM bir
# tarayıcı sayfa yenilemesi (yeni bir HTTP isteği, baştan oturum_kontrol())
# tetikliyordu — soğuk başlangıç çerez yarışına (core/auth.py'deki aynı
# sorun) yeniden maruz kalma riski VE ?zaman=bugun sorgu parametresinin bu
# yenileme sürecinde güvenilir taşınmaması ihtimali vardı. Push bildirimleri
# (farklı origin'deki servis worker'dan açıldıkları için) bu dış-link
# yöntemine mahkum, ama BURASI zaten uygulamanın İÇİNDE — dış link yerine
# st.switch_page() ile SAYFA İÇİ geçiş yapılabilir, oturum hiç bozulmaz.
# "Bugün" filtresi de sorgu parametresi yerine DOĞRUDAN session_state'e
# yazılıyor (Danisman_FSBOIlanlari.py/Danisman_StartkeyIlanlari.py zaten
# "fsbo_zaman"/"startkey_zaman" session_state anahtarını okuyor) — push
# bildirimindeki ?zaman=bugun ile AYNI sonucu, daha güvenilir şekilde verir.
_URL_SAYFA_HARITASI = {
    "/Danisman_Talep": "pages/Danisman_Talep.py",
    "/Danisman_Portfoy": "pages/Danisman_Portfoy.py",
    "/Danisman_FSBOIlanlari": "pages/Danisman_FSBOIlanlari.py",
    "/Danisman_StartkeyIlanlari": "pages/Danisman_StartkeyIlanlari.py",
}
_URL_ZAMAN_SESSION_ANAHTARI = {
    "/Danisman_FSBOIlanlari": "fsbo_zaman",
    "/Danisman_StartkeyIlanlari": "startkey_zaman",
}


def _bildirim_url_coz(url):
    """url'i (core/bildirim_tetikleyici.py'nin ürettiği birkaç sabit
    kalıptan biri) uygulama içi bir sayfaya çözer. Eşleşme yoksa (None,
    None) döner — çağıran taraf bu durumda eski dış-link davranışına
    (st.link_button) düşer, ileride eklenecek tanınmayan bir url türü
    sessizce kırılmasın diye."""
    if not url:
        return None, None
    try:
        parcalar = urlparse(url)
    except Exception:
        return None, None
    hedef_sayfa = _URL_SAYFA_HARITASI.get(parcalar.path)
    if not hedef_sayfa:
        return None, None
    bugun_mu = parse_qs(parcalar.query).get("zaman") == ["bugun"]
    session_anahtari = _URL_ZAMAN_SESSION_ANAHTARI.get(parcalar.path) if bugun_mu else None
    return hedef_sayfa, session_anahtari


su_kullanici = su_anki_danisman()
bildirimler = bildirimlerimi_cek(su_kullanici, limit=30)

if not bildirimler:
    st.info("Henüz bir bildirimin yok — yeni bir talep/portföy paylaşıldığında ya da sana özel bir bildirim gönderildiğinde burada görünecek.")
    st.stop()

# DÜZELTME (01.10.2026, Meltem: "tüm bildirimlere basınca görüntüle
# buyonu çıkıyor mümkünse ana sf daki bildirim yazısına doğrudan
# tıklansın") — kök istek: ayrı bir "Görüntüle →" butonuna basmak yerine
# bildirimin BAŞLIĞININ KENDİSİ tıklanabilir olsun (Danışman Panosu'nun
# başka yerlerinde de kurulu desenle aynı — bkz. Danisman_Secim.py'deki
# Talep/Portföy kartları notu: "TEK kontrol, ayrı buton eklemezdim").
# st.button'ın kendi görünümünü CSS ile düz/kalın metne benzetip, hedefi
# ÇÖZÜLEBİLEN bildirimlerde başlık artık doğrudan o butonun kendisi.
# Hedefi çözülemeyen (tanınmayan) url'lerde eski "Görüntüle →" dış link
# butonu olduğu gibi korunuyor — kırılma riski yok.
st.markdown(
    """
    <style>
    div[class*="st-key-bildirim_baslik_"] button {
        all: unset;
        display: block;
        width: 100%;
        font-weight: 700;
        font-size: 1rem;
        line-height: 1.4;
        cursor: pointer;
        color: inherit;
    }
    div[class*="st-key-bildirim_baslik_"] button:hover {
        text-decoration: underline;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

for b in bildirimler:
    with st.container(border=True, key=f"bildirim_{b.get('id')}"):
        hedef_sayfa, session_anahtari = (
            _bildirim_url_coz(b["url"]) if b.get("url") else (None, None)
        )
        ust_col, zaman_col = st.columns([5, 2])
        with ust_col:
            if hedef_sayfa:
                if st.button(
                    b.get("baslik") or "",
                    key=f"bildirim_baslik_{b.get('id')}",
                ):
                    if session_anahtari:
                        st.session_state[session_anahtari] = "Bugün"
                    st.switch_page(hedef_sayfa)
            else:
                st.markdown(f"**{b.get('baslik') or ''}**")
        with zaman_col:
            st.caption(_zaman_once(b.get("created_at")))
        if b.get("govde"):
            st.write(b["govde"])
        if b.get("url") and not hedef_sayfa:
            st.link_button("Görüntüle →", b["url"], use_container_width=True)

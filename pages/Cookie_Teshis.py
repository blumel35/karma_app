import streamlit as st
from streamlit_cookies_controller import CookieController


TEST_COOKIE = "startkey_cookie_test"
TEST_VALUE = "OK_0808"


st.title("🍪 Cookie Teşhis")
st.caption(
    "Bu sayfa yalnızca tarayıcı cookie mekanizmasını test eder. "
    "Gerçek kullanıcı oturumuna veya Supabase'e dokunmaz."
)


# Auth sistemindeki controller'dan tamamen ayrı bir test instance'ı
try:
    ctrl = CookieController(key="cookie_diag_controller")
except Exception as e:
    st.error("CookieController başlatılamadı.")
    st.code(repr(e))
    st.stop()


# ---------------------------------------------------------
# İKİ FARKLI OKUMA
#
# 1) ctrl.get:
#    streamlit-cookies-controller'ın kendi gördüğü değer
#
# 2) st.context.cookies:
#    Tarayıcının yeni HTTP/WebSocket bağlantısında Streamlit'e
#    gerçekten gönderdiği cookie
#
# NOT:
# st.context.cookies sonucunu F5'TEN SONRA değerlendireceğiz.
# ---------------------------------------------------------

try:
    component_value = ctrl.get(TEST_COOKIE)
except Exception as e:
    component_value = f"HATA: {repr(e)}"

try:
    browser_value = st.context.cookies.get(TEST_COOKIE)
except Exception as e:
    browser_value = f"HATA: {repr(e)}"


st.subheader("Mevcut durum")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**CookieController görüyor:**")
    if component_value:
        st.success(str(component_value))
    else:
        st.warning("YOK")

with col2:
    st.markdown("**Streamlit tarayıcıdan aldı:**")
    if browser_value:
        st.success(str(browser_value))
    else:
        st.warning("YOK")


st.divider()


if st.button(
    "1 — Test cookie'sini yaz",
    type="primary",
    use_container_width=True,
):
    try:
        ctrl.set(
            TEST_COOKIE,
            TEST_VALUE,
            path="/",
            max_age=60 * 60,   # 1 saat
        )

        st.success(
            "Cookie yazma komutu gönderildi. "
            "Şimdi 2-3 saniye bekle ve tarayıcıda F5'e bas."
        )

        st.info(
            "F5'ten SONRA bu sayfada özellikle "
            "'Streamlit tarayıcıdan aldı' kutusuna bak."
        )

    except Exception as e:
        st.error("Cookie yazma sırasında Python/component hatası oluştu.")
        st.code(repr(e))


if st.button(
    "Test cookie'sini temizle",
    use_container_width=True,
):
    try:
        ctrl.remove(
            TEST_COOKIE,
            path="/",
        )
        st.info(
            "Silme komutu gönderildi. 2-3 saniye sonra F5'e bas."
        )
    except Exception as e:
        st.error("Cookie silinirken hata oluştu.")
        st.code(repr(e))


st.divider()

st.markdown(
    """
### Sonucu nasıl okuyacağız?

**F5'ten sonra:**

- İki kutuda da `OK_0808` → cookie sistemi canlıda çalışıyor.
- Solda `OK_0808`, sağda `YOK` → component kendi içinde yazmış gibi
  görünüyor ama tarayıcı cookie'yi Streamlit'e geri göndermiyor.
- İkisi de `YOK` → cookie yazma işlemi çalışmıyor.
- Ekranda `HATA:` çıkarsa → hata metni doğrudan teşhis için kullanılabilir.
"""
)


st.divider()
st.header("🔐 Auth Restore Teşhisi")

st.caption(
    "Bu test token değerini ekranda göstermez. "
    "Sadece oturum geri yükleme zincirinin hangi adımda durduğunu kontrol eder."
)

if st.button("2 — Auth restore zincirini test et", use_container_width=True):

    import json

    from core.auth import (
        _cookie_ctrl,
        _COOKIE_ADI,
        _get_supa,
        _profil_cek,
        _valid_actor,
    )

    # --------------------------------------------------
    # 1. COOKIE OKUNABİLİYOR MU?
    # --------------------------------------------------
    st.subheader("1. Cookie okuma")

    try:
        ctrl = _cookie_ctrl()

        if not ctrl:
            st.error("❌ CookieController oluşturulamadı.")
            st.stop()

        raw = ctrl.get(_COOKIE_ADI)

        if not raw:
            st.error("❌ startkey_session cookie'si CookieController tarafından okunamadı.")
            st.stop()

        st.success("✅ startkey_session cookie'si okundu.")

    except Exception as e:
        st.error("❌ Cookie okuma hatası")
        st.code(f"{type(e).__name__}: {e}")
        st.stop()


    # --------------------------------------------------
    # 2. COOKIE JSON OLARAK ÇÖZÜLEBİLİYOR MU?
    # --------------------------------------------------
    st.subheader("2. Cookie içeriği")

    try:
        data = json.loads(raw) if isinstance(raw, str) else raw

        if not isinstance(data, dict):
            st.error("❌ Cookie içeriği dict/JSON değil.")
            st.stop()

        refresh_token = data.get("refresh_token", "")

        if not refresh_token:
            st.error("❌ Cookie içinde refresh_token yok.")
            st.stop()

        st.success(
            f"✅ Cookie geçerli JSON. Refresh token mevcut "
            f"(uzunluk: {len(refresh_token)} karakter)."
        )

    except Exception as e:
        st.error("❌ Cookie JSON olarak çözülemedi.")
        st.code(f"{type(e).__name__}: {e}")
        st.stop()


    # --------------------------------------------------
    # 3. SUPABASE CLIENT OLUŞUYOR MU?
    # --------------------------------------------------
    st.subheader("3. Supabase bağlantısı")

    try:
        supa = _get_supa()

        if not supa:
            st.error("❌ Supabase client oluşturulamadı.")
            st.stop()

        st.success("✅ Supabase client oluşturuldu.")

    except Exception as e:
        st.error("❌ Supabase client hatası")
        st.code(f"{type(e).__name__}: {e}")
        st.stop()


    # --------------------------------------------------
    # 4. REFRESH TOKEN SUPABASE TARAFINDAN KABUL EDİLİYOR MU?
    # --------------------------------------------------
    st.subheader("4. Refresh session")

    try:
        res = supa.auth.refresh_session(refresh_token)

        st.write("User döndü:", bool(getattr(res, "user", None)))
        st.write("Session döndü:", bool(getattr(res, "session", None)))

        session = getattr(res, "session", None)

        st.write(
            "Access token döndü:",
            bool(getattr(session, "access_token", None)) if session else False
        )

        st.write(
            "Yeni refresh token döndü:",
            bool(getattr(session, "refresh_token", None)) if session else False
        )

        if not getattr(res, "user", None):
            st.error("❌ Supabase refresh çağrısı user döndürmedi.")
            st.stop()

        if not session:
            st.error("❌ Supabase refresh çağrısı session döndürmedi.")
            st.stop()

        if not getattr(session, "access_token", None):
            st.error("❌ Yeni access_token yok.")
            st.stop()

        if not getattr(session, "refresh_token", None):
            st.error("❌ Yeni refresh_token yok.")
            st.stop()

        st.success("✅ Supabase refresh token'ı kabul etti.")

    except Exception as e:
        st.error("❌ Supabase refresh_session HATA verdi.")
        st.code(f"{type(e).__name__}: {e}")
        st.stop()


    # --------------------------------------------------
    # 5. PROFİL ÇEKİLEBİLİYOR MU?
    # --------------------------------------------------
    st.subheader("5. Kullanıcı profili")

    try:
        profil = _profil_cek(supa, res.user.id)

        if profil:
            st.success("✅ kullanicilar tablosundan profil bulundu.")
        else:
            st.warning(
                "⚠️ Profil bulunamadı. Bu tek başına auth başarısızlığı "
                "olmamalı; kod fallback bilgilerle devam edebiliyor."
            )

    except Exception as e:
        st.error("❌ Profil sorgusu hata verdi.")
        st.code(f"{type(e).__name__}: {e}")
        st.stop()


    # --------------------------------------------------
    # 6. AUTH.PY'NİN OLUŞTURDUĞU KULLANICI GEÇERLİ Mİ?
    # --------------------------------------------------
    st.subheader("6. Aktör doğrulaması")

    try:
        email = res.user.email or ""

        kullanici_test = {
            "id": res.user.id,
            "email": email,
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "ad": (
                profil.get("ad", email.split("@")[0])
                if profil else email.split("@")[0]
            ),
            "rol": profil.get("rol", "danisan") if profil else "danisan",
            "ofis_id": profil.get("ofis_id", "") if profil else "",
            "ofis_adi": profil.get("ofis_adi", "") if profil else "",
        }

        if _valid_actor(kullanici_test):
            st.success("✅ Kullanıcı _valid_actor kontrolünden geçti.")
        else:
            st.error("❌ Kullanıcı _valid_actor kontrolünden GEÇEMEDİ.")
            st.stop()

    except Exception as e:
        st.error("❌ Aktör doğrulama hatası")
        st.code(f"{type(e).__name__}: {e}")
        st.stop()


    st.success(
        "🎯 RESTORE ZİNCİRİNİN TÜM TEMEL ADIMLARI BAŞARILI."
    )
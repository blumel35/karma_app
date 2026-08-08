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
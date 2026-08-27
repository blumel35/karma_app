# pages/Hesap_Aktivasyon.py
# Startkey Zeta — yalnızca davet edilen kullanıcının ilk şifresini belirlemesi için.
# Karma App'e veya Danışman Panosu'na giriş/yönlendirme yapmaz.

import streamlit as st

from core.auth import davet_sifresi_guncelle, davet_token_dogrula


# ─────────────────────────────────────────────────────
# SADE, BAĞIMSIZ GÖRÜNÜM
# ─────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    [data-testid="stHeader"] { display: none !important; }
    [data-testid="stAppViewContainer"] > .main > .block-container {
        padding-top: 0 !important;
        max-width: 100% !important;
    }
    .stApp { background: #FBF7F0; }
    </style>
    """,
    unsafe_allow_html=True,
)


_INVITE_KEYS = (
    "_invite_flow_active",
    "_invite_access_token",
    "_invite_refresh_token",
    "_invite_email",
)


def _invite_state_temizle() -> None:
    for key in _INVITE_KEYS:
        st.session_state.pop(key, None)


def _param(name: str) -> str:
    value = st.query_params.get(name, "")
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value or "").strip()


# Başarı ekranı aynı tarayıcı oturumunda yenilense bile giriş linki göstermez.
if st.session_state.get("_invite_password_done"):
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.markdown("<div style='height:14vh'></div>", unsafe_allow_html=True)
        st.success("Hesabınız hazır")
        st.markdown(
            """
            **Şifreniz başarıyla oluşturuldu.**

            Uygulama giriş bağlantısı yöneticiniz tarafından ayrıca paylaşılacaktır.  
            Bu sayfayı kapatabilirsiniz.
            """
        )
    st.stop()


# ─────────────────────────────────────────────────────
# DAVET BAĞLANTISI KONTROLÜ
# ─────────────────────────────────────────────────────
# Token link açılır açılmaz tüketilmez. Kullanıcı önce şifresini yazar;
# token yalnız "Şifremi Oluştur" tıklandığında doğrulanır. Böylece kişi
# sayfayı yanlışlıkla açıp kapatırsa davetini boşa harcamaz.
auth_action = _param("auth_action")
token_hash = _param("token_hash")
auth_type = _param("type")

# DÜZELTME: app.py kök URL'deki davet parametrelerini görünce buraya
# st.switch_page() ile yönlendiriyor — ancak query parametreleri hedef
# sayfanın ilk render'ında burada boş gelebiliyor (Streamlit switch_page
# kısıtı, gerçek ortamda doğrulandı). app.py bu ihtimale karşı token_hash'i
# ayrıca session_state'e de yazıyor; query param boşsa oradan geri düşülür.
if not token_hash:
    _redirect_token = str(st.session_state.pop("_invite_redirect_token_hash", "") or "").strip()
    if _redirect_token:
        token_hash = _redirect_token
        auth_action = "invite"
        auth_type = "invite"

# Daha önce bu sayfa oturumunda token doğrulanmışsa URL temizlenmiş olabilir;
# geçici doğrulanmış davet oturumuyla form çalışmaya devam eder.
invite_verified = bool(st.session_state.get("_invite_flow_active"))

if not invite_verified:
    if not token_hash or auth_action != "invite" or auth_type != "invite":
        st.error("Bu sayfa yalnızca geçerli bir kullanıcı davet bağlantısıyla açılabilir.")
        st.stop()


# ─────────────────────────────────────────────────────
# İLK ŞİFRE FORMU
# ─────────────────────────────────────────────────────
_, center, _ = st.columns([1, 1.2, 1])

with center:
    st.markdown("<div style='height:10vh'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="text-align:center;margin-bottom:28px;">
          <div style="display:inline-flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;background:#1C2B47;border-radius:10px;
                        display:flex;align-items:center;justify-content:center;
                        font-size:18px;font-weight:800;color:#fff;">Z</div>
            <div style="text-align:left;">
              <div style="font-size:11px;color:#8A8271;letter-spacing:.12em;
                          text-transform:uppercase;">Startkey Zeta</div>
              <div style="font-size:20px;font-weight:700;color:#1C2B47;letter-spacing:-.03em;">
                          Hesabınızı Oluşturun</div>
            </div>
          </div>
          <div style="font-size:14px;color:#8A8271;margin-top:12px;">
            İlk kullanım için kendi şifrenizi belirleyin.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        email = st.session_state.get("_invite_email", "")
        if email:
            st.caption(f"Hesap: {email}")

        sifre1 = st.text_input(
            "Yeni şifre",
            type="password",
            placeholder="En az 8 karakter",
            key="invite_password_1",
        )
        sifre2 = st.text_input(
            "Yeni şifre tekrar",
            type="password",
            placeholder="Şifrenizi tekrar yazın",
            key="invite_password_2",
        )

        st.caption(
            "En az 8 karakter kullanın. Daha güçlü bir şifre için harf, "
            "rakam ve özel karakterleri birlikte tercih edin."
        )

        if st.button(
            "Şifremi Oluştur",
            type="primary",
            use_container_width=True,
            key="invite_password_save",
        ):
            if not sifre1 or not sifre2:
                st.error("İki şifre alanını da doldurun.")
            elif sifre1 != sifre2:
                st.error("Yazdığınız şifreler birbiriyle eşleşmiyor.")
            elif len(sifre1) < 8:
                st.error("Şifreniz en az 8 karakter olmalı.")
            else:
                # İlk tıklamada davet tokenını doğrula. Başarılı olursa URL'den
                # hemen temizle ve yalnız bu Streamlit session'ında geçici token
                # çiftini tut. Normal Karma App oturumu/cookie'si OLUŞTURULMAZ.
                if not st.session_state.get("_invite_flow_active"):
                    with st.spinner("Davetiniz doğrulanıyor..."):
                        dogrulama = davet_token_dogrula(token_hash)

                    if not dogrulama:
                        st.query_params.clear()
                        _invite_state_temizle()
                        st.error(
                            "Bu davet bağlantısı geçersiz veya süresi dolmuş. "
                            "Yeni bir davet bağlantısı isteyin."
                        )
                        st.stop()

                    st.session_state["_invite_flow_active"] = True
                    st.session_state["_invite_access_token"] = dogrulama["access_token"]
                    st.session_state["_invite_refresh_token"] = dogrulama["refresh_token"]
                    st.session_state["_invite_email"] = dogrulama.get("email", "")
                    # Tek kullanımlık token doğrulandı; artık browser URL'sinde kalmasın.
                    st.query_params.clear()

                with st.spinner("Şifreniz oluşturuluyor..."):
                    ok = davet_sifresi_guncelle(
                        st.session_state.get("_invite_access_token", ""),
                        st.session_state.get("_invite_refresh_token", ""),
                        sifre1,
                    )

                if ok:
                    _invite_state_temizle()
                    st.session_state.pop("invite_password_1", None)
                    st.session_state.pop("invite_password_2", None)
                    st.session_state["_invite_password_done"] = True
                    st.rerun()
                else:
                    # Token doğrulandıktan sonra şifre politikası nedeniyle update
                    # reddedilirse geçici davet session'ı korunur; kullanıcı sayfayı
                    # kapatmadan daha güçlü bir şifreyle tekrar deneyebilir.
                    st.error(
                        "Şifre kaydedilemedi. Daha güçlü bir şifre deneyin. "
                        "Sorun devam ederse yöneticinizden destek isteyin."
                    )

    st.markdown(
        """
        <div style="text-align:center;margin-top:20px;font-size:11px;color:rgba(28,43,71,0.3);">
          Startkey Zeta · Hesap Aktivasyonu
        </div>
        """,
        unsafe_allow_html=True,
    )

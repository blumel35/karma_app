# pages/giris.py
# Giriş ekranı — Supabase Auth + local session persistence

import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import giris_yap, sifremi_sifirla, set_session_fields
from core.personel_manager import save_login_session, load_login_session, enrich_session_from_personel

st.markdown("""
<style>
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stHeader"] { display: none !important; }
[data-testid="stAppViewContainer"] > .main > .block-container {
    padding-top: 0 !important;
    max-width: 100% !important;
}
.stApp { background: #0F172A; }
</style>
""", unsafe_allow_html=True)

# ── AÇIK OTURUM KONTROLÜ ──────────────────────────────────────────────────────
# st.session_state'de zaten kullanıcı varsa (app.py'de local session yüklendi)
# otomatik yönlendirme YAPMA — kullanıcıya bilgi ver ve buton sun.
if st.session_state.get("kullanici"):
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.markdown("<div style='height:8vh'></div>", unsafe_allow_html=True)
        kullanici = st.session_state["kullanici"]
        ad = kullanici.get("ad_soyad") or kullanici.get("ad") or kullanici.get("email", "").split("@")[0]
        st.markdown(f"""
        <div style="text-align:center;margin-bottom:24px;">
          <div style="font-size:20px;font-weight:700;color:#fff;">👋 Hoş geldiniz, {ad}!</div>
          <div style="font-size:14px;color:rgba(255,255,255,0.5);margin-top:8px;">
            Oturumunuz açık.
          </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("→ Ana Sayfaya Git", type="primary", use_container_width=True):
            st.switch_page("pages/ana_sayfa.py")
    st.stop()

# ── LAYOUT ────────────────────────────────────────────────────────────────────
_, center, _ = st.columns([1, 1.2, 1])

with center:
    st.markdown("<div style='height:8vh'></div>", unsafe_allow_html=True)

    # Logo / Marka
    st.markdown("""
    <div style="text-align:center;margin-bottom:32px;">
      <div style="display:inline-flex;align-items:center;gap:10px;">
        <div style="width:40px;height:40px;background:#1E3A5F;border-radius:10px;
                    display:flex;align-items:center;justify-content:center;
                    font-size:18px;font-weight:800;color:#fff;">Z</div>
        <div style="text-align:left;">
          <div style="font-size:11px;color:rgba(255,255,255,0.4);letter-spacing:.12em;
                      text-transform:uppercase;">Startkey</div>
          <div style="font-size:20px;font-weight:700;color:#fff;letter-spacing:-.03em;">
                      Zeta Panel</div>
        </div>
      </div>
      <div style="font-size:14px;color:rgba(255,255,255,0.45);margin-top:12px;">
        Hesabınıza giriş yapın
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Form kapsayıcı
    with st.container(border=True):
        mod = st.radio("", ["Giriş Yap", "Şifremi Unuttum"],
                       horizontal=True, label_visibility="collapsed",
                       key="giris_mod")

        if mod == "Giriş Yap":
            email = st.text_input("E-posta", placeholder="ornek@startkey.com",
                                  key="giris_email")
            sifre = st.text_input("Şifre", type="password",
                                  placeholder="••••••••", key="giris_sifre")

            if st.button("Giriş Yap →", type="primary",
                         use_container_width=True, key="btn_giris"):
                if not email or not sifre:
                    st.error("E-posta ve şifre zorunludur.")
                else:
                    with st.spinner("Giriş yapılıyor..."):
                        kullanici = giris_yap(email.strip(), sifre)
                    if kullanici:
                        # Excel personel kaydıyla zenginleştir (rol, foto_path, ofis vb.)
                        kullanici = enrich_session_from_personel(kullanici)

                        # ── Standart session_state alanları — merkezi fonksiyon ──
                        set_session_fields(kullanici)
                        ad = st.session_state["user_name"]
                        rol = st.session_state["user_role"]

                        # ── Local geliştirme: login session'ı kaydet ────────
                        # (Cloud'da load_login_session() kendini otomatik
                        #  devre dışı bırakıyor, bu yüzden burada güvenli.)
                        try:
                            save_login_session({
                                "id":        kullanici.get("id", ""),
                                "email":     kullanici.get("email", ""),
                                "ad":        kullanici.get("ad", ""),
                                "ad_soyad":  ad,
                                "rol":       rol,
                                "ofis_id":   kullanici.get("ofis_id", ""),
                                "ofis_adi":  kullanici.get("ofis_adi", ""),
                                "foto_url":  kullanici.get("foto_url", ""),
                                "logo_url":  kullanici.get("logo_url", ""),
                                "user_key":  kullanici.get("user_key", ""),
                            })
                        except Exception:
                            pass

                        st.success(f"Hoş geldiniz, {ad}!")
                        st.switch_page("pages/ana_sayfa.py")
                    else:
                        st.error("E-posta veya şifre hatalı.")

        else:  # Şifremi unuttum
            email_r = st.text_input("E-posta adresiniz", key="reset_email")
            if st.button("Sıfırlama Linki Gönder", use_container_width=True,
                         key="btn_reset"):
                if email_r:
                    ok = sifremi_sifirla(email_r.strip())
                    if ok:
                        st.success("Şifre sıfırlama linki e-postanıza gönderildi.")
                    else:
                        st.error("Gönderilemedi. Supabase bağlantısını kontrol edin.")
                else:
                    st.error("E-posta adresi girin.")

    st.markdown("""
    <div style="text-align:center;margin-top:20px;font-size:11px;
                color:rgba(255,255,255,0.2);">
      Startkey Zeta Panel · 2026
    </div>
    """, unsafe_allow_html=True)

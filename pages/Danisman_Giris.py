# pages/Danisman_Giris.py
# Danışman Panosu için BAĞIMSIZ, sade giriş ekranı.
#
# Karma App'in ana giriş ekranından (pages/giris.py) FARKI: başarılı
# giriş sonrası ana_sayfa.py'ye (Karma App'in tam menüsü) değil,
# Danisman_Pano.py'ye (sade, tek amaçlı arayüz) yönlendiriyor.
#
# Kimlik doğrulama AYNI Supabase hesaplarını kullanıyor (core.auth) —
# danışman zaten Karma App'e girdiği e-posta/şifre ile buraya da girer.
# Bu link, Karma App'in geri kalanından bağımsız paylaşılabilir; giriş
# yapmadan hiçbir Karma App menüsü/navbar'ı görünmez.

import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import giris_yap, set_session_fields, oturum_kontrol
from core.personel_manager import enrich_session_from_personel

st.markdown("""
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
""", unsafe_allow_html=True)

# Session'da VEYA tarayıcı cookie'sinde geçerli oturum varsa kullanıcıdan
# yeniden şifre isteme. DÜZELTME (08.08.2026): eskiden burada sadece
# `st.session_state.get("kullanici")` kontrol ediliyordu — bu, cookie
# restore'unu hiç çağırmıyordu (session_state her sayfa yenilemesinde
# sıfırlandığı için orada hiçbir zaman "kullanici" bulunamıyordu, cookie
# var olsa bile). oturum_kontrol() ise session boşsa startkey_session
# cookie'sini okuyup Supabase üzerinden geri yüklemeyi zaten deniyor
# (core/auth.py) — bu çağrıyı burada da kullanmak, mevcut restore
# mekanizmasını devreye sokuyor.
if oturum_kontrol():
    st.switch_page("pages/Danisman_Secim.py")
    st.stop()

_, center, _ = st.columns([1, 1.2, 1])

with center:
    st.markdown("<div style='height:10vh'></div>", unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center;margin-bottom:32px;">
      <div style="display:inline-flex;align-items:center;gap:10px;">
        <div style="width:40px;height:40px;background:#1C2B47;border-radius:10px;
                    display:flex;align-items:center;justify-content:center;
                    font-size:18px;font-weight:800;color:#fff;">Z</div>
        <div style="text-align:left;">
          <div style="font-size:11px;color:#8A8271;letter-spacing:.12em;
                      text-transform:uppercase;">Startkey Zeta</div>
          <div style="font-size:20px;font-weight:700;color:#1C2B47;letter-spacing:-.03em;">
                      Danışman Panosu</div>
        </div>
      </div>
      <div style="font-size:14px;color:#8A8271;margin-top:12px;">
        Talep ve portföyleri takip edin, hızlıca yenilerini ekleyin.
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        email = st.text_input("E-posta", placeholder="ornek@startkey.com", key="dg_email")
        sifre = st.text_input("Şifre", type="password", placeholder="••••••••", key="dg_sifre")

        if st.button("Giriş Yap →", type="primary", use_container_width=True, key="dg_btn"):
            if not email or not sifre:
                st.error("E-posta ve şifre zorunludur.")
            else:
                with st.spinner("Giriş yapılıyor..."):
                    kullanici = giris_yap(email.strip(), sifre)
                if kullanici:
                    kullanici = enrich_session_from_personel(kullanici)
                    set_session_fields(kullanici)
                    # NOT (08.08.2026): save_login_session() buradan
                    # kaldırıldı — dosya tabanlı eski LOCAL_SESSION_RESTORE
                    # mekanizmasının parçasıydı, Streamlit Cloud'da zaten
                    # bilerek kapalı (sunucu-paylaşımlı dosya riski, bkz.
                    # core/auth.py). Kalıcılık artık tamamen tarayıcı
                    # cookie'siyle sağlanıyor (_tarayici_oturumu_kaydet),
                    # bu çağrı cloud'da işlevsizdi, gereksiz kod olarak
                    # temizlendi.
                    # Cookie yazma + auth restore zinciri artık doğrulandı
                    # (08.08.2026, Auth Restore Teşhisi ile). Normal akış:
                    # doğrudan seçim ekranına geç.
                    st.switch_page("pages/Danisman_Secim.py")
                else:
                    st.error("E-posta veya şifre hatalı.")

    st.markdown("""
    <div style="text-align:center;margin-top:20px;font-size:11px;color:rgba(28,43,71,0.3);">
      Startkey Zeta · Danışman Panosu
    </div>
    """, unsafe_allow_html=True)

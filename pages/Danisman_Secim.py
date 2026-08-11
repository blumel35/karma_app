"""
pages/Danisman_Secim.py

Danışman Panosu'nun giriş sonrası ANA ekranı (2026-08 revizyonu).

Önceki mimaride (Danisman_Pano.py) tek sayfada form + kayıtlarım +
filtreler + 3 sekme birlikteydi — bu sayfa onun yerine, kullanıcının
ilk gördüğü şeyin sade bir "nereye gitmek istiyorum" seçimi olmasını
sağlıyor:

- İki büyük kart: Talep Panosu / Portföy Panosu (ana sayı + tıklanabilir
  "+N yeni" rozeti — rozete tıklayınca ilgili panoya SADECE SON 7
  GÜNDEKİ kayıtlar filtrelenmiş halde açılır).
- Favori Listem butonu.
- "+ Ekle" butonu — ortak dialog (core.danisman_ortak.ekle_dialog),
  Talep Panosu / Portföy Panosu ekranlarının hiçbirinde ayrıca YOK.
- "Son 24 saat" aktivite özeti (kim ne ekledi, kısa liste + tüm
  paylaşımlar linki).
- Sağ üstte hamburger menü: Kendi Kayıtlarım, Zeta Paylaşımları, Çıkış Yap.
"""

import streamlit as st

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.danisman_ortak import (
    talepleri_cek, portfoyleri_cek, son_N_gun_filtrele,
    ekle_dialog, render_activity_bar, render_topbar, hide_sidebar_css,
)

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()

st.markdown("""
<style>
div[class*="st-key-dp_talep_git"] button,
div[class*="st-key-dp_portfoy_git"] button {
    background-color: #1b2540 !important;
    border-color: #1b2540 !important;
    color: #ffffff !important;
}
div[class*="st-key-dp_talep_git"] button:hover,
div[class*="st-key-dp_portfoy_git"] button:hover {
    background-color: #28345a !important;
    border-color: #28345a !important;
    color: #ffffff !important;
}
/* DÜZELTME (10.08.2026): "+ Yeni Talep/Portföy Ekle" navy dolgudan
   gri/soft zemine geçti — mockup karşılaştırmasında karar verildi.
   Sık kullanılan ama "ağır" hissettirmemesi istenen bir eylem için
   nötr gri daha uygun bulundu; "Talep/Portföy Panosuna Git" gibi asıl
   birincil (navy) eylemlerden bilinçli olarak ayrıştırıldı. */
div[class*="st-key-dp_ekle_btn"] button {
    background-color: #eef0f3 !important;
    border-color: #dde1e6 !important;
    color: #3d4457 !important;
}
div[class*="st-key-dp_ekle_btn"] button:hover {
    background-color: #e2e5ea !important;
    border-color: #ccd1d8 !important;
    color: #3d4457 !important;
}
}
.dp-icon-box {
    width: 38px; height: 38px; border-radius: 9px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; margin-bottom: 8px;
}
.dp-icon-box.talep { background: rgba(27,37,64,.08); color: #1b2540; }
.dp-icon-box.portfoy { background: rgba(184,137,47,.12); color: #b8892f; }
.dp-stat-row {
    display: flex; align-items: baseline; justify-content: flex-start;
    gap: 8px; padding-top: 10px; margin-top: 8px;
    border-top: 1px solid #ecebe5;
}
.dp-stat-num { font-size: 22px; font-weight: 800; color: #1b2540; }
.dp-stat-num.portfoy { color: #b8892f; }

/* DÜZELTME (09.08.2026 — mobil kart sıkılaştırma): Talep/Portföy
   kartları mobilde gereğinden fazla dikey yer kaplıyordu. Kartlar
   TEK SÜTUNDA KALIYOR (bu daha önce onaylanmış bir karardı, geri
   alınmadı) — sadece her kartın iç boşlukları ve eleman boyutları
   küçültülüp "kare" değil "kısa dikdörtgen" hissi versin diye
   sıkılaştırıldı. */
@media (max-width: 480px) {
    div[class*="st-key-dp_kart_talep"] div[data-testid="stVerticalBlockBorderWrapper"],
    div[class*="st-key-dp_kart_portfoy"] div[data-testid="stVerticalBlockBorderWrapper"] {
        padding: 12px 14px !important;
    }
    .dp-icon-box {
        width: 28px !important;
        height: 28px !important;
        border-radius: 7px !important;
        font-size: 15px !important;
        margin-bottom: 4px !important;
    }
    .dp-icon-box svg {
        width: 15px !important;
        height: 15px !important;
    }
    .dp-stat-row {
        padding-top: 6px !important;
        margin-top: 4px !important;
    }
    .dp-stat-num {
        font-size: 18px !important;
    }
    div[class*="st-key-dp_talep_git"] button,
    div[class*="st-key-dp_portfoy_git"] button {
        padding: 8px 12px !important;
        font-size: 13px !important;
    }
    div[class*="st-key-dp_talep_yeni_rozet"] button,
    div[class*="st-key-dp_portfoy_yeni_rozet"] button {
        padding: 4px 10px !important;
        font-size: 11.5px !important;
    }
    /* Kartların içindeki st.write("") boşluk verici satırlar — masaüstünde
       gerekli dikey nefes payı için vardı, mobilde sıkılaştırma hedefiyle
       çelişiyor. Bu boş paragrafları mobilde tamamen görünmez yapıyoruz. */
    div[class*="st-key-dp_kart_talep"] [data-testid="stElementContainer"]:has(p:empty),
    div[class*="st-key-dp_kart_portfoy"] [data-testid="stElementContainer"]:has(p:empty) {
        display: none !important;
    }
}

/* Stat satırındaki boş kutu — Streamlit'in kendi sütun grubu
   (stHorizontalBlock) ve tekil sütun (stColumn) elemanlarının bir
   yerden miras aldığı border/background'ı sıfırlıyoruz. Header'daki
   aynı türden kutu sorununu çözen desenle birebir aynı yaklaşım.
   DÜZELTME (09.08.2026 — mobil regresyon): Bu kural masaüstünde
   çalışıyordu ama mobilde (dar ekranda stColumn'lar dikey yığılınca)
   "255 aktif talep" üstünde boş, kenarlıklı bir kutu kalıyordu — reset
   yalnızca stHorizontalBlock/stColumn'u kapsıyordu, altlarındaki
   stVerticalBlock/stElementContainer sarmalayıcılarını KAPSAMIYORDU.
   Seçici bu iki katmanı da içerecek şekilde genişletildi; ayrıca olası
   bir kalıntı min-height/padding ihtimaline karşı bunlar da sıfırlandı.
   Canlıda hâlâ görünürse: DevTools → Inspect ile gerçek elemanı bulup
   buraya class'ını ekle (bu geniş kural zarar vermez, sadece garanti
   payı). */
div[class*="st-key-dp_kart_talep"] [data-testid="stHorizontalBlock"],
div[class*="st-key-dp_kart_portfoy"] [data-testid="stHorizontalBlock"],
div[class*="st-key-dp_kart_talep"] [data-testid="stColumn"],
div[class*="st-key-dp_kart_portfoy"] [data-testid="stColumn"],
div[class*="st-key-dp_kart_talep"] [data-testid="stVerticalBlock"],
div[class*="st-key-dp_kart_portfoy"] [data-testid="stVerticalBlock"],
div[class*="st-key-dp_kart_talep"] [data-testid="stElementContainer"],
div[class*="st-key-dp_kart_portfoy"] [data-testid="stElementContainer"] {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    min-height: 0 !important;
}

/* "+N yeni" rozetleri — mockup'taki .new-badge ile aynı mantık: saf/
   doygun renk değil, marka renginin %8-12 opaklığı (pastel görünüm
   böyle elde ediliyor, farklı bir palet eklemekle değil). Pill şekli
   (border-radius 999px), border yok, kompakt padding. */
div[class*="st-key-dp_talep_yeni_rozet"] button {
    background-color: rgba(27,37,64,.08) !important;
    color: #1b2540 !important;
    border: none !important;
    border-radius: 999px !important;
    font-weight: 700 !important;
    white-space: nowrap !important;
    width: auto !important;
    display: inline-flex !important;
    padding: 6px 14px !important;
}
div[class*="st-key-dp_talep_yeni_rozet"] button:hover {
    background-color: rgba(27,37,64,.14) !important;
}
div[class*="st-key-dp_portfoy_yeni_rozet"] button {
    background-color: rgba(184,137,47,.12) !important;
    color: #b8892f !important;
    border: none !important;
    border-radius: 999px !important;
    font-weight: 700 !important;
    white-space: nowrap !important;
    width: auto !important;
    display: inline-flex !important;
    padding: 6px 14px !important;
}
div[class*="st-key-dp_portfoy_yeni_rozet"] button:hover {
    background-color: rgba(184,137,47,.20) !important;
}

/* "Favori Listem" / "Uzmanlık Bölgelerim" / "+ Yeni Talep/Portföy Ekle" —
   üçü de kompakt pill boyutunda (içeriğe göre genişlik, ince kenarlık
   yerine dolgu rengi ekle'de), "Talep/Portföy Panosuna Git" gibi tam
   genişlik/ağır butonlarla karışmasınlar diye bilinçli olarak küçük
   tutuldu. DÜZELTME (09.08.2026): "+ Ekle" artık navy dolgu (yukarıdaki
   dp_talep_git/dp_portfoy_git kuralı) — bu yüzden arka plan/yazı rengi
   kuralları buradan dp_ekle_btn için AYRILDI, sadece boyut/pill şekli
   üçü için ortak kaldı; renk kuralı favori/uzmanlık için ayrı, ekle
   için yukarıdaki navy kuralda tanımlı (çakışmasın diye).*/
div[class*="st-key-dp_favori_btn"] button,
div[class*="st-key-dp_uzmanlik_btn"] button,
div[class*="st-key-dp_ekle_btn"] button {
    width: auto !important;
    display: inline-flex !important;
    padding: 8px 16px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
}
div[class*="st-key-dp_favori_btn"] button,
div[class*="st-key-dp_uzmanlik_btn"] button {
    border-color: #e3e1da !important;
    background: #ffffff !important;
    color: #5b6478 !important;
}
/* DÜZELTME (10.08.2026): "Uzmanlık Bölgelerim" artık Favori Listem ile
   AYNI nötr beyaz stili paylaşmıyor — sık kullanılacak bir ekran olduğu
   için kendine has bir vurgu istendi. Palette'te lacivert (Talep) ve
   gold (Portföy) zaten dolu olduğundan, gri (Ekle ile karışmasın) yerine
   ayrı bir slate/teal tonu seçildi — mockup karşılaştırmasında karar
   verildi. Bu kural yukarıdaki paylaşılan (beyaz) kuraldan SONRA geldiği
   için CSS cascade'de öncelikli, override ediyor. */
div[class*="st-key-dp_uzmanlik_btn"] button {
    border-color: #cfe0e0 !important;
    background: #eaf1f1 !important;
    color: #2f5858 !important;
}
div[class*="st-key-dp_uzmanlik_btn"] button:hover {
    border-color: #b9d4d4 !important;
    background: #ddeaea !important;
    color: #2f5858 !important;
}
/* Yıldız — ::first-letter denemesi güvenilir çalışmadı (Streamlit'in
   buton metnini sardığı iç eleman yapısı net değil, kısmi metin
   renklendirmesi tutarsız). Bunun yerine yıldızı buton METNİNDEN
   TAMAMEN ÇIKARDIK, CSS ::before ile bağımsız bir eleman olarak
   ekliyoruz — bu, herhangi bir iç metin yapısına bağımlı değil,
   kendi rengini garantili taşır. */
div[class*="st-key-dp_favori_btn"] button::before {
    content: "★";
    color: #b8892f !important;
    margin-right: 6px;
    font-size: 14px;
}
/* DÜZELTME (09.08.2026): 📍 pin emojisi kaldırıldı — ekran görüntülerinde
   hâlâ göründüğü belirtildi. Karar: "Uzmanlık Bölgelerim" sade metin
   olarak kalsın (⭐ Favori Listem'in aksine, pin uygulamanın başka hiçbir
   yerinde tekrarlanmıyordu, bu yüzden kaldırılması tercih edildi). */

/* NOT (2. tur — geri alındı): Daha önce burada mobilde kartları zorla
   yan yana (50%/50%) tutan bir medya sorgusu vardı. Gerçek testte
   içeriğin (sayı, rozet, buton) dar sütunda taştığı görüldü — amatör
   bir görünüme sebep oluyordu. Streamlit'in DOĞAL davranışına
   (mobilde sütunları alt alta, tam genişlikte dizmek) geri dönüldü —
   daha güvenli, taşma riski yok. */
</style>
""", unsafe_allow_html=True)

with st.container(border=True, key="dp_page_frame"):
    render_topbar("Startkey Zeta Danışman Panosu", ikon="")

    # DÜZELTME (2. tur): "+ Ekle" butonu artık alttaki chip satırında
    # değil, açıklama cümlesiyle AYNI satırda, sağda — sık kullanılan bir
    # eylem olduğu için daha görünür/erişilebilir bir konuma taşındı.
    # DÜZELTME (09.08.2026): Buton metni "+ Ekle" yerine "+ Yeni Talep/
    # Portföy Ekle" oldu — ne ekleneceği tek bakışta net olsun diye.
    # Sütun oranı da [5,1]'den [3,2]'ye genişletildi; buton kendi
    # içeriğine göre otomatik genişlikte (width:auto, aşağıdaki CSS'te)
    # ama daha uzun metnin dar bir sütuna sıkışıp taşmaması için ekle_col
    # daha fazla yer alıyor.
    cap_col, ekle_col = st.columns([3, 2])
    with cap_col:
        st.caption("Talep ve portföyleri canlı takip edin, hızlıca yeni kayıt ekleyin.")
    with ekle_col:
        if st.button("+ Yeni Talep/Portföy Ekle", key="dp_ekle_btn", use_container_width=True):
            ekle_dialog()
    st.write("")

    talepler = talepleri_cek()
    portfoyler = portfoyleri_cek()
    # "+N yeni" rozeti ve sayaçlar TÜM KAYNAKLARI kapsar (Zeta + Startkey/mail
    # birlikte) — Talep/Portföy Panosu zaten her zaman tüm havuzu gösteriyor,
    # bu yüzden rozet de aynı kapsamda tutarlı olmalı. Yalnızca Zeta'ya özel
    # görünüm için: hamburger menü → Zeta Paylaşımları.
    talep_yeni = son_N_gun_filtrele(talepler, 7)
    portfoy_yeni = son_N_gun_filtrele(portfoyler, 7)

    # DÜZELTME (2. tur): Talep/Portföy kartlarını kendi key'li konteynerine
    # alıyoruz — mobilde bu SATIRA ÖZEL bir CSS kuralı uygulayabilmek için
    # (Streamlit'in varsayılan davranışı dar ekranda sütunları alt alta
    # dizmek; burada bilinçli olarak bunu geçersiz kılıp yan yana, dar iki
    # dikdörtgen halinde tutuyoruz — "1 kutuluk yer" talebi).
    with st.container(key="dp_kartlar_row"):
        col_talep, col_portfoy = st.columns(2, gap="small")

    with col_talep:
        with st.container(border=True, key="dp_kart_talep"):
            st.markdown(
                "<div style='height:4px;background:#1b2540;border-radius:3px;margin:-1px 0 12px 0;'></div>"
                "<div class='dp-icon-box talep'>"
                "<svg width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
                "<path d='M12 3v13m0 0-4-4m4 4 4-4'/><path d='M4 19h16'/>"
                "</svg></div>",
                unsafe_allow_html=True,
            )
            st.markdown("**Talep Panosu**")
            st.caption("Alıcı taleplerini görüntüle ve yönet")

            stat_col, badge_col = st.columns([2, 1])
            with stat_col:
                st.markdown(f"<div class='dp-stat-row'><span class='dp-stat-num'>{len(talepler)}</span>"
                            f"<span style='color:#5b6478;font-size:13px;'>aktif talep</span></div>",
                            unsafe_allow_html=True)
            with badge_col:
                if talep_yeni:
                    st.write("")
                    if st.button(f"● +{len(talep_yeni)} yeni", key="dp_talep_yeni_rozet"):
                        st.session_state["dp_sadece_yeni"] = True
                        st.switch_page("pages/Danisman_Talep.py")

            st.write("")
            if st.button("Talep Panosuna Git →", key="dp_talep_git", type="primary", use_container_width=True):
                st.session_state["dp_sadece_yeni"] = False
                st.switch_page("pages/Danisman_Talep.py")

    with col_portfoy:
        with st.container(border=True, key="dp_kart_portfoy"):
            st.markdown(
                "<div style='height:4px;background:#b8892f;border-radius:3px;margin:-1px 0 12px 0;'></div>"
                "<div class='dp-icon-box portfoy'>"
                "<svg width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
                "<path d='M3 11.5 12 4l9 7.5'/><path d='M5 10v9h14v-9'/>"
                "</svg></div>",
                unsafe_allow_html=True,
            )
            st.markdown("**Portföy Panosu**")
            st.caption("Portföyleri görüntüle ve yönet")

            stat_col, badge_col = st.columns([2, 1])
            with stat_col:
                st.markdown(f"<div class='dp-stat-row'><span class='dp-stat-num portfoy'>{len(portfoyler)}</span>"
                            f"<span style='color:#5b6478;font-size:13px;'>aktif portföy</span></div>",
                            unsafe_allow_html=True)
            with badge_col:
                if portfoy_yeni:
                    st.write("")
                    if st.button(f"● +{len(portfoy_yeni)} yeni", key="dp_portfoy_yeni_rozet"):
                        st.session_state["dp_sadece_yeni"] = True
                        st.switch_page("pages/Danisman_Portfoy.py")

            st.write("")
            if st.button("Portföy Panosuna Git →", key="dp_portfoy_git", type="primary", use_container_width=True):
                st.session_state["dp_sadece_yeni"] = False
                st.switch_page("pages/Danisman_Portfoy.py")

    st.write("")

    col_uzmanlik, col_favori = st.columns([1, 1])
    with col_uzmanlik:
        if st.button("Uzmanlık Bölgelerim", key="dp_uzmanlik_btn"):
            st.switch_page("pages/Danisman_UzmanlikBolgeleri.py")
    with col_favori:
        if st.button("Favori Listem", key="dp_favori_btn"):
            st.switch_page("pages/Danisman_Favoriler.py")

    st.write("")
    render_activity_bar()

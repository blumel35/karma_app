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
    uzmanlik_bolgelerini_cek, su_anki_danisman, ILAN_PORTAL_DEGERLERI,
)
from core.bolge_secici import bolgelerini_cek
from core.push_bildirim import render_bildirim_izni_butonu, bildirim_gonder

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
/* NOT (11.08.2026 — ikinci deneme): İlk düzeltme (inline-flex + width
   !important doğrudan .dp-icon-box üzerinde) canlıda çözmedi — demek ki
   sorun kutunun KENDİ genişliğinde değil, onu SARAN Streamlit elemanının
   (muhtemelen bir platform güncellemesiyle gelen yeni varsayılan arka
   plan/genişlik davranışı) üzerinde. Bu kural, ikon kutusunu içeren
   markdown sarmalayıcısını doğrudan hedefleyip olası arka planı/
   genişliğini sıfırlıyor — .dp-icon-box'ın KENDİ rengine dokunmadan. */
div[class*="st-key-dp_kart_talep"] [data-testid="stMarkdownContainer"]:has(.dp-icon-box),
div[class*="st-key-dp_kart_portfoy"] [data-testid="stMarkdownContainer"]:has(.dp-icon-box),
div[class*="st-key-dp_kart_talep"] [data-testid="stElementContainer"]:has(.dp-icon-box),
div[class*="st-key-dp_kart_portfoy"] [data-testid="stElementContainer"]:has(.dp-icon-box) {
    background: transparent !important;
    width: fit-content !important;
}
.dp-icon-box {
    width: 38px !important;
    max-width: 38px !important;
    height: 38px; border-radius: 9px;
    display: inline-flex !important; flex: 0 0 auto !important;
    align-items: center; justify-content: center;
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

/* DÜZELTME (09.08.2026 — mobil kart sıkılaştırma, GÜNCELLEME 11.08.2026
   — 2. tur, daha da sıkılaştırıldı): Talep/Portföy kartları mobilde
   hâlâ fazla yer kaplıyordu. Kartlar TEK SÜTUNDA KALIYOR (bu daha önce
   onaylanmış bir karardı, geri alınmadı) — iç boşluklar ve eleman
   boyutları bir tur daha küçültüldü. Ayrıca dp_page_frame'in (tüm
   sayfayı saran çerçeve) kendi üst dolgusu da mobilde daraltıldı —
   üst tarafta göze batan boşluğun bir kısmı buradan geliyordu. */
@media (max-width: 480px) {
    /* DÜZELTME (11.08.2026 — 3. tur): Platform güncellemesiyle Streamlit
       artık st.columns()'ları mobilde daha GENİŞ bir noktada alt alta
       dizmeye başlamış olabilir. Bunun İKİ somut sonucu görüldü:
       (1) dp_kartlar_row'daki iki kart (Talep/Portföy) beklenenden dar
       kaldı — her ikisi de tam genişlik almıyordu.
       (2) Kart İÇİNDEKİ stat_col/badge_col ([2,1] oranlı, "247 aktif
       talep" + "+22 yeni") artık yan yana değil ALT ALTA render
       oluyordu — bu da aralarında büyük boşluklu, "kutulu" bir görünüm
       yaratıyordu (bu bir CSS border/arka plan hatası DEĞİL, sadece
       stacking'in kendisiydi). Her iki noktada da Streamlit'in kendi
       responsive stacking kararına güvenmek yerine, iki sütunlu
       düzeni AÇIKÇA zorluyoruz. */
    div[class*="st-key-dp_kartlar_row"] [data-testid="stColumn"] {
        width: 100% !important;
        min-width: 100% !important;
        flex: 1 1 100% !important;
    }
    /* DÜZELTME (12.08.2026 — 4. tur): Önceki turda burada stat_col/
       badge_col'u display:grid ile zorlamak, rozeti ("+22 yeni") kart
       sınırının dışına taşıran YENİ bir görsel hataya yol açtı — grid,
       Streamlit'in bu elemanlara zaten uyguladığı satır-içi flex
       stillerle çakışmış olabilir. Bu tur DAHA MUHAFAZAKAR bir
       yaklaşıma dönüldü: layout modunu (flex→grid) değiştirmek yerine,
       Streamlit'in KENDİ flex düzenini koruyup sadece satır kırılmasını
       (flex-wrap) engelliyoruz — daha az agresif, çakışma riski daha
       düşük. */
    div[class*="st-key-dp_kart_talep"] [data-testid="stHorizontalBlock"],
    div[class*="st-key-dp_kart_portfoy"] [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
    }
    div[class*="st-key-dp_kart_talep"] [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
    div[class*="st-key-dp_kart_portfoy"] [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        width: auto !important;
        min-width: 0 !important;
        flex: initial !important;
    }

    div[class*="st-key-dp_page_frame"] {
        padding: 14px 14px 16px 14px !important;
    }
    div[class*="st-key-dp_kart_talep"] div[data-testid="stVerticalBlockBorderWrapper"],
    div[class*="st-key-dp_kart_portfoy"] div[data-testid="stVerticalBlockBorderWrapper"] {
        padding: 10px 12px !important;
    }
    .dp-icon-box {
        width: 24px !important;
        height: 24px !important;
        max-width: 24px !important;
        border-radius: 6px !important;
        font-size: 13px !important;
        margin-bottom: 3px !important;
    }
    .dp-icon-box svg {
        width: 13px !important;
        height: 13px !important;
    }
    .dp-stat-row {
        padding-top: 5px !important;
        margin-top: 3px !important;
    }
    .dp-stat-num {
        font-size: 16px !important;
    }
    div[class*="st-key-dp_kart_talep"] p,
    div[class*="st-key-dp_kart_portfoy"] p {
        margin-bottom: 2px !important;
        font-size: 12.5px !important;
    }
    div[class*="st-key-dp_talep_git"] button,
    div[class*="st-key-dp_portfoy_git"] button {
        padding: 7px 12px !important;
        font-size: 12.5px !important;
    }
    div[class*="st-key-dp_talep_yeni_rozet"] button,
    div[class*="st-key-dp_portfoy_yeni_rozet"] button {
        padding: 3px 9px !important;
        font-size: 11px !important;
    }
    /* Kartlar arası dikey boşluk da azaltıldı (Streamlit sütun grubu
       varsayılan gap'i). */
    div[class*="st-key-dp_kartlar_row"] div[data-testid="stHorizontalBlock"] {
        row-gap: 8px !important;
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
/* DÜZELTME (12.08.2026 — 4. tur, fikir değiştirildi): Uzmanlık
   Bölgelerim'e kendine has teal vurgusu verilmişti (10.08.2026), sonra
   bu turda GERİ ALINDI — artık Favori Listem ile AYNI nötr beyaz stili
   paylaşıyor (yukarıdaki paylaşılan kural zaten bunu sağlıyor, bu
   yüzden burada AYRICA bir override YOK). Ayrım artık sadece kendi pin
   ikonuyla (★ yerine 📍 mantığı) sağlanıyor, renkle değil. */
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
/* Pin ikonu (12.08.2026 — 3. tur): temiz çizgisel SVG, Talep/Portföy
   kartlarındaki ikonlarla aynı stroke mantığında. DÜZELTME (4. tur):
   Buton artık nötr olduğu için ikon rengi de nötr griye (#5b6478,
   butonun kendi yazı rengiyle aynı) çekildi — teal'e özel bir renk
   kalmadı. */
div[class*="st-key-dp_uzmanlik_btn"] button {
    display: inline-flex !important;
    align-items: center !important;
}
div[class*="st-key-dp_uzmanlik_btn"] button::before {
    content: "";
    display: inline-block;
    width: 14px;
    height: 14px;
    margin-right: 7px;
    background-repeat: no-repeat;
    background-size: contain;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%235b6478' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z'/%3E%3Ccircle cx='12' cy='10' r='3'/%3E%3C/svg%3E");
}
/* Bölge sayısı rozeti — Uzmanlık Bölgelerim butonunun yanındaki ayrı,
   dekoratif pill (mockup'taki "4 bölge" gibi). Kendi butonu değil,
   sadece bilgi amaçlı — tıklanabilirlik ana butonda kalıyor. */
div[class*="st-key-dp_uzmanlik_sayi"] {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
}
.dp-bolge-sayisi {
    display: inline-flex;
    align-items: center;
    background: #eef0f3;
    color: #5b6478;
    font-size: 11.5px;
    font-weight: 700;
    padding: 5px 11px;
    border-radius: 999px;
    white-space: nowrap;
}

/* NOT (2. tur — geri alındı): Daha önce burada mobilde kartları zorla
   yan yana (50%/50%) tutan bir medya sorgusu vardı. Gerçek testte
   içeriğin (sayı, rozet, buton) dar sütunda taştığı görüldü — amatör
   bir görünüme sebep oluyordu. Streamlit'in DOĞAL davranışına
   (mobilde sütunları alt alta, tam genişlikte dizmek) geri dönüldü —
   daha güvenli, taşma riski yok. */
</style>
""", unsafe_allow_html=True)

with st.container(border=True, key="dp_page_frame"):
    render_topbar("Danışman Panosu", eyebrow="Startkey Zeta")

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
    # DÜZELTME (13.08.2026 — KRİTİK): "620 aktif portföy" sayısı, Portföy
    # Panosu kartının kendisi (linkin gittiği yer) artık resmi ilanları
    # (zeta1/zeta2) hariç tuttuğu için AYNI hariç tutmayı burada da
    # uygulamazsak sayı ile gerçek liste birbirini tutmuyordu (örn. "620"
    # yazıp tıklayınca 500 kayıt görünmesi gibi bir tutarsızlık). Zeta
    # Portföyleri'nin kendi sayısı ayrı bir yerde (o sayfanın kendisinde,
    # ileride ayrı bir kart eklenebilir) — burada DEĞİL.
    portfoyler = [
        v for v in portfoyleri_cek()
        if str(v.get("kaynak") or "").strip().lower() not in ILAN_PORTAL_DEGERLERI
    ]
    # "+N yeni" rozeti ve sayaçlar TÜM KAYNAKLARI kapsar (Zeta + Startkey/mail
    # birlikte, resmi portal ilanları HARİÇ) — Talep/Portföy Panosu zaten
    # bu kapsamda tutarlı, bu yüzden rozet de aynı kapsamda tutarlı olmalı.
    # Yalnızca Zeta'ya özel görünüm için: hamburger menü → Zeta Paylaşımları.
    # Resmi ilanlar için: hamburger menü → Zeta Portföyleri.
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
        # DÜZELTME (12.08.2026): Buton + gerçek bölge sayısı rozeti aynı
        # satırda, mockup'taki "Uzmanlık Bölgelerim  4 bölge" yerleşimine
        # uygun. Sayı sabit değil — uzmanlik_bolgelerini_cek() ile canlı
        # okunuyor, kullanıcının o an seçili ilçe adedini gösteriyor.
        uzm_btn_col, uzm_sayi_col = st.columns([3, 1])
        with uzm_btn_col:
            if st.button("Uzmanlık Bölgelerim", key="dp_uzmanlik_btn", use_container_width=True):
                st.switch_page("pages/Danisman_UzmanlikBolgeleri.py")
        with uzm_sayi_col:
            secili_bolge_sayisi = len(uzmanlik_bolgelerini_cek(su_anki_danisman()))
            if secili_bolge_sayisi:
                st.markdown(
                    f"<div class='dp-bolge-sayisi'>{secili_bolge_sayisi} bölge</div>",
                    unsafe_allow_html=True,
                )
    with col_favori:
        if st.button("Favori Listem", key="dp_favori_btn"):
            st.switch_page("pages/Danisman_Favoriler.py")

    st.write("")

    # ── FSBO İlanları — YENİ (30.08.2026), Uzmanlık Bölgelerim ile AYNI
    # "buton + canlı bölge sayısı rozeti" deseni. BİLEREK ayrı bir satırda,
    # üsttekilerin genişliğini değiştirmeden eklendi — kartların büyük
    # ölçekli yeniden düzenlenmesi (FSBO'nun birincil karta terfi etmesi)
    # onaylanmış ayrı bir mockup işi, henüz başlanmadı; bu sadece ekranı
    # gerçek kullanıma açan minimum adım.
    col_fsbo, _col_fsbo_bos = st.columns([1, 1])
    with col_fsbo:
        fsbo_btn_col, fsbo_sayi_col = st.columns([3, 1])
        with fsbo_btn_col:
            if st.button("FSBO İlanları", key="dp_fsbo_btn", use_container_width=True):
                st.switch_page("pages/Danisman_FSBOIlanlari.py")
        with fsbo_sayi_col:
            fsbo_bolge_sayisi = len(bolgelerini_cek("fsbo_bolgeleri", su_anki_danisman()))
            if fsbo_bolge_sayisi:
                st.markdown(
                    f"<div class='dp-bolge-sayisi'>{fsbo_bolge_sayisi} bölge</div>",
                    unsafe_allow_html=True,
                )

    st.write("")

    # ── TELEFON BİLDİRİMLERİ — FAZ 1 (31.08.2026, Meltem: "nolur mümkün
    # olsun") — sadece TEMEL ALTYAPI: izin iste + abone ol + kendine bir
    # test bildirimi gönder. Henüz hiçbir OTOMATİK tetikleyici (FSBO takip
    # alarmı, yeni portföy/eşleşen talep bildirimi) yok — bunlar bu
    # altyapı üzerine ayrı, sonraki adımlarda inşa edilecek. Bilerek bir
    # expander içinde, sade — asıl ekranı kalabalıklaştırmasın diye.
    with st.expander("🔔 Telefon bildirimleri (deneme aşaması)", expanded=False):
        st.caption(
            "Aşağıdaki düğmeye basınca yeni bir sekme açılır — orada "
            "'Bildirimleri Aç'a bas, tarayıcı izin isteyecek, izin ver. "
            "Sonra o sekmeyi kapatıp buraya dönebilirsin."
        )
        render_bildirim_izni_butonu(su_anki_danisman(), key_prefix="dp_pb")
        if st.button("Kendime test bildirimi gönder", key="dp_pb_test"):
            try:
                sonuc = bildirim_gonder(
                    su_anki_danisman(),
                    "Test Bildirimi",
                    "Bildirimler çalışıyor! 🎉",
                )
                if sonuc["gonderildi"]:
                    st.success(f"{sonuc['gonderildi']} cihaza gönderildi.")
                elif sonuc["silinen"]:
                    st.warning("Kayıtlı abonelik süresi dolmuş görünüyor — yukarıdan tekrar 'Bildirimleri Aç'a bas.")
                else:
                    st.warning("Henüz kayıtlı bir bildirim aboneliğin yok — önce yukarıdan 'Bildirimleri Aç'a bas.")
            except Exception as e:
                st.error(f"Gönderilemedi: {e}")

    render_activity_bar()

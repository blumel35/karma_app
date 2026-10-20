# core/yeni_ana_sayfa.py
# -*- coding: utf-8 -*-
"""
YENİ Danışman Panosu ana sayfası (özellik anahtarı arkasında; yalnızca
Supabase 'ozellik_erisim' tablosunda yetkili olan kullanıcılar görür).

pages/Danisman_Secim.py bu modülü SADECE
core.ozellik_erisim.ozellik_acik_mi("yeni_ana_sayfa") True ise çağırır;
diğer herkes eski ekranı görmeye devam eder.

İki sayfa (mockup v13): "Ana sayfa" ve "Radarım". Sayfa seçimi st.tabs ile
DEĞİL st.radio ile yapılır (st.tabs her çalıştırmada TÜM sekmelerin kodunu
çalıştırır; Radarım'ın ağır sorguları ana sayfayı da yavaşlatırdı).

Ana sayfa = mevcut ana ekranın (pages/Danisman_Secim.py) KOPYASI, şu farklarla:
  - "Telefon bildirimleri" bölümü yok,
  - "Startkey İlanları" butonu yok (Radarım'da Startkey kutusu olacak),
  - "Son 24 saat" ayrı kart değil, "Bildirimlerim" kartının içinde (tek başlık).
Eski dosyaya dokunulmadı; yeni arayüz herkese açılınca eski ekran temizlenir.
"""

import streamlit as st
from datetime import date, datetime, timedelta

from core.danisman_ortak import (
    talepleri_cek, portfoyleri_cek, son_N_gun_filtrele,
    ekle_dialog, render_topbar, hide_sidebar_css,
    uzmanlik_bolgelerini_cek, uzmanlik_bolgesi_filtrele,
    su_anki_danisman, ILAN_PORTAL_DEGERLERI,
    son_24_saat_ozeti, bildirim_url_coz, bildirim_zaman_etiketi,
)
from core.bolge_secici import bolgelerini_cek, pazar_ilanlarini_cek
from core.push_bildirim import bildirimlerimi_cek


def _stil_yaz():
    st.markdown("""
    <style>
    /* ── HERO KARTLARI — Uzmanlık Bölgelerim / FSBO İlanları ─────────────
       YENİ (27.09.2026 — hiyerarşi revizyonu). Talep/Portföy Panosu'nun
       ESKİ birincil kart deseninin (navy CTA butonu, üst renk şeridi) aynısı
       — sadece hedefi değişti. Üst şerit rengi kart kimliğini taşıyor
       (gold=Uzmanlık, kiremit=FSBO — mockup'ta onaylanan ayrım), CTA butonu
       ise ikisinde de navy (uygulamanın genel "birincil eylem" rengi,
       Talep/Portföy'ün eski "Git" butonlarıyla AYNI kural — tutarlılık). */
    div[class*="st-key-dp_hero_uzmanlik"] div[data-testid="stVerticalBlockBorderWrapper"],
    div[class*="st-key-dp_hero_fsbo"] div[data-testid="stVerticalBlockBorderWrapper"] {
        padding: 13px 12px 12px 12px !important;
    }
    .dp-hero-accent {
        height: 4px; border-radius: 3px; margin: -1px 0 9px 0;
    }
    .dp-hero-accent.uzmanlik { background: #b8892f; }
    .dp-hero-accent.fsbo { background: #bb5f3c; }
    .dp-hero-title {
        font-size: 12.5px; font-weight: 700; color: #1b2540; margin-bottom: 2px;
    }
    .dp-hero-icon { font-size: 19px; margin-bottom: 2px; }
    .dp-hero-num-row {
        display: flex; align-items: baseline; gap: 5px; margin: 2px 0 3px 0;
    }
    .dp-hero-num { font-size: 22px; font-weight: 800; color: #1b2540; }
    .dp-hero-num-unit { font-size: 12px; font-weight: 600; color: #9a9488; }
    /* "+N yeni" rozeti — bilerek statik/bilgi amaçlı (buton değil), sıcak
       kırmızımsı-turuncu ton (marka renklerinden bilerek AYRI — "dikkat/
       yenilik" sinyali, iki hero kartta da AYNI renk, sadece üst şerit
       kart kimliğine göre değişiyor). */
    .dp-hero-new-badge {
        font-size: 9.5px; font-weight: 700; color: #b5432f;
        background: #f7e3df; border-radius: 8px; padding: 2px 5px;
        white-space: nowrap;
    }
    .dp-hero-caption {
        font-size: 10.5px; color: #9a9488; line-height: 1.3; margin-bottom: 9px;
    }
    div[class*="st-key-dp_hero_uzmanlik_git"] button,
    div[class*="st-key-dp_hero_fsbo_git"] button {
        color: #ffffff !important;
        font-size: 11.5px !important;
        padding: 8px 0 !important;
    }
    /* DÜZELTME (27.09.2026, Meltem: "buton rengi değişmemiş"): mockup'ta
       FSBO'nun CTA butonu kendi üst şeridiyle (kiremit) AYNI renkteydi —
       gerçek uygulamada ikisi de yanlışlıkla navy kalmıştı (Talep/Portföy'ün
       eski "hepsi navy" kuralı düşünülmeden buraya taşınmış). Artık Uzmanlık
       navy, FSBO kiremit — mockup'la birebir. */
    div[class*="st-key-dp_hero_uzmanlik_git"] button {
        background-color: #1b2540 !important;
        border-color: #1b2540 !important;
    }
    div[class*="st-key-dp_hero_uzmanlik_git"] button:hover {
        background-color: #28345a !important;
        border-color: #28345a !important;
        color: #ffffff !important;
    }
    div[class*="st-key-dp_hero_fsbo_git"] button {
        background-color: #bb5f3c !important;
        border-color: #bb5f3c !important;
    }
    div[class*="st-key-dp_hero_fsbo_git"] button:hover {
        background-color: #a34f30 !important;
        border-color: #a34f30 !important;
        color: #ffffff !important;
    }

    /* ── İKİNCİL KARTLAR — Talep Panosu / Portföy Panosu ──────────────────
       YENİ (27.09.2026 — hiyerarşi revizyonu, KÜÇÜLTÜLDÜ): eskiden bu iki
       kart hero'ydu (ikon kutusu + büyük sayı + "+N yeni" TIKLANABİLİR rozet
       + ayrı tam genişlikte "Git →" butonu). Meltem'in geri bildirimi
       ("kartın tamamı tıklanabiliyorsa oku belirginleştir, ayrıca buton
       eklemezdim") — Streamlit'te gerçek "tüm kart tıklanabilir" (native
       <a>) desteklenmiyor (bu dosyadaki başka hiçbir yerde de JS/özel
       component hack'i kullanılmıyor, bilinçli bir sınır) — bu yüzden EN
       YAKIN karşılığı uygulandı: üç ayrı kontrolü (sayı+rozet+"Git" butonu)
       TEK bir büyütülmüş, dairesel ok ÇİPİNE indirdik — kartta görünen TEK
       tıklanabilir eleman bu, ayrıca tam genişlik CTA butonu YOK. "+N yeni"
       artık statik bilgi (tıklanamaz) — önceki "sadece yenileri filtrele"
       kısayolu bu sadeleştirmede kasıtlı olarak kaldırıldı; istenirse ayrı
       bir yerde geri eklenebilir. */
    div[class*="st-key-dp_kart_talep"] div[data-testid="stVerticalBlockBorderWrapper"],
    div[class*="st-key-dp_kart_portfoy"] div[data-testid="stVerticalBlockBorderWrapper"] {
        padding: 14px 14px !important;
    }
    .dp-sec-accent {
        height: 3px; border-radius: 3px; margin: -1px 0 8px 0;
        background: #1b2540;
    }
    .dp-sec-title-row {
        display: flex; align-items: center; justify-content: space-between;
    }
    .dp-sec-title { font-size: 13px; font-weight: 700; color: #1b2540; }
    .dp-sec-num-row {
        display: flex; align-items: baseline; gap: 7px; flex-wrap: wrap;
        margin-top: 3px;
    }
    .dp-sec-num { font-size: 21px; font-weight: 800; color: #1b2540; }
    .dp-sec-num-unit { font-size: 11px; font-weight: 600; color: #9a9488; }
    .dp-sec-new {
        font-size: 10.5px; font-weight: 700; color: #b5432f;
        background: #f7e3df; border-radius: 8px; padding: 1px 6px;
        white-space: nowrap;
    }
    /* Dairesel ok çipi — kartın TEK tıklanabilir kontrolü. */
    div[class*="st-key-dp_talep_git"] button,
    div[class*="st-key-dp_portfoy_git"] button {
        width: 34px !important;
        height: 34px !important;
        min-height: 34px !important;
        border-radius: 50% !important;
        background: #f2ede0 !important;
        border: none !important;
        color: #b8892f !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        flex-shrink: 0 !important;
    }
    div[class*="st-key-dp_talep_git"] button:hover,
    div[class*="st-key-dp_portfoy_git"] button:hover {
        background: #e7dfc8 !important;
    }

    /* Kartların içindeki Streamlit sütun/element sarmalayıcılarının kalıntı
       border/arka planını sıfırlıyoruz — hero+ikincil kartların TÜMÜ için
       ortak, önceki turlarda çözülmüş aynı desen. */
    div[class*="st-key-dp_hero_uzmanlik"] [data-testid="stHorizontalBlock"],
    div[class*="st-key-dp_hero_fsbo"] [data-testid="stHorizontalBlock"],
    div[class*="st-key-dp_hero_uzmanlik"] [data-testid="stColumn"],
    div[class*="st-key-dp_hero_fsbo"] [data-testid="stColumn"],
    div[class*="st-key-dp_kart_talep"] [data-testid="stHorizontalBlock"],
    div[class*="st-key-dp_kart_portfoy"] [data-testid="stHorizontalBlock"],
    div[class*="st-key-dp_kart_talep"] [data-testid="stColumn"],
    div[class*="st-key-dp_kart_portfoy"] [data-testid="stColumn"],
    div[class*="st-key-dp_hero_uzmanlik"] [data-testid="stVerticalBlock"],
    div[class*="st-key-dp_hero_fsbo"] [data-testid="stVerticalBlock"],
    div[class*="st-key-dp_kart_talep"] [data-testid="stVerticalBlock"],
    div[class*="st-key-dp_kart_portfoy"] [data-testid="stVerticalBlock"],
    div[class*="st-key-dp_hero_uzmanlik"] [data-testid="stElementContainer"],
    div[class*="st-key-dp_hero_fsbo"] [data-testid="stElementContainer"],
    div[class*="st-key-dp_kart_talep"] [data-testid="stElementContainer"],
    div[class*="st-key-dp_kart_portfoy"] [data-testid="stElementContainer"] {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        min-height: 0 !important;
    }

    /* MOBİL — hero VE ikincil satırları, Talep/Portföy'ün eski mobil
       düzeltmesiyle (09-12.08.2026, 4 tur) AYNI kanıtlanmış desen: Streamlit
       sütunları dar ekranda doğal olarak alt alta diziyor — burada bilinçli
       olarak bunu geçersiz kılıp iki kartı hep YAN YANA tutuyoruz. */
    @media (max-width: 480px) {
        div[class*="st-key-dp_hero_row"] [data-testid="stColumn"],
        div[class*="st-key-dp_kartlar_row"] [data-testid="stColumn"] {
            width: 100% !important;
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }
        div[class*="st-key-dp_hero_uzmanlik"] [data-testid="stHorizontalBlock"],
        div[class*="st-key-dp_hero_fsbo"] [data-testid="stHorizontalBlock"],
        div[class*="st-key-dp_kart_talep"] [data-testid="stHorizontalBlock"],
        div[class*="st-key-dp_kart_portfoy"] [data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
        }
        div[class*="st-key-dp_hero_uzmanlik"] [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
        div[class*="st-key-dp_hero_fsbo"] [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
        div[class*="st-key-dp_kart_talep"] [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
        div[class*="st-key-dp_kart_portfoy"] [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            width: auto !important;
            min-width: 0 !important;
            flex: initial !important;
        }
        div[class*="st-key-dp_page_frame"] {
            padding: 14px 14px 16px 14px !important;
        }
        div[class*="st-key-dp_hero_uzmanlik"] div[data-testid="stVerticalBlockBorderWrapper"],
        div[class*="st-key-dp_hero_fsbo"] div[data-testid="stVerticalBlockBorderWrapper"] {
            padding: 11px 10px 10px 10px !important;
        }
        div[class*="st-key-dp_kart_talep"] div[data-testid="stVerticalBlockBorderWrapper"],
        div[class*="st-key-dp_kart_portfoy"] div[data-testid="stVerticalBlockBorderWrapper"] {
            padding: 11px 12px !important;
        }
        .dp-hero-num { font-size: 19px !important; }
        .dp-hero-title { font-size: 11.5px !important; }
        .dp-hero-caption { font-size: 10px !important; }
        .dp-sec-num { font-size: 18px !important; }
        .dp-sec-title { font-size: 12px !important; }
        div[class*="st-key-dp_hero_row"] div[data-testid="stHorizontalBlock"],
        div[class*="st-key-dp_kartlar_row"] div[data-testid="stHorizontalBlock"] {
            row-gap: 8px !important;
        }
    }

    /* ── ÜÇÜNCÜL PILL'LER — Startkey İlanları / Favori Listem ────────────
       Uzmanlık Bölgelerim hero'ya terfi ettiği için eski pill grubundan
       ÇIKTI — Startkey artık Favori Listem ile AYNI satırda, AYNI nötr pill
       stiliyle (aşağıdaki paylaşılan kural ikisini de kapsıyor). */
    div[class*="st-key-dp_favori_btn"] button,
    div[class*="st-key-dp_startkey_btn"] button {
        width: auto !important;
        display: inline-flex !important;
        padding: 8px 16px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        border-color: #e3e1da !important;
        background: #ffffff !important;
        color: #5b6478 !important;
    }
    div[class*="st-key-dp_favori_btn"] button::before {
        content: "★";
        color: #b8892f !important;
        margin-right: 6px;
        font-size: 14px;
    }
    div[class*="st-key-dp_startkey_btn"] button::before {
        content: "🏢";
        margin-right: 6px;
        font-size: 13px;
    }
    div[class*="st-key-dp_startkey_sayi"] {
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

    /* "+ Yeni Talep/Portföy Ekle" — DEĞİŞMEDİ, ayrı nötr gri stil. */
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
    div[class*="st-key-dp_ekle_btn"] button {
        width: auto !important;
        display: inline-flex !important;
        padding: 8px 16px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ── BİLDİRİMLERİM KARTI — "Son 24 saat" + bildirim önizlemesi TEK kartta ──
# Kaynak: core.danisman_ortak.render_activity_bar + render_bildirim_onizleme
# (aynı veri fonksiyonları; yalnızca iki ayrı kart tek başlık altında birleşti).
def _bildirimler_karti(startkey_yeni_sayisi=0):
    ozet = son_24_saat_ozeti()
    bildirimler = bildirimlerimi_cek(su_anki_danisman(), limit=3)
    aktivite_var = bool(
        ozet["talep_sayisi"] or ozet["portfoy_sayisi"]
        or ozet["ilan_sayisi"] or startkey_yeni_sayisi
    )
    if not aktivite_var and not bildirimler:
        return

    st.markdown(
        """
        <style>
        div[class*="st-key-ya_bildirim_baslik_"] button {
            all: unset;
            display: block;
            width: 100%;
            font-size: 0.875rem;
            line-height: 1.5;
            cursor: pointer;
            color: inherit;
        }
        div[class*="st-key-ya_bildirim_baslik_"] button:hover {
            text-decoration: underline;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True, key="ya_bildirimler_kutu"):
        st.markdown(
            "<span style='display:inline-flex;align-items:center;gap:6px;'>"
            "<svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='#b8892f' stroke-width='2' "
            "stroke-linecap='round' stroke-linejoin='round'><path d='M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9'/>"
            "<path d='M13.73 21a2 2 0 0 1-3.46 0'/></svg>"
            "<span style='font-size:1.05rem'><b>Bildirimlerim</b></span></span>",
            unsafe_allow_html=True,
        )

        if aktivite_var:
            _sayi = lambda n: f"<b style='color:#1b2540;'>{n}</b>"
            ilan_cumle = f", {_sayi(ozet['ilan_sayisi'])} yeni Zeta ilanı" if ozet["ilan_sayisi"] else ""
            startkey_cumle = (
                f", {_sayi(startkey_yeni_sayisi)} yeni Startkey ilanı (bölgelerinde)"
                if startkey_yeni_sayisi else ""
            )
            st.markdown(
                f"<div style='margin-top:6px'><b>Son 24 saat:</b> {_sayi(ozet['talep_sayisi'])} yeni talep, "
                f"{_sayi(ozet['portfoy_sayisi'])} yeni portföy paylaşımı{ilan_cumle}{startkey_cumle}</div>",
                unsafe_allow_html=True,
            )
            for olay in ozet["son_olaylar"]:
                st.caption(f"• **{olay['danisman']}** {olay['eylem']}")
            pb1, pb2 = st.columns(2)
            with pb1:
                if st.button("Tüm Paylaşımlar →", key="ya_tum_paylasimlar", use_container_width=True):
                    st.switch_page("pages/Danisman_Paylasimlar.py")
            with pb2:
                if st.button("Zeta Portföyleri →", key="ya_tum_ilanlar", use_container_width=True):
                    st.session_state["dp_zeta_ilan_sadece_yeni"] = True
                    st.switch_page("pages/Danisman_ZetaPortfoyleri.py")

        if aktivite_var and bildirimler:
            st.divider()

        for b in bildirimler:
            _govde = f" — {b['govde']}" if b.get("govde") else ""
            _zaman = bildirim_zaman_etiketi(b.get("created_at"), kisa=True)
            _zaman_on = f"{_zaman} · " if _zaman else ""
            hedef_sayfa, session_anahtari = bildirim_url_coz(b.get("url"))
            if hedef_sayfa:
                if st.button(
                    f"• {_zaman_on}{b.get('baslik') or ''}{_govde}",
                    key=f"ya_bildirim_baslik_{b.get('id')}",
                ):
                    if session_anahtari:
                        st.session_state[session_anahtari] = "Bugün"
                    st.switch_page(hedef_sayfa)
            else:
                st.caption(f"• {_zaman_on}**{b.get('baslik') or ''}**{_govde}")
        if bildirimler:
            if st.button("Tüm Bildirimler →", key="ya_tum_bildirimler", use_container_width=True):
                st.switch_page("pages/Danisman_Bildirimlerim.py")


# ── ANA SAYFA GÖVDESİ (mevcut ana ekranın kopyası) ───────────────────────
def _ana_sayfa_govde():
    cap_col, ekle_col = st.columns([3, 2])
    with cap_col:
        st.caption("Talep ve portföyleri canlı takip edin, hızlıca yeni kayıt ekleyin.")
    with ekle_col:
        if st.button("+ Yeni Talep/Portföy Ekle", key="dp_ekle_btn", use_container_width=True):
            ekle_dialog()
    st.write("")

    # ── VERİ ────────────────────────────────────────────────────────────
    talepler = talepleri_cek()
    portfoyler = [
        v for v in portfoyleri_cek()
        if str(v.get("kaynak") or "").strip().lower() not in ILAN_PORTAL_DEGERLERI
    ]
    talep_yeni = son_N_gun_filtrele(talepler, 7)
    portfoy_yeni = son_N_gun_filtrele(portfoyler, 7)

    su_kullanici = su_anki_danisman()

    # Uzmanlık Bölgelerim — hero için: seçili bölge sayısı + o bölgelerde
    # eşleşen (talep+portföy) aktif kayıt sayısı + son 7 gündeki eşleşen
    # yeni kayıt sayısı ("+N yeni" rozeti).
    uzmanlik_ilceler = [
        r.get("ilce") for r in uzmanlik_bolgelerini_cek(su_kullanici) if r.get("ilce")
    ]
    uzmanlik_bolge_sayisi = len(uzmanlik_ilceler)
    uzmanlik_eslesenler = (
        uzmanlik_bolgesi_filtrele(talepler + portfoyler, uzmanlik_ilceler)
        if uzmanlik_ilceler else []
    )
    uzmanlik_aktif_sayisi = len(uzmanlik_eslesenler)
    uzmanlik_yeni_sayisi = len(son_N_gun_filtrele(uzmanlik_eslesenler, 7)) if uzmanlik_eslesenler else 0

    # FSBO İlanları — hero için: seçili bölge + toplam ilan sayısı + bugün
    # yayınlanan/güncellenen ilan sayısı ("+N yeni" rozeti). Aynı veri
    # kaynağı/mantığı pages/Danisman_FSBOIlanlari.py ile TUTARLI (kalıcı
    # fsbo_bolgeleri seçimi, izmir_pazar_ilanlar tablosu, marka=mulk_sahibi).
    fsbo_kayitlar = bolgelerini_cek("fsbo_bolgeleri", su_kullanici)
    fsbo_ilceler = [k["ilce"] for k in fsbo_kayitlar]
    fsbo_bolge_sayisi = len(fsbo_ilceler)
    fsbo_ilanlar = pazar_ilanlarini_cek("mulk_sahibi", fsbo_ilceler) if fsbo_ilceler else []

    def _ilan_tarihi_gun(v):
        t = v.get("ilan_tarihi")
        if not t:
            return None
        try:
            return datetime.strptime(str(t)[:10], "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return None

    # DÜZELTME (27.09.2026, Meltem: "bildirim gelmedi, revy de ilanlar 3
    # gün geriden geliyor ondan olabilir mi"): "+N yeni" rozetleri (aşağıda
    # fsbo_bugun_sayisi / startkey_bugun_sayisi) ÖNCEDEN _ilan_tarihi_gun
    # (Revy'nin kendi, gecikmeli/güvenilmez "İlan tarihi" sütunu) == bugün
    # şartına bakıyordu — Supabase'te gerçek veriyle doğrulandı, bu
    # neredeyse hiç eşleşmiyor. "Son 7 gün" caption'ı (fsbo_ilanlar_yakin,
    # aşağıda) BİLEREK _ilan_tarihi_gun'da bırakıldı — Danisman_FSBOIlanlari.py
    # sayfasının kendi varsayılan filtresiyle TUTARLI kalsın diye, o sayfaya
    # bu turda dokunulmadı. Sadece "bugün" rozetleri, yeni
    # ilk_gorulme_tarihi sütununa (core/izmir_pazar_sync.py'nin upsert'inin
    # HİÇ dokunmadığı, sadece gerçek İLK INSERT'te Postgres DEFAULT now()
    # ile dolan bir zaman damgası) geçirildi — bkz. core/bildirim_tetikleyici.py
    # içindeki aynı düzeltmenin ayrıntılı açıklaması.
    def _ilk_gorulme_gun(v):
        t = v.get("ilk_gorulme_tarihi")
        if not t:
            return None
        try:
            return datetime.strptime(str(t)[:10], "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return None

    _bugun = date.today()
    # DÜZELTME (27.09.2026, Meltem: "2 ilçe ... bölge adedi doğru ilan
    # adedi hatalı"): "Bölgelerinde N aktif ilan" caption'ı önceden
    # pazar_ilanlarini_cek()'in HAM/TÜM ZAMANLARDAKİ "aktif=True" toplamını
    # (2405 gibi) gösteriyordu — pages/Danisman_FSBOIlanlari.py'nin kendi
    # dosya başı notunda da açıklandığı gibi ("izmir_pazar_sync.py'de
    # otomatik pasifleştirme BİLİNÇLİ OLARAK kapalı ... tek başına
    # 'aktif=True' filtresi hâlâ çok eski ilanları da getirebiliyor"), bu
    # ham toplam güncel/anlamlı bir sayı DEĞİL — o sayfanın kendisi de tam
    # bu yüzden varsayılan olarak "Son 7 Gün" filtresiyle açılıyor (101/2405
    # gibi). Ana ekran kartı da AYNI "Son 7 Gün" penceresine çekildi —
    # artık FSBO sayfasını ilk açtığında gördüğün sayıyla TUTARLI.
    _esik_7gun = _bugun - timedelta(days=7)
    fsbo_ilanlar_yakin = [
        v for v in fsbo_ilanlar if (_ilan_tarihi_gun(v) or date.min) >= _esik_7gun
    ]
    fsbo_ilan_sayisi = len(fsbo_ilanlar_yakin)
    fsbo_bugun_sayisi = len([v for v in fsbo_ilanlar if _ilk_gorulme_gun(v) == _bugun])

    # Startkey İlanları — YENİ (27.09.2026, Meltem: "son 24 saatte
    # startkey yeni ilan adedini de bölge bazlı göstersin"): Uzmanlık/
    # FSBO'dan TAMAMEN BAĞIMSIZ kendi bölge tablosu (startkey_ilan_bolgeleri)
    # + izmir_pazar_ilanlar (marka='startkey') — SADECE "Son 24 saat"
    # bandına eklenen bir ek bilgi, kendi hero/ikincil kartı YOK (o karar
    # bu turda yeniden açılmadı, sadece bu tek sayı istendi).
    startkey_kayitlar = bolgelerini_cek("startkey_ilan_bolgeleri", su_kullanici)
    startkey_ilceler = [k["ilce"] for k in startkey_kayitlar]
    startkey_ilanlar = pazar_ilanlarini_cek("startkey", startkey_ilceler) if startkey_ilceler else []
    startkey_bugun_sayisi = len([v for v in startkey_ilanlar if _ilk_gorulme_gun(v) == _bugun])

    # ── HERO — Uzmanlık Bölgelerim + FSBO İlanları ──────────────────────
    with st.container(key="dp_hero_row"):
        col_hero_uzm, col_hero_fsbo = st.columns(2, gap="small")

    with col_hero_uzm:
        with st.container(border=True, key="dp_hero_uzmanlik"):
            st.markdown("<div class='dp-hero-accent uzmanlik'></div>", unsafe_allow_html=True)
            st.markdown("<div class='dp-hero-icon'>📍</div>", unsafe_allow_html=True)
            st.markdown("<div class='dp-hero-title'>Uzmanlık Bölgelerim</div>", unsafe_allow_html=True)
            _yeni_rozet = (
                f"<span class='dp-hero-new-badge'>+{uzmanlik_yeni_sayisi} yeni</span>"
                if uzmanlik_yeni_sayisi else ""
            )
            st.markdown(
                f"<div class='dp-hero-num-row'><span class='dp-hero-num'>{uzmanlik_bolge_sayisi}</span>"
                f"<span class='dp-hero-num-unit'>bölge</span>{_yeni_rozet}</div>",
                unsafe_allow_html=True,
            )
            if uzmanlik_bolge_sayisi:
                st.markdown(
                    f"<div class='dp-hero-caption'>Bölgelerinde {uzmanlik_aktif_sayisi} aktif kayıt</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div class='dp-hero-caption'>Henüz bölge seçmedin</div>",
                    unsafe_allow_html=True,
                )
            _uzm_buton_metni = "Bölgelerimi Gör" if uzmanlik_bolge_sayisi else "Bölge Seç"
            if st.button(_uzm_buton_metni, key="dp_hero_uzmanlik_git", use_container_width=True):
                st.switch_page("pages/Danisman_UzmanlikBolgeleri.py")

    with col_hero_fsbo:
        with st.container(border=True, key="dp_hero_fsbo"):
            st.markdown("<div class='dp-hero-accent fsbo'></div>", unsafe_allow_html=True)
            st.markdown("<div class='dp-hero-icon'>📋</div>", unsafe_allow_html=True)
            st.markdown("<div class='dp-hero-title'>FSBO İlanları</div>", unsafe_allow_html=True)
            # DÜZELTME (27.09.2026, Meltem: "fsbo ilanlarında da 2 bölge 14
            # ilan desin tüm izmir fsbo ilanları yazmasın"): birincil
            # rakam artık Uzmanlık Bölgelerim ile AYNI desende — SEÇİLİ
            # BÖLGE SAYISI (küçük, anlamlı bir sayı), toplam ilan adedi
            # ise alttaki caption'a taşındı ("Bölgelerinde N aktif ilan").
            # Önceki hâlde tek başına gösterilen büyük "ilan" rakamı bölge
            # bağlamı olmadan "tüm İzmir" gibi okunuyordu — artık ikisi
            # birlikte, net biçimde.
            _fsbo_yeni_rozet = (
                f"<span class='dp-hero-new-badge'>+{fsbo_bugun_sayisi} yeni</span>"
                if fsbo_bugun_sayisi else ""
            )
            st.markdown(
                f"<div class='dp-hero-num-row'><span class='dp-hero-num'>{fsbo_bolge_sayisi}</span>"
                f"<span class='dp-hero-num-unit'>bölge</span>{_fsbo_yeni_rozet}</div>",
                unsafe_allow_html=True,
            )
            if fsbo_ilceler:
                st.markdown(
                    f"<div class='dp-hero-caption'>Bölgelerinde son 7 günde {fsbo_ilan_sayisi} ilan</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div class='dp-hero-caption'>Henüz FSBO bölgesi seçmedin</div>",
                    unsafe_allow_html=True,
                )
            _fsbo_buton_metni = "FSBO Listesini Aç" if fsbo_ilceler else "Bölge Seç"
            if st.button(_fsbo_buton_metni, key="dp_hero_fsbo_git", use_container_width=True):
                st.switch_page("pages/Danisman_FSBOIlanlari.py")

    st.write("")

    # ── İKİNCİL — Talep Panosu / Portföy Panosu ──────────────────────────
    with st.container(key="dp_kartlar_row"):
        col_talep, col_portfoy = st.columns(2, gap="small")

    with col_talep:
        with st.container(border=True, key="dp_kart_talep"):
            st.markdown("<div class='dp-sec-accent'></div>", unsafe_allow_html=True)
            tcol1, tcol2 = st.columns([5, 1])
            with tcol1:
                st.markdown("<div class='dp-sec-title'>Talep Panosu</div>", unsafe_allow_html=True)
            with tcol2:
                if st.button("→", key="dp_talep_git", help="Talep Panosuna git"):
                    st.session_state["dp_sadece_yeni"] = False
                    st.switch_page("pages/Danisman_Talep.py")
            _talep_yeni_html = (
                f"<span class='dp-sec-new'>+{len(talep_yeni)} yeni</span>" if talep_yeni else ""
            )
            st.markdown(
                f"<div class='dp-sec-num-row'><span class='dp-sec-num'>{len(talepler)}</span>"
                f"<span class='dp-sec-num-unit'>aktif</span>{_talep_yeni_html}</div>",
                unsafe_allow_html=True,
            )

    with col_portfoy:
        with st.container(border=True, key="dp_kart_portfoy"):
            st.markdown("<div class='dp-sec-accent'></div>", unsafe_allow_html=True)
            pcol1, pcol2 = st.columns([5, 1])
            with pcol1:
                st.markdown("<div class='dp-sec-title'>Portföy Panosu</div>", unsafe_allow_html=True)
            with pcol2:
                if st.button("→", key="dp_portfoy_git", help="Portföy Panosuna git"):
                    st.session_state["dp_sadece_yeni"] = False
                    st.switch_page("pages/Danisman_Portfoy.py")
            _portfoy_yeni_html = (
                f"<span class='dp-sec-new'>+{len(portfoy_yeni)} yeni</span>" if portfoy_yeni else ""
            )
            st.markdown(
                f"<div class='dp-sec-num-row'><span class='dp-sec-num'>{len(portfoyler)}</span>"
                f"<span class='dp-sec-num-unit'>aktif</span>{_portfoy_yeni_html}</div>",
                unsafe_allow_html=True,
            )

    st.write("")

    # ── ÜÇÜNCÜL — Favori Listem ──────────────────────────────────────────
    # (Startkey İlanları butonu yeni arayüzde kaldırıldı — Radarım'da
    # "Startkey portföyleri" olarak yer alacak. Startkey bölge sayısı ve
    # ilan verisi "Son 24 saat" cümlesi için yukarıda hâlâ hesaplanıyor.)
    if st.button("Favori Listem", key="dp_favori_btn"):
        st.switch_page("pages/Danisman_Favoriler.py")

    st.write("")

    _bildirimler_karti(startkey_yeni_sayisi=startkey_bugun_sayisi)


# ── GİRİŞ NOKTASI ────────────────────────────────────────────────────────
def render_yeni_ana_sayfa():
    hide_sidebar_css()
    _stil_yaz()
    with st.container(border=True, key="dp_page_frame"):
        render_topbar("Danışman Panosu", eyebrow="Startkey Zeta")

        sayfa = st.radio(
            "Sayfa",
            ["Ana sayfa", "Radarım"],
            horizontal=True,
            key="ya_sayfa",
            label_visibility="collapsed",
        )
        st.caption("🧪 Yeni arayüz (deneme) — yalnızca yetkili kullanıcılar görüyor. "
                   "Eski ekran için adres sonuna ?eski=1 ekle.")

        if sayfa == "Ana sayfa":
            _ana_sayfa_govde()
        else:
            st.info("Yeni Radarım (Portföylerim / Taleplerim akışları) sonraki adımda buraya gelecek.")
            if st.button("Mevcut Radarım sayfasını aç →", key="ya_eski_radarim"):
                st.switch_page("pages/Danisman_Bolgem.py")

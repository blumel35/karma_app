"""
pages/Danisman_Secim.py

Danışman Panosu'nun giriş sonrası ANA ekranı (2026-08 revizyonu; 2026-09-27
hiyerarşi revizyonu).

DÜZELTME (27.09.2026 — HİYERARŞİ REVİZYONU, Meltem: "uzmanlık bölgelerim ve
fsbo ilanları belki de bu uygulamanın ana unsurları olmalı talep ve portföy
panosu / startkey ilanları ve favorilerim de takip etmeli"): önceki
mimaride Talep/Portföy Panosu ekranın en büyük/birincil kartlarıydı. Bir
mockup turu (Artifact tasarım aracı, Meltem'in geri bildirimleriyle 5 tur
rafine edildi) sonrası onaylanan yeni hiyerarşi:

  1) HERO (en büyük, en üstte): Uzmanlık Bölgelerim + FSBO İlanları — ikisi
     de danışmanın GÜNLÜK, tekrarlı kullandığı takip araçları (Meltem:
     "danısmanlar en cok fsbo çalışmaları içn not tutar arama takibi
     yapar... piyasada fsbo takibi için bizim gibi günlük bildirim veren
     bir uygulama yok").
  2) İKİNCİL (orta boy): Talep Panosu / Portföy Panosu — hâlâ önemli ama
     artık "ana unsur" değil, kompakt kart + tek bir dairesel ok çipi
     (tıklanabilirlik sinyali, Meltem'in "oku belirginleştir, ayrıca buton
     eklemezdim" geri bildirimine göre — TEK kontrol, ayrı "Git" butonu
     YOK).
  3) ÜÇÜNCÜL (en küçük, pill): Startkey İlanları + Favori Listem.

- "Son 24 saat" aktivite özeti — sayılar artık lacivert/bold (Meltem:
  "3 ve 2 sayılarını lacivert/bold yaparsak göz taramasında hemen
  yakalanır") — bkz. core.danisman_ortak.render_activity_bar.
- "Bildirimlerim" önizlemesi (aktivite özetinin hemen altında).
- Sağ üstte hamburger menü: Kendi Kayıtlarım, Zeta Paylaşımları, Çıkış Yap.

NOT: "🔔 Telefon Bildirimleri (deneme aşaması)" bloğu BİLİNÇLİ OLARAK ana
ekranda kalıyor — Meltem'in kendi sorusuna kendi cevabı: "Bildirim özelliği
deneme aşamasındaysa şimdilik anlaşılır; oturduğunda ayarlara taşınabilir."
İleride bir "Ayarlar" ekranı açılırsa oraya taşınması gündeme gelebilir,
şimdilik dokunulmadı.
"""

import streamlit as st
from datetime import date, datetime, timedelta

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.danisman_ortak import (
    talepleri_cek, portfoyleri_cek, son_N_gun_filtrele,
    ekle_dialog, render_activity_bar, render_bildirim_onizleme,
    render_topbar, hide_sidebar_css,
    uzmanlik_bolgelerini_cek, uzmanlik_bolgesi_filtrele,
    su_anki_danisman, ILAN_PORTAL_DEGERLERI,
)
from core.bolge_secici import bolgelerini_cek, pazar_ilanlarini_cek
from core.push_bildirim import render_bildirim_izni_butonu, bildirim_gonder, abonelikleri_cek

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()

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

with st.container(border=True, key="dp_page_frame"):
    render_topbar("Danışman Panosu", eyebrow="Startkey Zeta")

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

    # ── ÜÇÜNCÜL — Startkey İlanları + Favori Listem ─────────────────────
    # Startkey İlanları kendi ayrı bölge tablosunu (startkey_ilan_bolgeleri)
    # kullanır — FSBO'dan/Uzmanlık Bölgelerim'den BAĞIMSIZ (değişmedi).
    col_startkey, col_favori = st.columns([1, 1])
    with col_startkey:
        startkey_btn_col, startkey_sayi_col = st.columns([3, 1])
        with startkey_btn_col:
            if st.button("Startkey İlanları", key="dp_startkey_btn", use_container_width=True):
                st.switch_page("pages/Danisman_StartkeyIlanlari.py")
        with startkey_sayi_col:
            startkey_bolge_sayisi = len(bolgelerini_cek("startkey_ilan_bolgeleri", su_kullanici))
            if startkey_bolge_sayisi:
                st.markdown(
                    f"<div class='dp-bolge-sayisi'>{startkey_bolge_sayisi} bölge</div>",
                    unsafe_allow_html=True,
                )
    with col_favori:
        if st.button("Favori Listem", key="dp_favori_btn"):
            st.switch_page("pages/Danisman_Favoriler.py")

    st.write("")

    # ── TELEFON BİLDİRİMLERİ — FAZ 1 (değişmedi; bkz. dosya başı notu). ──
    with st.expander("🔔 Telefon bildirimleri (deneme aşaması)", expanded=False):
        _abonelik_sayisi = len(abonelikleri_cek(su_kullanici))
        if _abonelik_sayisi:
            st.caption(f"✅ Zaten {_abonelik_sayisi} cihaz kayıtlı — her seferinde tekrar 'Bildirimleri Aç'a basmana gerek yok.")
        st.caption(
            "Yeni bir cihazdan/tarayıcıdan bildirim almak istersen: "
            "aşağıdaki düğmeye bas, yeni bir sekme açılır — orada "
            "'Bildirimleri Aç'a bas, tarayıcı izin isteyecek, izin ver. "
            "Sonra o sekmeyi kapatıp buraya dönebilirsin. (Bu, o cihaz "
            "için TEK SEFERLİK bir kurulum.)"
        )
        render_bildirim_izni_butonu(su_kullanici, key_prefix="dp_pb")
        _test_baslik = st.text_input(
            "Test bildirimi başlığı", value="Zeta Radar", key="dp_pb_test_baslik",
        )
        _test_govde = st.text_input(
            "Test bildirimi mesajı", value="Bildirimler çalışıyor! 🎉", key="dp_pb_test_govde",
        )
        if st.button("Kendime test bildirimi gönder", key="dp_pb_test"):
            try:
                sonuc = bildirim_gonder(
                    su_kullanici,
                    _test_baslik or "Zeta Radar",
                    _test_govde or "",
                )
                if sonuc["gonderildi"] and not sonuc["hata"] and not sonuc["silinen"]:
                    st.success(f"{sonuc['gonderildi']} cihaza gönderildi.")
                elif sonuc["gonderildi"]:
                    st.warning(
                        f"{sonuc['gonderildi']} cihaza gönderildi, "
                        f"{sonuc['hata']} cihazda hata oluştu, "
                        f"{sonuc['silinen']} kayıtlı abonelik süresi dolmuş görünüyor "
                        "(o cihazda tekrar 'Bildirimleri Aç'a basman gerekebilir)."
                    )
                elif sonuc["silinen"]:
                    st.warning("Kayıtlı abonelik süresi dolmuş görünüyor — yukarıdan tekrar 'Bildirimleri Aç'a bas.")
                elif sonuc["hata"]:
                    st.warning(f"{sonuc['hata']} cihazda gönderim hatası oluştu — birazdan tekrar dene.")
                else:
                    st.warning("Henüz kayıtlı bir bildirim aboneliğin yok — önce yukarıdan 'Bildirimleri Aç'a bas.")
                if sonuc.get("hata_detay"):
                    st.caption("Hata ayrıntısı (teşhis için):")
                    for _d in sonuc["hata_detay"]:
                        st.code(_d)
            except Exception as e:
                st.error(f"Gönderilemedi: {e}")

    render_activity_bar(startkey_yeni_sayisi=startkey_bugun_sayisi)
    render_bildirim_onizleme()

"""
pages/Danisman_Kayitlarim.py

Kendi Kayıtlarım ekranı — eski Danisman_Pano.py içindeki "Kayıtlarım"
expander'ının ayrı sayfaya çıkarılmış hali. Artık ana ekranda değil,
hamburger menüden erişiliyor (düşük frekanslı bir yönetim eylemi).

GÜVENLİK SINIRI (değişmedi): yalnız "kaynak" alanı Zeta değerlerinden
biri (Danışman Panosu'ndan girilmiş) VE "talep_eden_danisan" şu an
giriş yapmış kullanıcıyla eşleşen kayıtlar silinebilir. Startkey/mail
kaynaklı hiçbir kayıda bu ekrandan asla dokunulamaz.

YENİ (02.10.2026, Meltem: "kaydet butonu ile oluşan bilginin uygulamaya
kayıtlarım bölümüne düşmesini istiyorum") — dördüncü bir sekme eklendi:
"Yatırım Talepleri". Yatırım Alıcısı İhtiyaç Formu'nda (bkz. assets/
yatirim-formu.html) müşteri "Kaydet"e bastığında doğrudan Supabase'deki
musteri_talepleri tablosuna yazıyor; bu sekme o tabloyu su_anki_danisman()'a
göre filtreleyip (core.danisman_ortak.yatirim_taleplerini_cek) listeliyor.
"""

import streamlit as st
from html import escape as _esc
from datetime import datetime, timezone

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.danisman_ortak import (
    talepleri_cek, portfoyleri_cek, kaynak_filtrele, su_anki_danisman,
    su_anki_danisman_varyantlari, kendi_talepleri_cek, kendi_portfoylerini_cek,
    kayit_sil, sil_onayli, kayit_notunu_guncelle, render_topbar, hide_sidebar_css,
    ILAN_PORTAL_DEGERLERI, yatirim_taleplerini_cek,
)


def _yatirim_zaman_once(iso_str):
    """created_at (Supabase ISO 8601 timestamptz) → 'X gün önce' gibi okunaklı
    bir metin. pages/Danisman_Bildirimlerim.py'deki _zaman_once ile AYNI
    mantık — küçük/self-contained bir yardımcı olduğu için burada da ayrı
    tutuldu (bu kod tabanındaki yerleşik desen)."""
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

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Kendi Kayıtlarım", ikon="📂", geri_hedefi="pages/Danisman_Secim.py")

# KART GÖRÜNÜMÜ (bu tur revizyonu): önceki hâlde her kayıt çıplak bir
# st.columns satırıydı, hiçbir çerçeve/kart içinde değildi — "Sil" butonu
# görsel olarak kayıttan kopuk duruyordu. Şimdi her kayıt kendi bordered
# container'ında, diğer danışman ekranlarındaki (Talep/Portföy kartları)
# aynı görsel dille (beyaz kart, ince kenarlık) — Sil butonu artık aynı
# kartın içinde, kayıtla fiziksel olarak bütünleşik.
st.markdown("""
<style>
div[class*="st-key-dp_kayit_card_"] {
    padding: 14px 16px !important;
    margin-bottom: 10px !important;
}
div[class*="st-key-dp_kayit_sil_"] button,
div[class*="st-key-_sil_onay_"][class*="_ac"] button {
    border-color: #e3e1da !important;
    color: #b3261e !important;
    font-size: 12.5px !important;
}
/* Not kaydet butonu — Sil ile karışmasın diye nötr (kırmızı değil) */
div[class*="st-key-dp_not_kaydet_"] button {
    border-color: #e3e1da !important;
    color: #1b2540 !important;
    font-size: 12.5px !important;
}
/* YENİ (12.08.2026 — İlanlarım bölümü): "↗ İlana Git" linki — Portföy
   Panosu'ndaki kart içi linkle (pano_export.py .kart-ilan-link) aynı
   görsel dil, burada Streamlit-native markdown içinde. */
.dp-ilan-link {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 11.5px;
    font-weight: 700;
    color: #1b2540;
    background: #eef0f3;
    border: 1px solid #dde1e6;
    padding: 4px 11px;
    border-radius: 20px;
    text-decoration: none;
    margin-top: 6px;
}
</style>
""", unsafe_allow_html=True)

su_kullanici = su_anki_danisman()

# YENİ (12.08.2026 — İlanlarım / Kayıtlarım ayrımı):
#   "Zeta Portföylerim" → Revy'den senkronize, portallarda (sahibinden
#                  vb.) FİİLEN YAYINLANAN resmi ilanların — SALT OKUNUR
#                  (kaynağı Revy/portal, buradan silinmesi/düzenlenmesi
#                  anlamlı değil), sadece "↗ İlana Git" linkiyle referans.
#   "Taleplerim" / "Portföylerim" → Danışman Panosu'ndan elle girilmiş,
#                  ilan sitelerinde BULUNMAYAN kayıtlar (kaynak zeta/ofis).
#                  Silinebilir/notu düzenlenebilir — değişmedi.
# revy_sync.py artık üretime entegre — "Zeta Portföylerim" gerçek veriyle
# dolmaya başlamış olmalı.
#
# DÜZELTME (12.08.2026 — 2. tur): Üç bölüm artık ALT ALTA koşullu
# başlıklar yerine SEKME (st.tabs) olarak gösteriliyor — Favoriler ve
# Uzmanlık Bölgelerim'deki aynı desen, tutarlılık için.
# DÜZELTME (10.10.2026, "eski kayıtlarım silindi" şikâyeti): önceden
# burada talepleri_cek()/portfoyleri_cek() (TÜM danışmanların SON 60 GÜN
# kayıtları) çekilip içinden kişinin kayıtları süzülüyordu — yani 60
# günden eski her kayıt veritabanında dururken ekrandan kayboluyordu
# (Zeta Portföylerim'de de, çünkü Revy ilanlarının kayit_tarihi yalnız
# ilk eklemede yazılır). Artık kişinin kendi kayıtları tarih sınırı
# olmadan, sunucu tarafında süzülerek çekiliyor; ayrıca aynı kişinin
# e-posta/e-posta önü adıyla yazılmış eski kayıtları da dahil.
_adlar = tuple(su_anki_danisman_varyantlari() or [su_kullanici])
_tum_portfoyler = kendi_portfoylerini_cek(_adlar)
_tum_talepler = kendi_talepleri_cek(_adlar)
kendi_ilanlarim = [
    v for v in _tum_portfoyler
    if str(v.get("kaynak") or "").strip().lower() in ILAN_PORTAL_DEGERLERI
]
kendi_talepler = kaynak_filtrele(_tum_talepler, "Zeta")
kendi_portfoyler = [
    v for v in kaynak_filtrele(_tum_portfoyler, "Zeta")
    # "zeta1"/"zeta2" (resmi ilanlar) burada DEĞİL, "Zeta Portföylerim"
    # sekmesinde — ikisi birbirine karışmasın diye.
    and str(v.get("kaynak") or "").strip().lower() not in ILAN_PORTAL_DEGERLERI
]

# YENİ (02.10.2026, Meltem: "kaydet butonu ile oluşan bilginin uygulamaya
# kayıtlarım bölümüne düşmesini istiyorum") — Yatırım Alıcısı İhtiyaç
# Formu üzerinden (bkz. assets/yatirim-formu.html, pages/Yatirim_Formu.py)
# "Kaydet" butonuna basan müşterilerin talepleri, diğer üç sekmeyle AYNI
# ekranda, dördüncü bir sekme olarak. yatirim_taleplerini_cek() zaten
# su_anki_danisman()'a göre filtreli dönüyor — burada ayrıca filtrelemeye
# gerek yok (talep/portföy'den farkı: orada tek tablo HERKESİN kayıtlarını
# tutuyor ve burada elle filtreleniyor, musteri_talepleri'nde filtre zaten
# sorgu seviyesinde).
kendi_yatirim_talepleri = yatirim_taleplerini_cek(su_kullanici)

if not kendi_ilanlarim and not kendi_talepler and not kendi_portfoyler and not kendi_yatirim_talepleri:
    st.info("Henüz Danışman Panosu'ndan eklediğin bir kayıt yok.")
    st.stop()

sekme_ilan, sekme_talep, sekme_portfoy, sekme_yatirim = st.tabs([
    f"Zeta Portföylerim ({len(kendi_ilanlarim)})",
    f"Taleplerim ({len(kendi_talepler)})",
    f"Portföylerim ({len(kendi_portfoyler)})",
    f"Yatırım Talepleri ({len(kendi_yatirim_talepleri)})",
])

with sekme_ilan:
    if not kendi_ilanlarim:
        st.caption("Henüz Revy'den senkronize edilmiş bir ilanın yok.")
    else:
        st.caption("Portallarda (sahibinden vb.) yayınlanan aktif ilanların — salt okunur.")
        for v in kendi_ilanlarim:
            with st.container(border=True, key=f"dp_kayit_card_ilan_{v['id']}"):
                st.markdown(f"**İlan:** {v.get('ozet', '')}")
                ilan_linki = v.get("ilan_linki")
                if ilan_linki:
                    st.markdown(
                        f"<a class='dp-ilan-link' href='{_esc(ilan_linki)}' target='_blank' "
                        f"rel='noopener noreferrer'>↗ İlana Git</a>",
                        unsafe_allow_html=True,
                    )

# NOT ALANI (09.08.2026): Kayıt oluşturulurken girilen "Ek Not" daha önce
# sadece o an yazılabiliyordu, sonradan hiçbir yerden düzenlenemiyordu.
# Şimdi her kartın altında aynı alan (talep: ozel_kriterler, portföy:
# ozellikler) görünür ve düzenlenebilir — "Notu Kaydet" ile Supabase'e
# yazılır. Boş bırakılıp kaydedilirse not temizlenmiş olur (bilinçli;
# ayrı bir "notu sil" eylemi eklemeye gerek yok).

with sekme_talep:
    if not kendi_talepler:
        st.caption("Henüz Danışman Panosu'ndan eklediğin bir talep yok.")
    for v in kendi_talepler:
        with st.container(border=True, key=f"dp_kayit_card_talep_{v['id']}"):
            c1, c2 = st.columns([5, 1])
            with c1:
                kopru_etiket = " · 🔗 Köprü" if str(v.get("iliski_tipi") or "").lower() == "kopru" else ""
                st.markdown(f"**Talep:** {v.get('ozet', '')}{kopru_etiket}")
                # YENİ (13.08.2026): Müşteri adı/telefonu SADECE burada
                # (Kendi Kayıtlarım) görünür — pano_export.py'deki
                # paylaşılan kart şablonunda hiç yer almıyor.
                if v.get("musteri_adi") or v.get("musteri_telefon"):
                    st.caption(
                        f"👤 {v.get('musteri_adi') or '—'}"
                        + (f" · 📞 {v.get('musteri_telefon')}" if v.get("musteri_telefon") else "")
                    )
            with c2:
                if sil_onayli(f"kayit_talep_{v['id']}"):
                    kayit_sil("alici_talepleri", v["id"])
                    talepleri_cek.clear()
                    kendi_talepleri_cek.clear()
                    st.rerun()
            yeni_not = st.text_area(
                "Not", value=v.get("ozel_kriterler") or "",
                key=f"dp_not_talep_{v['id']}", height=68,
                label_visibility="collapsed",
                placeholder="Bu talep için not ekle (opsiyonel)...",
            )
            if st.button("Notu Kaydet", key=f"dp_not_kaydet_talep_{v['id']}"):
                kayit_notunu_guncelle("alici_talepleri", v["id"], "ozel_kriterler", yeni_not.strip())
                talepleri_cek.clear()
                kendi_talepleri_cek.clear()
                st.success("Not kaydedildi.")
                st.rerun()

with sekme_portfoy:
    if not kendi_portfoyler:
        st.caption("Henüz Danışman Panosu'ndan eklediğin bir portföy yok.")
    for v in kendi_portfoyler:
        with st.container(border=True, key=f"dp_kayit_card_portfoy_{v['id']}"):
            c1, c2 = st.columns([5, 1])
            with c1:
                kopru_etiket = " · 🔗 Köprü" if str(v.get("iliski_tipi") or "").lower() == "kopru" else ""
                st.markdown(f"**Portföy:** {v.get('ozet', '')}{kopru_etiket}")
                if v.get("musteri_adi") or v.get("musteri_telefon"):
                    st.caption(
                        f"👤 {v.get('musteri_adi') or '—'}"
                        + (f" · 📞 {v.get('musteri_telefon')}" if v.get("musteri_telefon") else "")
                    )
            with c2:
                if sil_onayli(f"kayit_portfoy_{v['id']}"):
                    kayit_sil("portfoyler", v["id"])
                    portfoyleri_cek.clear()
                    kendi_portfoylerini_cek.clear()
                    st.rerun()
            yeni_not = st.text_area(
                "Not", value=v.get("ozellikler") or "",
                key=f"dp_not_portfoy_{v['id']}", height=68,
                label_visibility="collapsed",
                placeholder="Bu portföy için not ekle (opsiyonel)...",
            )
            if st.button("Notu Kaydet", key=f"dp_not_kaydet_portfoy_{v['id']}"):
                kayit_notunu_guncelle("portfoyler", v["id"], "ozellikler", yeni_not.strip())
                portfoyleri_cek.clear()
                kendi_portfoylerini_cek.clear()
                st.success("Not kaydedildi.")
                st.rerun()

with sekme_yatirim:
    if not kendi_yatirim_talepleri:
        st.caption("Henüz Yatırım Alıcısı İhtiyaç Formu üzerinden eklenen bir talep yok.")
    for v in kendi_yatirim_talepleri:
        with st.container(border=True, key=f"dp_kayit_card_yatirim_{v['id']}"):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"**{_esc(v.get('musteri_adi') or 'İsimsiz')}** · {_esc(v.get('mulk_turu') or '—')}")
                alt_satir = []
                if v.get("telefon"):
                    alt_satir.append(f"📞 {v['telefon']}")
                if v.get("eposta"):
                    alt_satir.append(f"✉️ {v['eposta']}")
                bmin, bmax = v.get("butce_min"), v.get("butce_max")
                if bmin or bmax:
                    bmin_g = f"{int(bmin):,}".replace(",", ".") if bmin else "—"
                    bmax_g = f"{int(bmax):,}".replace(",", ".") if bmax else "—"
                    alt_satir.append(f"💰 {bmin_g} – {bmax_g} TL")
                if v.get("oncelikli_bolge"):
                    alt_satir.append(f"📍 {v['oncelikli_bolge']}")
                if alt_satir:
                    st.caption(" · ".join(alt_satir))
                st.caption(_yatirim_zaman_once(v.get("created_at")))
                # YENİ: danışmanın tek tıkla müşteriyi WhatsApp'tan
                # arayabilmesi için — Danisman_ZetaPortfoyleri.py'deki
                # "↗ İlana Git" linkiyle AYNI görsel dil (.dp-ilan-link).
                tel_rakam = "".join(ch for ch in str(v.get("telefon") or "") if ch.isdigit())
                if tel_rakam:
                    st.markdown(
                        f"<a class='dp-ilan-link' href='https://wa.me/{tel_rakam}' target='_blank' "
                        f"rel='noopener noreferrer'>↗ WhatsApp'ta Aç</a>",
                        unsafe_allow_html=True,
                    )
            with c2:
                if sil_onayli(f"kayit_yatirim_{v['id']}"):
                    kayit_sil("musteri_talepleri", v["id"])
                    yatirim_taleplerini_cek.clear()
                    st.rerun()
            # Formun TÜM cevapları — client-side buildRows() ile AYNI
            # Türkçe etiketlerle "detaylar.alanlar" içinde zaten hazır
            # geliyor (bkz. yatirim-formu.html:kaydet()); burada sadece
            # bir expander'da listeleniyor, ayrı bir render fonksiyonu
            # yazmaya gerek kalmadı.
            detaylar = v.get("detaylar") or {}
            alanlar = detaylar.get("alanlar") if isinstance(detaylar, dict) else None
            if alanlar:
                with st.expander("Tüm detaylar"):
                    for k, val in alanlar.items():
                        st.markdown(f"**{_esc(str(k))}:** {_esc(str(val)) if val else '—'}")

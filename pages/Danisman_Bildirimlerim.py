"""
pages/Danisman_Bildirimlerim.py

YENİ (26.09.2026, Meltem: "bu bildirimlerin danışman panodaki bildirim
sayfasında da gösterilmesini istiyorum. kişi kendisi de uygulamaya girip
son bildirimleri görmeli"): telefon push bildirimlerinin (core/push_
bildirim.py, core/bildirim_tetikleyici.py) kalıcı bir izini — push
kaçırılsa/izin verilmemiş olsa bile içeriden görülebilen bir "gelen
kutusu" ekranı. bildirim_gonder() artık HER çağrıldığında (push başarılı
olsun olmasın) core/push_bildirim.py'deki bildirim_gecmisi tablosuna bir
satır yazıyor — bu sayfa o tabloyu su_anki_danisman()'a göre filtreleyip
listeliyor.

Diğer Danışman ekranlarıyla AYNI iskelet: oturum_kontrol + hide_sidebar_css
+ render_topbar (geri butonu Danışman Panosu'na).
"""

import streamlit as st
from datetime import datetime, timezone

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.danisman_ortak import su_anki_danisman, render_topbar, hide_sidebar_css
from core.push_bildirim import bildirimlerimi_cek

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Bildirimlerim", ikon="🔔", geri_hedefi="pages/Danisman_Secim.py")


def _zaman_once(iso_str):
    """created_at (Supabase'den ISO 8601 timestamptz) → 'X dakika/saat/gün
    önce' gibi okunaklı bir metin. Ayrıştırma başarısız olursa (beklenmez
    ama best-effort) ham değeri olduğu gibi döner."""
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


su_kullanici = su_anki_danisman()
bildirimler = bildirimlerimi_cek(su_kullanici, limit=30)

if not bildirimler:
    st.info("Henüz bir bildirimin yok — yeni bir talep/portföy paylaşıldığında ya da sana özel bir bildirim gönderildiğinde burada görünecek.")
    st.stop()

for b in bildirimler:
    with st.container(border=True, key=f"bildirim_{b.get('id')}"):
        ust_col, zaman_col = st.columns([5, 2])
        with ust_col:
            st.markdown(f"**{b.get('baslik') or ''}**")
        with zaman_col:
            st.caption(_zaman_once(b.get("created_at")))
        if b.get("govde"):
            st.write(b["govde"])
        if b.get("url"):
            st.link_button("Görüntüle →", b["url"], use_container_width=True)

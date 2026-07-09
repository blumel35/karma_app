import streamlit as st
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from core.ui_helpers import render_navbar, render_page_header
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.mail_job import run_mail_fetch_job, run_pending_ai_parse_job

render_navbar(
    user_role=st.session_state.get("user_role", "danisan"),
    user_name=st.session_state.get("user_name", ""),
    user_initials=st.session_state.get("user_initials", ""),
)
st.title("Mail İşlem")

st.caption(
    "Not: Bu ekran manuel çalıştırma içindir. Aynı işlemler artık GitHub Actions "
    "üzerinden otomatik olarak da periyodik çalışıyor (bkz. scripts/mail_auto_job.py)."
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Mailleri Çek")
    st.caption("INBOX ve 1_Alici_Depo klasörlerinden, son başarılı çekimden bu yana gelen mailleri çeker")

    if st.button("Mailleri Çek", use_container_width=True, type="primary"):
        durum = st.status("Mailler çekiliyor...", expanded=True)

        try:
            def guncelle(mesaj):
                durum.write(mesaj)

            sonuc = run_mail_fetch_job(durum_callback=guncelle)

            if sonuc["yeni_kayit"] == 0 and sonuc["hata_sayisi"] == 0:
                durum.update(label="Yeni mail bulunamadı", state="complete")
                st.info("Yeni mail yok.")
            else:
                durum.update(
                    label=f"✅ {sonuc['yeni_kayit']} yeni mail kaydedildi!",
                    state="complete" if sonuc["hata_sayisi"] == 0 else "error",
                )
                st.success(f"✅ {sonuc['yeni_kayit']} yeni mail kaydedildi!")

                with st.expander("Çekim özeti", expanded=sonuc["hata_sayisi"] > 0):
                    st.markdown(f"""
- **Bulunan mail:** {sonuc['bulunan']}
- **Yeni kaydedilen:** {sonuc['yeni_kayit']}
- **Hata sayısı:** {sonuc['hata_sayisi']}
- **Süre:** {sonuc['sure_saniye']} sn
""")
                    for klasor, k_ozet in sonuc.get("ozet_klasor", {}).items():
                        st.write(f"- `{klasor}`: {k_ozet['bulunan']} mail, {k_ozet['hata']} hata")

                    if sonuc["hata_sayisi"] > 0:
                        st.warning("Bazı mailler okunamadı, detaylar:")
                        for h in sonuc["hata_log"][:20]:
                            st.write(f"- [{h.get('klasor')}] uid={h.get('uid')}: {h.get('hata')}")

        except Exception as e:
            durum.update(label="❌ Hata oluştu", state="error")
            st.error(f"Hata: {type(e).__name__}: {e}")
            import traceback
            st.code(traceback.format_exc())

with col2:
    st.subheader("2. AI ile Kategorize Et")
    st.caption("Mailleri Claude AI ile analiz eder — alıcı talebi mi, portföy paylaşımı mı ayırır")

    islenecek_limit = st.number_input(
        "Bu çalıştırmada en fazla kaç kayıt işlensin?",
        min_value=10, max_value=200, value=100, step=10,
    )

    if st.button("AI ile Kategorize Et", use_container_width=True, type="primary"):
        durum2 = st.status("Mailler işleniyor...", expanded=True)

        try:
            def guncelle2(mesaj):
                durum2.write(mesaj)

            sonuc = run_pending_ai_parse_job(limit=int(islenecek_limit), durum_callback=guncelle2)

            if sonuc["islenen"] == 0:
                durum2.update(label="İşlenecek yeni kayıt yok", state="complete")
                st.info("Tüm kayıtlar zaten işlenmiş.")
            else:
                durum2.update(
                    label=f"✅ {sonuc['alici']} alıcı/diğer, {sonuc['portfoy']} portföy işlendi!",
                    state="complete" if sonuc["hatali"] == 0 else "error",
                )
                st.success(
                    f"✅ {sonuc['alici']} alıcı talebi/diğer, {sonuc['portfoy']} portföy paylaşımı ayrıştırıldı!"
                )

                kalan = sonuc.get("kalan", 0)
                if kalan > 0:
                    st.info(f"📋 Hâlâ **{kalan}** kayıt işlenmeyi bekliyor. Devam etmek için butona tekrar bas.")
                else:
                    st.success("🎉 Bekleyen kayıt kalmadı, hepsi işlendi!")

                with st.expander("AI işleme özeti", expanded=sonuc["hatali"] > 0):
                    st.markdown(f"""
- **İşlenen kayıt:** {sonuc['islenen']}
- **Alıcı talebi / diğer:** {sonuc['alici']}
- **Portföy paylaşımı:** {sonuc['portfoy']}
- **Hatalı (parse_status='failed'):** {sonuc['hatali']}
- **Kalan (parse_status='raw'):** {kalan}
- **Süre:** {sonuc['sure_saniye']} sn
""")
                    if sonuc["hatali"] > 0:
                        st.warning(
                            "Hatalı kayıtlar silinmedi, `alici_talepleri` tablosunda "
                            "`parse_status='failed'` olarak işaretlendi — `parse_error` "
                            "kolonundan sebebini görebilirsin."
                        )

        except Exception as e:
            durum2.update(label="❌ Hata oluştu", state="error")
            st.error(f"Hata: {type(e).__name__}: {e}")
            import traceback
            st.code(traceback.format_exc())

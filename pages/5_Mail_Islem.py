import streamlit as st
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from core.ui_helpers import render_navbar, render_page_header
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.mail_fetcher import mailleri_cek
from core.mail_parser import mailleri_isle
from core.supabase_client import get_client

render_navbar(
    user_role=st.session_state.get("user_role", "danisan"),
    user_name=st.session_state.get("user_name", ""),
    user_initials=st.session_state.get("user_initials", ""),
)
st.title("Mail İşlem")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Mailleri Çek")
    st.caption("INBOX ve 1_Alici_Depo klasörlerinden mailleri çeker")

    if st.button("Mailleri Çek", use_container_width=True, type="primary"):
        durum = st.status("Mailler çekiliyor...", expanded=True)

        try:
            def guncelle(mesaj):
                durum.write(mesaj)

            veriler = mailleri_cek(durum_callback=guncelle)

            if not veriler:
                durum.update(label="Yeni mail bulunamadı", state="complete")
                st.info("Yeni mail yok.")
            else:
                supabase = get_client()

                mevcut_alici = supabase.table("alici_talepleri").select("message_id").execute()
                mevcut_portfoy = supabase.table("portfoyler").select("message_id").execute()

                mevcut_idler = set(
                    [r["message_id"] for r in mevcut_alici.data if r["message_id"]] +
                    [r["message_id"] for r in mevcut_portfoy.data if r["message_id"]]
                )

                yeni_veriler = [v for v in veriler if v.get("message_id") not in mevcut_idler]
                durum.write(f"{len(yeni_veriler)} yeni mail Supabase'e kaydediliyor...")

                kayit_sayisi = 0
                for kayit in yeni_veriler:
                    try:
                        supabase.table("alici_talepleri").insert(kayit).execute()
                        kayit_sayisi += 1
                    except Exception as e:
                        continue

                durum.update(label=f"✅ {kayit_sayisi} yeni mail kaydedildi!", state="complete")
                st.success(f"✅ {kayit_sayisi} yeni mail kaydedildi!")

        except Exception as e:
            durum.update(label="❌ Hata oluştu", state="error")
            st.error(f"Hata: {type(e).__name__}: {e}")
            import traceback
            st.code(traceback.format_exc())

with col2:
    st.subheader("2. AI ile Kategorize Et")
    st.caption("Mailleri Claude AI ile analiz eder — alıcı talebi mi, portföy paylaşımı mı ayırır")

    if st.button("AI ile Kategorize Et", use_container_width=True, type="primary"):
        durum2 = st.status("Mailler işleniyor...", expanded=True)

        try:
            supabase = get_client()

            response = supabase.table("alici_talepleri")\
                .select("*")\
                .eq("bolge_mahalle", "")\
                .limit(100)\
                .execute()
            kayitlar = response.data

            if not kayitlar:
                durum2.update(label="İşlenecek yeni kayıt yok", state="complete")
                st.info("Tüm kayıtlar zaten işlenmiş.")
            else:
                durum2.write(f"{len(kayitlar)} kayıt işlenecek...")

                def guncelle2(mesaj):
                    durum2.write(mesaj)

                alici_sonuclar, portfoy_sonuclar = mailleri_isle(
                    kayitlar, durum_callback=guncelle2
                )

                for kayit in alici_sonuclar:
                    supabase.table("alici_talepleri").update({
                        "kategori": kayit.get("kategori", "diger"),
                        "ozet": kayit.get("ozet", ""),
                        "islem_tipi": kayit.get("islem_tipi", ""),
                        "mulk_tipi": kayit.get("mulk_tipi", ""),
                        "il": kayit.get("il", ""),
                        "ilce": kayit.get("ilce", ""),
                        "ilceler": kayit.get("ilceler", []),
                        "bolge_mahalle": kayit.get("bolge_mahalle", "diger"),
                        "oda_sayisi_m2": kayit.get("oda_sayisi_m2", ""),
                        "max_butce": kayit.get("max_butce", ""),
                        "ozel_kriterler": kayit.get("ozel_kriterler", ""),
                        "iletisim_not": kayit.get("iletisim_not", "")
                    }).eq("id", kayit["id"]).execute()

                portfoy_sayisi = 0
                for portfoy in portfoy_sonuclar:
                    try:
                        supabase.table("portfoyler").insert(portfoy).execute()
                        supabase.table("alici_talepleri")\
                            .delete()\
                            .eq("message_id", portfoy["message_id"])\
                            .execute()
                        portfoy_sayisi += 1
                    except Exception as e:
                        st.warning(f"Portföy eklenemedi: {e}")
                        continue

                durum2.update(
                    label=f"✅ {len(alici_sonuclar)} alıcı, {portfoy_sayisi} portföy işlendi!",
                    state="complete"
                )
                st.success(f"✅ {len(alici_sonuclar)} alıcı talebi, {portfoy_sayisi} portföy paylaşımı ayrıştırıldı!")

        except Exception as e:
            durum2.update(label="❌ Hata oluştu", state="error")
            st.error(f"Hata: {type(e).__name__}: {e}")
            import traceback
            st.code(traceback.format_exc())
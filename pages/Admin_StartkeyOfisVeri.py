"""
pages/Admin_StartkeyOfisVeri.py

Startkey ofis verisi — yönetici sayfası (07.10.2026). Meltem: "ofis yönetimi
için bir Startkey ofisleri analizi... revy excel tablosundaki tümü işime
yarayabilir... bu veriyi eksiksiz doğru çekebilmek."

Veriyi GitHub Actions'taki "Startkey Ofis Verisi Çekimi" işi (startkey_ofis_job.py)
Supabase'e yazar; bu sayfa durumu gösterir, tutarlılık kontrollerini
çalıştırır ve veriyi Excel olarak indirtir. Danışman panosuyla ilgisi yoktur.

ERİŞİM: yalnızca "Meltem Bulu" adlı hesap. Hamburger menüde yalnızca onda görünür.

ÖNEMLİ: app.py'de hem st.Page olarak tanımlanması hem de st.navigation()
listesine eklenmesi gerekir — aksi halde "Could not find page" hatası verir.
"""

import streamlit as st

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime
from core.auth import oturum_kontrol
from core.danisman_ortak import render_topbar, hide_sidebar_css
from core.supabase_client import get_client
from core import startkey_ofis_veri as V

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Startkey Ofis Verisi", ikon="📊", geri_hedefi="pages/Danisman_Secim.py")

# ── ERİŞİM KAPISI ────────────────────────────────────────────────────
_YONETICI_ISIMLERI = {"meltem bulu"}
_kullanici_sozlugu = st.session_state.get("kullanici", {}) or {}
_oturum_adi = str(
    st.session_state.get("user_name")
    or _kullanici_sozlugu.get("ad_soyad")
    or _kullanici_sozlugu.get("ad")
    or ""
).strip().lower()
if _oturum_adi not in _YONETICI_ISIMLERI:
    st.error("Bu sayfa yalnızca yönetici içindir.")
    st.stop()

supa = get_client()

st.caption(
    "Kapsam: İzmir'in 30 ilçesi · konut + ticari + arsa · satılık + kiralık · "
    "Revy'de ofis adında “Startkey” geçen ilanlar · ilan tarihi 01.01.2025 ve sonrası · "
    "aktif + yayından kalkmış."
)

# ── DURUM ÖZETİ ──────────────────────────────────────────────────────
c1, c2 = st.columns([5, 1])
with c2:
    if st.button("↻ Yenile", use_container_width=True, key="sov_yenile"):
        for k in ("sov_ozet", "sov_excel", "sov_ilce", "sov_capraz"):
            st.session_state.pop(k, None)

if "sov_ozet" not in st.session_state:
    try:
        with st.spinner("Durum okunuyor..."):
            st.session_state["sov_ozet"] = V.ozet(supa)
    except Exception:
        st.error(
            "Startkey ofis tabloları okunamadı. Tablolar henüz oluşturulmamış olabilir: "
            "`startkey_ofis_veri_migration.sql` dosyasını Supabase > SQL Editor'da bir kez çalıştırın."
        )
        st.stop()
oz = st.session_state["sov_ozet"]

if not oz["log"]:
    st.info(
        "Henüz hiç çekim yapılmamış. GitHub > Actions > “Startkey Ofis Verisi Çekimi” > "
        "Run workflow. İlk seferde “sadece_sinama” kutusunu işaretleyip çalıştırın."
    )
    st.stop()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Toplam ilan", f"{oz['toplam']:,}".replace(",", "."))
m2.metric("Aktif", f"{oz['aktif']:,}".replace(",", "."))
m3.metric("Yayından kalkmış", f"{oz['pasif']:,}".replace(",", "."))
m4.metric("Tamamlanan çekim", f"{oz['kombinasyon_tamam']} / {oz['kombinasyon_beklenen']}")

son = (oz["son_zaman"] or "")[:19].replace("T", " ")
sin = oz["son_sinama"]
sin_txt = ""
if sin:
    sin_txt = " · son sınama: " + ("başarılı ✅" if sin.get("sonuc") == "tamam" else "BAŞARISIZ ❌")
st.caption(f"Son kayıt: {son} (UTC){sin_txt}")

# ── EKSİKSİZLİK DURUMU ───────────────────────────────────────────────
tam = (
    oz["kombinasyon_tamam"] == oz["kombinasyon_beklenen"]
    and not oz["kombinasyon_eksik"]
)
if tam and not oz["tek_gun_limit"]:
    st.success("Tüm 360 kombinasyon eksiksiz tamamlandı.")
else:
    if oz["kombinasyon_tamam"] < oz["kombinasyon_beklenen"]:
        st.warning(
            f"Çekim henüz tamamlanmadı: {oz['kombinasyon_tamam']} / {oz['kombinasyon_beklenen']} "
            "kombinasyon bitti. GitHub'da işi tekrar çalıştırın — kaldığı yerden devam eder."
        )
    if oz["kombinasyon_eksik"]:
        st.error(f"{len(oz['kombinasyon_eksik'])} kombinasyon EKSİK kaldı (yeniden çalıştırınca tekrar denenir).")
        st.dataframe(
            [{"Durum": r.get("durum"), "İlçe": r.get("ilce"), "Mülk": r.get("mulk"),
              "İşlem": r.get("islem"), "Neden": str((r.get("detay") or {}).get("hatalar", ""))[:160]}
             for r in oz["kombinasyon_eksik"]],
            use_container_width=True, hide_index=True,
        )
    if oz["tek_gun_limit"]:
        st.error(
            f"{len(oz['tek_gun_limit'])} kombinasyonda tek bir günde bile Revy'nin 1000 satır "
            "sınırına çarpıldı; o günlerin ilanları KESİLMİŞ olabilir."
        )
        st.dataframe(
            [{"Durum": r.get("durum"), "İlçe": r.get("ilce"), "Mülk": r.get("mulk"),
              "İşlem": r.get("islem"),
              "Günler": ", ".join((r.get("detay") or {}).get("tek_gun_limit_gunleri", []))}
             for r in oz["tek_gun_limit"]],
            use_container_width=True, hide_index=True,
        )

if oz["belirsiz_bos"]:
    st.warning(
        f"{len(oz['belirsiz_bos'])} kombinasyonda Revy standart dışı bir 'boş' yanıt verdi "
        "(sonuç yok sayıldı). Çekim Raporu sayfasında ve log tablosunda örnek yanıtı görebilirsiniz."
    )
if oz["gevsek"]:
    st.info(
        f"{oz['gevsek']} ilanın ofis adı yalnızca gevşek eşleşti (ör. “START KEY”). "
        "Excel'de “Ofis Eşleşme” sütunu = gevsek; analizden önce gözden geçirin."
    )
if oz["url_yok"]:
    st.warning(f"{oz['url_yok']} satırda ilan linki yoktu ve kaydedilemedi.")

st.divider()

# ── KONTROLLER ───────────────────────────────────────────────────────
st.subheader("Kontroller")
k1, k2 = st.columns(2)
with k1:
    if st.button("İlçe dağılımını göster", use_container_width=True, key="sov_ilce_btn"):
        with st.spinner("İlanlar okunuyor..."):
            st.session_state["sov_ilce"] = V.ilce_durum_tablosu(supa)
with k2:
    if st.button("Günlük sync ile çapraz kontrol", use_container_width=True, key="sov_capraz_btn"):
        with st.spinner("İki kaynak karşılaştırılıyor..."):
            st.session_state["sov_capraz"] = V.capraz_kontrol(supa)

if "sov_ilce" in st.session_state:
    st.markdown("**İlçe dağılımı**")
    st.dataframe(st.session_state["sov_ilce"], use_container_width=True, hide_index=True)

if "sov_capraz" in st.session_state:
    st.markdown("**Çapraz kontrol — aktif Startkey ilanları (ilan tarihi ≥ 2025)**")
    st.caption(
        "Yeni tablo ile günlük sync'in (izmir_pazar_ilanlar) aktif Startkey sayıları aynı şeyi "
        "farklı yollarla sayar. Büyük fark = bir tarafta eksik var. Küçük farklar normaldir "
        "(çekimler farklı zamanlarda yapılır; günlük sync'te yalnız seçili ilçeler vardı)."
    )
    st.dataframe(st.session_state["sov_capraz"], use_container_width=True, hide_index=True)

st.divider()

# ── EXCEL ────────────────────────────────────────────────────────────
st.subheader("Excel")
st.caption(
    "Sayfalar: Açıklama · İlanlar (Revy'nin tüm sütunları + 5 sistem sütunu) · Ofis Özeti · Çekim Raporu."
)
if st.button("Excel'i hazırla", type="primary", use_container_width=True, key="sov_excel_btn"):
    ilerleme = st.progress(0, text="İlanlar okunuyor...")
    try:
        beklenen = max(oz["toplam"], 1)
        satirlar = V.tum_ilanlar(
            supa, ilerleme=lambda n: ilerleme.progress(min(n / beklenen, 1.0), text=f"{n:,} ilan okundu"),
        )
        ilerleme.progress(1.0, text="Excel oluşturuluyor...")
        veri = V.excel_uret(satirlar, oz["son_kombinasyonlar"])
        st.session_state["sov_excel"] = (veri, datetime.now().strftime("%Y%m%d_%H%M"), len(satirlar))
    except Exception:
        st.error("Excel hazırlanamadı. Sayfayı yenileyip tekrar deneyin.")
    finally:
        ilerleme.empty()

if "sov_excel" in st.session_state:
    veri, zaman, n = st.session_state["sov_excel"]
    st.success(f"Hazır: {n:,} ilan.".replace(",", "."))
    st.download_button(
        "⬇️ Excel'i indir",
        data=veri,
        file_name=f"startkey_ofis_ilanlari_{zaman}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="sov_excel_indir",
    )

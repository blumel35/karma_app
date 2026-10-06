"""
pages/Danisman_AdminBolgeler.py

Yönetici bölge sayfası (06.10.2026) — Meltem: "bana bir admin sayfası ekleyelim,
ben orada her danışman için onlara sorarak en fazla 5 adet olacak şekilde
FSBO / Startkey ve Uzmanlık Bölgelerim için bölgelerini kaydedeyim."

Yönetici seçtiği danışman ADINA üç bölge türünü (FSBO, Startkey, Uzmanlık)
kaydeder: en fazla 5 ilçe; FSBO ve Startkey'de ilçe başına isteğe bağlı
mahalle daraltması ve bildirim açık/kapalı. Mantık core/admin_bolge.py'de.

ERİŞİM: yalnızca "Meltem Bulu" adlı hesap (paylaşım bloğundaki test
kapısıyla aynı kural). Hiçbir menüde linklenmiyor — doğrudan adresle açılır:
/Danisman_AdminBolgeler

KANONİK AD: kayıtlar zeta_personel_listesi.xlsx'teki ad_soyad ile yazılır
(uygulamanın oturumda kullandığı adla aynı).

ÖNEMLİ: app.py'de hem st.Page olarak tanımlanması hem de st.navigation()
listesine eklenmesi gerekir — aksi halde "Could not find page" hatası verir.
"""

import streamlit as st

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.danisman_ortak import (
    IZMIR_ILCELERI, render_topbar, hide_sidebar_css,
)
from core.personel_manager import load_personel_listesi
from core.bolge_secici import ilcenin_mahalleleri
from core.admin_bolge import (
    BOLGE_TURLERI, MAX_BOLGE, bolgeleri_cek, tum_bolgeleri_cek, cihaz_sayilari,
    bolgeleri_kaydet, ilce_bildirim_ayarla, ilce_mahallelerini_ayarla,
)

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Danışman Bölgeleri", ikon="🗂️", geri_hedefi="pages/Danisman_Secim.py")

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

# Pilot grup (06.10.2026) — listenin başında gösterilir.
PILOT_ISIMLERI = [
    "Ahmet Koç", "Sinan Yücesoy", "Ömer Bayraktar",
    "Turgay Özdemir", "Mustafa Balcı", "Erhan Yaşar",
]

# Kayıt/güncelleme sonrası st.rerun() mesajı kaybettirdiği için bir sonraki
# çalıştırmada gösterilmek üzere oturumda bekletilir.
_mesaj = st.session_state.pop("ab_mesaj", None)
if _mesaj:
    st.success(_mesaj)

# ── PERSONEL LİSTESİ ─────────────────────────────────────────────────
ustte, yenile_col = st.columns([5, 1])
with yenile_col:
    if st.button("↻ Listeyi yenile", key="ab_liste_yenile"):
        load_personel_listesi(force_reload=True)
        st.rerun()

_df = load_personel_listesi()
if _df is None or _df.empty or "ad_soyad" not in _df.columns:
    st.error("Personel listesi okunamadı (zeta_personel_listesi.xlsx).")
    st.stop()

_tum_kisiler = [
    {k: ("" if v is None or str(v) == "nan" else str(v)) for k, v in satir.items()}
    for satir in _df.to_dict("records")
    if str(satir.get("ad_soyad") or "").strip()
]


def _sirala(kisiler):
    pilot = [k for ad in PILOT_ISIMLERI for k in kisiler if k["ad_soyad"] == ad]
    diger = sorted(
        (k for k in kisiler if k["ad_soyad"] not in PILOT_ISIMLERI),
        key=lambda k: k["ad_soyad"],
    )
    return pilot + diger


with ustte:
    sadece_pilot = st.toggle("Sadece pilot grup", value=True, key="ab_sadece_pilot")

kisiler = _sirala(
    [k for k in _tum_kisiler if (not sadece_pilot) or k["ad_soyad"] in PILOT_ISIMLERI]
)
if not kisiler:
    st.warning("Listede gösterilecek danışman yok.")
    st.stop()

eksik_pilot = [ad for ad in PILOT_ISIMLERI if ad not in {k["ad_soyad"] for k in _tum_kisiler}]
if eksik_pilot:
    st.warning(
        "Pilot gruptan personel listesinde bulunmayanlar: " + ", ".join(eksik_pilot)
    )

# ── GENEL DURUM TABLOSU ──────────────────────────────────────────────
_veri = {tur: tum_bolgeleri_cek(tur) for tur in BOLGE_TURLERI}
_cihaz = cihaz_sayilari()


def _ilce_ozeti(satirlar, mahalle_var):
    parcalar = []
    for r in sorted(satirlar, key=lambda x: x.get("ilce") or ""):
        metin = r.get("ilce") or ""
        if mahalle_var and (r.get("mahalleler") or []):
            metin += f" ({len(r['mahalleler'])} mah.)"
        if r.get("bildirim_acik") is False:
            metin += " 🔕"
        parcalar.append(metin)
    return ", ".join(parcalar) if parcalar else "—"


with st.expander("Genel durum", expanded=True):
    tablo_satirlari = []
    for k in kisiler:
        ad = k["ad_soyad"]
        satir = {"Danışman": ad, "Ofis": k.get("ofis_adi", "")}
        for tur, cfg in BOLGE_TURLERI.items():
            satir[cfg["etiket"]] = _ilce_ozeti(_veri[tur].get(ad, []), cfg["mahalle"])
        satir["Bildirim cihazı"] = _cihaz.get(ad, 0)
        satir["Telefon"] = "var" if k.get("telefon", "").strip() else "yok"
        tablo_satirlari.append(satir)
    st.dataframe(tablo_satirlari, hide_index=True, use_container_width=True)
    st.caption("🔕 = bu ilçe için bildirim kapalı.")

# ── DANIŞMAN SEÇİMİ ──────────────────────────────────────────────────
secili = st.selectbox(
    "Danışman",
    kisiler,
    format_func=lambda k: f"{k['ad_soyad']} — {k.get('ofis_adi', '')}",
    key="ab_secili_kisi",
)
ad = secili["ad_soyad"]

bilgi = []
if secili.get("rol"):
    bilgi.append(f"rol: {secili['rol']}")
if secili.get("telefon", "").strip():
    bilgi.append(f"telefon: {secili['telefon']}")
bilgi.append(f"bildirim cihazı: {_cihaz.get(ad, 0)}")
st.caption(" · ".join(bilgi))

# Aynı kişinin e-posta önekiyle (ör. "turgay.ozdemir") açılmış eski kayıtları
# varsa uyar — bildirimler isim eşleşmesiyle çalıştığı için bunlar kaybolur.
_alias = (secili.get("email") or "").split("@")[0].strip()
if _alias and _alias.lower() != ad.lower():
    _alias_bulunan = []
    for tur, cfg in BOLGE_TURLERI.items():
        if bolgeleri_cek(tur, _alias):
            _alias_bulunan.append(cfg["etiket"])
    if _cihaz.get(_alias):
        _alias_bulunan.append("bildirim cihazı")
    if _alias_bulunan:
        st.warning(
            f"'{_alias}' adıyla da kayıt var ({', '.join(_alias_bulunan)}). "
            f"Bu kayıtlar '{ad}' ile eşleşmez; birleştirilmesi gerekir."
        )


def _tur_sekmesi(tur):
    cfg = BOLGE_TURLERI[tur]
    kayitlar = bolgeleri_cek(tur, ad)
    mevcut = [r["ilce"] for r in kayitlar]

    secim = st.multiselect(
        f"{cfg['etiket']} ilçeleri (en fazla {MAX_BOLGE})",
        options=IZMIR_ILCELERI,
        default=mevcut,
        max_selections=MAX_BOLGE,
        key=f"ab_{tur}_ilce_{ad}",
        placeholder=f"İlçe seç (en fazla {MAX_BOLGE})...",
    )
    if st.button("Kaydet", key=f"ab_{tur}_kaydet_{ad}", type="primary"):
        try:
            bolgeleri_kaydet(tur, ad, secim)
            st.session_state["ab_mesaj"] = f"{ad}: {cfg['etiket']} bölgeleri kaydedildi."
            st.rerun()
        except Exception as e:
            st.error(f"Kaydedilemedi: {e}")

    if not kayitlar:
        st.info("Bu danışman için henüz kayıtlı ilçe yok.")
        return

    st.markdown("**İlçe bazlı ayarlar**")
    for r in kayitlar:
        ilce = r["ilce"]
        if cfg["mahalle"]:
            c1, c2 = st.columns([1, 3])
        else:
            c1, c2 = st.container(), None
        with c1:
            onceki_bildirim = r.get("bildirim_acik", True) is not False
            yeni_bildirim = st.toggle(
                f"{ilce} — bildirim", value=onceki_bildirim,
                key=f"ab_{tur}_bildirim_{ad}_{ilce}",
            )
            if yeni_bildirim != onceki_bildirim:
                try:
                    ilce_bildirim_ayarla(tur, ad, ilce, yeni_bildirim)
                    st.rerun()
                except Exception as e:
                    st.error(f"Kaydedilemedi: {e}")
        if c2 is not None:
            with c2:
                onceki_mahalle = list(r.get("mahalleler") or [])
                secenekler = sorted(
                    set(ilcenin_mahalleleri(ilce, cfg["marka"])) | set(onceki_mahalle)
                )
                if not secenekler:
                    st.caption(f"{ilce}: bu ilçede henüz mahalle verisi yok.")
                    continue
                yeni_mahalle = st.multiselect(
                    f"{ilce} — mahalle", options=secenekler, default=onceki_mahalle,
                    key=f"ab_{tur}_mahalle_{ad}_{ilce}",
                    placeholder="Tüm mahalleler (daraltma yok)",
                )
                if set(yeni_mahalle) != set(onceki_mahalle):
                    try:
                        ilce_mahallelerini_ayarla(tur, ad, ilce, yeni_mahalle)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Kaydedilemedi: {e}")


sekmeler = st.tabs([cfg["etiket"] for cfg in BOLGE_TURLERI.values()])
for sekme, tur in zip(sekmeler, BOLGE_TURLERI):
    with sekme:
        _tur_sekmesi(tur)

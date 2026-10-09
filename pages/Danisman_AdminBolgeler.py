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
    sifre_belirle, giris_hesaplari, eslestirme_kodu_uret,
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


_TR_ALFABE = "abcçdefgğhıijklmnoöprsştuüvyz"


def _tr_anahtar(metin):
    """Türkçe alfabe sırası (ı/i, ö, ş, ü... doğru yerde)."""
    kucuk = str(metin).replace("İ", "i").replace("I", "ı").lower()
    return [_TR_ALFABE.find(ch) if ch in _TR_ALFABE else 100 + ord(ch) for ch in kucuk]


def _sirala(kisiler):
    pilot = [k for ad in PILOT_ISIMLERI for k in kisiler if k["ad_soyad"] == ad]
    diger = sorted(
        (k for k in kisiler if k["ad_soyad"] not in PILOT_ISIMLERI),
        key=lambda k: _tr_anahtar(k["ad_soyad"]),
    )
    return pilot + diger


def _zeta1_gd_mi(k):
    ofis = (k.get("ofis_id", "") or k.get("ofis_adi", "")).replace(" ", "").lower()
    return k.get("rol", "").strip().lower() == "gd" and ofis == "zeta1"


LISTE_SECENEKLERI = ["Zeta 1 GD'leri", "Pilot grup", "Tüm personel"]
with ustte:
    liste_secimi = st.radio(
        "Liste", LISTE_SECENEKLERI, horizontal=True, key="ab_liste",
        label_visibility="collapsed",
    )

if liste_secimi == "Zeta 1 GD'leri":
    _secilenler = [k for k in _tum_kisiler if _zeta1_gd_mi(k)]
elif liste_secimi == "Pilot grup":
    _secilenler = [k for k in _tum_kisiler if k["ad_soyad"] in PILOT_ISIMLERI]
else:
    _secilenler = _tum_kisiler
kisiler = _sirala(_secilenler)
if not kisiler:
    st.warning("Listede gösterilecek danışman yok.")
    st.stop()

eksik_pilot = [ad for ad in PILOT_ISIMLERI if ad not in {k["ad_soyad"] for k in _tum_kisiler}]
if eksik_pilot and liste_secimi == "Pilot grup":
    st.warning(
        "Pilot gruptan personel listesinde bulunmayanlar: " + ", ".join(eksik_pilot)
    )

# ── GENEL DURUM TABLOSU ──────────────────────────────────────────────
_veri = {tur: tum_bolgeleri_cek(tur) for tur in BOLGE_TURLERI}
_cihaz = cihaz_sayilari()
_hesaplar = giris_hesaplari()


def _hesap_durumu(k):
    """'var · son giriş 30.09' / 'var · hiç girmemiş' / 'yok' / '?'"""
    if _hesaplar is None:
        return "?"
    e = (k.get("email") or "").strip().lower()
    if e not in _hesaplar:
        return "yok"
    son = _hesaplar[e]
    if not son:
        return "var · hiç girmemiş"
    try:
        return f"var · son giriş {son.strftime('%d.%m')}"
    except AttributeError:
        return f"var · son giriş {str(son)[8:10]}.{str(son)[5:7]}"


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
        satir["Uygulama hesabı"] = _hesap_durumu(k)
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
bilgi.append(f"hesap: {_hesap_durumu(secili)}")
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

# ── iPHONE BİLDİRİM EŞLEŞTİRME KODU ──────────────────────────────────
# YENİ (09.10.2026). iPhone'da bildirim izni yalnızca ana ekrana eklenmiş
# uygulamadan verilebilir ve Karma App'ten açılan bağlantıdaki token o
# uygulamaya taşınamaz. Çözüm: yönetici 6 haneli kod üretir, danışman
# ana ekrandaki "SZ Bildirim" uygulamasına yazar; abonelik bu danışman
# adına kaydolur. Kod 10 dk geçerli ve tek kullanımlıktır.
with st.expander("iPhone bildirim eşleştirme kodu", expanded=(_cihaz.get(ad, 0) == 0)):
    st.caption(
        "Danışman iPhone'unda bildirim açamıyorsa: aşağıdan kod üret, danışmana ilet. "
        "Danışman önce "
        "https://blumel35.github.io/zeta-bildirim adresini Safari'de açıp "
        "Paylaş > Ana Ekrana Ekle yapar, sonra ana ekrandaki 'SZ Bildirim' "
        "simgesinden uygulamayı açıp kodu yazar ve izin verir."
    )
    _kod_anahtar = f"ab_eslestirme_{ad}"
    if st.button("Kod üret", key=f"ab_kod_btn_{ad}"):
        try:
            _kod, _son = eslestirme_kodu_uret(ad)
            st.session_state[_kod_anahtar] = (_kod, _son)
        except Exception as e:
            st.session_state.pop(_kod_anahtar, None)
            st.error(f"Kod üretilemedi: {e}")
    if st.session_state.get(_kod_anahtar):
        _kod, _son = st.session_state[_kod_anahtar]
        st.code(_kod, language=None)
        st.caption(
            f"{ad} için kod. 10 dakika geçerli, tek kullanımlık. "
            "Kullanıldıktan sonra bu sayfayı yenileyince 'Bildirim cihazı' 1 olmalı."
        )

# ── GİRİŞ ŞİFRESİ BELİRLE ────────────────────────────────────────────
# YENİ (06.10.2026, Meltem: "şifre değiştirmek isteyen bana müracaat etsin").
# Danışman panosunda "şifremi unuttum" / şifre değiştirme ekranı YOK; bu
# yüzden yönetici, seçili danışmanın giriş şifresini buradan belirler.
# Şifre kaydedilmez/gösterilmez, yalnızca Supabase Auth'a gönderilir.
with st.expander("Giriş şifresi belirle", expanded=False):
    _hesap_email = (secili.get("email") or "").strip()
    if not _hesap_email:
        st.warning("Bu danışmanın personel listesinde e-posta adresi yok.")
    else:
        st.caption(
            f"Hesap: {_hesap_email}. Belirlediğin şifreyi danışmana sen iletirsin; "
            "danışmanın kendi başına değiştireceği bir ekran şu an yok."
        )
        with st.form(f"ab_sifre_form_{ad}", clear_on_submit=True):
            _sifre1 = st.text_input("Yeni şifre (en az 8 karakter)", type="password")
            _sifre2 = st.text_input("Yeni şifre (tekrar)", type="password")
            _gonder = st.form_submit_button("Şifreyi belirle", type="primary")
        if _gonder:
            if _sifre1 != _sifre2:
                st.error("Şifreler aynı değil.")
            else:
                try:
                    sifre_belirle(_hesap_email, _sifre1)
                    st.success(f"{ad} için giriş şifresi belirlendi.")
                except Exception as e:
                    st.error(f"Şifre belirlenemedi: {e}")

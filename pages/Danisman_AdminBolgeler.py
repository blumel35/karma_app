"""
pages/Danisman_AdminBolgeler.py

BÖLGE HAVUZU (09.10.2026): üçüncü görünüm — ilçeye düşen tüm kayıtlar
(Startkey ilanı, alıcı talebi, paylaşım, Zeta portföyü, yatırım talebi...)
tek akışta; salt-okunur, bildirim GÖNDERMEZ (alıcı simülasyonu). Veri
katmanı core/bolge_havuzu.py. Dış besleme kanalı: musteri_talepleri.

GÖRÜNÜM (09.10.2026): iki görünüm — "Bölgeye göre" (ilçe -> mahalle kapsamı,
kim takip ediyor) ve "Danışmana göre" (eski akış). İkisinde de danışman
düzenleme/hesap işlemleri aynı danisman_paneli() içinde.

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
from core import bolge_havuzu as bh
from core.admin_bolge import (
    BOLGE_TURLERI, MAX_BOLGE, bolgeleri_cek, tum_bolgeleri_cek, cihaz_sayilari,
    bolgeleri_kaydet, ilce_bildirim_ayarla, ilce_mahallelerini_ayarla,
    sifre_belirle, giris_hesaplari, eslestirme_kodu_uret,
    alias_birlestirme_plani, alias_birlestir,
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
mod = st.radio(
    "Görünüm", ["Havuz", "Bölgeye göre", "Danışmana göre"], horizontal=True, key="ab_mod",
)
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
if mod == "Danışmana göre":
    with ustte:
        liste_secimi = st.radio(
            "Liste", LISTE_SECENEKLERI, horizontal=True, key="ab_liste",
            label_visibility="collapsed",
        )
else:
    liste_secimi = "Tüm personel"

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


with st.expander("Genel durum", expanded=(mod == "Danışmana göre")):
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

def danisman_paneli(secili):
    """Seçili danışmanın bilgi satırı, eski-ad uyarısı/birleştirme, bölge
    sekmeleri ve hesap işlemleri. İki görünümde de aynı panel kullanılır."""
    ad = secili["ad_soyad"]
    st.markdown(f"#### {ad}")

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
            # YENİ (09.10.2026): önizleme + onaylı birleştirme.
            try:
                _plan = alias_birlestirme_plani(_alias, ad)
            except Exception as e:
                _plan = None
                st.error(f"Birleştirme planı çıkarılamadı: {e}")
            if _plan:
                _satirlar = []
                for _tur, _cfg in BOLGE_TURLERI.items():
                    _p = _plan[_tur]
                    if not (_p["tasi"] or _p["zaten_var"] or _p["sigmayan"]):
                        continue
                    _parca = []
                    if _p["tasi"]:
                        _parca.append("taşınacak: " + ", ".join(_p["tasi"]))
                    if _p["zaten_var"]:
                        _parca.append(f"'{ad}' altında zaten var (eski kayıt silinecek): " + ", ".join(_p["zaten_var"]))
                    if _p["sigmayan"]:
                        _parca.append(f"en fazla {MAX_BOLGE} ilçe sınırına sığmıyor (olduğu yerde kalır): " + ", ".join(_p["sigmayan"]))
                    _satirlar.append(f"- **{_cfg['etiket']}** — " + "; ".join(_parca))
                if _plan.get("cihaz"):
                    _satirlar.append(f"- **Bildirim cihazı**: {_plan['cihaz']} cihaz '{ad}' adına taşınacak")
                st.markdown("\n".join(_satirlar))
                if st.button(f"'{_alias}' kayıtlarını '{ad}' ile birleştir", key=f"ab_birlestir_{ad}"):
                    try:
                        alias_birlestir(_alias, ad)
                        st.success("Birleştirildi. Sayfayı yenileyip uyarının kaybolduğunu kontrol et.")
                    except Exception as e:
                        st.error(f"Birleştirilemedi: {e}")


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

    # ── HESAP İŞLEMLERİ (iPhone kodu + şifre) — tek küçük alan ───────────
    # iPhone'da bildirim izni yalnızca ana ekrana eklenmiş uygulamadan verilebilir
    # ve Karma App'ten açılan bağlantıdaki token o uygulamaya taşınamaz. Çözüm:
    # yönetici 6 haneli kod üretir, danışman ana ekrandaki "SZ Bildirim"
    # uygulamasına yazar; abonelik bu danışman adına kaydolur (10 dk, tek kullanımlık).
    # Şifre: danışman panosunda "şifremi unuttum" yok; yönetici belirler,
    # şifre kaydedilmez/gösterilmez, yalnızca Supabase Auth'a gönderilir.
    with st.expander(
        "Hesap işlemleri — iPhone bildirim kodu · giriş şifresi",
        expanded=(_cihaz.get(ad, 0) == 0),
    ):
        sek_kod, sek_sifre = st.tabs(["iPhone bildirim kodu", "Giriş şifresi"])
        with sek_kod:
            st.caption(
                "Danışman iPhone'unda bildirim açamıyorsa: kod üret, danışmana ilet. "
                "Danışman önce https://blumel35.github.io/zeta-bildirim adresini Safari'de "
                "açıp Paylaş > Ana Ekrana Ekle yapar, sonra ana ekrandaki 'SZ Bildirim' "
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
                    "Kullanıldıktan sonra sayfayı yenileyince 'Bildirim cihazı' 1 olmalı."
                )
        with sek_sifre:
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



# ══ BÖLGEYE GÖRE GÖRÜNÜM ═════════════════════════════════════════════
import html as _html


def _takipci_kayitlari():
    """Tüm bölge kayıtları, kişiye çözümlenmiş düz liste. Kayıt adı kanonik
    ad_soyad ise doğrudan, e-posta önü ('ahmet.koc') ise o kişiye ama
    eski=True ile; hiçbirine uymazsa kisi=None (listede yok)."""
    ana = {k["ad_soyad"].strip().casefold(): k for k in _tum_kisiler}
    alias = {}
    for k in _tum_kisiler:
        a = (k.get("email") or "").split("@")[0].strip().casefold()
        if a and a not in ana:
            alias[a] = k
    sonuc = []
    for tur, cfg in BOLGE_TURLERI.items():
        for kayit_adi, satirlar in _veri[tur].items():
            anahtar = kayit_adi.strip().casefold()
            kisi, eski = ana.get(anahtar), False
            if kisi is None and anahtar in alias:
                kisi, eski = alias[anahtar], True
            gorunen = kisi["ad_soyad"] if kisi else kayit_adi
            for r in satirlar:
                sonuc.append({
                    "ad": gorunen, "kisi": kisi, "eski": eski, "tur": tur,
                    "ilce": r.get("ilce") or "",
                    "mahalleler": list(r.get("mahalleler") or []) if cfg["mahalle"] else [],
                    "bildirim": r.get("bildirim_acik") is not False,
                })
    return sonuc


def _kapsamdakiler(kayitlar, ilce, mahalle):
    """İlçe (mahalle=None) ya da mahalle kapsamındaki takipçi kayıtları;
    her birine 'kapsam' etiketi eklenir. Boş mahalle listesi = tüm ilçe."""
    sonuc = []
    for t in kayitlar:
        if t["ilce"] != ilce:
            continue
        if t["tur"] == "uzmanlik":
            sonuc.append({**t, "kapsam": "ilçe uzmanı"})
        elif mahalle is None:
            kapsam = "tüm ilçe" if not t["mahalleler"] else f"{len(t['mahalleler'])} mahalle"
            sonuc.append({**t, "kapsam": kapsam})
        elif not t["mahalleler"]:
            sonuc.append({**t, "kapsam": "tüm ilçe (filtresiz)"})
        elif mahalle in t["mahalleler"]:
            sonuc.append({**t, "kapsam": "bu mahalle (özel)"})
    return sonuc


def bolge_gorunumu():
    kayitlar = _takipci_kayitlari()

    # Kapsam özeti: takip edilen ilçeler, en yoğundan en aza
    def _say(ilce, tur):
        return len({t["ad"] for t in kayitlar if t["ilce"] == ilce and t["tur"] == tur})

    def _toplam(ilce):
        return len({t["ad"] for t in kayitlar if t["ilce"] == ilce})

    ozet = [
        {
            "İlçe": i,
            "Toplam danışman": _toplam(i),
            **{cfg["etiket"]: _say(i, tur) for tur, cfg in BOLGE_TURLERI.items()},
        }
        for i in IZMIR_ILCELERI
    ]
    takip_edilen = sorted(
        (o for o in ozet if o["Toplam danışman"] > 0),
        key=lambda o: (-o["Toplam danışman"], _tr_anahtar(o["İlçe"])),
    )
    kimsenin_olmayan = [o["İlçe"] for o in ozet if o["Toplam danışman"] == 0]
    en_kalabalik = (
        IZMIR_ILCELERI.index(takip_edilen[0]["İlçe"]) if takip_edilen else 0
    )
    st.markdown("**Takip edilen ilçeler (yoğundan aza)**")
    if takip_edilen:
        st.dataframe(takip_edilen, hide_index=True, use_container_width=True)
    else:
        st.info("Henüz hiçbir ilçe takip edilmiyor.")
    if kimsenin_olmayan:
        st.caption("Kimsenin takip etmediği ilçeler: " + ", ".join(kimsenin_olmayan))

    ilce = st.selectbox(
        "İlçe", IZMIR_ILCELERI, index=en_kalabalik, key="ab_bolge_ilce",
    )

    # Mahalle listesi: canlı ilan verisi + takipçilerin seçtikleri
    mahalleler = set()
    for tur, cfg in BOLGE_TURLERI.items():
        if cfg["mahalle"]:
            mahalleler |= set(ilcenin_mahalleleri(ilce, cfg["marka"]))
    for t in kayitlar:
        if t["ilce"] == ilce:
            mahalleler |= set(t["mahalleler"])
    mahalleler = sorted(mahalleler, key=_tr_anahtar)

    secenekler = ["(Tüm ilçe)"] + mahalleler
    mah_secim = st.selectbox("Mahalle", secenekler, key=f"ab_bolge_mahalle_{ilce}")
    mahalle = None if mah_secim == "(Tüm ilçe)" else mah_secim

    kapsam = _kapsamdakiler(kayitlar, ilce, mahalle)
    uzmanlar = sorted({t["ad"] for t in kapsam if t["tur"] == "uzmanlik"}, key=_tr_anahtar)

    # Koyu bölge kartı + rozetler
    def _rozet(metin, renk):
        return (
            f"<span style='display:inline-block;margin:6px 6px 0 0;padding:3px 10px;"
            f"border-radius:6px;font-size:12px;font-weight:600;{renk}'>{_html.escape(metin)}</span>"
        )

    sayilar = {
        tur: len({t["ad"] for t in kapsam if t["tur"] == tur}) for tur in BOLGE_TURLERI
    }
    kapali = len({t["ad"] for t in kapsam if not t["bildirim"]})
    baslik = ilce if mahalle is None else f"{ilce} / {mahalle}"
    uzman_metin = ", ".join(uzmanlar) if uzmanlar else "kimse seçmemiş"
    rozetler = (
        _rozet(f"FSBO {sayilar['fsbo']}", "background:#e0f2fe;color:#0369a1;")
        + _rozet(f"Startkey {sayilar['startkey']}", "background:#e0e7ff;color:#4338ca;")
        + _rozet(f"Uzmanlık {sayilar['uzmanlik']}", "background:#ede9fe;color:#6d28d9;")
        + (_rozet(f"{kapali} danışmanda bildirim kapalı", "background:#fef3c7;color:#92400e;") if kapali else "")
    )
    st.markdown(
        f"<div style='background:#1C2B47;color:#fff;border-radius:14px;padding:16px 18px;margin:8px 0'>"
        f"<div style='font-size:20px;font-weight:700'>{_html.escape(baslik)}</div>"
        f"<div style='font-size:12px;opacity:.75;margin-top:4px'>Bölge uzmanı: {_html.escape(uzman_metin)}</div>"
        f"<div>{rozetler}</div></div>",
        unsafe_allow_html=True,
    )

    # İlçe görünümünde: filtresiz özet + yalnızca ÖZEL seçilen mahalleler
    if mahalle is None:
        filtresiz = {"fsbo": set(), "startkey": set()}
        ozel_mahalle = {}   # mahalle -> {tur: set(ad)}
        for t in kayitlar:
            if t["ilce"] != ilce or t["tur"] == "uzmanlik":
                continue
            if not t["mahalleler"]:
                filtresiz[t["tur"]].add(t["ad"])
            for m in t["mahalleler"]:
                ozel_mahalle.setdefault(m, {"fsbo": set(), "startkey": set()})[t["tur"]].add(t["ad"])

        def _adlar(kume):
            return ", ".join(sorted(kume, key=_tr_anahtar)) or "—"

        st.caption(
            "Tüm ilçeyi alanlar (mahalle filtresi boş) — "
            f"FSBO: {_adlar(filtresiz['fsbo'])} · Startkey: {_adlar(filtresiz['startkey'])}"
        )
        if ozel_mahalle:
            st.markdown("**Seçili mahalleler**")
            st.dataframe(
                [
                    {
                        "Mahalle": m,
                        "FSBO (özel seçen)": _adlar(v["fsbo"]),
                        "Startkey (özel seçen)": _adlar(v["startkey"]),
                        "Özel seçen sayısı": len(v["fsbo"] | v["startkey"]),
                    }
                    for m, v in sorted(
                        ozel_mahalle.items(),
                        key=lambda x: (-len(x[1]["fsbo"] | x[1]["startkey"]), _tr_anahtar(x[0])),
                    )
                ],
                hide_index=True, use_container_width=True,
            )
        else:
            st.caption("Bu ilçede mahalle filtresi kullanan danışman yok.")

    # Takipçi listesi (danışman bazında toplanmış)
    gruplar = {}
    for t in kapsam:
        g = gruplar.setdefault(t["ad"], {"kisi": t["kisi"], "kayit": []})
        g["kayit"].append(t)
    if not gruplar:
        st.info("Bu kapsamda takip eden danışman yok.")
        return
    tablo = []
    for ad_, g in sorted(gruplar.items(), key=lambda x: _tr_anahtar(x[0])):
        parca = [f"{BOLGE_TURLERI[t['tur']]['etiket']}: {t['kapsam']}" for t in g["kayit"]]
        acik = [t["bildirim"] for t in g["kayit"]]
        notlar = []
        if any(t["eski"] for t in g["kayit"]):
            notlar.append("eski adla kayıt var")
        if g["kisi"] is None:
            notlar.append("personel listesinde yok")
        tablo.append({
            "Danışman": ad_,
            "Ofis": (g["kisi"] or {}).get("ofis_adi", "") or "?",
            "Takip": " · ".join(parca),
            "Bildirim": "açık" if all(acik) else ("kapalı 🔕" if not any(acik) else "kısmen"),
            "Cihaz": _cihaz.get(ad_, 0),
            "Not": ", ".join(notlar),
        })
    st.markdown("**Bu kapsamı takip edenler**")
    st.dataframe(tablo, hide_index=True, use_container_width=True)

    acilabilir = [ad_ for ad_, g in gruplar.items() if g["kisi"] is not None]
    acilabilir.sort(key=_tr_anahtar)
    sec = st.selectbox(
        "Danışmanı aç (bölge, hesap, şifre, kod)", ["—"] + acilabilir, key="ab_bolge_ac",
    )
    if sec != "—":
        with st.container(border=True):
            danisman_paneli(gruplar[sec]["kisi"])



# ══ BÖLGE HAVUZU GÖRÜNÜMÜ ════════════════════════════════════════════
_RENKLER = {
    "indigo": ("#e0e7ff", "#4338ca"), "violet": ("#ede9fe", "#6d28d9"),
    "orange": ("#ffedd5", "#c2410c"), "sky": ("#e0f2fe", "#0369a1"),
    "teal": ("#ccfbf1", "#0f766e"), "amber": ("#fef3c7", "#92400e"),
    "rose": ("#ffe4e6", "#be123c"), "slate": ("#e2e8f0", "#334155"),
}


@st.cache_data(ttl=120, show_spinner="Havuz yükleniyor...")
def _havuz_yukle(gun, ilceler):
    return bh.havuzu_yukle(gun, list(ilceler))


def havuz_gorunumu():
    tanimlar = bh.sekme_tanimlari()
    kayitlar = _takipci_kayitlari()

    c1, c2, c3 = st.columns([3, 3, 1])
    with c2:
        donem = st.selectbox("Dönem", list(bh.DONEMLER), index=1, key="bh_donem")
    with c3:
        st.write("")
        if st.button("↻ Yenile", key="bh_yenile"):
            _havuz_yukle.clear()
            st.rerun()
    havuz, hatalar = _havuz_yukle(bh.DONEMLER[donem], tuple(IZMIR_ILCELERI))
    for kaynak, msj in hatalar.items():
        st.warning(f"{kaynak} okunamadı, havuza dahil edilmedi: {msj}")

    sayilar = bh.ilce_sayilari(havuz)
    belirsiz_var = bh.ILCE_BELIRSIZ in sayilar
    secenekler = ["(Tüm ilçeler)"] + list(IZMIR_ILCELERI) + ([bh.ILCE_BELIRSIZ] if belirsiz_var else [])
    en_yogun = max(
        (i for i in sayilar if i in IZMIR_ILCELERI),
        key=lambda i: sum(sayilar[i].values()), default=None,
    )
    with c1:
        ilce_secim = st.selectbox(
            "İlçe", secenekler, key="bh_ilce",
            index=secenekler.index(en_yogun) if en_yogun else 0,
        )
    ilce = None if ilce_secim == "(Tüm ilçeler)" else ilce_secim
    liste = bh.ilceye_gore(havuz, ilce)

    # Başlık kartı
    def _chip(metin, renk):
        bg, fg = _RENKLER.get(renk, _RENKLER["slate"])
        return (
            f"<span style='display:inline-block;margin:6px 6px 0 0;padding:3px 10px;"
            f"border-radius:6px;font-size:12px;font-weight:600;background:{bg};color:{fg};'>"
            f"{_html.escape(metin)}</span>"
        )

    if ilce and ilce != bh.ILCE_BELIRSIZ:
        uz = sorted({t["ad"] for t in kayitlar if t["ilce"] == ilce and t["tur"] == "uzmanlik"}, key=_tr_anahtar)
        takipci = len({t["ad"] for t in kayitlar if t["ilce"] == ilce})
        alt = f"Bölge uzmanı: {', '.join(uz) if uz else 'kimse seçmemiş'} · Bu ilçeyi takip eden: {takipci} danışman"
    elif ilce:
        alt = "Hiçbir ilçeyle eşleşmeyen form kayıtları — bölge metni ilçe adı içermiyor."
    else:
        alt = "Tüm İzmir — ilçe seçerek daralt."
    chipler = "".join(_chip(f"{ad} {len(liste.get(k, []))}", renk) for k, ad, _k, renk in tanimlar)
    st.markdown(
        f"<div style='background:#1C2B47;color:#fff;border-radius:14px;padding:16px 18px;margin:8px 0'>"
        f"<div style='font-size:20px;font-weight:700'>{_html.escape(ilce_secim.strip('()') if ilce is None else ilce)}"
        f"<span style='font-size:12px;font-weight:500;opacity:.7;margin-left:10px'>{_html.escape(donem.lower())}</span></div>"
        f"<div style='font-size:12px;opacity:.75;margin-top:4px'>{_html.escape(alt)}</div>"
        f"<div>{chipler}</div></div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Salt-okunur simülasyon: bu ekran bildirim göndermez, hiçbir şeyi değiştirmez. "
        "Şimdilik bağlı olmayan dış kanallar: satıcı / ev sahibi / kiracı formları "
        "(bağlandıklarında kendi sekmeleriyle buraya düşer)."
    )

    # Tüm ilçeler: ilçe x tür özet tablosu
    if ilce is None and sayilar:
        satirlar = []
        for i, v in sayilar.items():
            satirlar.append({
                "İlçe": i,
                **{ad: v.get(k, 0) for k, ad, _kisa, _r in tanimlar},
                "Toplam": sum(v.values()),
            })
        satirlar.sort(key=lambda r: (-r["Toplam"], _tr_anahtar(r["İlçe"])))
        with st.expander(f"İlçelere göre dağılım ({len(satirlar)} ilçe)", expanded=False):
            st.dataframe(satirlar, hide_index=True, use_container_width=True)

    sekmeler = st.tabs([f"{ad} ({len(liste.get(k, []))})" for k, ad, _kisa, _r in tanimlar])
    for sekme, (k, ad, _kisa, renk) in zip(sekmeler, tanimlar):
        with sekme:
            _havuz_sekmesi(k, ad, renk, liste.get(k, []), ilce, kayitlar, donem)


def _havuz_sekmesi(tur, ad, renk, kayit_listesi, ilce, takipci_kayitlari, donem):
    if not kayit_listesi:
        st.info(f"{donem.lower()} içinde bu kapsamda {ad.lower()} kaydı yok.")
        return
    simdi = bh.datetime.now(bh.timezone.utc)
    tablo = [
        {
            "": "🆕" if k["yeni"] else "",
            "Kayıt": k["baslik"],
            "Ayrıntı": k["alt"],
            "Kaynak": k.get("kaynak") or "",
            "Sahibi": k["sahip"] or "—",
            "İlçe": ", ".join(i for i in k["ilceler"] if i) or "—",
            "Zaman": bh.zaman_etiketi(k["zaman"], simdi),
        }
        for k in kayit_listesi
    ]
    olay = st.dataframe(
        tablo, hide_index=True, use_container_width=True, height=min(420, 38 + 35 * len(tablo)),
        on_select="rerun", selection_mode="single-row",
        key=f"bh_df_{tur}_{ilce}_{donem}",
    )
    secili = list(olay.selection.rows) if olay and olay.selection else []
    if not secili:
        st.caption("Ayrıntı ve bildirim simülasyonu için bir satır seç.")
        return
    k = kayit_listesi[secili[0]]
    kart, bildirim = st.columns([3, 2])
    with kart:
        with st.container(border=True):
            st.markdown(f"**{_html.escape(k['baslik'])}**", unsafe_allow_html=True)
            for etiket, deger in k["alanlar"]:
                if deger:
                    st.markdown(f"<span style='color:#64748b;font-size:12px'>{_html.escape(str(etiket))}</span><br>"
                                f"{_html.escape(str(deger))}", unsafe_allow_html=True)
            if k.get("link"):
                st.link_button("İlana git ↗", k["link"])
    with bildirim:
        with st.container(border=True):
            hedef_ilce = ilce if ilce and ilce != bh.ILCE_BELIRSIZ else (
                next((i for i in k["ilceler"] if i), None))
            st.markdown("**🔔 Bildirim simülasyonu**")
            st.caption("Gönderilmedi — bugün bu kayıt için ne olurdu:")
            st.markdown(f"> {_html.escape(bh.mesaj_onizleme(tur, k))}", unsafe_allow_html=True)
            if not hedef_ilce:
                st.warning("İlçe belirsiz — bölgeye göre alıcı çıkarılamıyor.")
            else:
                alicilar = bh.alicilar(tur, k, takipci_kayitlari, hedef_ilce)
                if not alicilar:
                    st.warning(f"{hedef_ilce} için bu kayda bildirim alacak danışman yok "
                               "(uzman/takipçi seçilmemiş).")
                for a in alicilar:
                    cihaz = _cihaz.get(a["ad"], 0)
                    durum = "" if a["bildirim"] else " 🔕 kapalı"
                    cihaz_n = "" if cihaz else " · cihaz yok"
                    st.markdown(f"- **{_html.escape(a['ad'])}** — {_html.escape(', '.join(a['nedenler']))}{durum}{cihaz_n}")
            if k.get("sahip"):
                st.caption(f"Kayıt sahibi ({k['sahip']}) bildirim almaz.")


# ══ AKIŞ ═════════════════════════════════════════════════════════════
if mod == "Havuz":
    havuz_gorunumu()
elif mod == "Bölgeye göre":
    bolge_gorunumu()
else:
    secili = st.selectbox(
        "Danışman",
        kisiler,
        format_func=lambda k: f"{k['ad_soyad']} — {k.get('ofis_adi', '')}",
        key="ab_secili_kisi",
    )
    danisman_paneli(secili)

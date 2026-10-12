"""
pages/Danisman_Bolgem.py  —  "Radarım" (eski adı Bölgem)

Danışmanın tek bakışta tüm kayıtlarını gördüğü genel panel (12.10.2026, Meltem kararları):
  - Kendi alıcı talepleri / portföyleri / yatırım talepleri: HER ilçeden, dönem süzgeci olmadan.
  - Ekip kayıtları (alıcı talebi, paylaşım, Zeta, Startkey, FSBO): Uzmanlık Bölgelerim'deki en fazla 5 ilçe
    + kendi kayıtlarının bulunduğu ilçeler.
SALT OKUNUR; eşleşme/puanlama bilinçli olarak kapsam dışı. Bölge seçimi ve bildirim ayarları eski sayfalarda
(Uzmanlık Bölgelerim, FSBO İlanları, Startkey İlanları) aynen duruyor.

Düzen: üstte ilçe özet tablosu (bir bakışta), altında ilçe seçici, altında sıralı sekmeler:
Alıcı taleplerim · Portföylerim · Alıcı talebi · Paylaşım · Zeta portföyü · Startkey ilanı · FSBO ilanı ·
Yatırım talebim.

GİZLİLİK: Yatırım talepleri (müşteri adı/telefon içerir) yalnız ilgili danışmanın ekranında görünür;
musteri_talepleri sorgusu danışmana göre SUNUCU tarafında süzülür, başkasının kaydı hiç okunmaz.
"""
import html as _html

import streamlit as st

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.danisman_ortak import (
    su_anki_danisman, su_anki_danisman_varyantlari, render_topbar, hide_sidebar_css, IZMIR_ILCELERI,
)
from core.bolge_secici import bolgelerini_cek
from core import bolge_havuzu as bh
from core import bolgem as bg
from core.havuz_tablo_bilesen import havuz_tablosu

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Radarım", ikon="📡", geri_hedefi="pages/Danisman_Secim.py")

MAX_BOLGE = 5
BOLGE_TABLOLARI = ("uzmanlik_bolgeleri", "fsbo_bolgeleri", "startkey_ilan_bolgeleri")
@st.cache_data(ttl=120, show_spinner="Ekip verisi yükleniyor...")
def _ortak(gun):
    return bg.ortak_yukle(gun)


@st.cache_data(ttl=60, show_spinner="Kayıtların yükleniyor...")
def _kendi(adlar):
    return bg.kendi_yukle(list(adlar))


@st.cache_data(ttl=300, show_spinner="İlçelerindeki ilanlar yükleniyor...")
def _pazar(gun, ilceler):
    return bg.pazar_yukle(gun, list(ilceler))


@st.cache_data(ttl=60, show_spinner="Yatırım talepleri yükleniyor...")
def _yatirim(adlar):
    return bg.yatirim_yukle(list(adlar), list(IZMIR_ILCELERI))


def _bolgelerim(kullanici):
    """Danışmanın seçtiği EN FAZLA 5 bölge (ilçe). Asıl kaynak Uzmanlık Bölgelerim; orada hiç seçim yoksa
    (12.10.2026: "her danışman yalnız seçtiği max 5 bölgeyi görsün") FSBO, sonra Startkey listesindeki
    ilçelerden ilk 5'i alınır."""
    hatalar = []
    for tablo in BOLGE_TABLOLARI:           # Uzmanlık önce
        sonuc, gorulen = [], set()
        try:
            for r in bolgelerini_cek(tablo, kullanici):
                i = (r.get("ilce") or "").strip()
                if i and bh.tr_kucuk(i) not in gorulen:
                    gorulen.add(bh.tr_kucuk(i))
                    sonuc.append(i)
        except Exception as e:      # noqa: BLE001
            hatalar.append(f"{tablo}: {e}")
        if sonuc:
            return sonuc[:MAX_BOLGE], hatalar
    return [], hatalar


_KISA_SEKME = {"taleplerim": "Taleplerim", "portfoylerim": "Portföylerim", "talep": "Ekip talebi", "paylasim": "Paylaşım",
               "zeta": "Zeta", "startkey": "Startkey", "fsbo": "FSBO", "yatirim": "Yatırım"}

_OZET_GRUPLAR = (
    ("Benim kayıtlarım", "g1", (("taleplerim", "Talep"), ("portfoylerim", "Portföy"), ("yatirim", "Yatırım"))),
    ("Ekip (ilçelerimdeki)", "g2", (("talep", "Talep"), ("paylasim", "Paylaşım"), ("zeta", "Zeta"),
                                    ("startkey", "Startkey"), ("fsbo", "FSBO"))),
)


def _ozet_tablosu(sayilar, dis, ilceler, donem, ek=()):
    """Bir bakışta özet: tek tablo, çubuklu sayılar. 👤 = benim kayıtlarım, 👥 = ekip.
    "Benim kayıtlarım" sütunları Excel'deki gibi gizlenebilir."""
    satirlar = [(i, sayilar[i]) for i in ilceler]
    satirlar.sort(key=lambda x: (-x[1]["talep"], -x[1]["zeta"], bg.tr_sira(x[0])))
    ben_kol = [(k, f"👤 {a_}") for k, a_ in _OZET_GRUPLAR[0][2]]
    ekip_kol = [(k, f"👥 {a_}") for k, a_ in _OZET_GRUPLAR[1][2]]

    with st.expander(f"İlçe özeti · {donem.lower()} · {len(ilceler)} ilçe", expanded=True):
        ben_goster = st.toggle("👤 Benim kayıtlarım", value=True, key="bg_ozet_ben")
        kolonlar = (ben_kol if ben_goster else []) + ekip_kol
        veri = []
        for i, v in satirlar:
            veri.append({"İlçe": f"{i} ◦" if i in ek else i,
                         **{ad: int(v.get(k, 0) or 0) for k, ad in ben_kol + ekip_kol}})
        if any(dis.values()):
            veri.append({"İlçe": bg.BOLGE_DISI,
                         **{ad: int(dis.get(k, 0) or 0) for k, ad in ben_kol},
                         **{ad: 0 for _k, ad in ekip_kol}})
        cfg = {}
        for k, ad in ben_kol + ekip_kol:
            tavan = max([r[ad] for r in veri] + [1])
            cfg[ad] = st.column_config.ProgressColumn(ad, format="%d", min_value=0, max_value=tavan, width="small")
        try:
            cfg["İlçe"] = st.column_config.TextColumn("İlçe", pinned=True, width="small")
        except TypeError:
            pass
        st.dataframe(veri, hide_index=True, use_container_width=True, column_config=cfg,
                     column_order=["İlçe"] + [ad for _k, ad in kolonlar],
                     height=min(38 + 35 * len(veri), 420))
        st.caption("👤 benim kayıtlarım (her ilçeden, dönemden bağımsız) · 👥 ekip kayıtları (ilçelerimdeki, seçili dönem)."
                   + (" ◦ Uzmanlık bölgen değil; kendi kaydın olduğu için eklendi." if ek else ""))


def _sekme(tur, ad, kayitlar, secim, donem):
    if not kayitlar:
        st.info("Bu kapsamda kayıt yok.")
        return
    simdi = bh.datetime.now(bh.timezone.utc)
    kolonlar = [
        {"k": "Kayıt", "label": "Kayıt", "w": 230},
        {"k": "İlan", "label": "İlan", "w": 70, "link": True},
        {"k": "İşlem", "label": "İşlem", "w": 90},
        {"k": "Yaş / Kat", "label": "Yaş / Kat", "w": 130},
        {"k": "Ayrıntı", "label": "Ayrıntı", "w": 210},
        {"k": "Kaynak", "label": "Kaynak · tarih", "w": 210},
        {"k": "Sahibi", "label": "Sahibi", "w": 120},
        {"k": "İlçe", "label": "İlçe", "w": 100},
        {"k": "Zaman", "label": "Zaman", "w": 100, "sk": True},
    ]
    satirlar = [{
        "id": k["id"], "yeni": bool(k.get("yeni")), "u": bh.guvenli_url(k.get("link")),
        "t": k["zaman"].timestamp() if k.get("zaman") else 0,
        "h": {
            "Kayıt": k["baslik"], "İşlem": k.get("islem") or "—", "Yaş / Kat": k.get("yas_kat") or "—",
            "Ayrıntı": k.get("alt") or "", "Kaynak": bg.kaynak_metni(k), "Sahibi": k.get("sahip") or "—",
            "İlçe": ", ".join(i for i in k.get("ilceler") or [] if i) or "—",
            "Zaman": bh.zaman_etiketi(k.get("zaman"), simdi),
        },
    } for k in kayitlar]
    sonuc = havuz_tablosu(
        kolonlar, satirlar, key=f"bg_tbl_{tur}_{secim}_{donem}", secimsiz=True,
        kart={"baslik": "Kayıt", "meta": ["Kaynak"], "alt": ["İlçe", "İşlem", "Ayrıntı", "Sahibi"]},
    ) or {}
    k = {x["id"]: x for x in kayitlar}.get(sonuc.get("aktif"))
    if tur == "zeta":
        st.caption("Zeta = portallarda yayındaki aktif ilanlar; dönem süzgeci uygulanmaz.")
    if not k:
        st.caption("Bir kayda dokunursan ayrıntısı altta açılır.")
        return
    ilce_etiket = "Aranan ilçeler" if k.get("tur") in ("talep", "yatirim_alici") else "İlçe"
    zaman = k.get("zaman")
    ek_alanlar = []
    if zaman:
        try:
            from zoneinfo import ZoneInfo
            ek_alanlar.append(("Tarih", zaman.astimezone(ZoneInfo("Europe/Istanbul")).strftime("%d.%m.%Y %H:%M")))
        except Exception:       # noqa: BLE001
            ek_alanlar.append(("Tarih", bh.tarih_metni(zaman)))
    ek_alanlar.append((ilce_etiket, ", ".join(i for i in k.get("ilceler") or [] if i)))
    with st.container(border=True):
        st.markdown(f"**{_html.escape(k['baslik'])}**", unsafe_allow_html=True)
        hucre = "".join(
            f"<div><div style='color:#64748b;font-size:11px;letter-spacing:.3px'>{_html.escape(str(e))}</div>"
            f"<div style='font-size:14px;margin-top:1px'>{_html.escape(str(d))}</div></div>"
            for e, d in ek_alanlar + list(k.get("alanlar") or []) if d
        )
        st.markdown(f"<div style='display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));"
                    f"gap:10px 18px;margin:6px 0 10px'>{hucre}</div>", unsafe_allow_html=True)
        if bh.guvenli_url(k.get("link")):
            st.link_button("İlana git ↗", bh.guvenli_url(k.get("link")))


# ══ AKIŞ ═════════════════════════════════════════════════════════════
kullanici = su_anki_danisman()
adlar = tuple(su_anki_danisman_varyantlari() or [kullanici])
bolgeler, bolge_hatalari = _bolgelerim(kullanici)
for h in bolge_hatalari:
    st.warning(f"Bölge listesi okunamadı: {h}")

c1, c2 = st.columns([5, 1])
with c1:
    donem = st.selectbox("Dönem (ekip kayıtları için)", list(bg.DONEMLER), index=1, key="bg_donem",
                         help="Kendi kayıtların bu seçimden etkilenmez; her zaman hepsi görünür.")
with c2:
    st.write("")
    if st.button("↻ Yenile", key="bg_yenile"):
        _ortak.clear()
        _kendi.clear()
        _pazar.clear()
        _yatirim.clear()
        st.rerun()

gun = bg.DONEMLER[donem]
ortak, hata1 = _ortak(gun)
kendi, hata2 = _kendi(adlar)
yatirim, hata3 = _yatirim(adlar)
kendi_liste = bg.kendi_kayitlar(ortak, kendi, yatirim, adlar)
ilceler, ek_ilceler = bg.kapsam_ilceleri(bolgeler, kendi_liste)
pazar, hata4 = _pazar(gun, tuple(ilceler))
for hatalar in (hata1, hata2, hata3, hata4):
    for kaynak, msj in hatalar.items():
        st.warning(f"{kaynak} okunamadı, ekrana dahil edilmedi: {msj}")

if not bolgeler:
    st.info("Uzmanlık bölgen henüz seçili değil. Uzmanlık Bölgelerim sayfasından en fazla 5 ilçe seçersen o "
            "ilçelerdeki ekip kayıtları da burada toplanır. Şimdilik kendi kayıtlarının bulunduğu ilçeler görünüyor.")
    if st.button("📍 Uzmanlık Bölgelerim'e git", key="bg_git_uzmanlik"):
        st.switch_page("pages/Danisman_UzmanlikBolgeleri.py")

liste, bilgi = bg.kayitlari_kur(ortak, pazar, kendi_liste, ilceler)
sayilar, dis = bg.ilce_sayilari(liste, ilceler)

if ilceler:
    _ozet_tablosu(sayilar, dis, ilceler, donem, ek_ilceler)

secenekler = [bg.TUM_BOLGELER] + list(ilceler) + ([bg.BOLGE_DISI] if any(dis.values()) else [])


def _etiket(i):
    if i == bg.TUM_BOLGELER:
        return i
    if i == bg.BOLGE_DISI:
        return f"{i}  ·  {dis['taleplerim']} talebim  ·  {dis['portfoylerim']} portföyüm  ·  {dis['yatirim']} yatırım"
    v = sayilar.get(i, {})
    t, z, f = v.get("talep", 0), v.get("zeta", 0), v.get("fsbo", 0)
    i = i + (" ◦" if i in ek_ilceler else "")
    return f"{i}  ·  {z} Zeta  ·  {t} talep" + (f"  ·  {f} FSBO" if f else "")


secim = st.selectbox("İlçe", secenekler, key="bg_ilce", format_func=_etiket)
gorunen = bg.ilceye_gore(liste, secim, ilceler)

baslik_metin = secim.strip("()") if secim in (bg.TUM_BOLGELER, bg.BOLGE_DISI) else secim
st.markdown(
    f"<div style='margin:6px 0 2px;font-size:19px;font-weight:700;color:#1c2b47'>{_html.escape(baslik_metin)}"
    f"<span style='font-size:12px;font-weight:500;color:#64748b;margin-left:8px'>ekip kayıtları: {_html.escape(donem.lower())}</span></div>",
    unsafe_allow_html=True,
)
if secim == bg.TUM_BOLGELER:
    bayat_n, bayat_yer = bg.bayat_sayisi(ortak, ilceler), "İlçelerindeki"
elif secim == bg.BOLGE_DISI:
    bayat_n, bayat_yer = 0, ""
else:
    bayat_n, bayat_yer = bg.bayat_sayisi(ortak, [secim]), f"{secim} ilçesindeki"
if bayat_n:
    st.caption(f"⚠ {bayat_yer} {bayat_n} Zeta ilanı son {bh.BAYAT_ESIK_SAAT // 24} gündür Revy senkronunda "
               "görünmüyor (yayından kalkmış olabilir); ekip listesinde gösterilmiyor, kendi ilanların uyarıyla görünür.")
with st.expander("ℹ️ Nasıl okunur?"):
    st.markdown(
        "- **Benim kayıtlarım** (Taleplerim, Portföylerim, Yatırım): yalnız sana ait, her ilçeden ve dönemden bağımsız. "
        "Portföylerim = Zeta portföyün + paylaşımların. Yatırım talepleri yalnız sana görünür.\n"
        f"- **Ekip**: Uzmanlık bölgelerin ve kendi kayıtlarının ilçeleri. Talep, Paylaşım, Startkey ve FSBO "
        f"**{donem.lower()}** içinde gelenleri gösterir; Zeta ofisin aktif stokudur (dönemden bağımsız). "
        "Senin kayıtların da ekip sayılarına dahildir.\n"
        "- Birden çok ilçeyi kapsayan kayıt her ilçede ayrı sayılır.\n"
        "- Kaynak sütunundaki tarih: mail/paylaşım/Zeta için kayıt tarihi; Startkey ve FSBO ilanı için sisteme "
        "ilk girdiği tarih.\n"
        "- Ekran salt-okunur: bildirim göndermez, hiçbir şeyi değiştirmez. Uzmanlık bölgelerini Uzmanlık Bölgelerim, "
        "bildirim ayarlarını FSBO İlanları ve Startkey İlanları sayfalarından yapabilirsin."
    )

sekmeler = st.tabs([f"{_KISA_SEKME[k]} ({len(gorunen[k])})" for k, *_ in bg.TURLER])
for sekme, (k, ad, _s, _r) in zip(sekmeler, bg.TURLER):
    with sekme:
        _sekme(k, ad, gorunen[k], secim, donem)

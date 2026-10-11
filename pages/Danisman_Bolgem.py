"""
pages/Danisman_Bolgem.py

"Bölgem" — danışmanın kendi bölgelerindeki (seçtiği en fazla 5 bölge (Uzmanlık Bölgelerim))
tüm kayıtların tek panelde toplandığı ekran (11.10.2026, Meltem: "tüm kayıtları bir arada göreceğimiz panel").
SALT OKUNUR; eşleşme/puanlama bilinçli olarak kapsam dışı. Bölge seçimi ve bildirim ayarları eski
sayfalarda (Uzmanlık Bölgelerim, FSBO İlanları, Startkey İlanları) aynen duruyor.

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
render_topbar("Bölgem", ikon="🧭", geri_hedefi="pages/Danisman_Secim.py")

MAX_BOLGE = 5
BOLGE_TABLOLARI = ("uzmanlik_bolgeleri", "fsbo_bolgeleri", "startkey_ilan_bolgeleri")
_RENK = {
    "indigo": ("#e0e7ff", "#4338ca"), "violet": ("#ede9fe", "#6d28d9"), "orange": ("#ffedd5", "#c2410c"),
    "sky": ("#e0f2fe", "#0369a1"), "teal": ("#ccfbf1", "#0f766e"), "emerald": ("#d1fae5", "#047857"),
}


@st.cache_data(ttl=120, show_spinner="Ekip verisi yükleniyor...")
def _ortak(gun):
    return bg.ortak_yukle(gun)


@st.cache_data(ttl=300, show_spinner="Bölgendeki ilanlar yükleniyor...")
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


def _chip(metin, renk):
    bg_, fg = _RENK.get(renk, ("#e2e8f0", "#334155"))
    return (f"<span style='display:inline-block;margin:6px 6px 0 0;padding:3px 10px;border-radius:6px;"
            f"font-size:12px;font-weight:600;background:{bg_};color:{fg};'>{_html.escape(metin)}</span>")


_KISA = {"taleplerim": "Taleplerim", "portfoylerim": "Portföylerim", "talep": "Alıcı talebi", "paylasim": "Paylaşım",
         "zeta": "Zeta", "startkey": "Startkey", "fsbo": "FSBO", "yatirim": "Yatırım"}


def _ozet_tablosu(sayilar, dis, ilceler, donem):
    """Bir bakışta özet. Sütunlar sekme sırasıyla; ekip sütunları kişinin kendi kayıtlarını da içerir."""
    satirlar = []
    for i in ilceler:
        v = sayilar[i]
        satirlar.append({"İlçe": i, **{_KISA[k]: v[k] for k, *_ in bg.TURLER}})
    satirlar.sort(key=lambda r: (-r["Alıcı talebi"], -r["Zeta"], bg.tr_sira(r["İlçe"])))
    if any(dis.values()):
        satirlar.append({"İlçe": bg.BOLGE_DISI, **{_KISA[k]: (dis[k] if k in ("taleplerim", "portfoylerim", "yatirim") else None)
                                                  for k, *_ in bg.TURLER}})
    cfg = {"İlçe": st.column_config.TextColumn("İlçe", width="small")}
    for k, *_ in bg.TURLER:
        ad = _KISA[k]
        if k in ("talep", "paylasim", "zeta", "startkey", "fsbo"):
            tavan = max([(r.get(ad) or 0) for r in satirlar] + [1])
            cfg[ad] = st.column_config.ProgressColumn(ad, format="%d", min_value=0, max_value=tavan, width="small")
        else:
            cfg[ad] = st.column_config.NumberColumn(ad, format="%d", width="small")
    with st.expander(f"İlçe özeti — {donem.lower()} ({len(ilceler)} ilçe)", expanded=True):
        st.dataframe(satirlar, hide_index=True, use_container_width=True, column_config=cfg,
                     height=min(38 + 35 * len(satirlar), 380))
        st.caption(
            f"Taleplerim ve Portföylerim yalnız sana ait kayıtlardır (bölge dışındakiler dahil; Portföylerim = Zeta "
            f"portföyün + paylaşımların). Alıcı talebi, Paylaşım, Startkey ve FSBO {donem.lower()} içinde gelenleri sayar "
            "ve senin kayıtlarını da içerir; Zeta ofisin aktif stokudur (dönemden bağımsız); Yatırım yalnız sana "
            "atananlardır (dönemden bağımsız). Birden çok ilçeyi kapsayan kayıt her ilçede sayılır."
        )


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
        {"k": "Kaynak", "label": "Kaynak", "w": 140},
        {"k": "Sahibi", "label": "Sahibi", "w": 120},
        {"k": "İlçe", "label": "İlçe", "w": 100},
        {"k": "Zaman", "label": "Zaman", "w": 100, "sk": True},
    ]
    satirlar = [{
        "id": k["id"], "yeni": bool(k.get("yeni")), "u": bh.guvenli_url(k.get("link")),
        "t": k["zaman"].timestamp() if k.get("zaman") else 0,
        "h": {
            "Kayıt": k["baslik"], "İşlem": k.get("islem") or "—", "Yaş / Kat": k.get("yas_kat") or "—",
            "Ayrıntı": k.get("alt") or "", "Kaynak": k.get("kaynak") or "—", "Sahibi": k.get("sahip") or "—",
            "İlçe": ", ".join(i for i in k.get("ilceler") or [] if i) or "—",
            "Zaman": bh.zaman_etiketi(k.get("zaman"), simdi),
        },
    } for k in kayitlar]
    sonuc = havuz_tablosu(kolonlar, satirlar, key=f"bg_tbl_{tur}_{secim}_{donem}", secimsiz=True) or {}
    k = {x["id"]: x for x in kayitlar}.get(sonuc.get("aktif"))
    if tur == "zeta":
        st.caption("Zeta portföyü = portallarda yayındaki aktif ilanlar; dönem süzgeci uygulanmaz.")
    if not k:
        st.caption("Bir satıra tıklarsan ayrıntısı açılır.")
        return
    with st.container(border=True):
        st.markdown(f"**{_html.escape(k['baslik'])}**", unsafe_allow_html=True)
        hucre = "".join(
            f"<div><div style='color:#64748b;font-size:11px;letter-spacing:.3px'>{_html.escape(str(e))}</div>"
            f"<div style='font-size:14px;margin-top:1px'>{_html.escape(str(d))}</div></div>"
            for e, d in (k.get("alanlar") or []) if d
        )
        st.markdown(f"<div style='display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));"
                    f"gap:10px 18px;margin:6px 0 10px'>{hucre}</div>", unsafe_allow_html=True)
        if bh.guvenli_url(k.get("link")):
            st.link_button("İlana git ↗", bh.guvenli_url(k.get("link")))


# ══ AKIŞ ═════════════════════════════════════════════════════════════
kullanici = su_anki_danisman()
adlar = tuple(su_anki_danisman_varyantlari() or [kullanici])
ilceler, bolge_hatalari = _bolgelerim(kullanici)
for h in bolge_hatalari:
    st.warning(f"Bölge listesi okunamadı: {h}")

c1, c2 = st.columns([5, 1])
with c1:
    donem = st.selectbox("Dönem", list(bg.DONEMLER), index=1, key="bg_donem")
with c2:
    st.write("")
    if st.button("↻ Yenile", key="bg_yenile"):
        _ortak.clear()
        _pazar.clear()
        _yatirim.clear()
        st.rerun()

if not ilceler:
    st.info("Henüz bölge seçmedin. Uzmanlık Bölgelerim sayfasından "
            "en fazla 5 ilçe seçince o ilçelerdeki tüm kayıtlar burada toplanır. Aşağıda yalnız kendi kayıtların görünür.")
    if st.button("📍 Uzmanlık Bölgelerim'e git", key="bg_git_uzmanlik"):
        st.switch_page("pages/Danisman_UzmanlikBolgeleri.py")

gun = bg.DONEMLER[donem]
ortak, hata1 = _ortak(gun)
pazar, hata2 = _pazar(gun, tuple(ilceler))
yatirim, hata3 = _yatirim(adlar)
for hatalar in (hata1, hata2, hata3):
    for kaynak, msj in hatalar.items():
        st.warning(f"{kaynak} okunamadı, ekrana dahil edilmedi: {msj}")

liste, bilgi = bg.kayitlari_kur(ortak, pazar, yatirim, ilceler, adlar)
sayilar, dis = bg.ilce_sayilari(liste, ilceler)

if ilceler:
    _ozet_tablosu(sayilar, dis, ilceler, donem)

secenekler = [bg.TUM_BOLGELER] + list(ilceler) + ([bg.BOLGE_DISI] if any(dis.values()) else [])


def _etiket(i):
    if i == bg.TUM_BOLGELER:
        return i
    if i == bg.BOLGE_DISI:
        return f"{i}  ·  {dis['taleplerim']} talebim  ·  {dis['portfoylerim']} portföyüm"
    v = sayilar.get(i, {})
    t, z, f = v.get("talep", 0), v.get("zeta", 0), v.get("fsbo", 0)
    return f"{i}  ·  {z} portföy  ·  {t} talep" + (f"  ·  {f} FSBO" if f else "")


secim = st.selectbox("İlçe", secenekler, key="bg_ilce", format_func=_etiket)
gorunen = bg.ilceye_gore(liste, secim, ilceler)

st.markdown(
    "<div style='background:#1C2B47;color:#fff;border-radius:14px;padding:16px 18px;margin:8px 0'>"
    f"<div style='font-size:20px;font-weight:700'>{_html.escape(secim.strip('()') if secim in (bg.TUM_BOLGELER, bg.BOLGE_DISI) else secim)}"
    f"<span style='font-size:12px;font-weight:500;opacity:.7;margin-left:10px'>{_html.escape(donem.lower())}</span></div>"
    f"<div>{''.join(_chip(f'{ad} {len(gorunen[k])}', renk) for k, ad, _s, renk in bg.TURLER)}</div></div>",
    unsafe_allow_html=True,
)
if bilgi["bayat_bolgede"]:
    st.caption(f"Bölgelerindeki {bilgi['bayat_bolgede']} Zeta ilanı, son {bh.BAYAT_ESIK_SAAT // 24} gündür Revy "
               "senkronunda görünmediği için (yayından kalkmış olabilir) ekip listesinde gösterilmiyor; "
               "kendi ilanların uyarı işaretiyle görünür.")
st.caption("Salt-okunur: bu ekran bildirim göndermez, hiçbir şeyi değiştirmez. Bölge seçimini ve bildirim ayarlarını "
           "Uzmanlık Bölgelerim, FSBO İlanları ve Startkey İlanları sayfalarından yapabilirsin.")

sekmeler = st.tabs([f"{ad} ({len(gorunen[k])})" for k, ad, _s, _r in bg.TURLER])
for sekme, (k, ad, _s, _r) in zip(sekmeler, bg.TURLER):
    with sekme:
        _sekme(k, ad, gorunen[k], secim, donem)

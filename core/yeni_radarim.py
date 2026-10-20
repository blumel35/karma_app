# core/yeni_radarim.py
# -*- coding: utf-8 -*-
"""
YENİ Radarım — FAZ 1: "Portföylerim" akışı (mockup v13).

Yalnızca yeni ana sayfanın (core/yeni_ana_sayfa.py) "Radarım" sayfasında,
özellik anahtarı arkasında çalışır. Mevcut Radarım (pages/Danisman_Bolgem.py,
core/bolgem.py) ve danışmanların ekranı DEĞİŞMEDİ. SALT OKUNUR, bildirim yok.

Akış A:  Portföylerim  →  [ Alıcı talepleri | Benzer Startkey portföyleri ]  →  Eşleşmeler
Akış B:  Taleplerim  →  [ Zeta portföyleri | Startkey portföyleri | Portföy paylaşımları ]  →  Eşleşmeler
  (B'deki portföy kutuları, taleplerimden en az biriyle OLASI eşiğini (%40) geçen portföyleri sayar;
   Eşleşmeler = güçlü (%70+) talep→portföy çiftleri. Bir talep birden çok ilçe istediyse her birinde sayılır.)

Yeni puan/eşleşme kuralı YOK:
  - Veri: core.eslesme_havuzu.veri_yukle() (Bölge Havuzu "Eşleşme" sekmesiyle aynı).
  - Eşleşme: core.eslesme_havuzu.portfoyden_taleplere() (ilçe 40 / bütçe 35 /
    oda 15 / kriter 10; işlem-mülk tipi uyumsuzsa eleme; eşik güçlü 70, olası 40).
  - Talep/paylaşım ömrü: es.omre_gore (kiralık 14 / satılık 45 gün), Zeta/Startkey aktif stok.
  - Bayat (Revy'de görünmeyen) Zeta ilanları veri_yukle'de zaten dışarıda.
Bölge kapsamı, mevcut Radarım ile aynı karar (12.10.2026): Uzmanlık Bölgelerim (en fazla 5)
+ kendi kayıtlarının bulunduğu ilçeler.

"Benzer Startkey portföyü" (bu sayfada tanımlı, motorun yardımcılarıyla): aynı ilçe,
aynı işlem ve mülk tipi, fiyat ±%30 içinde, oda sayısı en fazla 1 fark. Fiyatı okunamayan
ilan "benzer" sayılmaz (iddiayı sağlam tutmak için).
"""
import html as _html
from datetime import datetime, timezone

import streamlit as st

from core import bolge_havuzu as bh
from core import bolgem as bg
from core import eslesme_havuzu as es
from core.eslesme_kart_bilesen import eslesme_kartlari
from core.havuz_tablo_bilesen import havuz_tablosu
from core.bolge_secici import bolgelerini_cek
from core.danisman_ortak import su_anki_danisman, su_anki_danisman_varyantlari
from core.match_engine import (
    _mulk_normalize, _islem_normalize, _belirsiz_mi, _sayi_ayikla, _oda_secenekleri_cikar,
)

MAX_BOLGE = 5
BOLGE_TABLOLARI = ("uzmanlik_bolgeleri", "fsbo_bolgeleri", "startkey_ilan_bolgeleri")
TUM = "Tüm uzmanlık bölgelerim"
BENZER_FIYAT_ORAN = 0.30
GRUP_SAYFA = 15


# ── VERİ ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Radarım verisi yükleniyor...")
def _veri():
    return es.veri_yukle()


@st.cache_data(ttl=60, show_spinner=False)
def _bolgeler(kullanici):
    """Danışmanın en fazla 5 bölgesi: Uzmanlık Bölgelerim; hiç yoksa FSBO, sonra Startkey listesi
    (core/bolgem'in mevcut Radarım'daki kuralıyla aynı)."""
    for tablo in BOLGE_TABLOLARI:
        sonuc, gorulen = [], set()
        try:
            for r in bolgelerini_cek(tablo, kullanici):
                i = (r.get("ilce") or "").strip()
                if i and bh.tr_kucuk(i) not in gorulen:
                    gorulen.add(bh.tr_kucuk(i))
                    sonuc.append(i)
        except Exception:      # noqa: BLE001
            continue
        if sonuc:
            return sonuc[:MAX_BOLGE]
    return []


def _fiyat(motor):
    return _sayi_ayikla(motor.get("fiyat"))


def _benzer_mi(p, s):
    """p: benim portföyümün motor sözlüğü, s: Startkey ilanının motor sözlüğü."""
    if (p.get("ilce") or "").strip().lower() != (s.get("ilce") or "").strip().lower():
        return False
    a, b = _islem_normalize(p.get("islem_tipi")), _islem_normalize(s.get("islem_tipi"))
    if not _belirsiz_mi(a) and not _belirsiz_mi(b) and a != b:
        return False
    a, b = _mulk_normalize(p.get("mulk_tipi")), _mulk_normalize(s.get("mulk_tipi"))
    if not _belirsiz_mi(a) and not _belirsiz_mi(b) and a != b:
        return False
    fp, fs = _fiyat(p), _fiyat(s)
    if not fp or not fs or abs(fs - fp) > fp * BENZER_FIYAT_ORAN:
        return False
    op, os_ = _oda_secenekleri_cikar(p.get("oda_sayisi_m2")), _oda_secenekleri_cikar(s.get("oda_sayisi_m2"))
    if op and os_ and min(abs(x - y) for x in op for y in os_) > 1:
        return False
    return True


@st.cache_data(ttl=120, show_spinner="Eşleşmeler hesaplanıyor...")
def _hesapla(adlar, bolgeler, secim):
    """Akış A'nın tüm katmanları. adlar/bolgeler tuple, secim: None (tümü) ya da bir ilçe adı."""
    veri, hatalar, bilgi = _veri()
    simdi = datetime.now(timezone.utc)
    talepler = es.omre_gore(veri["talep"], simdi)
    paylasim = es.omre_gore(veri["paylasim"], simdi)
    benim_p = [k for k in veri["zeta"] + paylasim if bg.benim_mi(k, adlar)]
    benim_t = [k for k in talepler if bg.benim_mi(k, adlar)]
    ilceler, ek = bg.kapsam_ilceleri(list(bolgeler), {"p": benim_p, "t": benim_t})
    kume = bg._ilce_kumesi(ilceler if secim is None else [secim])

    port = [k for k in benim_p if bg.bolgede_mi(k, kume)]
    bolge = [k for k in talepler if bg.bolgede_mi(k, kume)]

    # Benzer Startkey: benim portföylerimi ilçeye göre indeksle
    idx = {}
    for p in port:
        idx.setdefault((p["motor"].get("ilce") or "").strip().lower(), []).append(p)
    benz = []
    for s in veri["startkey"]:
        adaylar = idx.get((s["motor"].get("ilce") or "").strip().lower())
        if not adaylar:
            continue
        esl = [p for p in adaylar if _benzer_mi(p["motor"], s["motor"])]
        if esl:
            benz.append((s, esl))

    ciftler = es.portfoyden_taleplere(port, bolge, ust_n=5, min_skor=es.OLASI_ESIK)

    # ── Akış B: Taleplerim → uygun portföyler (kaynağa göre) → Eşleşmeler ──
    tal = [k for k in benim_t if bg.bolgede_mi(k, kume)]
    kaynaklar_b = {"zp": veri["zeta"], "sk": veri["startkey"], "pay": paylasim}
    uygun, ciftler_b = {}, []
    for ad, adaylar in kaynaklar_b.items():
        cf = es.talepten_portfoylere(tal, adaylar, ust_n=5, min_skor=es.OLASI_ESIK) if tal else []
        ciftler_b.extend(cf)
        gor, sira = {}, []
        for c in cf:
            kid = c["aday"]["kid"]
            if kid not in gor:
                gor[kid] = (c["aday"], [])
                sira.append(kid)
            gor[kid][1].append((c["kaynak"], c["skor"]))
        uygun[ad] = [(gor[k][0], sorted(gor[k][1], key=lambda x: -x[1])) for k in sira]
    return {
        "ilceler": ilceler, "ek": ek, "port": port, "bolge": bolge, "benz": benz, "ciftler": ciftler,
        "tal": tal, "uygun": uygun, "ciftler_b": ciftler_b,
        "hatalar": hatalar, "bayat": (bilgi or {}).get("bayat_zeta", 0),
    }


# ── GÖSTERİM YARDIMCILARI ───────────────────────────────────────────────
def _dagilim(kayitlar, kume_ilce=None):
    """{ilçe: adet} — bir kayıt birden çok ilçedeyse her birinde sayılır."""
    d = {}
    for k in kayitlar:
        for i in {i for i in k.get("ilceler") or [] if i}:
            if kume_ilce is None or bh.tr_kucuk(i) in kume_ilce:
                d[i] = d.get(i, 0) + 1
    return d


def _kutu_html(simge, baslik, sayi, dagilim, ilk=False):
    sirali = sorted(dagilim.items(), key=lambda x: (-x[1], bg.tr_sira(x[0])))
    gor, kalan = sirali[:4], len(sirali) - 4
    satirlar = "".join(f"<div><b>{n}</b> {_html.escape(i)}</div>" for i, n in gor)
    if kalan > 0:
        satirlar += f"<div class='yr-ek'>+{kalan} ilçe</div>"
    if not satirlar:
        satirlar = "<div class='yr-bos'>—</div>"
    return (
        f"<div class='yr-kutu{' yr-ilk' if ilk else ''}'>"
        f"<div class='yr-sol'><div class='yr-bas'>{simge}{_html.escape(baslik)}</div><div class='yr-sayi'>{sayi}</div></div>"
        f"<div class='yr-sag'>{satirlar}</div></div>"
    )


_CSS = """
<style>
div[class*="st-key-yr_akis_"] > div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; }
div[class*="st-key-yr_akis_a"] { border-top: 5px solid #1b2742; }
div[class*="st-key-yr_akis_b"] { border-top: 5px solid #2e7d6f; }
.yr-kutu { display:flex; justify-content:space-between; gap:10px; align-items:flex-start; }
.yr-sol { min-width:0; }
.yr-bas { font-size:12.5px; font-weight:700; color:#1b2742; line-height:1.25; }
.yr-sayi { font-size:24px; font-weight:800; color:#1b2742; line-height:1.15; margin-top:2px; }
.yr-ilk .yr-bas { font-size:15px; } .yr-ilk .yr-sayi { font-size:34px; }
.yr-sag { font-size:11.5px; color:#5b6478; text-align:left; line-height:1.45; border-left:1px solid #e6dfd0; padding-left:10px; min-width:84px; }
.yr-sag b { color:#1b2742; } .yr-ek, .yr-bos { color:#9a9488; }
div[class*="st-key-yr_box_"] div[data-testid="stVerticalBlockBorderWrapper"] { border:1px solid #e6dfd0 !important; border-radius:12px; padding:10px 12px !important; background:#fff; }
div[class*="st-key-yr_box_es_"] div[data-testid="stVerticalBlockBorderWrapper"] { background:#fbf4e1; }
div[class*="st-key-yr_box_"][class*="_secili"] div[data-testid="stVerticalBlockBorderWrapper"] { border:2px solid #b08a2e !important; }
div[class*="st-key-yr_box_"] [data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; align-items:flex-start; }
div[class*="st-key-yr_box_"] [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] { min-width:0 !important; }
div[class*="st-key-yr_ok_"] button {
    width:32px !important; height:32px !important; min-height:32px !important; border-radius:50% !important;
    background:#f2ede0 !important; border:none !important; color:#b08a2e !important; padding:0 !important; font-weight:700 !important;
}
div[class*="st-key-yr_ok_"] button:hover { background:#e7dfc8 !important; }
.yr-ok-asagi { text-align:center; color:#b08a2e; font-weight:700; line-height:1; margin:2px 0; }
div[class*="st-key-yr_detay"] { border-top:4px solid #b08a2e; }
</style>
"""


def _acik():
    return list(st.session_state.get("yr_acik") or [])


def _sec(k):
    """Kutuya basınca listesi kutunun altında açılır; aynı kutuya tekrar basınca kapanır.
    Kutular birbirinden bağımsızdır: birini açmak diğerlerini kapatmaz."""
    acik = _acik()
    if k in acik:
        acik.remove(k)
    else:
        acik.append(k)
    st.session_state["yr_acik"] = acik


def _kapat(k):
    st.session_state["yr_acik"] = [x for x in _acik() if x != k]


def _kutu(anahtar, simge, baslik, sayi, dagilim, ilk=False):
    secili = anahtar in _acik()
    with st.container(border=True, key=f"yr_box_{anahtar}_{'secili' if secili else 'degil'}"):
        c1, c2 = st.columns([7, 1])
        with c1:
            st.markdown(_kutu_html(simge, baslik, sayi, dagilim, ilk), unsafe_allow_html=True)
        with c2:
            st.button(
                "▴" if secili else "▾", key=f"yr_ok_{anahtar}", on_click=_sec, args=(anahtar,),
                help=f"{baslik} listesini {'kapat' if secili else 'aç'}",
            )


def _tablo(kayitlar, anahtar):
    if not kayitlar:
        st.info("Bu kapsamda kayıt yok.")
        return
    simdi = datetime.now(timezone.utc)
    kolonlar = [
        {"k": "Kayıt", "label": "Kayıt", "w": 230},
        {"k": "İlan", "label": "İlan", "w": 70, "link": True},
        {"k": "İşlem", "label": "İşlem", "w": 90},
        {"k": "Fiyat", "label": "Fiyat / Bütçe", "w": 120},
        {"k": "Ayrıntı", "label": "Ayrıntı", "w": 210},
        {"k": "Kaynak", "label": "Kaynak · tarih", "w": 190},
        {"k": "Sahibi", "label": "Sahibi", "w": 120},
        {"k": "İlçe", "label": "İlçe", "w": 100},
        {"k": "Zaman", "label": "Zaman", "w": 100, "sk": True},
    ]
    satirlar = [{
        "id": k["kid"], "yeni": False, "u": bh.guvenli_url(k.get("link")),
        "t": k["zaman"].timestamp() if k.get("zaman") else 0,
        "h": {
            "Kayıt": k["baslik"], "İşlem": k.get("islem") or "—", "Fiyat": k.get("fiyat") or "—",
            "Ayrıntı": k.get("alt") or "",
            "Kaynak": f"{k.get('kaynak') or '—'} · {bh.tarih_metni(k.get('zaman'))}" if k.get("zaman") else (k.get("kaynak") or "—"),
            "Sahibi": k.get("sahip") or "—",
            "İlçe": ", ".join(i for i in k.get("ilceler") or [] if i) or "—",
            "Zaman": bh.zaman_etiketi(k.get("zaman"), simdi),
        },
    } for k in kayitlar]
    havuz_tablosu(
        kolonlar, satirlar, key=f"yr_tbl_{anahtar}", secimsiz=True,
        kart={"baslik": "Kayıt", "meta": ["Kaynak"], "alt": ["İlçe", "İşlem", "Fiyat", "Sahibi"]},
    )


def _eslesme_detay(ciftler, anahtar, sec):
    duzey = st.radio("Göster", ["Sadece güçlü (%70+)", "Güçlü + olası (%40+)"], key=f"yr_duzey_{sec}", horizontal=True)
    gorunen = [c for c in ciftler if c["guclu"]] if duzey.startswith("Sadece") else ciftler
    if not gorunen:
        st.info("Bu filtrelerde eşleşme yok.")
        return
    gruplar = es.gruplari_kur(gorunen)
    n = st.session_state.get(f"yr_n_{anahtar}", GRUP_SAYFA)
    secilen = gruplar[:n]
    imza = "|".join([str(len(gruplar)), str(n), duzey, anahtar] + [g["kaynak"]["baslik"][:20] + str(g["en_iyi"]) for g in secilen[:5]])
    eslesme_kartlari(
        [{"kaynak": g["kaynak"], "adaylar": g["adaylar"]} for g in secilen],
        es.kart_css(), imza, key=f"yr_esk_{anahtar}",
    )
    st.caption(f"{len(secilen)} / {len(gruplar)} portföy gösteriliyor")
    if len(gruplar) > n and st.button(f"Daha fazla göster (+{GRUP_SAYFA})", key=f"yr_daha_{sec}"):
        st.session_state[f"yr_n_{anahtar}"] = n + GRUP_SAYFA
        st.rerun()


def _benzer_tablo(benz):
    """Benzer Startkey ilanları, hangi portföyüme benzedikleri ayrıntıda."""
    kayitlar = []
    for s, esl in benz:
        k = dict(s)
        k["alt"] = ("Benzediği portföyün: " + " · ".join(p["baslik"][:40] for p in esl[:2])
                    + (f" (+{len(esl) - 2})" if len(esl) > 2 else ""))
        kayitlar.append(k)
    return kayitlar


def _uygun_tablo(uygun):
    """Taleplerime uyan portföyler; hangi talebime kaç puanla uyduğu ayrıntıda."""
    kayitlar = []
    for p, eslesenler in uygun:
        k = dict(p)
        k["alt"] = ("Uyduğu talebin: " + " · ".join(f"{t['baslik'][:36]} (%{sk})" for t, sk in eslesenler[:2])
                    + (f" (+{len(eslesenler) - 2})" if len(eslesenler) > 2 else ""))
        kayitlar.append(k)
    return kayitlar


def _detay(sec, baslik, h, secim_ad, kullanici):
    with st.container(border=True, key=f"yr_detay_{sec}"):
        t1, t2 = st.columns([6, 2])
        with t1:
            st.markdown(f"**{_html.escape(baslik)} · {_html.escape(secim_ad)}**")
        with t2:
            st.button("✕ Kapat", key=f"yr_kapat_{sec}", on_click=_kapat, args=(sec,))
        anahtar = f"{kullanici}_{sec}_{secim_ad}"
        if sec == "port":
            _tablo(h["port"], anahtar)
        elif sec == "bolge":
            _tablo(h["bolge"], anahtar)
        elif sec == "benz":
            _tablo(_benzer_tablo(h["benz"]), anahtar)
        elif sec == "es":
            _eslesme_detay(h["ciftler"], anahtar, sec)
        elif sec == "tal":
            _tablo(h["tal"], anahtar)
        elif sec in ("zp", "sk", "pay"):
            _tablo(_uygun_tablo(h["uygun"][sec]), anahtar)
        else:
            _eslesme_detay(h["ciftler_b"], anahtar, sec)


# ── GİRİŞ NOKTASI ───────────────────────────────────────────────────────
def render_yeni_radarim():
    st.markdown(_CSS, unsafe_allow_html=True)
    kullanici = su_anki_danisman()
    adlar = tuple(su_anki_danisman_varyantlari() or [kullanici])

    # Yönetici: başka bir danışmanın Radarım'ını görüntüleyebilir (mevcut Radarım ile aynı kural).
    if str(st.session_state.get("user_name") or "").strip().lower() in {"meltem bulu"}:
        try:
            from core.personel_manager import load_personel_listesi
            _df = load_personel_listesi()
            kisiler = sorted({str(a).strip() for a in _df["ad_soyad"].dropna() if str(a).strip()}, key=bg.tr_sira)
        except Exception:      # noqa: BLE001
            kisiler = []
        if kisiler:
            secilen_kisi = st.selectbox("Danışman (yönetici görünümü)", ["Kendim"] + kisiler, key="yr_kisi")
            if secilen_kisi != "Kendim":
                kullanici, adlar = secilen_kisi, (secilen_kisi,)
                st.info(f"👁 {secilen_kisi} adına görüntülüyorsun.")

    bolgeler = tuple(_bolgeler(kullanici))
    ilk = _hesapla(adlar, bolgeler, None)
    ilceler = ilk["ilceler"]

    c1, c2 = st.columns([5, 1])
    with c1:
        secenek = [TUM] + list(ilceler)
        secim_ad = st.selectbox(
            "📍 Uzmanlık bölgesi seç", secenek, key=f"yr_ilce_{kullanici}",
            format_func=lambda i: i + (" ◦" if i in ilk["ek"] else ""),
        )
    with c2:
        st.write("")
        if st.button("↻ Yenile", key="yr_yenile"):
            _veri.clear()
            _hesapla.clear()
            st.rerun()
    if ilk["ek"]:
        st.caption("◦ Uzmanlık bölgen değil; kendi kaydın olduğu için eklendi.")
    if not bolgeler:
        st.info("Uzmanlık bölgen seçili değil. Uzmanlık Bölgelerim'den en fazla 5 ilçe seçersen o ilçelerdeki "
                "ekip kayıtları da burada toplanır.")
    for kaynak, msj in ilk["hatalar"].items():
        st.warning(f"{kaynak} okunamadı, dahil edilmedi: {msj}")

    secim = None if secim_ad == TUM else secim_ad
    h = _hesapla(adlar, bolgeler, secim)
    guclu = [c for c in h["ciftler"] if c["guclu"]]
    benz_kayit = [s for s, _ in h["benz"]]
    kume = None if secim is None else {bh.tr_kucuk(secim)}

    # ── Akış A ── (liste, basılan kutunun hemen altında açılır)
    adlar_ = {"port": "Portföylerim", "bolge": "Alıcı talepleri", "benz": "Benzer Startkey portföyleri", "es": "Eşleşmeler",
              "tal": "Taleplerim", "zp": "Zeta portföyleri", "sk": "Startkey portföyleri",
              "pay": "Portföy paylaşımları", "es_b": "Eşleşmeler (taleplerim)"}
    acik = [k for k in _acik() if k in adlar_]

    def _altinda(anahtar):
        if anahtar in acik:
            _detay(anahtar, adlar_[anahtar], h, secim_ad, kullanici)

    with st.container(border=True, key="yr_akis_a"):
        _kutu("port", "🏠 ", adlar_["port"], len(h["port"]), _dagilim(h["port"], kume), ilk=True)
        _altinda("port")
        st.markdown("<div class='yr-ok-asagi'>↓</div>", unsafe_allow_html=True)
        _kutu("bolge", "", adlar_["bolge"], len(h["bolge"]), _dagilim(h["bolge"], kume))
        _altinda("bolge")
        _kutu("benz", "", adlar_["benz"], len(benz_kayit), _dagilim(benz_kayit, kume))
        _altinda("benz")
        st.markdown("<div class='yr-ok-asagi'>↓</div>", unsafe_allow_html=True)
        _kutu("es", "", adlar_["es"], len(guclu), _dagilim([c["kaynak"] for c in guclu], kume))
        _altinda("es")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    guclu_b = [c for c in h["ciftler_b"] if c["guclu"]]
    with st.container(border=True, key="yr_akis_b"):
        _kutu("tal", "📋 ", adlar_["tal"], len(h["tal"]), _dagilim(h["tal"], kume), ilk=True)
        _altinda("tal")
        st.markdown("<div class='yr-ok-asagi'>↓</div>", unsafe_allow_html=True)
        for ad in ("zp", "sk", "pay"):
            uyg = [p for p, _ in h["uygun"][ad]]
            _kutu(ad, "", adlar_[ad], len(uyg), _dagilim(uyg, kume))
            _altinda(ad)
        st.markdown("<div class='yr-ok-asagi'>↓</div>", unsafe_allow_html=True)
        _kutu("es_b", "", "Eşleşmeler", len(guclu_b), _dagilim([c["kaynak"] for c in guclu_b], kume))
        _altinda("es_b")
    st.caption("Taleplerim akışında portföy kutuları, taleplerinden en az biriyle %40+ uyuşan portföyleri sayar; "
               "Eşleşmeler yalnızca güçlü (%70+) çiftlerdir.")
    if not acik:
        st.caption("Kutulardaki ▾ düğmesine basınca ilgili liste kutunun altında açılır; istediğin kadarını aynı anda açık tutabilirsin.")
    if h["bayat"]:
        st.caption(f"⚠ {h['bayat']} Zeta ilanı son günlerde Revy'de görünmediği için (yayından kalkmış olabilir) "
                   "eşleştirmeye alınmadı.")
